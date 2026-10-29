"""Load the SAME dataset into MySQL (relational baseline). Run after docker compose up."""
import mysql.connector
from seed_data import build_dataset
import config


def run_script(cur, path):
    for stmt in open(path).read().split(";"):
        if stmt.strip():
            cur.execute(stmt)


if __name__ == "__main__":
    users, edges, posts, events = build_dataset(config.NUM_USERS)
    con = mysql.connector.connect(**config.MYSQL)
    cur = con.cursor()
    run_script(cur, "schema.sql")

    cur.executemany("INSERT INTO users VALUES (%s,%s,%s,%s)",
                    [(u["_id"], u["name"], u["city"], u["joined"]) for u in users])
    cur.executemany("INSERT INTO user_interests VALUES (%s,%s)",
                    [(u["_id"], i) for u in users for i in u["interests"]])
    cur.executemany("INSERT INTO follows VALUES (%s,%s)", edges)
    cur.executemany("INSERT INTO posts VALUES (%s,%s,%s,%s,%s,%s)",
                    [(p["_id"], p["author"], p["topic"], p["text"], p["likes"], p["created"]) for p in posts])
    cur.executemany("INSERT INTO activity VALUES (%s,%s,%s,%s,%s)", events)
    con.commit()

    for t in ["users", "user_interests", "follows", "posts", "activity"]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"MySQL table {t:<15}: {cur.fetchone()[0]} rows")
    con.close()
