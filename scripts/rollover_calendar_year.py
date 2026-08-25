#!/usr/bin/env python3
"""
Annual calendar-year rollover for the seg_fund store.

Run once in Jan/Feb. Captures the PREVIOUS calendar year's return into a new
yr_<YEAR> column on fund_series:

  - Prefers the latest performance_history snapshot taken during <YEAR>
    (the monthly cron snapshots on the 15th, so this is e.g. the Dec-15 row --
    the trailing return_1y there approximates the calendar-year return).
  - Falls back to the series' current trailing return_1y if no in-year
    snapshot exists yet (first-ever run).

This keeps adding a new year column each Feb so the volatility / drawdown
calculations in calc_pipeline.py and seg_fund_filters.py stay current without
manual schema edits. (Those scripts' ANNUAL_COLS list should be extended to
include the new column so it feeds volatility -- noted in carrier_seg_fund_sources.md.)

Usage:
    python3 scripts/rollover_calendar_year.py
"""
import sqlite3
import sys
from datetime import datetime

DEFAULT_DB = "/root/.hermes/cache/seg_funds.db"


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    con = sqlite3.connect(db)
    cur = con.cursor()
    year = datetime.now().year - 1
    col = "yr_%d" % year

    try:
        cur.execute("ALTER TABLE fund_series ADD COLUMN %s REAL" % col)
        print("added column %s" % col)
    except sqlite3.OperationalError:
        pass  # already exists

    rows = cur.execute("SELECT series_id, return_1y FROM fund_series").fetchall()
    n = 0
    for sid, cur1y in rows:
        snap = cur.execute(
            "SELECT return_1y FROM performance_history "
            "WHERE series_id=? AND snapshot_date LIKE ? "
            "ORDER BY snapshot_date DESC LIMIT 1",
            (sid, "%s-%%" % year),
        ).fetchone()
        val = snap[0] if snap and snap[0] is not None else cur1y
        cur.execute(
            "UPDATE fund_series SET %s=? WHERE series_id=?" % col, (val, sid)
        )
        n += 1
    con.commit()
    con.close()
    print("rolled over %d series into %s (prev year = %d)" % (n, col, year))


if __name__ == "__main__":
    main()
