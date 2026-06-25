#!/usr/bin/env python3
"""Generate an ATR-stop equity curve chart for a single symbol.

Reads the best stop_factor+trailing_pct from `atr_stop_optimization` for the
given symbol, reruns the backtest, and writes a PNG showing:
  • Strategy equity curve (dollar value over time)
  • Buy & Hold reference
  • Annotated entry/exit markers

Methodology (documented in the UI):
  - Long-only.
  - Entry: close > SMA200 (long bias filter).
  - Initial stop: entry_price - stop_factor * ATR(14).
  - Trailing stop: highest_high_since_entry * (1 - trailing_pct).
  - Exit: either stop hit, or close < SMA200 * 0.95 (trend filter exit).
  - Position sizing: min(5% of capital, 1% of capital / ATR) — risk-normalized.
  - Commission: $9.99 per trade.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Any

import mysql.connector
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

REPO_ROOT = Path(__file__).resolve().parents[1]

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "ksfraser.ca"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "ksfraser_stockmarket"),
    "password": os.environ.get("DB_PASS", "Zaqwsx9sm1@"),
    "database": os.environ.get("DB_NAME", "ksfraser_stock_market"),
    "charset": "utf8mb4",
    "autocommit": True,
}


def fetch_price_data(symbol: str, start: str, end: str) -> pd.DataFrame:
    conn = mysql.connector.connect(**DB_CONFIG)
    df = pd.read_sql_query(
        """
        SELECT price_date, open as o, high as h, low as l, close as c, volume
        FROM stockprices
        WHERE symbol = %s AND price_date BETWEEN %s AND %s
        ORDER BY price_date
        """,
        conn,
        params=(symbol, start, end),
        parse_dates=["price_date"],
    )
    conn.close()
    if df.empty:
        return df
    df = df.set_index("price_date").sort_index()
    for col in ["o", "h", "l", "c", "v"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["h"].values
    low = df["l"].values
    close = df["c"].values
    tr_list = []
    for i in range(1, len(high)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        tr_list.append(tr)
    tr = np.array([0.0] + tr_list)
    return pd.Series(tr, index=df.index).rolling(period).mean()


def get_best_params(symbol: str) -> dict[str, Any] | None:
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT stop_factor, trailing_pct, pnl_pct, n_trades, win_rate, expectancy
        FROM atr_stop_optimization
        WHERE symbol = %s
        ORDER BY pnl_pct DESC
        LIMIT 1
        """,
        (symbol,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "stop_factor": float(row[0]),
        "trailing_pct": float(row[1]),
        "pnl_pct": float(row[2]),
        "n_trades": int(row[3]),
        "win_rate": float(row[4]),
        "expectancy": float(row[5]),
    }


