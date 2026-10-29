# The same tasks in each NoSQL query language

## Friend suggestions (Q1) - Cypher (Neo4j Browser, localhost:7474)
```cypher
MATCH (me:User {id:1})-[:FOLLOWS]->(f:User)-[:FOLLOWS]->(s:User)
WHERE s.id <> 1 AND NOT (me)-[:FOLLOWS]->(s)
RETURN s.id AS suggested_user, count(DISTINCT f) AS mutual_friends
ORDER BY mutual_friends DESC LIMIT 5;
```
Visual (screenshot):
```cypher
MATCH p=(me:User {id:1})-[:FOLLOWS*1..2]->(x) RETURN p LIMIT 60;
```

## Content recommendations (Q2) - CQL then MongoDB shell
```sql
-- cqlsh
SELECT topic FROM social.activity_by_user WHERE user_id = 1 LIMIT 30;
```
```js
// mongosh / Compass
use social
db.posts.aggregate([
  { $match: { topic: { $in: ["tech", "music"] }, author: { $ne: 1 } } },
  { $sort: { likes: -1 } }, { $limit: 5 }
])
```

## Trending topics (Q3) - MongoDB aggregation
```js
db.posts.aggregate([
  { $group: { _id: "$topic", total_likes: { $sum: "$likes" }, posts: { $sum: 1 } } },
  { $sort: { total_likes: -1 } }, { $limit: 5 }
])
```

## Cold start (Q4) - Cypher
```cypher
MATCH (u:User) WHERE any(i IN u.interests WHERE i IN ['tech','music'])
OPTIONAL MATCH (u)<-[f:FOLLOWS]-()
RETURN u.id, u.name, count(f) AS followers ORDER BY followers DESC LIMIT 5;
```

## Three-hop reach (Q5) - Cypher
```cypher
MATCH (a:User {id:1})-[:FOLLOWS*3]->(x) RETURN count(DISTINCT x);
```

## Caching - Redis (redis-cli)
```
KEYS rec:*
GET rec:friends:1
TTL rec:friends:1
```
