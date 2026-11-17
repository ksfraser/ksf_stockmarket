#!/usr/bin/env python3
import os
import subprocess
import sys

REPO = "/root/Documents/stockmarket/php/stockmarket-app"

# Decrypt the vault to get the db password
vault_path = os.path.join(REPO, "group_vars", "vault.yml")
pw_file = "/home/ksf_stockmarket/.vault_pass"
result = subprocess.run(
    ["ansible-vault", "view", "--vault-password-file", pw_file, vault_path],
    capture_output=True, text=True,
)
if result.returncode != 0:
    print("VAULT_DECRYPT_FAILED:", result.stderr.strip(), file=sys.stderr)
    sys.exit(1)
import yaml
data = yaml.safe_load(result.stdout) or {}
db_password = data.get("db_password", "") if isinstance(data, dict) else ""

print("DB_PASS_SET:", bool(db_password))

import pymysql
conn = pymysql.connect(
    host="ksfraser.ca", port=3306,
    database="ksfraser_stock_market",
    user="ksfraser_stockmarket",
    password=db_password,
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)
cur = conn.cursor()
cur.execute("SELECT event_id, event_type, status, occurred_at, attempts FROM event_queue ORDER BY occurred_at ASC")
rows = cur.fetchall()
print("ROWS:")
for r in rows:
    print(r)
cur.execute("SELECT COUNT(*) AS n FROM event_queue")
print("TOTAL:", cur.fetchone()["n"])
cur.execute("SELECT status, COUNT(*) AS n FROM event_queue GROUP BY status")
print("BY_STATUS:")
for r in cur.fetchall():
    print(r)
conn.close()
