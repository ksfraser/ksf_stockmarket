#!/usr/bin/env python3
"""
Database connection module for ksf_stockmarket monitoring.
Uses environment variables for configuration (injected via Ansible Vault).
"""

import os
import pymysql
from typing import Dict, Optional, Any


def get_connection() -> pymysql.connections.Connection:
    """
    Get a MariaDB connection using environment variables.
    Falls back to defaults for local development.
    """
    config = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', '3306')),
        'user': os.environ.get('DB_USER', 'ksfraser_stockmarket'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'ksfraser_stock_market'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': True,
    }
    return pymysql.connect(**config)


def get_monitored_symbols(list_type: Optional[str] = None) -> list:
    """
    Fetch active symbols to monitor from watchlist_symbols table.
    
    Args:
        list_type: 'portfolio', 'watchlist', or None for all
        
    Returns:
        List of dicts: {symbol, volume_spike_threshold, list_type, notes}
    """
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


def log_monitoring_run(job_name: str, status: str, symbol_count: int = 0, 
                        alert_count: int = 0, details: Optional[Dict] = None) -> int:
    """
    Log a monitoring run to the monitoring_runs table.
    
    Returns:
        The inserted run ID
    """
    import json
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO monitoring_runs (job_name, status, symbol_count, alert_count, details)
                VALUES (%s, %s, %s, %s, %s)
            """, (job_name, status, symbol_count, alert_count, 
                  json.dumps(details) if details else None))
            return conn.insert_id()
    finally:
        conn.close()


def update_monitoring_run(run_id: int, status: str, alert_count: Optional[int] = None,
                          details: Optional[Dict] = None) -> None:
    """Update a monitoring run record."""
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
                
            params = params + [status]  # Final params
            cur.execute(f"UPDATE monitoring_runs SET {', '.join(updates)} WHERE id = %s", 
                       [run_id])
    finally:
        conn.close()


if __name__ == '__main__':
    # Test connection
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("✓ Database connection successful")
        conn.close()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")