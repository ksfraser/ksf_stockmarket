#!/usr/bin/env python3
"""
ATR Stop Factor Parameter Sweep for MariaDB
Runs walk-forward backtest to find optimal ATR stop parameters per symbol
Tests: stop_factor (ATR multiplier) and trailing_stop_pct
"""
import os
import sys
import json
import time
import signal
import logging
from datetime import datetime, date
import pandas as pd
import numpy as np

# MariaDB connection
import mysql.connector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'ksfraser.ca'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'ksfraser_stockmarket'),
    'password': os.environ.get('DB_PASS', 'Zaqwsx9sm1@'),
    'database': os.environ.get('DB_NAME', 'ksfraser_stock_market'),
    'charset': 'utf8mb4',
    'autocommit': True,
    'connection_timeout': 60,
    'pool_name': 'ksf_atr_sweep',
    'pool_size': 3,
}

_POOL = mysql.connector.pooling.MySQLConnectionPool(
    pool_name=DB_CONFIG['pool_name'],
    pool_size=DB_CONFIG['pool_size'],
    **{k: v for k, v in DB_CONFIG.items() if k not in ('pool_name', 'pool_size')}
)


def get_connection():
    """Get pooled MariaDB connection."""
    return _POOL.get_connection()

def fetch_price_data(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV data for a symbol."""
    conn = get_connection()
    df = pd.read_sql_query(f"""
        SELECT price_date, open as o, high as h,
               low as l, close as c, volume as v
        FROM stockprices
        WHERE symbol = %s AND price_date BETWEEN %s AND %s
        ORDER BY price_date
    """, conn, params=(symbol, start, end), parse_dates=['price_date'])
    conn.close()
    if df.empty:
        return df
    df = df.set_index('price_date').sort_index()
    for col in ['o','h','l','c','v']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def fetch_portfolio_symbols() -> list:
    """Get symbols currently held in portfolio."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM portfolio WHERE shares > 0")
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return symbols

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR using Ta-Lib style formula."""
    high = df['h'].values
    low = df['l'].values
    close = df['c'].values
    
    tr_list = []
    for i in range(1, len(high)):
        tr = max(high[i] - low[i], 
                 abs(high[i] - close[i-1]), 
                 abs(low[i] - close[i-1]))
        tr_list.append(tr)
    
    tr = np.array([0] + tr_list)
    atr = pd.Series(tr, index=df.index).rolling(period).mean()
    return atr

def run_backtest(df: pd.DataFrame, stop_factor: float = 2.0, trailing_pct: float = 0.10, initial_capital: float = 100000) -> dict:
    """Run backtest with ATR stop + trailing stop."""
    if df.empty or len(df) < 60:
        return {'error': 'Insufficient data'}
    
    df = df.copy()
    df['atr'] = calculate_atr(df)
    df = df.dropna(subset=['atr'])
    
    position = 0
    entry_price = 0
    stop_price = 0
    trailing_stop = 0
    cash = initial_capital
    trades = []
    highest_high = None
    
    for i in range(20, len(df)):
        curr = df.iloc[i]
        
        # Update trailing stop (working copy: highest high since entry - trailing_pct)
        if position > 0 and highest_high is not None:
            highest_high = max(highest_high, curr['h'])
            new_trailing_stop = highest_high * (1 - trailing_pct)
            if new_trailing_stop > trailing_stop:
                trailing_stop = new_trailing_stop
            
            # Check trailing stop hit
            if curr['l'] <= trailing_stop:
                pnl = (trailing_stop - entry_price) * position - 9.95
                cash += trailing_stop * position - 9.95
                trades.append({'type': 'TRAILING', 'price': trailing_stop, 'pnl': pnl})
                position = 0
                trailing_stop = 0
                highest_high = None
                continue
            
            # Check ATR stop hit
            if curr['l'] <= stop_price:
                pnl = (stop_price - entry_price) * position - 9.95
                cash += stop_price * position - 9.95
                trades.append({'type': 'ATR_STOP', 'price': stop_price, 'pnl': pnl})
                position = 0
                trailing_stop = 0
                highest_high = None
                continue
        
        # Simple entry: price > SMA200 (long bias)
        sma200 = df['c'].iloc[i-200:i].mean() if i >= 200 else df['c'].iloc[i-20:i].mean()
        
        if position == 0 and curr['c'] > sma200 and curr['atr'] > 0:
            # Position sizing: min(max_pct_portfolio, risk_based_size)
            risk_size = (initial_capital * 0.01) / curr['atr']  # $1000 risk / ATR
            max_size = initial_capital * 0.05  # 5% max position
            size_dollar = min(max_size, risk_size)
            
            if size_dollar > 0:
                position = size_dollar / curr['c']
                entry_price = curr['c']
                stop_price = curr['c'] - stop_factor * curr['atr']
                highest_high = curr['h']
                trailing_stop = highest_high * (1 - trailing_pct)
                cash -= entry_price * position + 9.95
                trades.append({'type': 'ENTRY', 'price': entry_price, 'pnl': 0})
        
        # Exit on SMA crossover (below 200)
        elif position > 0 and curr['c'] < sma200 * 0.95:
            pnl = (curr['c'] - entry_price) * position - 9.95
            cash += curr['c'] * position - 9.95
            trades.append({'type': 'EXIT', 'price': curr['c'], 'pnl': pnl})
            position = 0
            trailing_stop = 0
            highest_high = None
    
    final_value = cash + position * df['c'].iloc[-1]
    pnl = final_value - initial_capital
    pnl_pct = pnl / initial_capital * 100
    
    wins = [t['pnl'] for t in trades if t['type'] != 'ENTRY' and t['pnl'] > 0]
    losses = [t['pnl'] for t in trades if t['type'] != 'ENTRY' and t['pnl'] <= 0]
    
    return {
        'final_value': final_value,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'n_trades': len([t for t in trades if t['type'] != 'ENTRY']),
        'win_rate': len(wins) / len([t for t in trades if t['type'] != 'ENTRY' and t['pnl'] != 0]) * 100 if [t for t in trades if t['type'] != 'ENTRY' and t['pnl'] != 0] else 0,
        'avg_win': np.mean(wins) if wins else 0,
        'avg_loss': np.mean(losses) if losses else 0,
        'expectancy': ((len(wins) * (np.mean(wins) if wins else 0) + len(losses) * (np.mean(losses) if losses else 0)) / len([t for t in trades if t['type'] != 'ENTRY'])) if [t for t in trades if t['type'] != 'ENTRY'] else 0
    }

def main():
    """Run parameter sweep."""
    symbols = fetch_portfolio_symbols()
    logger.info(f"Testing {len(symbols)} portfolio symbols: {symbols}")
    
    start_date = '2022-01-01'
    end_date = str(date.today())
    
    stop_factors = [1.5, 2.0, 2.5, 3.0]
    trailing_pcts = [0.05, 0.07, 0.10, 0.12]
    initial_capital = 100000
    
    # Create output table
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atr_stop_optimization (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            ts TEXT,
            symbol TEXT,
            stop_factor REAL,
            trailing_pct REAL,
            pnl REAL,
            pnl_pct REAL,
            n_trades INTEGER,
            win_rate REAL,
            avg_win REAL,
            avg_loss REAL,
            expectancy REAL,
            final_value REAL
        )
    """)
    # Add trailing_pct column if missing
    cursor.execute("SHOW COLUMNS FROM atr_stop_optimization LIKE 'trailing_pct'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE atr_stop_optimization ADD COLUMN trailing_pct REAL")
    conn.commit()
    conn.close()
    
    results = []
    for symbol in symbols:
        df = fetch_price_data(symbol, start_date, end_date)
        if df.empty:
            logger.warning(f"No data for {symbol}")
            continue
        
        for stop_factor in stop_factors:
            for trailing_pct in trailing_pcts:
                try:
                    result = run_backtest(df, stop_factor, trailing_pct, initial_capital)
                    if 'error' not in result:
                        result['symbol'] = symbol
                        result['stop_factor'] = stop_factor
                        result['trailing_pct'] = trailing_pct
                        results.append(result)
                        
                        # Insert into DB
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO atr_stop_optimization 
                            (ts, symbol, stop_factor, trailing_pct, pnl, pnl_pct, n_trades, win_rate, avg_win, avg_loss, expectancy, final_value)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            datetime.now().isoformat(), symbol, stop_factor, trailing_pct,
                            result['pnl'], result['pnl_pct'], result['n_trades'],
                            result['win_rate'], result['avg_win'], result['avg_loss'],
                            result['expectancy'], result['final_value']
                        ))
                        conn.commit()
                        conn.close()
                        logger.info(f"{symbol} stop={stop_factor}× trailing={trailing_pct}: PnL={result['pnl_pct']:.2f}%, Trades={result['n_trades']}")
                except Exception as e:
                    logger.error(f"Error for {symbol}: {e}")
    
    # Summary
    if results:
        print("\n=== TOP 10 RESULTS BY PnL ===")
        sorted_results = sorted(results, key=lambda x: x['pnl_pct'], reverse=True)[:10]
        for r in sorted_results:
            print(f"{r['symbol']} stop={r['stop_factor']}× trailing={r['trailing_pct']}%: PnL={r['pnl_pct']:.2f}% Trades={r['n_trades']}")
        
        print("\n=== AVERAGE BY STOP FACTOR ===")
        by_factor = {}
        for r in results:
            sf = r['stop_factor']
            if sf not in by_factor:
                by_factor[sf] = []
            by_factor[sf].append(r)
        
        for sf in sorted(by_factor.keys()):
            avg_pnl = np.mean([r['pnl_pct'] for r in by_factor[sf]])
            logger.info(f"Stop {sf}×: Avg PnL {avg_pnl:.2f}%")

if __name__ == '__main__':
    main()