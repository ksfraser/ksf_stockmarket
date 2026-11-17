#!/usr/bin/env python3
"""Independent probe of the live event_queue histogram via config_loader."""
import os
import sys

REPO = "/root/Documents/stockmarket/php/stockmarket-app"
for _c in [REPO, os.path.join(REPO, "python")]:
    if _c not in sys.path:
        sys.path.insert(0, _c)

from config_loader import Config  # noqa: E402
import pymysql  # noqa: E402
from pymysql import cursors as _  # noqa: F401

cfg = Config(os.path.join(REPO, "config.yaml"))
conn_cfg = {
    "host": cfg.data.db_host,
    "port": int(getattr(cfg.data, "db_port", 3306)),
    "database": cfg.data.db_name,
    "user": cfg.data.db_user,
    "password": cfg.db_password or cfg.secrets.get("db_password") or os.environ.get("DB_PASS", ""),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

print("conn cfg resolved: host=%s port=%s user=%s db=%s password_set=%s"
      % (conn_cfg["host"], conn_cfg["port"], conn_cfg["user"],
         conn_cfg["database"],
         bool(conn_cfg["password"])))

hist = {}
pending = 0
with pymysql.connect(**conn_cfg) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT status, COUNT(*) AS c FROM event_queue GROUP BY status")
        for row in cur.fetchall():
            hist[row["status"]] = row["c"]
        cur.execute("SELECT COUNT(*) AS n FROM event_queue WHERE status='pending'")
        pending = cur.fetchone()["n"]

total = sum(hist.values())
print("HISTOGRAM (event_queue):")
for s in sorted(hist):
    print("  %-10s %d" % (s, hist[s]))
print("TOTAL: %d  PENDING: %d" % (total, pending))
