"""Extended db package (python/src/db) — shadows python/db when python/src is on sys.path.

This package provides exchange_routing.py which the DAO imports via
`from db.exchange_routing import ...`. When python/src/ is on sys.path
before python/, this __init__.py makes python/src/db/ a regular package
that Python finds before the python/db/ package."""