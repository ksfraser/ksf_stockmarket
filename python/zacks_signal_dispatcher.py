#!/usr/bin/env python3
"""
zacks_signal_dispatcher.py — Run after zacks_scraper.py --all completes.
Queries DB for bullish/bearish 4-week F1 EPS revision signals, sends
Discord notifications, and inserts into alert_queue.
"""

import sys
import os
import json
import datetime

sys.path.insert(0, os.path.dirname(__file__))

from db.mysql_adapter import MySQLConnection

DISCORD_CHANNEL = "1516481638924812489"


def get_webhook():
    """Read Discord webhook from system_settings."""
    conn = MySQLConnection(
        host=os.environ.get("DB_HOST", "ksfraser.ca"),
        user=os.environ.get("DB_USER", "ksfraser_stockmarket"),
        password=os.environ.get("DB_PASS", ""),
        database=os.environ.get("DB_NAME", "ksfraser_stock_market"),
    )
    with conn:
        row = conn.fetchone(
            "SELECT setting_value FROM system_settings WHERE setting_key = 'discord_alert_webhook'"
        )
        return row["setting_value"] if row else None


def send_discord(webhook_url: str, message: str) -> bool:
    """Send a message to Discord via webhook."""
    import requests

    try:
        resp = requests.post(
            webhook_url,
            json={"content": message, "thread_id": DISCORD_CHANNEL},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"  Discord send failed: {e}")
        return False


def insert_alert(conn, symbol: str, change_value: float, direction: str,
                 forward_eps: float, message: str):
    """Insert signal into alert_queue."""
    payload = json.dumps({
        "symbol": symbol,
        "change_value": change_value,
        "direction": direction,
        "forward_eps": forward_eps,
        "message": message,
    })
    now = datetime.datetime.utcnow()
    alert_id = f"zacks-{symbol}-{now.strftime('%Y%m%d%H%M%S')}"
    sql = """
        INSERT INTO alert_queue
        (id, alert_type, symbol, severity, payload, status, created_at)
        VALUES (%s, %s, %s, %s, %s, 'pending', %s)
    """
    conn.execute(
        sql,
        (alert_id, "zacks_eps_revision", symbol, "high", payload,
         now.strftime("%Y-%m-%d %H:%M:%S")),
    )


def get_signals(conn):
    """Fetch bullish and bearish signals using each symbol's latest fetch_date."""
    # Get the latest fetch_date per symbol that has EPS data
    latest_dates = conn.fetchall("""
        SELECT symbol, MAX(fetch_date) AS latest_date
        FROM fundamentals
        WHERE zacks_eps_change_f1_4w IS NOT NULL
        GROUP BY symbol
    """)

    if not latest_dates:
        return [], []

    # Build a list of (symbol, latest_date) and query each one
    bullish = []
    bearish = []

    for ld in latest_dates:
        symbol = ld["symbol"]
        latest = ld["latest_date"]

        row = conn.fetchone("""
            SELECT f.symbol, f.zacks_eps_change_f1_4w AS change_value,
                   f.forward_eps, sm.name
            FROM fundamentals f
            JOIN symbol_master sm ON f.symbol = sm.symbol
            WHERE f.symbol = %s AND f.fetch_date = %s
        """, (symbol, latest))

        if row and row["change_value"] is not None:
            if row["change_value"] > 0:
                bullish.append(row)
            elif row["change_value"] < 0:
                bearish.append(row)

    # Sort: bullish by change_value DESC, bearish by change_value ASC
    bullish.sort(key=lambda r: r["change_value"], reverse=True)
    bearish.sort(key=lambda r: r["change_value"])

    return bullish[:5], bearish[:5]


def main():
    webhook_url = get_webhook()
    if not webhook_url:
        print("ERROR: No Discord webhook found in system_settings")
        return

    print(f"Discord webhook: {webhook_url[:50]}...")

    conn = MySQLConnection(
        host=os.environ.get("DB_HOST", "ksfraser.ca"),
        user=os.environ.get("DB_USER", "ksfraser_stockmarket"),
        password=os.environ.get("DB_PASS", ""),
        database=os.environ.get("DB_NAME", "ksfraser_stock_market"),
    )

    with conn:
        # Get scrape stats - count of symbols with any Zacks data updated today
        row = conn.fetchone(
            "SELECT COUNT(DISTINCT symbol) AS cnt FROM fundamentals WHERE fetch_date = CURDATE()"
        )
        scraped_today = row["cnt"]
        row = conn.fetchone(
            "SELECT COUNT(DISTINCT symbol) AS cnt FROM fundamentals WHERE fetch_date = CURDATE() AND zacks_eps_change_f1_4w IS NOT NULL"
        )
        with_eps_today = row["cnt"]
        total_with_eps = conn.fetchone(
            "SELECT COUNT(DISTINCT symbol) AS cnt FROM fundamentals WHERE zacks_eps_change_f1_4w IS NOT NULL"
        )["cnt"]
        print(f"Scrape stats: {scraped_today} symbols updated today, "
              f"{with_eps_today} with EPS data today, "
              f"{total_with_eps} total with EPS data (all time)")

        bullish, bearish = get_signals(conn)

    print(f"\nBullish signals: {len(bullish)}")
    print(f"Bearish signals: {len(bearish)}")

    any_sent = False

    # Process bullish
    for sig in bullish:
        symbol = sig["symbol"]
        change = sig["change_value"]
        fwd_eps = sig["forward_eps"]
        name = sig.get("name", "")

        msg = (
            f"📈 {symbol} Zacks EPS revision alert: "
            f"4-week F1 EPS change = +{change:.2f}. "
            f"This is a leading indicator — analysts raising estimates "
            f"signals institutional accumulation ahead of price moves."
        )
        print(f"  BULLISH: {msg}")

        if send_discord(webhook_url, msg):
            any_sent = True
            with conn:
                insert_alert(conn, symbol, change, "bullish", fwd_eps, msg)
            print(f"    → Discord sent + alert_queue inserted")

    # Process bearish
    for sig in bearish:
        symbol = sig["symbol"]
        change = sig["change_value"]
        fwd_eps = sig["forward_eps"]
        name = sig.get("name", "")

        msg = (
            f"📉 {symbol} Zacks EPS revision alert: "
            f"4-week F1 EPS change = {change:.2f}. "
            f"This is a leading indicator — analysts cutting estimates "
            f"signals institutional distribution ahead of price declines."
        )
        print(f"  BEARISH: {msg}")

        if send_discord(webhook_url, msg):
            any_sent = True
            with conn:
                insert_alert(conn, symbol, change, "bearish", fwd_eps, msg)
            print(f"    → Discord sent + alert_queue inserted")

    # No signals
    if not bullish and not bearish:
        msg = (
            "📊 Zacks EPS watch: No significant 4-week F1 revisions "
            "(positive or negative) in tonight's scrape."
        )
        print(f"  NO SIGNALS: {msg}")
        if send_discord(webhook_url, msg):
            any_sent = True

    print(f"\nDone. Signals dispatched: {any_sent}")


if __name__ == "__main__":
    main()
