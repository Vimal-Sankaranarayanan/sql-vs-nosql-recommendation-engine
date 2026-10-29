"""Generate and load synthetic social network data into MongoDB, Neo4j, and Cassandra."""
import random
from datetime import datetime, timedelta
import pymongo
from neo4j import GraphDatabase
from cassandra.cluster import Cluster
import config

TOPICS = ["tech", "music", "travel", "sports", "food", "gaming", "art", "science", "movies", "fashion"]
CITIES = ["New York", "San Francisco", "London", "Berlin", "Tokyo", "Paris", "Toronto", "Sydney", "Austin", "Seattle"]
ACTIONS = ["view", "like", "share", "comment"]
FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Ethan", "Fiona", "George", "Hannah", "Ian", "Julia",
               "Kevin", "Laura", "Mike", "Nina", "Oscar", "Paula", "Quinn", "Rachel", "Sam", "Tina"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Taylor", "Anderson"]


def build_dataset(num_users=2000):
    random.seed(42)
    base_date = datetime(2023, 1, 1)

    # 1. Generate users
    users = []
    for uid in range(1, num_users + 1):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        city = random.choice(CITIES)
        joined = base_date + timedelta(days=random.randint(0, 700))
        # Ensure user 1 has tech and music to align with queries_nosql.md
        if uid == 1:
            interests = ["tech", "music", "gaming"]
        else:
            k = random.randint(1, 4)
            interests = random.sample(TOPICS, k)
        users.append({
            "_id": uid,
            "name": name,
            "city": city,
            "joined": joined,
            "interests": interests
        })

    # 2. Generate follows (edges)
    edges = []
    edge_set = set()
    avg_out_degree = 12
    for u in range(1, num_users + 1):
        k = random.randint(avg_out_degree - 4, avg_out_degree + 4)
        targets = random.sample(range(1, num_users + 1), min(k + 1, num_users))
        for v in targets:
            if u != v and (u, v) not in edge_set:
                edge_set.add((u, v))
                edges.append((u, v))

    # Guarantee user 1 has friends and friends-of-friends
    u1_friends = [v for (u, v) in edges if u == 1]
    if len(u1_friends) < 5:
        for f in range(2, 8):
            if (1, f) not in edge_set:
                edge_set.add((1, f))
                edges.append((1, f))
                u1_friends.append(f)

    # 3. Generate posts
    num_posts = num_users * 3
    posts = []
    for pid in range(1, num_posts + 1):
        author = random.randint(1, num_users)
        topic = random.choice(TOPICS)
        text = f"Exploring ideas and updates in {topic}! Post #{pid}"
        likes = int(random.expovariate(1 / 40))  # realistic long-tail likes
        created = base_date + timedelta(days=random.randint(200, 750), hours=random.randint(0, 23))
        posts.append({
            "_id": pid,
            "author": author,
            "topic": topic,
            "text": text,
            "likes": likes,
            "created": created
        })

    # 4. Generate activity events (user_id, ts, post_id, topic, action)
    events = []
    # Ensure user 1 has clear recent activity in 'tech' and 'music'
    for _ in range(25):
        ts = base_date + timedelta(days=random.randint(700, 750), minutes=random.randint(0, 1440))
        events.append((1, ts, random.randint(1, num_posts), "tech", random.choice(ACTIONS)))
    for _ in range(15):
        ts = base_date + timedelta(days=random.randint(700, 750), minutes=random.randint(0, 1440))
        events.append((1, ts, random.randint(1, num_posts), "music", random.choice(ACTIONS)))

    for uid in range(2, min(num_users + 1, 500)):
        num_user_events = random.randint(5, 20)
        for _ in range(num_user_events):
            p = random.choice(posts)
            ts = p["created"] + timedelta(hours=random.randint(1, 48))
            events.append((uid, ts, p["_id"], p["topic"], random.choice(ACTIONS)))

    return users, edges, posts, events


def seed_mongo(users, posts):
    client = pymongo.MongoClient(config.MONGO_URI)
    db = client["social"]
    db.posts.drop()
    db.posts.insert_many(posts)
    db.posts.create_index([("topic", 1), ("likes", -1)])
    count = db.posts.count_documents({})
    client.close()
    return count


def seed_neo4j(users, edges):
    driver = GraphDatabase.driver(config.NEO4J_URI, auth=config.NEO4J_AUTH)
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        s.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        
        # Batch insert users
        batch_size = 1000
        for i in range(0, len(users), batch_size):
            batch = [{"id": u["_id"], "name": u["name"], "city": u["city"], "interests": u["interests"]}
                     for u in users[i:i + batch_size]]
            s.run("UNWIND $batch AS u CREATE (:User {id: u.id, name: u.name, city: u.city, interests: u.interests})",
                  batch=batch)
            
        # Batch insert follows
        for i in range(0, len(edges), 2500):
            batch = [{"src": a, "dst": b} for a, b in edges[i:i + 2500]]
            s.run("""
            UNWIND $batch AS rel
            MATCH (a:User {id: rel.src}), (b:User {id: rel.dst})
            CREATE (a)-[:FOLLOWS]->(b)
            """, batch=batch)
            
        user_cnt = s.run("MATCH (u:User) RETURN count(u) AS c").single()["c"]
        rel_cnt = s.run("MATCH ()-[r:FOLLOWS]->() RETURN count(r) AS c").single()["c"]
    driver.close()
    return user_cnt, rel_cnt


def seed_cassandra(events):
    cluster = Cluster(config.CASSANDRA_HOSTS)
    session = cluster.connect()
    
    session.execute("""
    CREATE KEYSPACE IF NOT EXISTS social
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
    """)
    session.set_keyspace("social")
    
    session.execute("DROP TABLE IF EXISTS activity_by_user")
    session.execute("""
    CREATE TABLE activity_by_user (
        user_id int,
        ts timestamp,
        post_id int,
        topic text,
        action text,
        PRIMARY KEY (user_id, ts, post_id)
    ) WITH CLUSTERING ORDER BY (ts DESC, post_id ASC)
    """)
    
    insert_stmt = session.prepare("""
    INSERT INTO activity_by_user (user_id, ts, post_id, topic, action)
    VALUES (?, ?, ?, ?, ?)
    """)
    
    for event in events:
        session.execute(insert_stmt, event)
        
    row_count = len(events)
    cluster.shutdown()
    return row_count


if __name__ == "__main__":
    print("Generating synthetic dataset...")
    users, edges, posts, events = build_dataset(config.NUM_USERS)

    print("Seeding MongoDB...")
    mongo_count = seed_mongo(users, posts)
    print(f"MongoDB posts: {mongo_count} documents")

    print("Seeding Neo4j...")
    user_cnt, rel_cnt = seed_neo4j(users, edges)
    print(f"Neo4j: {user_cnt} users, {rel_cnt} follows relationships")

    print("Seeding Cassandra...")
    cass_count = seed_cassandra(events)
    print(f"Cassandra activity_by_user: {cass_count} records")

    print("\nSeeding complete.")
