"""NoSQL Recommendation Engine with Redis caching layer."""
import json
import time
from collections import Counter
import redis
import pymongo
from neo4j import GraphDatabase
from cassandra.cluster import Cluster
import config

CACHE_TTL = 300  # 5 minutes


class RecommendationEngine:
    def __init__(self):
        self.redis = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
        self.mongo = pymongo.MongoClient(config.MONGO_URI)["social"]
        self.neo4j = GraphDatabase.driver(config.NEO4J_URI, auth=config.NEO4J_AUTH)
        self.cassandra = Cluster(config.CASSANDRA_HOSTS).connect("social")

    def get_friend_recommendations(self, user_id=1):
        cache_key = f"rec:friends:{user_id}"
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached), "cache HIT"

        # Graph traversal in Neo4j
        query = """
        MATCH (me:User {id:$id})-[:FOLLOWS]->(f:User)-[:FOLLOWS]->(s:User)
        WHERE s.id <> $id AND NOT (me)-[:FOLLOWS]->(s)
        RETURN s.id AS suggested_user, count(DISTINCT f) AS mutual_friends
        ORDER BY mutual_friends DESC LIMIT 5
        """
        with self.neo4j.session() as session:
            result = session.run(query, id=user_id)
            recs = [{"suggested_user": row["suggested_user"], "mutual_friends": row["mutual_friends"]} for row in result]

        self.redis.set(cache_key, json.dumps(recs), ex=CACHE_TTL)
        return recs, "cache MISS"

    def get_content_recommendations(self, user_id=1):
        cache_key = f"rec:content:{user_id}"
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached), "cache HIT"

        # 1. Fetch user activity from Cassandra (column family)
        rows = self.cassandra.execute("SELECT topic FROM activity_by_user WHERE user_id = %s LIMIT 30", (user_id,))
        topics = [r.topic for r in rows if r.topic]
        top_topics = [t for t, _ in Counter(topics).most_common(2)] if topics else ["tech", "music"]

        # 2. Query MongoDB for top posts in those topics (document store)
        pipeline = [
            {"$match": {"topic": {"$in": top_topics}, "author": {"$ne": user_id}}},
            {"$sort": {"likes": -1}},
            {"$limit": 5},
            {"$project": {"_id": 1, "topic": 1, "likes": 1, "text": 1}}
        ]
        recs = list(self.mongo.posts.aggregate(pipeline))
        for r in recs:
            r["_id"] = int(r["_id"])

        self.redis.set(cache_key, json.dumps(recs), ex=CACHE_TTL)
        return recs, "cache MISS"

    def close(self):
        self.neo4j.close()
        self.cassandra.shutdown()


def run_demo(engine, user_id=1, run_label="Run 1"):
    print(f"\n==================== {run_label} ====================")
    t0 = time.perf_counter()

    # Friends recommendation
    t_f = time.perf_counter()
    friends, f_cache = engine.get_friend_recommendations(user_id)
    f_time = (time.perf_counter() - t_f) * 1000
    print(f"[Friends Rec]   [{f_cache}] ({f_time:.2f} ms)")
    for f in friends:
        print(f"   -> User {f['suggested_user']}: {f['mutual_friends']} mutual friends")

    # Content recommendation
    t_c = time.perf_counter()
    content, c_cache = engine.get_content_recommendations(user_id)
    c_time = (time.perf_counter() - t_c) * 1000
    print(f"[Content Rec]   [{c_cache}] ({c_time:.2f} ms)")
    for c in content:
        print(f"   -> Post {c['_id']} [{c['topic']}]: {c['likes']} likes | \"{c.get('text', '')[:40]}...\"")

    total_time = (time.perf_counter() - t0) * 1000
    print(f"Total response time: {total_time:.2f} ms")


if __name__ == "__main__":
    engine = RecommendationEngine()
    # Invalidate cache for clean cold run
    engine.redis.delete("rec:friends:1", "rec:content:1")

    print("Running Recommendation Engine for User 1...")
    run_demo(engine, user_id=1, run_label="Run 1 (Cold cache)")
    run_demo(engine, user_id=1, run_label="Run 2 (Cached)")

    engine.close()
