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

# All pipeline states with prices
rows = conn.fetchall(
    'SELECT sm.pipeline_state, COUNT(DISTINCT sm.symbol) AS cnt '
    'FROM symbol_master sm '
    'JOIN stockprices sp ON sm.symbol = sp.symbol '
    'WHERE sm.is_active = 1 '
    'GROUP BY sm.pipeline_state '
    'ORDER BY cnt DESC'
)
print('Active symbols with prices by state:')
for row in rows:
    print(f"  {row['pipeline_state']}: {row['cnt']}")

print()
# Active symbols WITHOUT prices
rows2 = conn.fetchall(
    'SELECT sm.symbol, sm.pipeline_state '
    'FROM symbol_master sm '
    'LEFT JOIN stockprices sp ON sm.symbol = sp.symbol '
    'WHERE sm.is_active = 1 AND sp.symbol IS NULL '
    'ORDER BY sm.symbol'
)
print('Active symbols without prices:', len(rows2))
for row in rows2[:20]:
    print(f"  {row['symbol']} -> {row['pipeline_state']}")
if len(rows2) > 20:
    print(f"  ... and {len(rows2)-20} more")

conn.close()
