"""
db_connector.py — Shared database connection module.

Reads credentials from config.yaml (via config_loader) or environment.
Production: MariaDB on ksfraser.ca.
Fallback: SQLite only when explicitly forced or when MySQL is unavailable and
the caller is in an allowed SQLite context.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DB_CONFIG: Dict[str, Any] = {}


def _find_config() -> str:
    for candidate in [
        os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml'),
        os.environ.get('KFSF_CONFIG', ''),
    ]:
        if candidate and os.path.isfile(candidate):
            return candidate
    return os.environ.get('KFSF_CONFIG', 'config.yaml')


def _load_db_config_from_config() -> Dict[str, Any]:
    try:
        from python.config_loader import Config
    except Exception:
        try:
            from config_loader import Config
        except Exception:
            return {}

    config_path = _find_config()
    cfg = Config(config_path)

    def _config_node_to_dict(node: Any) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        keys = ['db_host', 'db_port', 'db_name', 'db_user', 'db_password', 'db_pass']
        for key in keys:
            if hasattr(node, key):
                out[key] = getattr(node, key)
        return out

    data_dict = _config_node_to_dict(cfg.data) if hasattr(cfg, 'data') and cfg.data else {}
    secrets_dict = getattr(cfg, 'secrets', {}) or {}
    merged = {**data_dict, **secrets_dict}
    return merged


def _init_mysql() -> None:
    """Configure MariaDB/MySQL backend from config.yaml or environment."""
    global DB_CONFIG
    from_config = _load_db_config_from_config()

    host = (
        from_config.get('db_host')
        or os.environ.get('DB_HOST')
        or 'ksfraser.ca'
    )
    port = int(
        from_config.get('db_port')
        or os.environ.get('DB_PORT', '3306')
    )
    database = (
        from_config.get('db_name')
        or os.environ.get('DB_NAME')
        or 'ksfraser_stock_market'
    )
    user = (
        from_config.get('db_user')
        or os.environ.get('DB_USER')
    )
    password = (
        from_config.get('db_password')
        or from_config.get('db_pass')
        or os.environ.get('DB_PASS')
        or os.environ.get('DB_PASSWORD')
    )

    missing = [name for name, val in [('host', host), ('user', user), ('password', password), ('database', database)] if not val]
    if missing:
        raise RuntimeError(
            f"MariaDB configuration incomplete. Missing: {', '.join(missing)}. "
            "Check config.yaml/vault or environment variables."
        )

    DB_CONFIG.update({
        'backend': 'mysql',
        'host': host,
        'port': port,
        'database': database,
        'user': user,
        'password': password,
        'charset': 'utf8mb4',
        'use_unicode': True,
        'autocommit': False,
        'pool_name': 'ksf_pool',
        'pool_size': 5,
    })


def _init_sqlite() -> None:
    """Configure SQLite backend for explicitly allowed contexts."""
    global DB_CONFIG
    DB_CONFIG = {
        'backend': 'sqlite',
        'path': os.environ.get(
            'SQLITE_PATH',
            os.path.join(os.path.dirname(__file__), '..', 'data', 'ksf_stockmarket.db'),
        ),
    }
    os.makedirs(os.path.dirname(DB_CONFIG['path']), exist_ok=True)


def _init_config() -> None:
    global DB_CONFIG
    backend = os.environ.get('DB_BACKEND', 'auto').lower()

    if backend == 'sqlite':
        _init_sqlite()
        return

    if backend in ('mysql', 'mariadb'):
        _init_mysql()
        return

    try:
        _init_mysql()
        _connect_mysql().close()
        logger.info("DB backend: MariaDB/MySQL")
    except Exception as exc:
        logger.warning("MySQL unavailable (%s). SQLite fallback is disabled; set DB_BACKEND=sqlite if needed.", exc)
        raise RuntimeError(f"MariaDB unavailable: {exc}") from exc


def _connect_mysql() -> Any:
    """Create a MySQL connection using mysql.connector."""
    import mysql.connector
    try:
        return mysql.connector.connect(**{k: v for k, v in DB_CONFIG.items() if k != 'backend'})
    except Exception as exc:
        raise RuntimeError(f"MariaDB connection failed: {exc}") from exc


def get_connection():
    """Get a database connection (auto-detects backend when not pre-initialized)."""
    if not DB_CONFIG:
        _init_config()
    backend = DB_CONFIG.get('backend')
    if backend == 'mysql':
        return _connect_mysql()
    if backend == 'sqlite':
        import sqlite3
        path = DB_CONFIG['path']
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    raise RuntimeError(f"Unknown DB backend: {backend}")


def get_dict_cursor(conn):
    real = getattr(conn, '_conn', conn)
    if hasattr(real, 'row_factory') and real.row_factory is None:
        import sqlite3
        real.row_factory = sqlite3.Row
    return conn.cursor()
