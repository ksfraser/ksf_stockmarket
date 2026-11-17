import sys
sys.path.insert(0, '/root/Documents/stockmarket/php/stockmarket-app/python')
from config_loader import Config

cfg = Config('/root/Documents/stockmarket/php/stockmarket-app/config.yaml')
pw = cfg.db_password or cfg.secrets.get('db_password') or ''
print('DB host:', cfg.data.db_host)
print('DB port:', getattr(cfg.data, 'db_port', 3306))
print('DB name:', cfg.data.db_name)
print('DB user:', cfg.data.db_user)
print('DB password set:', bool(pw))

import pymysql
conn = pymysql.connect(
    host=cfg.data.db_host,
    port=int(getattr(cfg.data, 'db_port', 3306)),
    database=cfg.data.db_name,
    user=cfg.data.db_user,
    password=pw,
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)
cur = conn.cursor()
cur.execute("SELECT status, COUNT(*) AS c FROM event_queue GROUP BY status")
rows = cur.fetchall()
print('--- status histogram ---')
for r in rows:
    print(f"{r['status']}: {r['c']}")
cur.execute("SELECT COUNT(*) AS c FROM event_queue WHERE status='pending'")
print('pending count:', cur.fetchone()['c'])
cur.execute("SELECT COUNT(*) AS c FROM event_queue WHERE status='running'")
print('running count:', cur.fetchone()['c'])
cur.execute("SELECT COUNT(*) AS c FROM event_queue WHERE status='failed'")
print('failed count:', cur.fetchone()['c'])
conn.close()
