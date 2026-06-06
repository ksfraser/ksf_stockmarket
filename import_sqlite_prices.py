#!/usr/bin/env python3
"""Import missing SQLite price data into MariaDB for symbols that need it."""
import sqlite3, pymysql

sq = sqlite3.connect('/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db')
sc = sq.cursor()
conn = pymysql.connect(host='ksfraser.ca', port=3306, user='ksfraser_stockmarket',
                       password='Zaqwsx9sm1@', database='ksfraser_stock_market',
                       charset='utf8mb4')
cur = conn.cursor()
cur.execute('SET FOREIGN_KEY_CHECKS=0')

# Symbols that need more data
need_update = ['BPF.UN', 'PDC', 'RUS', 'SRV.UN', 'TFII']

insert_sql = """INSERT IGNORE INTO stockprices 
    (symbol, price_date, open, high, low, close, volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s)"""

total = 0
for sym in need_update:
    sc.execute('SELECT symbol, price_date, day_open, day_high, day_low, day_close, volume FROM stockprices WHERE symbol=?', (sym,))
    rows = sc.fetchall()
    print(f'{sym}: {len(rows):,} rows in SQLite', flush=True)
    
    for row in rows:
        try:
            cur.execute(insert_sql, row)
            total += 1
        except Exception as e:
            pass  # ignore duplicates
    
    conn.commit()
    
    # Verify
    cur.execute('SELECT COUNT(*) FROM stockprices WHERE symbol=%s', (sym,))
    print(f'  -> MariaDB now: {cur.fetchone()[0]:,} rows', flush=True)

cur.execute('SELECT COUNT(*) FROM stockprices')
print(f'\nTotal stockprices: {cur.fetchone()[0]:,}')
print(f'New rows inserted: {total:,}')

cur.execute('SET FOREIGN_KEY_CHECKS=1')
conn.close()
sq.close()
