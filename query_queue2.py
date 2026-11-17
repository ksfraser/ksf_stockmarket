import pymysql

db = {
    'host': 'ksfraser.ca',
    'port': 3306,
    'database': 'ksfraser_stock_market',
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': True,
}

conn = pymysql.connect(**db)
try:
    with conn.cursor() as cur:
        cur.execute("SELECT status, COUNT(*) AS cnt FROM event_queue GROUP BY status ORDER BY status")
        rows = cur.fetchall()
        print("=== STATUS HISTOGRAM ===")
        for r in rows:
            print(r['status'] + " : " + str(r['cnt']))
        total = sum(r['cnt'] for r in rows)
        print("TOTAL : " + str(total))

        cur.execute("SELECT event_id, event_type, payload, occurred_at FROM event_queue WHERE status='running' ORDER BY occurred_at ASC")
        stuck = cur.fetchall()
        print("\n=== STUCK RUNNING EVENTS ===")
        print("count: " + str(len(stuck)))
        for r in stuck:
            payload = r['payload']
            if isinstance(payload, dict):
                sym = payload.get('symbol', '')
            else:
                sym = str(payload)
            print(r['event_id'] + " | " + r['event_type'] + " | " + sym + " | " + str(r['occurred_at']))
finally:
    conn.close()
