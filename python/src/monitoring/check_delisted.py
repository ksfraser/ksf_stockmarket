#!/usr/bin/env python3
"""
Delisted Symbol Checker — Modular Version
========================================
Checks symbols for delisting status and updates symbol_status table.
"""

import sys
import os
import json
import argparse
from datetime import datetime, date
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yfinance as yf
from database import get_connection, log_monitoring_run
from symbol_resolver import resolve_for_yfinance


def get_symbols_to_check() -> List[Dict]:
    """Get all symbols that need delisting check from watchlist_symbols and symbol_master."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT sm.symbol, sm.exchange, 'active' as status
                FROM symbol_master sm
                WHERE sm.is_active = 1
                UNION
                SELECT ws.symbol, NULL, 'active' as status
                FROM watchlist_symbols ws
                WHERE ws.is_active = 1
                ORDER BY symbol
                LIMIT 20
            """)
            return cur.fetchall()
    finally:
        conn.close()


def check_symbol_status(symbol: str) -> Dict:
    """Check if symbol is still active via yfinance."""
    try:
        resolved = resolve_for_yfinance(symbol)
        stock = yf.Ticker(resolved)
        info = stock.info
        
        # Check for yfinance error response
        if info.get('symbol') is None or info.get('longName') is None:
            # Still might be valid for some symbols, check price history
            hist = stock.history(period='5d')
            if hist.empty or len(hist) == 0:
                return {'status': 'error', 'message': 'No price history available'}
        
        return {
            'status': 'active',
            'resolved': resolved,
            'name': info.get('longName', ''),
            'exchange': info.get('exchange', ''),
            'currency': info.get('currency', ''),
            'price': info.get('currentPrice', None),
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def run_delisted_check() -> int:
    """Run delisted check. Returns exit code."""
    symbols = get_symbols_to_check()
    
    run_id = log_monitoring_run('delisted_check', 'running', symbol_count=len(symbols))
    
    updated = []
    errors = []
    
    for sym in symbols:
        result = check_symbol_status(sym['symbol'])
        
        if result['status'] != 'active':
            errors.append({'symbol': sym['symbol'], **result})
            
            # Update status in DB
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO symbol_status (symbol, status, error_message, 
                                                  consecutive_failures)
                        VALUES (%s, %s, %s, 1)
                        ON DUPLICATE KEY UPDATE 
                            status = VALUES(status),
                            error_message = VALUES(error_message),
                            consecutive_failures = consecutive_failures + 1,
                            updated_at = NOW()
                    """, (sym['symbol'], result['status'], result.get('message')))
            finally:
                conn.close()
            updated.append(sym['symbol'])
    
    log_monitoring_run(run_id, 'success', alert_count=len(errors))
    
    if errors:
        print(f"⚠️  SYMSTATUS ALERT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        for e in errors[:10]:
            print(f"   {e['symbol']}: {e.get('message', 'unknown error')}")
        return 1
    
    print(f"✅ All symbols active — {datetime.now().strftime('%H:%M')}")
    return 0


if __name__ == '__main__':
    run_delisted_check()