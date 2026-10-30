#!/usr/bin/env python3
"""MIGRATION MONITOR — indicators_json → indicators columnar migration watchdog."""

import subprocess
import sys
import os
from datetime import datetime

LOG_FILE = "/tmp/migrate_monitor.log"
MIGRATE_SCRIPT = "/home/ksf_stockmarket/ksf_stockmarket/migrate_indicators_json_to_columnar.py"
MIGRATE_LOG = "/tmp/migrate_indicators.log"

DB_HOST = "ksfraser.ca"
DB_PORT = "3306"
DB_USER = "ksfraser_stockmarket"
DB_PASS = "Zaqwsx9sm1@"
DB_NAME = "ksfraser_stock_market"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(line)

def pgrep_migration():
    """Check if migration script is running. Returns PID or None."""
    try:
        r = subprocess.run(["pgrep", "-f", "migrate_indicators_json_to_columnar.py"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            pids = r.stdout.strip().split()
            return int(pids[0])
    except Exception as e:
        log(f"ERROR: pgrep failed: {e}")
    return None

def count_json_rows():
    """Query indicators_json row count."""
    query = ("SELECT COUNT(*) FROM indicators_json;")
    cmd = [
        "mysql",
        "-h", DB_HOST,
        "-P", DB_PORT,
        "-u", DB_USER,
        f"-p{DB_PASS}",
        DB_NAME,
        "-N", "-e", query
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            log(f"ERROR: mysql query failed: {r.stderr.strip()}")
            return -1
        return int(r.stdout.strip())
    except Exception as e:
        log(f"ERROR: count query exception: {e}")
        return -1

def restart_migration():
    """Restart the migration script in background."""
    env = os.environ.copy()
    env["DB_PASS"] = DB_PASS
    env["DB_USER"] = DB_USER
    env["DB_NAME"] = DB_NAME

    cmd = ["nohup", "python3", "-u", MIGRATE_SCRIPT]
    with open(MIGRATE_LOG, "a") as log_f:
        p = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, env=env)
    return p.pid

def remove_cron():
    """Remove this MIGRATION MONITOR cron entry."""
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if r.returncode != 0:
            log("ERROR: crontab -l failed — cannot remove self")
            return False
        new_cron = "\n".join(
            line for line in r.stdout.splitlines()
            if "MIGRATION MONITOR" not in line
        )
        # Ensure we don't end up with empty crontab causing issues
        subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)
        log("Cron job removed (migration complete).")
        return True
    except Exception as e:
        log(f"ERROR: cron removal failed: {e}")
        return False

def main():
    log("=== MIGRATION MONITOR RUN ===")

    # Step 1 & 2: Is migration alive?
    pid = pgrep_migration()
    if pid is not None:
        log(f"Migration alive (PID {pid}). Doing nothing.")
        sys.exit(0)

    # Step 3a: Migration is dead — check work remaining
    log("Migration script NOT running.")
    count = count_json_rows()
    if count < 0:
        log("Could not determine row count. Exiting.")
        sys.exit(1)

    log(f"indicators_json row count: {count}")

    # Step 3b: Empty → remove cron and exit
    if count == 0:
        log("indicators_json is empty. Migration complete.")
        remove_cron()
        sys.exit(0)

    # Step 3c: Has rows → restart
    log("indicators_json still has rows. Restarting migration...")
    new_pid = restart_migration()
    log(f"Migration restarted with PID {new_pid}.")

if __name__ == "__main__":
    main()
