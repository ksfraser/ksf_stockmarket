#!/usr/bin/env python3
"""Verify cron queue state by replicating cron_queue.py's DB connection."""
import os
import sys

REPO_ROOT = "/root/Documents/stockmarket/php/stockmarket-app"
SRC_ROOT = os.path.join(REPO_ROOT, "python", "src")
for _c in (REPO_ROOT, SRC_ROOT, os.path.join(REPO_ROOT, "python")):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from config_loader import Config  # noqa: E402
import pymysql  # noqa: E402

cfg = Config(os.path.join(REPO_ROOT, "config.yaml"))
conn_config = {
    "host": cfg.data.db_host,
    "port": int(getattr(cfg.data, "db_port", 3306)),
    "database": cfg.data.db_name,
    "user": cfg.data.db_user,
    "password": cfg.db_password or cfg.secrets.get("db_password") or os.environ.get("DB_PASS", ""),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

print("DB config:", {k: v for k, v in conn_config.items() if k not in ("password",)})
print("cfg.db_password present:", hasattr(cfg, "db_password"), "| type:", type(getattr(cfg, "db_password", None)))

con = pymysql.connect(**conn_config)
try:
    with con.cursor() as cur:
        cur.execute("SELECT status, COUNT(*) AS n FROM event_queue GROUP BY status ORDER BY status")
        rows = cur.fetchall()
    print("event_queue status histogram:")
    total = 0
    for r in rows:
        print(f"  {r['status']:12s} {r['n']}")
        total += r["n"]
    print(f"  {'TOTAL':12s} {total}")
    pending = [r for r in rows if r["status"] == "pending"]
    running = [r for r in rows if r["status"] == "running"]
    print("VERDICT:", "healthy-empty (no jobs pending, no stuck running)" if not pending and not running else "NOT empty")
    if pending:
        print("  pending rows:", pending)
    if running:
        print("  RUNNING rows:", running)
finally:
    con.close()
