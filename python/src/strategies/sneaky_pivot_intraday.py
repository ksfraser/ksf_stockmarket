#!/usr/bin/env python3
"""
Intraday Sneaky Pivot Backtester
=================================
Implements The Rumbers' 15-minute scalping strategy.

Requires: 15-minute OHLCV data in MariaDB intraday_15min table
"""

import os
import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def get_connection():
    """Connect to MariaDB using environment variables."""
    return pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER', 'ksfraser_stockmarket'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'ksfraser_stock_market'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def load_15min_data(symbol, date, conn=None):
    """Load 15-minute bars for a single day."""
    close_db = False
    if conn is None:
        conn = get_connection()
        close_db = True
    
    try:
        df = pd.read_sql_query("""
            SELECT datetime as ts, open as o, high as h, low as l, close as c, volume as v
            FROM intraday_15min 
            WHERE symbol = %s AND DATE(datetime) = %s
            ORDER BY datetime
        """, conn, params=(symbol, date))
        
        if df.empty:
            return None
        
        df = df.set_index('ts')
        # Filter to market hours (9:30 AM - 4:00 PM EST)
        df = df.between_time('09:30', '16:00')
        return df
    finally:
        if close_db:
            conn.close()


def detect_green_hammer(df, i):
    """Green hammer: small body near top, long lower wick (2x body minimum)."""
    o, h, l, c = df['o'].iloc[i], df['h'].iloc[i], df['l'].iloc[i], df['c'].iloc[i]
    body = abs(c - o)
    wick = c - l
    
    if body < (h - l) * 0.3 and c > o and wick > body * 2:
        return True
    return False


def detect_red_hammer(df, i):
    """Red hammer (sneaky): small red body, long lower wick."""
    o, h, l, c = df['o'].iloc[i], df['h'].iloc[i], df['l'].iloc[i], df['c'].iloc[i]
    body = abs(c - o)
    wick = h - c if c < o else h - o
    
    # Small red body with long lower wick
    if c <= o and body < (h - l) * 0.5:
        return True
    return False


def detect_upside_down_hammer(df, i):
    """Red upside-down hammer: small body, long upper wick."""
    o, h, l, c = df['o'].iloc[i], df['h'].iloc[i], df['l'].iloc[i], df['c'].iloc[i]
    body = abs(c - o)
    
    # Small body, long upper wick
    if body < (h - l) * 0.3 and (h - max(o, c)) > body * 1.5:
        return True
    return False


def sneaky_pivot_scalping(df, prev_high, prev_low, swing_high, swing_low):
    """
    Detect sneaky pivot entries based on 3-candle patterns.
    
    Returns: list of (index, signal_type, confidence) tuples
    """
    signals = []
    
    for i in range(2, len(df)):
        o, h, l, c = df['o'].iloc[i], df['h'].iloc[i], df['l'].iloc[i], df['c'].iloc[i]
        
        # Determine which zone we're in
        in_buy_zone = l < prev_low and h > swing_low
        in_sell_zone = h > prev_high and l < swing_high
        
        # BUY zone pattern: Green Hammer → Red Hammer → Upside-down Hammer
        if in_buy_zone and i >= 2:
            if (detect_green_hammer(df, i-2) and 
                detect_red_hammer(df, i-1) and 
                detect_upside_down_hammer(df, i)):
                signals.append((i, 'BUY', 80))
        
        # SELL zone pattern: Red shooting star → Green shooting star → Green shooting star
        elif in_sell_zone and i >= 2:
            # Check for shooting star patterns (long upper wick rejection)
            if (detect_upside_down_hammer(df, i-2) and 
                detect_upside_down_hammer(df, i-1) and 
                detect_upside_down_hammer(df, i)):
                signals.append((i, 'SELL', 80))
    
    return signals


def backtest_sneaky_pivot(symbol, date, conn=None):
    """Run sneaky pivot backtest for one symbol on one day."""
    df = load_15min_data(symbol, date, conn)
    
    if df is None or len(df) < 20:
        return None
    
    # Get previous day's levels for Range
    prev_df = load_15min_data(symbol, (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d'), conn)
    if prev_df is None:
        return None
    
    prev_high = prev_df['h'].max()
    prev_low = prev_df['l'].min()
    swing_high = prev_high  # Would need extended history for true swing
    swing_low = prev_low
    
    signals = sneaky_pivot_scalping(df, prev_high, prev_low, swing_high, swing_low)
    
    return {
        'symbol': symbol,
        'date': date,
        'n_bars': len(df),
        'prev_high': prev_high,
        'prev_low': prev_low,
        'signals': signals,
        'n_buys': sum(1 for s in signals if s[1] == 'BUY'),
        'n_sells': sum(1 for s in signals if s[1] == 'SELL'),
    }


if __name__ == '__main__':
    # Test with sample data
    print("Sneaky Pivot Intraday Detector")
    print("Testing pattern detection...")
    
    # Create sample data with hammer patterns
    sample = pd.DataFrame({
        'o': [100, 99, 100, 102, 101, 99],
        'h': [100, 101, 102, 102, 102, 99.5],
        'l': [95, 94, 96, 96, 95, 92],
        'c': [98, 99, 101, 101, 97, 93],
        'v': [1e6, 1e6, 1e6, 1e6, 1e6, 1e6]
    }, index=pd.date_range('2024-01-01 09:30', periods=6, freq='15min'))
    
    # Test candle pattern detection
    print(f"Bar 0: Green Hammer? {detect_green_hammer(sample, 0)}")
    print(f"Bar 1: Red Hammer? {detect_red_hammer(sample, 1)}")
    print(f"Bar 2: Upside-down Hammer? {detect_upside_down_hammer(sample, 2)}")
    
    print("\nNote: Requires intraday_15min table in MariaDB with 15-min OHLCV data")