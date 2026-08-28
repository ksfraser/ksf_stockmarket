#!/usr/bin/env python3
"""
Append a monthly performance_history snapshot for every fund series.

Idempotent per (series_id, snapshot_date) -- re-running on the 15th just
overwrites that day's row. The annual rollover (rollover_calendar_year.py)
reads the latest snapshot within a calendar year as that year's return, so
keeping this populated is what makes the Jan/Feb rollover accurate.

Usage:
    python3 scripts/snapshot_perf_history.py
"""
import segfund_db
import sys
from datetime import date

DEFAULT_DB = "/root/.hermes/cache/seg_funds.db"


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    conn, backend = segfund_db.get_conn()
    def q(sql, params=()):
        return segfund_db.run(conn, backend, sql, params)
    today = date.today().isoformat()
    rows = q(
        "SELECT series_id, return_1m, return_3m, return_6m, return_1y, "
        "return_3y, return_5y, return_10y, return_incept, ytd_return, price "
        "FROM fund_series"
    ).fetchall()
    n = 0
    for r in rows:
        q(
            "INSERT OR REPLACE INTO performance_history "
            "(series_id, snapshot_date, return_1m, return_3m, return_6m, "
            "return_1y, return_3y, return_5y, return_10y, return_incept, "
            "ytd_return, price) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (r[0], today, r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10]),
        )
        n += 1
    conn.commit()
    conn.close()
    print("snapshot %s: %d series" % (today, n))


if __name__ == "__main__":
    main()
