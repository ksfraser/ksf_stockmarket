#!/usr/bin/env python3
"""Import SQLite ta_indicators into MariaDB indicators table."""
import sqlite3, pymysql, sys

sq = sqlite3.connect('/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db')
sc = sq.cursor()
conn = pymysql.connect(host='ksfraser.ca', port=3306, user='ksfraser_stockmarket',
                       password='Zaqwsx9sm1@', database='ksfraser_stock_market',
                       charset='utf8mb4')
cur = conn.cursor()
cur.execute('SET FOREIGN_KEY_CHECKS=0')

# Column mapping
sc.execute('PRAGMA table_info(ta_indicators)')
sqlite_cols = [r[1] for r in sc.fetchall()]
cur.execute('DESCRIBE indicators')
mariadb_cols = [r[0] for r in cur.fetchall()]

def norm(n):
    n = n.lower()
    n = n.replace('bbands_', 'bb_')
    n = n.replace('_1d5', '_1_5').replace('_2d0', '_2_0').replace('_2d5', '_2_5')
    return n

mdb_norm = {norm(c): c for c in mariadb_cols}
mapping = {sc: mdb_norm[norm(sc)] for sc in sqlite_cols if norm(sc) in mdb_norm}

data_sqlite = [c for c in mapping if c not in ('symbol', 'price_date')]
data_mdb = [mapping[c] for c in data_sqlite]
all_cols = ['symbol', 'price_date'] + data_mdb
col_str = ', '.join(f'`{c}`' for c in all_cols)

select_str = ', '.join(f'"{c}"' for c in (['symbol', 'price_date'] + data_sqlite))
sc.execute(f'SELECT {select_str} FROM ta_indicators')
rows = sc.fetchall()
print(f'Rows: {len(rows):,}, Columns: {len(all_cols)}', flush=True)

# Insert one at a time but with prepared statement - faster than you'd think
insert_sql = f"INSERT IGNORE INTO indicators ({col_str}) VALUES ({','.join(['%s']*len(all_cols))})"

total = 0
errors = 0
for row in rows:
    try:
        cur.execute(insert_sql, row)
        total += 1
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f'ERR: {e}', flush=True)
    if total % 1000 == 0:
        conn.commit()
        pct = total/len(rows)*100
        print(f'  {total:,}/{len(rows):,} ({pct:.0f}%)', flush=True)

conn.commit()
cur.execute('SET FOREIGN_KEY_CHECKS=1')
cur.execute('SELECT COUNT(*) FROM indicators')
print(f'Done! Total: {cur.fetchone()[0]:,}, Inserted: {total:,}, Errors: {errors}')
conn.close()
sq.close()
