"""Runs every query in queries.sql and prints results + time (good for screenshots)."""
import time
import mysql.connector
import config

con = mysql.connector.connect(**config.MYSQL)
cur = con.cursor()
for block in open("queries.sql").read().split(";"):
    block = block.strip()
    if not block:
        continue
    title = block.splitlines()[0]
    t = time.perf_counter()
    cur.execute(block)
    rows = cur.fetchall()
    ms = (time.perf_counter() - t) * 1000
    print(f"\n{title}   [{ms:.1f} ms]")
    print("  columns:", [c[0] for c in cur.description])
    for row in rows:
        print("  ", row)
con.close()
