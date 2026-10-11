"""Base DAO for database operations (minimal stub for legacy imports)."""

class BaseDAO:
    """Base class for data access objects."""
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.conn = None

    def _conn(self):
        """Return a database connection."""
        import sqlite3
        return sqlite3.connect(self.db_path)
