"""Step 3: relational JOINs (MySQL) vs graph traversal (Neo4j) at growing graph sizes."""
import random
import mysql.connector
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from neo4j import GraphDatabase

import config

SIZES = [1000, 10000, 50000]
DEPTHS = [2, 3, 4]
SAMPLES = 20
random.seed(1)


def make_edges(n, out_degree=10):
    edges = []
    for u in range(1, n + 1):
        for v in random.sample(range(1, n + 1), out_degree + 1):
            if v != u:
                edges.append((u, v))
    return edges


def sql_query(d):
    joins = " ".join(f"JOIN bench_edges e{i} ON e{i}.src = e{i-1}.dst" for i in range(2, d + 1))
    return f"SELECT COUNT(DISTINCT e{d}.dst) FROM bench_edges e1 {joins} WHERE e1.src = %s"


def bench_sql(edges, starts):
    con = mysql.connector.connect(**config.MYSQL)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS bench_edges")
    cur.execute("CREATE TABLE bench_edges (src INT, dst INT, INDEX idx_src (src))")
    for i in range(0, len(edges), 20000):
        cur.executemany("INSERT INTO bench_edges VALUES (%s, %s)", edges[i:i + 20000])
    con.commit()
    out = {}
    for d in DEPTHS:
        q = sql_query(d)
        t = time.perf_counter()
        for s in starts:
            cur.execute(q, (s,))
            cur.fetchall()
        out[d] = (time.perf_counter() - t) * 1000 / len(starts)
    cur.execute("DROP TABLE bench_edges")
    con.close()
    return out


def bench_neo4j(driver, edges, starts):
    with driver.session() as s:
        s.run("MATCH (n:BUser) CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS")
        s.run("CREATE CONSTRAINT buser_id IF NOT EXISTS FOR (u:BUser) REQUIRE u.id IS UNIQUE")
        ids = sorted({a for a, _ in edges} | {b for _, b in edges})
        for i in range(0, len(ids), 5000):
            s.run("UNWIND $ids AS i CREATE (:BUser {id:i})", ids=ids[i:i + 5000])
        for i in range(0, len(edges), 5000):
            rows = [{"a": a, "b": b} for a, b in edges[i:i + 5000]]
            s.run("UNWIND $rows AS r MATCH (a:BUser {id:r.a}), (b:BUser {id:r.b}) CREATE (a)-[:F]->(b)", rows=rows)
        out = {}
        for d in DEPTHS:
            q = f"MATCH (a:BUser {{id:$id}})-[:F*{d}]->(x) RETURN count(DISTINCT x) AS c"
            t = time.perf_counter()
            for sid in starts:
                s.run(q, id=sid).single()
            out[d] = (time.perf_counter() - t) * 1000 / len(starts)
    return out


if __name__ == "__main__":
    driver = GraphDatabase.driver(config.NEO4J_URI, auth=config.NEO4J_AUTH)
    results = {}
    for n in SIZES:
        print(f"Benchmarking {n} users ...")
        edges = make_edges(n)
        starts = random.sample(range(1, n + 1), SAMPLES)
        results[n] = {"sql": bench_sql(edges, starts), "neo4j": bench_neo4j(driver, edges, starts)}

    print("\nUsers | Depth | SQL (ms) | Neo4j (ms)")
    for n in SIZES:
        for d in DEPTHS:
            print(f"{n:>6} | {d:>5} | {results[n]['sql'][d]:>8.2f} | {results[n]['neo4j'][d]:>10.2f}")

    fig, axes = plt.subplots(1, len(DEPTHS), figsize=(14, 4))
    for ax, d in zip(axes, DEPTHS):
        ax.plot(SIZES, [results[n]["sql"][d] for n in SIZES], "o-", label="SQL JOINs (MySQL)")
        ax.plot(SIZES, [results[n]["neo4j"][d] for n in SIZES], "s-", label="Neo4j traversal")
        ax.set_title(f"Depth {d} (hops)"); ax.set_xlabel("Users"); ax.set_ylabel("Avg query time (ms)")
        ax.legend()
    plt.tight_layout(); plt.savefig("benchmark.png", dpi=150)
    print("Saved benchmark.png")
    driver.close()
