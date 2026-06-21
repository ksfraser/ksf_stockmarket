#!/usr/bin/env python3
"""
Database connection module for ksf_stockmarket monitoring.
Uses config.yaml/vault via config_loader; falls back to environment variables.
"""
from __future__ import annotations

import os
import pymysql
from typing import Dict, Optional, Any


def _find_config() -> str:
    for candidate in [
        os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml'),
        os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),
        os.environ.get('KFSF_CONFIG', ''),
    ]:
        if candidate and os.path.isfile(candidate):
            return candidate
    return os.environ.get('KFSF_CONFIG', 'config.yaml')


def _secrets() -> Dict[str, Any]:
    try:
        from python.config_loader import Config
    except Exception:
        try:
            from config_loader import Config
        except Exception:
            return {}
    cfg = Config(_find_config())
    return dict(getattr(cfg, 'secrets', {}) or {})


def get_connection() -> pymysql.connections.Connection:
    secrets = _secrets()
    password = (
        secrets.get('db_password')
        or secrets.get('db_pass')
        or os.environ.get('DB_PASSWORD')
        or os.environ.get('DB_PASS', '')
    )
    config = {
        'host': os.environ.get('DB_HOST', 'ksfraser.ca'),
        'port': int(os.environ.get('DB_PORT', '3306')),
        'user': os.environ.get('DB_USER', 'ksfraser_stockmarket'),
        'password': password,
        'database': os.environ.get('DB_NAME', 'ksfraser_stock_market'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': True,
    }
    if not password:
        raise RuntimeError(
            "MariaDB password is not set. Provide DB_PASSWORD/DB_PASS in env, or store db_password in Ansible Vault/config.yaml."
        )
    return pymysql.connect(**config)


def get_monitored_symbols(list_type: Optional[str] = None) -> list:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT symbol, list_type, volume_spike_threshold, notes
                FROM watchlist_symbols
                WHERE monitor_volume = 1 AND is_active = 1
            """
            params = []
            if list_type:
                sql += " AND list_type = %s"
                params.append(list_type)
            sql += " ORDER BY list_type, symbol"
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def log_monitoring_run(
    job_name: str,
    status: str,
    symbol_count: int = 0,
    alert_count: int = 0,
    details: Optional[Dict] = None,
) -> int:
    import json
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO monitoring_runs (job_name, status, symbol_count, alert_count, details)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    job_name,
                    status,
                    symbol_count,
                    alert_count,
                    json.dumps(details) if details else None,
                ),
            )
            return conn.insert_id()
    finally:
        conn.close()


def update_monitoring_run(
    run_id: int,
    status: str,
    alert_count: Optional[int] = None,
    details: Optional[Dict] = None,
) -> None:
    import json
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            updates = ["completed_at = NOW()"]
            params = [run_id]

            if status:
                updates.append("status = %s")
                params.append(status)
            if alert_count is not None:
                updates.append("alert_count = %s")
                params.append(alert_count)
            if details:
                updates.append("details = %s")
                params.append(json.dumps(details))
            params.append(run_id)
            cur.execute(f"UPDATE monitoring_runs SET {', '.join(updates)} WHERE id = %s", params)
    finally:
        conn.close()


if __name__ == '__main__':
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("✓ Database connection successful")
        conn.close()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
