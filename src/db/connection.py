"""Centralized database connections (SQLite + MariaDB).

This is the ONLY module that opens raw connections. Repositories call
``DataSource.sqlite_connection(...)`` / ``DataSource.mariadb_connection(...)``
instead of ``sqlite3.connect`` / ``pymysql.connect`` so connection policy
(WAL, row factory, busy_timeout, charset, credential source) is consistent and
auditable. This is the "centralized DB" backbone of the layered architecture.

Allowlisted by ``scripts/guard_standardized_access.py`` (lives in ``src/db/``).
"""
from __future__ import annotations

import sqlite3
from typing import Optional

try:
    import pymysql
except ImportError:  # pragma: no cover - pymysql required only for MariaDB
    pymysql = None

from config.db import get_mariadb_config


class DataSource:
    """Single entry point for opening SQLite / MariaDB connections."""

    # --- SQLite ---------------------------------------------------------
    @staticmethod
    def sqlite_connection(path: str, *, row_factory=sqlite3.Row):
        """Open a SQLite connection with the project's standard pragmas."""
        conn = sqlite3.connect(path)
        conn.row_factory = row_factory
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # --- MariaDB --------------------------------------------------------
    @staticmethod
    def mariadb_connection(config: Optional[dict] = None):
        """Open a MariaDB connection from injected config or ``get_mariadb_config()``."""
        if pymysql is None:
            raise RuntimeError(
                "pymysql is not installed; cannot open a MariaDB connection"
            )
        cfg = dict(config or get_mariadb_config())
        return pymysql.connect(
            host=cfg.get("host", "ksfraser.ca"),
            user=cfg.get("user", "ksfraser_stockmarket"),
            password=cfg.get("password", ""),
            database=cfg.get("database", "ksfraser_stock_market"),
            charset=cfg.get("charset", "utf8mb4"),
            autocommit=False,
        )
