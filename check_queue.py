import os
import sys
sys.path.insert(0, '/home/ksf_stockmarket/ksf_stockmarket')
sys.path.insert(0, '/home/ksf_stockmarket/ksf_stockmarket/python')
import config_loader
import pymysql

cfg = config_loader.Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')
pw = cfg.secrets.get('db_password') or os.environ.get('DB_PASS', '')
print('db_host', cfg.data.db_host)
print('db_name', cfg.data.db_name)
print('db_user', cfg.data.db_user)
print('db_port', getattr(cfg.data, 'db_port', 3306))
print('pw', repr(pw))

conn = pymysql.connect(
    host=cfg.data.db_host,
    port=int(getattr(cfg.data, 'db_port', 3306)),
    database=cfg.data.db_name,
    user=cfg.data.db_user,
    password=pw,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) AS n FROM event_queue')
row = cur.fetchone()
print('event_queue total rows:', row['n'])

cur.execute(
    'SELECT event_id, event_type, status, failed_at, attempted_at, attempts '
    'FROM event_queue '
    'ORDER BY occurred_at DESC '
    'LIMIT 10'
)
for r in cur.fetchall():
    print(r)

conn.close()
