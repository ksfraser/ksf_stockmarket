"""
db/adapter.py — Abstract database adapter interface (portability layer).

All DB adapters implement this interface so scripts can swap SQLite ↔ MySQL
via dependency injection. Testing always uses SQLite; production uses MySQL.

Design notes (per AGENTS.md Portability rules):
- All identifiers UPPERCASE in SQL (reserved words must not be used as MySQL column names)
- Parameterized queries only — no f-string SQL
- Context manager support (with statement)
- Dict-based results ({'column': value}) for MySQL adapter
- Adapter chosen at runtime, never hardcoded in business logic
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
import logging

log = logging.getLogger(__name__)


class DBConnection(ABC):
    """Abstract connection interface. All adapters must implement these methods."""

    @abstractmethod
    def execute(self, sql: str, params: Optional[tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE. Returns affected row count."""
        ...

    @abstractmethod
    def fetchone(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """Execute SELECT and return single row as dict, or None."""
        ...

    @abstractmethod
    def fetchall(self, sql: str, params: Optional[tuple] = None) -> List[Dict]:
        """Execute SELECT and return all rows as list of dicts."""
        ...

    @abstractmethod
    def executemany(self, sql: str, params_list: List[tuple]) -> int:
        """Execute batch INSERT/UPDATE. Returns total affected rows."""
        ...

    @abstractmethod
    def commit(self) -> None:
        """Commit current transaction."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
        ...

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            log.error(f"DB error: {exc_val}")
        self.close()
        return False


class Database:
    """
    High-level database interface. Adapter passed via constructor (DI).

    Usage:
        db = Database(MySQLAdapter(host='...', ...))
        with db.connect() as conn:
            row = conn.fetchone("SELECT * FROM symbol_master WHERE symbol = %s", ('RY',))
    """

    def __init__(self, adapter: 'DBConnection'):
        self._adapter = adapter

    def connect(self) -> DBConnection:
        """Return adapter instance (opens connection on first use via _ensure_open)."""
        return self._adapter

    @classmethod
    def from_config(cls, config_path: str = 'config.yaml') -> 'Database':
        """Factory: build Database from YAML config (adapter chosen by 'db.engine' key)."""
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        db_cfg = cfg.get('database', {})
        engine = db_cfg.get('engine', 'sqlite')

        if engine == 'mysql':
            from db.mysql_adapter import MySQLAdapter
            return cls(MySQLAdapter(
                host=db_cfg.get('host', 'localhost'),
                user=db_cfg.get('user', ''),
                password=db_cfg.get('password', ''),
                database=db_cfg.get('database', ''),
                port=db_cfg.get('port', 3306),
            ))
        elif engine == 'sqlite':
            from db.sqlite_adapter import SQLiteAdapter
            db_path = db_cfg.get('path', 'analysis_results.db')
            return cls(SQLiteAdapter(db_path))
        else:
            raise ValueError(f"Unknown database engine: {engine}. Use 'mysql' or 'sqlite'.")
