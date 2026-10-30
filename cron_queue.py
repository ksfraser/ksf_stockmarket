#!/usr/bin/env python3
"""
cron_queue.py - Manage cron job queue, check for failures, and retry.

This script manages a queue of scheduled cron jobs stored in a SQLite database.
It supports three main actions:
  - check:   List jobs that have failed
  - retry:   Re-run failed jobs
  - run:     Execute a specific job by ID
"""

import argparse
import sqlite3
import subprocess
import sys
import os
import datetime
import logging
from pathlib import Path

DB_PATH = "/home/ksf_stockmarket/ksf_stockmarket/cron_queue.db"
LOG_FILE = "/tmp/cron_alert.log"

# Ensure log directory exists
LogHandler = logging.FileHandler(LOG_FILE)
LogHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger = logging.getLogger("cron_queue")
logger.addHandler(LogHandler)
logger.setLevel(logging.INFO)


def get_db_connection():
    """Get a database connection and ensure the schema exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn):
    """Create the necessary tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cron_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            schedule TEXT,
            last_run TEXT,
            next_run TEXT,
            status TEXT DEFAULT 'pending',
            exit_code INTEGER,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            run_time TEXT,
            exit_code INTEGER,
            error_message TEXT,
            FOREIGN KEY (job_id) REFERENCES cron_jobs(id)
        );
    """)
    conn.commit()


def _mark_job_failed(conn, job_id, error):
    """Mark a job as failed."""
    conn.execute(
        "UPDATE cron_jobs SET status='failed', error_message=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (error, job_id),
    )
    conn.commit()


def check_jobs(conn):
    """Check for failed jobs in the queue."""
    cursor = conn.execute(
        "SELECT id, name, command, status, error_message, last_run FROM cron_jobs WHERE status != 'pending' ORDER BY id"
    )
    jobs = cursor.fetchall()

    if not jobs:
        print("No jobs found in queue.")
        return 0

    failed_count = 0
    print(f"\n{'='*70}")
    print("CRON QUEUE STATUS REPORT")
    print(f"{'='*70}")

    for job_id, name, command, status, error, last_run in jobs:
        icon = "❌" if status == "failed" else "⚠️"
        print(f"\n{icon} Job #{job_id}: {name}")
        print(f"   Command: {command}")
        print(f"   Status: {status}")
        if error:
            print(f"   Error: {error}")
        if last_run:
            print(f"   Last run: {last_run}")

        if status == "failed":
            failed_count += 1

    print(f"\n{'='*70}")
    print(f"Total failed: {failed_count} / {len(jobs)}")
    print(f"{'='*70}\n")

    # Log to file
    if failed_count > 0:
        logger.warning(f"Found {failed_count} failed jobs in cron queue")

    return failed_count


def run_job(conn, job_id, max_attempts=3):
    """Run a specific job by ID."""
    cursor = conn.execute(
        "SELECT name, command, status FROM cron_jobs WHERE id=?",
        (job_id,),
    )
    row = cursor.fetchone()

    if not row:
        print(f"Error: Job #{job_id} not found.")
        return False

    name, command, status = row

    if status == "running":
        print(f"Error: Job #{job_id} ({name}) is already running.")
        return False

    # Update status to running
    conn.execute(
        "UPDATE cron_jobs SET status='running', last_run=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (job_id,),
    )
    conn.commit()

    print(f"Executing job #{job_id}: {name}")
    print(f"Command: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True,
            timeout=3600,
        )

        exit_code = result.returncode
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        # Update job status
        if exit_code == 0:
            conn.execute(
                "UPDATE cron_jobs SET status='success', error_message=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (job_id,),
            )
            print(f"✅ Job #{job_id} completed successfully (exit code 0)")
            if stdout:
                print(f"   Output: {stdout[:500]}")
        else:
            msg = f"Job #{job_id} failed (exit code {exit_code})"
            if stderr:
                msg += f": {stderr[:200]}"
            _mark_job_failed(conn, job_id, msg)
            print(f"❌ {msg}")

            # Auto-retry with limited attempts
            for attempt in range(2, min(max_attempts, 4)):
                print(f"   Retrying attempt {attempt}...")
                result2 = subprocess.run(
                    command,
                    shell=True,
                    executable="/bin/bash",
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )
                if result2.returncode == 0:
                    print(f"✅ Retry #{attempt} succeeded.")
                    conn.execute(
                        "UPDATE cron_jobs SET status='success', error_message=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (job_id,),
                    )
                    conn.commit()
                    break
                else:
                    msg = f"Retry #{attempt} failed (exit code {result2.returncode})"
                    if result2.stderr:
                        msg += f": {result2.stderr[:200]}"
                    _mark_job_failed(conn, job_id, msg)

        # Log to history
        conn.execute(
            "INSERT INTO job_history (job_id, run_time, exit_code, error_message) VALUES (?, ?, ?, ?)",
            (job_id, datetime.datetime.now().isoformat(), exit_code, "" if exit_code == 0 else (stderr or "Unknown error")),
        )
        conn.commit()

        return exit_code == 0

    except subprocess.TimeoutExpired:
        conn.execute(
            "UPDATE cron_jobs SET status='failed', error_message='Timed out after 1 hour', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (job_id,),
        )
        conn.commit()
        print(f"❌ Job #{job_id} timed out after 1 hour.")
        logger.error(f"Job #{job_id} timed out")
        return False
    except Exception as e:
        conn.execute(
            "UPDATE cron_jobs SET status='failed', error_message=str(e), updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (job_id,),
        )
        conn.commit()
        print(f"❌ Job #{job_id} encountered error: {e}")
        logger.error(f"Job #{job_id} error: {e}")
        return False


def retry_jobs(conn):
    """Retry all failed jobs in the queue."""
    cursor = conn.execute(
        "SELECT id, name, command, error_message FROM cron_jobs WHERE status='failed'"
    )
    jobs = cursor.fetchall()

    if not jobs:
        print("No failed jobs to retry.")
        return 0

    print(f"\n{'='*70}")
    print(f"RETRYING {len(jobs)} FAILED JOBS")
    print(f"{'='*70}\n")

    success_count = 0
    failure_count = 0

    for job_id, name, command, error in jobs:
        print(f"Retrying job #{job_id}: {name}")
        print(f"  Original error: {error}")
        print(f"  Command: {command}")
        print()

        try:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=3600,
            )

            if result.returncode == 0:
                print(f"   ✅ Retry #{job_id} succeeded.")
                conn.execute(
                    "UPDATE cron_jobs SET status='success', error_message=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (job_id,),
                )
                conn.commit()
                success_count += 1
                logger.info(f"Job #{job_id} retry succeeded")
            else:
                msg = f"Retry failed (exit code {result.returncode})"
                if result.stderr:
                    msg += f": {result.stderr[:200]}"
                _mark_job_failed(conn, job_id, msg)
                print(f"   ❌ Retry failed: {msg}")
                failure_count += 1
                logger.warning(f"Job #{job_id} retry failed: {msg}")
        except Exception as e:
            msg = f"Retry exception: {e}"
            _mark_job_failed(conn, job_id, msg)
            print(f"   ❌ Retry exception: {e}")
            failure_count += 1
            logger.error(f"Job #{job_id} retry exception: {e}")

    print(f"\n{'='*70}")
    print(f"Retry complete: {success_count} succeeded, {failure_count} failed")
    print(f"{'='*70}\n")

    return success_count


def main():
    parser = argparse.ArgumentParser(
        description="Manage cron job queue: check for failures and retry jobs."
    )
    parser.add_argument(
        "--job-id",
        type=int,
        help="Specific job ID to run (requires action=run)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        help="Only check jobs that have not run in the last N hours",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of jobs to process",
    )
    parser.add_argument(
        "action",
        choices=["check", "retry", "run"],
        help="Action to perform: check for failures, retry failed jobs, or run a specific job",
    )

    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        print("Run the cron_queue.py script to initialize.")
        sys.exit(1)

    conn = get_db_connection()

    try:
        if args.action == "check":
            check_jobs(conn)
        elif args.action == "retry":
            retry_jobs(conn)
        elif args.action == "run":
            if args.job_id is None:
                print("Error: --job-id is required for the 'run' action.")
                sys.exit(1)
            run_job(conn, args.job_id)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
