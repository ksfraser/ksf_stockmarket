#!/usr/bin/env python3
"""Generate an ATR drawdown-recovery chart for a single symbol.

Reads the per-multiple bounce-back analysis from `atr_stop_optimization`
for the given symbol and writes a PNG showing:
  • bounce_back_rate (fraction of m*ATR drops that later recovered to a
    new high) plotted against the ATR multiple m
  • the 70% "acceptable false-exit ceiling" and 50% reference lines
  • the recommended multiple (tightest m whose bounce <= threshold) marked

This replaces the old equity-curve chart, which was based on the previous
P&L-optimizing sweep that did not measure drawdown recovery.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import mysql.connector
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "ksfraser.ca"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "ksfraser_stockmarket"),
    "password": os.environ.get("DB_PASS", "Zaqwsx9sm1@"),
    "database": os.environ.get("DB_NAME", "ksfraser_stock_market"),
    "charset": "utf8mb4",
    "autocommit": True,
}


def get_rows(symbol: str) -> list:
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT atr_multiple, n_drops, bounce_back_rate, avg_recovery_days,
               max_drawdown_atr, recommended
        FROM atr_stop_optimization
        WHERE symbol = %s
        ORDER BY atr_multiple
        """,
        (symbol,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def generate_chart(symbol: str, output_path: str) -> dict[str, Any]:
    rows = get_rows(symbol)
    if not rows:
        raise ValueError(f"No sweep results for {symbol}")

    mult = [float(r[0]) for r in rows]
    n_drops = [int(r[1]) for r in rows]
    bounce = [float(r[2]) if r[2] is not None else np.nan for r in rows]
    maxdd = float(rows[0][4]) if rows[0][4] is not None else float("nan")
    rec_idx = next((i for i, r in enumerate(rows) if r[5]), None)
    rec_mult = mult[rec_idx] if rec_idx is not None else None

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(mult, bounce, "o-", color="#1f77b4", linewidth=2,
            markersize=7, label="Bounce-back rate")
    ax.axhline(0.70, color="#888888", linestyle="--", linewidth=1,
               label="70% acceptable false-exit ceiling")
    ax.axhline(0.50, color="#cccccc", linestyle=":", linewidth=1,
               label="50% reference")
    if rec_idx is not None:
        ax.plot([mult[rec_idx]], [bounce[rec_idx]], "r*", markersize=18,
                label=f"Recommended {mult[rec_idx]}x")
    ax.set_xlabel("ATR multiple  (stop placed m × ATR below running local high)")
    ax.set_ylabel("Bounce-back rate  (fraction of drops that recover to a new high)")
    ax.set_title(f"{symbol} — ATR Drawdown-Recovery   "
                 f"(recommended {rec_mult}x,  max drawdown {maxdd:.1f} ATR)")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")

    # Secondary axis: number of drop events per multiple (context)
    ax2 = ax.twinx()
    ax2.bar(mult, n_drops, width=0.06, color="#1f77b4", alpha=0.12)
    ax2.set_ylabel("Number of m×ATR drop events", color="#1f77b4")
    ax2.tick_params(axis="y", labelcolor="#1f77b4")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return {
        "symbol": symbol,
        "recommended_multiple": rec_mult,
        "max_drawdown_atr": maxdd,
        "bounce_by_multiple": {str(m): b for m, b in zip(mult, bounce)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ATR drawdown-recovery chart")
    parser.add_argument("symbol", help="Ticker symbol (e.g. RY)")
    parser.add_argument("output", help="Output PNG path")
    args = parser.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    info = generate_chart(args.symbol, args.output)
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
