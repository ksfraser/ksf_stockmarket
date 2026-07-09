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

# TA_READY symbols with recent prices_loaded events
ready_with_events = conn.fetchall(
    'SELECT sm.symbol, eq.event_id, eq.occurred_at '
    'FROM symbol_master sm '
    'JOIN event_queue eq ON eq.event_type = "prices_loaded" '
    '  AND JSON_EXTRACT(eq.payload, "$.symbol") = sm.symbol '
    'WHERE sm.is_active = 1 AND sm.pipeline_state = "ta_ready" '
    'ORDER BY eq.occurred_at DESC'
)
print(f'TA_READY symbols with prices_loaded event in queue: {len(ready_with_events)}')

# TA_READY symbols WITHOUT recent events
ready_without_events = conn.fetchall(
    'SELECT sm.symbol FROM symbol_master sm '
    'WHERE sm.is_active = 1 AND sm.pipeline_state = "ta_ready" '
    'AND NOT EXISTS ('
    '  SELECT 1 FROM event_queue eq '
    '  WHERE eq.event_type = "prices_loaded" '
    '  AND JSON_EXTRACT(eq.payload, "$.symbol") = sm.symbol'
    ')'
)
print(f'TA_READY symbols WITHOUT prices_loaded event in queue: {len(ready_without_events)}')
for row in ready_without_events[:20]:
    print(' ', row['symbol'])

# Check total event_queue size
total_events = conn.fetchone('SELECT COUNT(*) AS cnt FROM event_queue')
print(f'Total events in queue: {total_events["cnt"]}')

pending_events = conn.fetchone('SELECT COUNT(*) AS cnt FROM event_queue WHERE status = "pending"')
print(f'Pending events: {pending_events["cnt"]}')

conn.close()
