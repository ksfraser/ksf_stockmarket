"""
db/__init__.py — Database adapter layer.

Usage:
    from db import Database, MySQLAdapter, SQLiteAdapter

    # Production
    db = Database(MySQLAdapter(host='ksfraser.ca', user='...', password='...', database='...'))

    # Testing
    db = Database(SQLiteAdapter('/tmp/test.db'))

    # Or from config:
    db = Database.from_config('config.yaml')
"""
from db.adapter import Database
from db.mysql_adapter import MySQLAdapter
from db.sqlite_adapter import SQLiteAdapter

__all__ = ['Database', 'MySQLAdapter', 'SQLiteAdapter']
