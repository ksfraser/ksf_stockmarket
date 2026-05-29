"""
mysql_connector_shim.py — Stub mysql.connector for SQLite-only environments
===========================================================================
Allows importing mysql.connector without errors when running against SQLite.
The actual DB operations go through db_connector.py which handles SQLite compat.
"""
import sys
import types

# Create a fake mysql.connector module
mysql = types.ModuleType('mysql')
mysql_connector = types.ModuleType('mysql.connector')
mysql_connector.connect = lambda *a, **kw: None
mysql_connector.Error = Exception
mysql_connector.errors = types.ModuleType('mysql.connector.errors')
mysql_connector.errors.InterfaceError = Exception
mysql_connector.errors.DatabaseError = Exception
mysql_connector.errors.IntegrityError = Exception
mysql_connector.errors.ProgrammingError = Exception
mysql_connector.errors.DataError = Exception
mysql_connector.errors.OperationalError = Exception

# Fake cursor class
class FakeCursor:
    def __init__(self, *a, **kw): pass
    def execute(self, *a, **kw): pass
    def executemany(self, *a, **kw): pass
    def fetchone(self): return None
    def fetchall(self): return []
    def close(self): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass

mysql_connector.MySQLError = Exception
mysql_connector.cursor = types.ModuleType('mysql.connector.cursor')
mysql_connector.cursor.MySQLCursor = FakeCursor

# Register in sys.modules
sys.modules['mysql'] = mysql
sys.modules['mysql.connector'] = mysql_connector
sys.modules['mysql.connector.errors'] = mysql_connector.errors
sys.modules['mysql.connector.cursor'] = mysql_connector.cursor
