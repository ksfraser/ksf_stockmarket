#!/usr/bin/env python3
"""Pre-run DB baseline for the stockmarket cron queue.

Reads only non-sensitive connection fields (host/port/name/user + whether a
password is configured) and reports the event_queue status tally and the
pending events grouped by event_type. Prints no secrets.
"""
import os
import sys

APP = "/root/Documents/stockmarket/php/stockmarket-app"
for _extra in (APP, os.path.join(APP, "python")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

import pymysql  # noqa: E402
from config_loader import Config  # noqa: E402

cfg = Config(os.path.join(APP, "config.yaml"))

def db_from_env():
    return {
        "host": os.environ.get("DB_HOST", "ksfraser.ca"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "database": os.environ.get("DB_NAME", "ksfraser_stock_market"),
        "user": os.environ.get("DB_USER", "ksfraser_stockmarket"),
        "password": os.environ.get("DB_PASS", ""),
    }

def tally(host, port, database, user, password):
    conn = pymysql.connect(host=host, port=port, database=database,
                           user=user, password=password,
                           charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
                           autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status, COUNT(*) AS c FROM event_queue GROUP BY status")
            tall = {r["status"]: int(r["c"]) for r in cur.fetchall()}
    finally:
        conn.close()
    return tall

def main():
    print("== DB config from config.yaml ==")
    print("db_host:", cfg.data.db_host)
    print("db_port:", getattr(cfg.data, "db_port", "<not set; default 3306>"))
    print("db_name:", cfg.data.db_name)
    print("db_user:", cfg.data.db_user)
    print("db_password (from config):", bool(getattr(cfg, "db_password", None) or cfg.secrets.get("db_password")))
    print("env DB_PASS set:", bool(os.environ.get("DB_PASS")))
    print("env DB_HOST:", os.environ.get("DB_HOST"))
    print("env DB_PORT:", os.environ.get("DB_PORT"))

    creds = db_from_env()
    print("== connecting with env creds ==")
    print("conn host:", creds["host"], "port:", creds["port"],
          "db:", creds["database"], "user:", creds["user"], "pw_set:", bool(creds["password"]))
    try:
        tall = tally(creds["host"], creds["port"], creds["database"], creds["user"], creds["password"])
        print("== status tally ==")
        for s in ("pending", "running", "failed", "completed", "cancelled", "unknown"):
            print(f"  {s}: {tall.get(s, 0)}")
        if tall.get("pending"):
            with pymysql.connect(host=creds["host"], port=creds["port"], database=creds["database"],
                                 user=creds["user"], password=creds["password"],
                                 charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
                                 autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("""SELECT event_type, COUNT(*) AS c FROM event_queue
                                   WHERE status='pending' GROUP BY event_type""")
                    print("== pending grouped by event_type ==")
                    for r in cur.fetchall():
                        print(f"  {r['event_type']}: {r['c']}")
        print("== total ==")
        print("  ", sum(tall.values()))
    except Exception as exc:
        print("CONNECTION/QUERY FAILED:", type(exc).__name__, exc)

if __name__ == "__main__":
    main()
