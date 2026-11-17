#!/usr/bin/env python3
"""Direct live re-query of MariaDB event_queue status histogram."""
import os
import sys

sys.path.insert(0, "python")

from config_loader import Config  # noqa: E402

cfg = Config("config.yaml")
print("cfg.data:", cfg.data)
print("cfg.db_password (first 3 chars):", (cfg.db_password or "")[:3] + "..." if cfg.db_password else None)

conn = None
try:
    import pymysql
    conn = pymysql.connect(
        host=cfg.data.db_host,
        port=int(getattr(cfg.data, "db_port", 3306)),
        database=cfg.data.db_name,
        user=cfg.data.db_user,
        password=cfg.db_password or os.environ.get("DB_PASS", ""),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, COUNT(*) AS n FROM event_queue GROUP BY status ORDER BY status;"
        )
        rows = cur.fetchall()
    print("status histogram:")
    for r in rows:
        print(f"  {r['status']}: {r['n']}")
    with conn.cursor() as cur2:
        cur2.execute("SELECT COUNT(*) AS total FROM event_queue;")
        print("total:", cur2.fetchone()["total"])
except Exception as e:
    print("ERROR:", type(e).__name__, e)
    sys.exit(1)
finally:
    if conn is not None:
        conn.close()
