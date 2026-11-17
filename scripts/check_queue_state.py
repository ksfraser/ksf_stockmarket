import sys
sys.path.insert(0, '/root/Documents/stockmarket/php/stockmarket-app')
from config_loader import Config

cfg = Config('/root/Documents/stockmarket/php/stockmarket-app/config.yaml')
pw = cfg.db_password or cfg.secrets.get('db_password') or ''
print('db_password set:', bool(pw))
cfg_data = cfg.data
print('db_host:', cfg_data.db_host)
print('db_name:', cfg_data.db_name)
print('db_user:', cfg_data.db_user)

import pymysql
conn = pymysql.connect(
    host=cfg_data.db_host,
    port=int(getattr(cfg_data, 'db_port', 3306)),
    database=cfg_data.db_name,
    user=cfg_data.db_user,
    password=pw,
    charset='utf8mb4',
    autocommit=True,
)
cur = conn.cursor()
cur.execute("SELECT status, COUNT(*) AS c FROM event_queue GROUP BY status ORDER BY c DESC")
rows = cur.fetchall()
print('--- event_queue tally ---')
for r in rows:
    print(r[0], r[1])
conn.close()
