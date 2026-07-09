import pymysql.cursors
from config_loader import Config
from db.mysql_adapter import MySQLConnection

cfg = Config('config.yaml')
MYSQL = dict(
    host=cfg.data.db_host,
    user=cfg.data.db_user,
    password=cfg.db_password,
    database=cfg.data.db_name,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=20,
    read_timeout=120,
    write_timeout=120,
)
conn = MySQLConnection(**MYSQL)

nulls = conn.fetchall(
    'SELECT sm.symbol, MAX(sp.price_date) AS latest_price_date '
    'FROM symbol_master sm '
    'JOIN stockprices sp ON sm.symbol = sp.symbol '
    'WHERE sm.is_active = 1 AND sm.pipeline_state IS NULL '
    'GROUP BY sm.symbol '
    'ORDER BY latest_price_date DESC'
)
print('Active with prices and NULL pipeline_state:', len(nulls))

unknowns = conn.fetchall(
    'SELECT sm.symbol, MAX(sp.price_date) AS latest_price_date '
    'FROM symbol_master sm '
    'JOIN stockprices sp ON sm.symbol = sp.symbol '
    "WHERE sm.is_active = 1 AND sm.pipeline_state = 'unknown' "
    'GROUP BY sm.symbol '
    'ORDER BY latest_price_date DESC'
)
print('Active with prices and unknown pipeline_state:', len(unknowns))

candidates = conn.fetchall(
    'SELECT sm.symbol, MAX(sp.price_date) AS latest_price_date '
    'FROM symbol_master sm '
    'JOIN stockprices sp ON sm.symbol = sp.symbol '
    "WHERE sm.is_active = 1 AND sm.pipeline_state = 'candidate' "
    'GROUP BY sm.symbol '
    'ORDER BY latest_price_date DESC'
)
print('Active with prices and candidate pipeline_state:', len(candidates))

# Also check pending_backfill and prices_loaded
pending = conn.fetchall(
    'SELECT sm.symbol, MAX(sp.price_date) AS latest_price_date '
    'FROM symbol_master sm '
    'JOIN stockprices sp ON sm.symbol = sp.symbol '
    "WHERE sm.is_active = 1 AND sm.pipeline_state = 'pending_backfill' "
    'GROUP BY sm.symbol '
    'ORDER BY latest_price_date DESC'
)
print('Active with prices and pending_backfill pipeline_state:', len(pending))

pl = conn.fetchall(
    'SELECT sm.symbol, MAX(sp.price_date) AS latest_price_date '
    'FROM symbol_master sm '
    'JOIN stockprices sp ON sm.symbol = sp.symbol '
    "WHERE sm.is_active = 1 AND sm.pipeline_state = 'prices_loaded' "
    'GROUP BY sm.symbol '
    'ORDER BY latest_price_date DESC'
)
print('Active with prices and prices_loaded pipeline_state:', len(pl))

conn.close()
