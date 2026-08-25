#!/usr/bin/env python3
"""
normalize_empire_units.py - idempotent fix for Empire Life (carrier_id=7)
return columns stored as DECIMALS (0.0873 == 8.73%) instead of percentages.

Empire Life was seeded from prod metadata where some series carry decimal
returns while others are already percentages (mixed). This converts ONLY the
cleanly-decimal series (every return column's absolute value < 1) to
percentages by *100. Already-percentage series (any column >= 1) are left
untouched, so the script is safe to re-run after any re-seed.

Run once after seeding Empire Life. Idempotent.

Usage:
    python3 scripts/normalize_empire_units.py
    python3 scripts/normalize_empire_units.py --db /path/seg_funds.db
"""
import argparse
import sqlite3
import sys

DEFAULT_DB = "/root/.hermes/cache/seg_funds.db"
EMPIRE_CARRIER_ID = 7
RET_COLS = [
    "yr_2019", "yr_2020", "yr_2021", "yr_2022", "yr_2023", "yr_2024", "yr_2025",
    "return_1m", "return_3m", "return_6m", "return_1y", "return_3y",
    "return_5y", "return_10y", "return_incept", "ytd_return",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    cur = con.cursor()

    # Convert series whose returns are clearly decimals: every column |value| < 1
    # AND the largest, *100, lands in [1, 100) -- i.e. original in [0.01, 1.0).
    # This is idempotent: after one pass those become >=1 and are skipped. It
    # deliberately SKIPS sub-0.01 decimals (e.g. 0.0087 -> 0.87 still <1) to
    # avoid an infinite re-conversion loop; those few are flagged for manual
    # review. Empire is a decimal-source carrier, so this is the right call.
    abs_cols = ",".join("ABS(coalesce(%s,0))" % c for c in RET_COLS)
    having = "MAX(%s) < 1 AND MAX(%s) * 100 >= 1" % (abs_cols, abs_cols)
    ids = [r[0] for r in cur.execute(
        "SELECT s.series_id FROM fund_series s "
        "JOIN funds f ON f.fund_id = s.fund_id "
        "WHERE f.carrier_id = ? GROUP BY s.series_id HAVING " + having,
        (EMPIRE_CARRIER_ID,),
    ).fetchall()]

    if not ids:
        print("Empire Life: no decimal series found (already normalized).")
        con.close()
        return

    placeholders = ",".join("?" * len(ids))
    set_clause = ", ".join("%s = %s * 100" % (c, c) for c in RET_COLS)
    cur.execute(
        "UPDATE fund_series SET %s WHERE series_id IN (%s)" % (set_clause, placeholders),
        ids,
    )
    con.commit()
    con.close()
    print("Empire Life: converted %d decimal series to percentages." % len(ids))


if __name__ == "__main__":
    main()
