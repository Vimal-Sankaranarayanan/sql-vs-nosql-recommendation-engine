# SQL vs NoSQL: Friend & Content Recommendation Engine

MySQL (relational baseline) vs Neo4j (graph) + MongoDB (document) + Redis (key-value) + Cassandra (column family).

## Run
1. docker compose up -d          (wait ~60 s)
2. python -m venv venv ; activate it ; pip install -r requirements.txt
3. python seed_mysql.py          (loads MySQL)
4. python sql_demo.py            (runs queries.sql - the SQL results)
5. python seed_data.py           (loads MongoDB, Neo4j, Cassandra)
6. python recommend.py           (NoSQL recommendation engine)
7. python benchmark.py           (MySQL JOINs vs Neo4j traversal -> benchmark.png)

queries.sql = SQL | queries_nosql.md = Cypher, MongoDB, CQL, Redis equivalents