def run_backtest_with_equity(
    df: pd.DataFrame,
    stop_factor: float,
    trailing_pct: float,
    initial_capital: float = 100_000.0,
    commission: float = 9.99,
) -> dict[str, Any]:
    df = df.copy()
    df["atr"] = calculate_atr(df)
    df = df.dropna(subset=["atr"])

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    trailing_stop = 0.0
    cash = initial_capital
    highest_high = None
    equity: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []

    # SMA200
    df["sma200"] = df["c"].rolling(200).mean()

    for i in range(len(df)):
        curr = df.iloc[i]
        dt = curr.name.strftime("%Y-%m-%d") if hasattr(curr.name, "strftime") else str(curr.name)

        if position > 0:
            equity.append({"date": dt, "value": cash + position * curr["c"]})
        else:
            equity.append({"date": dt, "value": cash})

        if position > 0 and highest_high is not None:
            highest_high = max(highest_high, curr["h"])
            new_trailing = highest_high * (1 - trailing_pct)
            if new_trailing > trailing_stop:
                trailing_stop = new_trailing

            if curr["l"] <= trailing_stop:
                pnl = (trailing_stop - entry_price) * position - commission
                cash += trailing_stop * position - commission
                trades.append({"date": dt, "type": "TRAILING", "price": trailing_stop, "pnl": pnl})
                position = 0
                trailing_stop = 0.0
                highest_high = None
                equity[-1]["value"] = cash
                continue

            if curr["l"] <= stop_price:
                pnl = (stop_price - entry_price) * position - commission
                cash += stop_price * position - commission
                trades.append({"date": dt, "type": "ATR_STOP", "price": stop_price, "pnl": pnl})
                position = 0
                trailing_stop = 0.0
                highest_high = None
                equity[-1]["value"] = cash
                continue

            if pd.notna(curr["sma200"]) and curr["c"] < curr["sma200"] * 0.95:
                pnl = (curr["c"] - entry_price) * position - commission
                cash += curr["c"] * position - commission
                trades.append({"date": dt, "type": "EXIT_SMA", "price": curr["c"], "pnl": pnl})
                position = 0
                trailing_stop = 0.0
                highest_high = None
                equity[-1]["value"] = cash
                continue

        if position == 0 and pd.notna(curr["sma200"]) and curr["c"] > curr["sma200"] and curr["atr"] > 0:
            risk_dollars = initial_capital * 0.01
            risk_size = risk_dollars / curr["atr"]
            max_size = initial_capital * 0.05
            size_dollar = min(max_size, risk_size)
            if size_dollar > 0:
                shares = size_dollar / curr["c"]
                entry_price = curr["c"]
                stop_price = entry_price - stop_factor * curr["atr"]
                highest_high = curr["h"]
                trailing_stop = highest_high * (1 - trailing_pct)
                cash -= entry_price * shares + commission
                position = shares
                trades.append({"date": dt, "type": "ENTRY", "price": entry_price, "pnl": 0.0})

    final_value = cash + position * df["c"].iloc[-1]
    equity.append({"date": df.index[-1].strftime("%Y-%m-%d"), "value": final_value})

    buy_hold = [
        {
            "date": (df.index[i].strftime("%Y-%m-%d") if hasattr(df.index[i], "strftime") else str(df.index[i])),
            "value": initial_capital * (df["c"].iloc[i] / df["c"].iloc[0]),
        }
        for i in range(len(df))
    ]

    return {
        "equity": equity,
        "buy_hold": buy_hold,
        "trades": trades,
        "final_value": final_value,
        "pnl_pct": (final_value - initial_capital) / initial_capital * 100,
    }


def generate_chart(symbol: str, output_path: str) -> dict[str, Any]:
    params = get_best_params(symbol)
    if not params:
        raise ValueError(f"No sweep results for {symbol}")

    start = "2022-01-01"
    end = date.today().isoformat()
    df = fetch_price_data(symbol, start, end)
    if df.empty:
        raise ValueError(f"No price data for {symbol}")

    result = run_backtest_with_equity(
        df,
        stop_factor=params["stop_factor"],
        trailing_pct=params["trailing_pct"],
    )

    eq = pd.DataFrame(result["equity"])
    bh = pd.DataFrame(result["buy_hold"])
    eq["date"] = pd.to_datetime(eq["date"])
    bh["date"] = pd.to_datetime(bh["date"])

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(eq["date"], eq["value"], label="ATR Stop Strategy", color="#1f77b4", linewidth=1.8)
    ax.plot(bh["date"], bh["value"], label="Buy & Hold", color="#ff7f0e", linewidth=1.8, linestyle="--")
    ax.set_title(f"{symbol} — Best ATR Stop (factor={params['stop_factor']}, trailing={params['trailing_pct']*100:.0f}%)")
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return {
        "symbol": symbol,
        "stop_factor": params["stop_factor"],
        "trailing_pct": params["trailing_pct"],
        "pnl_pct": params["pnl_pct"],
        "n_trades": params["n_trades"],
        "win_rate": params["win_rate"],
        "expectancy": params["expectancy"],
        "final_value": result["final_value"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ATR stop chart for a symbol")
    parser.add_argument("symbol", help="Ticker symbol (e.g. RY)")
    parser.add_argument("output", help="Output PNG path")
    args = parser.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    info = generate_chart(args.symbol, args.output)
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    import json
    sys.exit(main())
