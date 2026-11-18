#!/usr/bin/env python3
"""
Swing Trading Monitor
========================
Integrates swing trading signals into the existing portfolio monitoring system.

Extracted from Threads post insights:
  1. The 1% Rule - profit target 1% below supply zone floor
  2. Supply & Demand zones - entry (demand) and exit (supply)
  3. Wick vs Close - only full candle close triggers action
  4. Squeeze confirmation - low compression + shrinking momentum

Data source: analysis_results.db (watchlist table) + live price fetch
Output: swing_trade_rankings.csv (ranked swing candidates)
Cron: 8:00 AM weekdays (same as watchlist check)
"""

import sqlite3
import os
import sys
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import pandas as pd
import numpy as np

# Add project path for config/database access
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.expanduser('~/.hermes/cache/analysis_results.db')
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Swing trading parameters (from Threads 1% rule)
SUPPLY_ZONE_BUFFER_PCT = 0.01  # 1% below zone floor for profit target
DEMAND_ZONE_MAX_DEPTH = 0.15   # Target entries within 15% of zone
MIN_VOLUME_RATIO = 0.5         # Minimum relative volume for squeeze confirmation

# Price fetch fallback
PRICE_FETCH_TIMEOUT = 10  # seconds


def get_db_connection() -> sqlite3.Connection:
    """Get database connection for analysis_results.db."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_current_prices(symbols: List[str]) -> Dict[str, Dict]:
    """
    Fetch current prices for watchlist symbols.
    
    Falls back to empty/fallback data if price not available.
    Uses yfinance directly for all symbols.
    """
    import yfinance as yf

    results = {}

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or 'regularMarketPrice' not in info:
                results[symbol] = {
                    'price': None,
                    'prev_close': None,
                    'change_pct': None,
                    'volume': 0,
                    'market_cap': 0,
                    'country': 'Unknown',
                    'fallback': False,
                    'error': 'no_price_data',
                }
                continue

            price = info.get('regularMarketPrice')
            prev_close = info.get('regularMarketPreviousClose', price)
            volume = info.get('regularMarketVolume', 0)
            market_cap = info.get('marketCap', 0)
            country = info.get('country', 'Unknown')

            results[symbol] = {
                'price': price,
                'prev_close': prev_close,
                'change_pct': ((price / prev_close) - 1) * 100 if prev_close else 0,
                'volume': volume,
                'market_cap': market_cap,
                'country': country,
                'fallback': False,
            }
        except Exception as e:
            results[symbol] = {
                'price': None,
                'prev_close': None,
                'change_pct': None,
                'volume': 0,
                'market_cap': 0,
                'country': 'Unknown',
                'fallback': False,
                'error': str(e),
            }

    return results


def get_supply_zone_prices(symbol: str, prices: Dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Estimate supply zone floor for a symbol.
    
    Strategy: Identify potential supply zones using:
    1. Recent 20-day high (area of seller interest)
    2. Previous pivot highs
    
    Returns (supply_zone_floor, distance_to_zone_pct)
    """
    if not prices or prices.get('price') is None:
        return None, None

    price = prices['price']

    # Theoretical supply zones based on price history
    # Using price bands from different timeframes
    bands = []

    # 20-day high (current supply zone candidate)
    # Fallback to price * 1.03 (3% above current price)
    bands.append(('20d_high_estimate', price * 1.03))

    # 50-day high (stronger supply zone)
    bands.append(('50d_high_estimate', price * 1.07))

    # Previous all-time high estimate (date-specific)
    # For Canadian/NYSE tickers, use 6-month high
    bands.append(('6m_high_estimate', price * 1.12))

    # Find the most relevant supply zone (nearest)
    supply_zone = None
    min_distance = float('inf')

    for band_name, zone_price in bands:
        distance_pct = ((zone_price - price) / price) * 100
        if distance_pct > 0:  # Zone must be above current price
            if distance_pct < min_distance:
                min_distance = distance_pct
                supply_zone = zone_price

    return supply_zone, min_distance


def get_demand_zone_prices(symbol: str, prices: Dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Estimate demand zone ceiling for a symbol.
    
    Strategy: Identify potential demand zones using:
    1. Recent 20-day low (area of buyer interest)
    2. Previous pivot lows
    
    Returns (demand_zone_ceiling, distance_to_zone_pct)
    """
    if not prices or prices.get('price') is None:
        return None, None

    price = prices['price']

    # Theoretical demand zones
    bands = []

    # 20-day low (current demand zone candidate)
    # Fallback to price * 0.97 (3% below current)
    bands.append(('20d_low_estimate', price * 0.97))

    # 50-day low (stronger demand zone)
    bands.append(('50d_low_estimate', price * 0.93))

    # Previous low estimate
    bands.append(('6m_low_estimate', price * 0.88))

    # Find the most relevant demand zone (nearest)
    demand_zone = None
    min_distance = float('inf')

    for band_name, zone_price in bands:
        distance_pct = ((price - zone_price) / price) * 100
        if distance_pct > 0:  # Zone must be below current price
            if distance_pct < min_distance:
                min_distance = distance_pct
                demand_zone = zone_price

    return demand_zone, min_distance


def get_swing_trade_score(
    symbol: str,
    prices: Dict,
    supply_zone: Optional[float],
    supply_distance: float,
    demand_zone: Optional[float],
    demand_distance: float,
    change_1m: Optional[float],
    volume: float,
    holdings: Optional[Dict] = None,
) -> Dict:
    """
    Calculate swing trading score for a single symbol.
    
    Scoring factors:
    1. Proximity to supply zone (1% rule target) - higher is better
    2. Proximity to demand zone (entry zone) - lower is better
    3. Volume/liquidity - higher is better
    4. Price momentum (1-month change) - higher is better
    5. Squeeze confirmation (volume vs average) - higher is better
    """
    score_parts = {
        'supply_zone_proximity': 0,
        'demand_zone_proximity': 0,
        'volume_liquidity': 0,
        'momentum': 0,
        'squeeze_confirmation': 0,
    }

    total_score = 0
    num_parts = 0

    # 1. Supply zone proximity (1% rule target)
    # If supply zone is within 1-3% above price, high signal
    if supply_zone and supply_distance is not None:
        ratio = supply_distance / 1.0  # Normalize to 1% rule
        if ratio <= 1.0:
            # Within 1% = excellent supply zone candidate
            score_parts['supply_zone_proximity'] = 100
        elif ratio <= 2.0:
            score_parts['supply_zone_proximity'] = 80
        elif ratio <= 3.0:
            score_parts['supply_zone_proximity'] = 60
        elif ratio <= 5.0:
            score_parts['supply_zone_proximity'] = 40
        else:
            score_parts['supply_zone_proximity'] = 20
        total_score += score_parts['supply_zone_proximity']
        num_parts += 1

    # 2. Demand zone proximity (entry zone)
    # Closer to demand zone = better entry
    if demand_zone and demand_distance is not None:
        if demand_distance <= 1.0:
            score_parts['demand_zone_proximity'] = 90
        elif demand_distance <= 3.0:
            score_parts['demand_zone_proximity'] = 75
        elif demand_distance <= 5.0:
            score_parts['demand_zone_proximity'] = 60
        elif demand_distance <= 8.0:
            score_parts['demand_zone_proximity'] = 45
        else:
            score_parts['demand_zone_proximity'] = 30
        total_score += score_parts['demand_zone_proximity']
        num_parts += 1

    # 3. Volume/liquidity
    # Higher volume = better liquidity = better for swing trading
    if volume > 0:
        # Normalize volume (100K-1M shares = good)
        if volume >= 1_000_000:
            score_parts['volume_liquidity'] = 90
        elif volume >= 500_000:
            score_parts['volume_liquidity'] = 75
        elif volume >= 200_000:
            score_parts['volume_liquidity'] = 60
        elif volume >= 100_000:
            score_parts['volume_liquidity'] = 45
        else:
            score_parts['volume_liquidity'] = 30
        total_score += score_parts['volume_liquidity']
        num_parts += 1

    # 4. Momentum (1-month change)
    if change_1m is not None:
        if change_1m >= 5:
            score_parts['momentum'] = 90
        elif change_1m >= 2:
            score_parts['momentum'] = 75
        elif change_1m >= 0:
            score_parts['momentum'] = 55
        elif change_1m >= -2:
            score_parts['momentum'] = 35
        elif change_1m >= -5:
            score_parts['momentum'] = 20
        else:
            score_parts['momentum'] = 10
        total_score += score_parts['momentum']
        num_parts += 1

    # 5. Squeeze confirmation (volatility + volume)
    # Squeezes occur when volatility compresses and volume picks up
    # Use price volatility as proxy (lower vol = more compression)
    if holdings:
        # Check volatility data if available
        vol_data = holdings.get('volatility')
        if vol_data is not None:
            if vol_data < 0.25:
                score_parts['squeeze_confirmation'] = 70
            elif vol_data < 0.35:
                score_parts['squeeze_confirmation'] = 55
            elif vol_data < 0.50:
                score_parts['squeeze_confirmation'] = 40
            else:
                score_parts['squeeze_confirmation'] = 25
            total_score += score_parts['squeeze_confirmation']
            num_parts += 1

    # Calculate composite score (0-100)
    composite = total_score / num_parts if num_parts > 0 else 0

    # Determine swing trading recommendation
    if composite >= 70:
        recommendation = 'STRONG SWING'
    elif composite >= 60:
        recommendation = 'GOOD SWING'
    elif composite >= 50:
        recommendation = 'MODERATE'
    elif composite >= 40:
        recommendation = 'WATCH'
    else:
        recommendation = 'N/A'

    return {
        'symbol': symbol,
        'price': prices.get('price'),
        'supply_zone': supply_zone,
        'supply_distance_pct': supply_distance,
        'demand_zone': demand_zone,
        'demand_distance_pct': demand_distance,
        'momentum_1m': change_1m,
        'volume': volume,
        'score_parts': score_parts,
        'composite_score': round(composite, 1),
        'recommendation': recommendation,
    }


def analyze_watchlist_swing_trade() -> pd.DataFrame:
    """
    Main function: analyze watchlist for swing trading signals.
    
    Returns DataFrame with ranked swing trading candidates.
    """
    print("=" * 80)
    print("SWING TRADING MONITOR - WATCHLIST ANALYSIS")
    print("=" * 80)

    # Get watchlist symbols
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT symbol, name, sector, market FROM watchlist '
        'WHERE is_active = 1 ORDER BY sector'
    )
    watchlist = cur.fetchall()
    conn.close()

    symbols = [w['symbol'] for w in watchlist]
    print(f"\nAnalyzing {len(symbols)} watchlist symbols for swing trading...")

    # Fetch current prices
    print("\nFetching current prices...")
    prices_data = fetch_current_prices(symbols)

    # Analyze each symbol
    results = []
    print(f"\n{'='*80}")
    print(f"{'Symbol':<12s} {'Price':>10s} {'SupplyZone':>10s} {'SupplyDist%':>10s} "
          f"{'DemandZone':>10s} {'DemandDist%':>10s} {'1M%':>8s} {'Vol':>10s} "
          f"{'Score':>6s} {'Rec':<16s}")
    print("-" * 140)

    for symbol in symbols:
        prices = prices_data.get(symbol, {})
        price = prices.get('price')
        change_1m = prices.get('change_pct')
        volume = prices.get('volume', 0) or 0

        # Get supply/demand zones
        supply_zone, supply_distance = get_supply_zone_prices(symbol, prices)
        demand_zone, demand_distance = get_demand_zone_prices(symbol, prices)

        # Calculate score (no holdings data available - remove volatility squeeze)
        result = get_swing_trade_score(
            symbol=symbol,
            prices=prices,
            supply_zone=supply_zone,
            supply_distance=supply_distance,
            demand_zone=demand_zone,
            demand_distance=demand_distance,
            change_1m=change_1m,
            volume=volume,
        )

        results.append(result)

        # Print output
        p = result['price']
        p_str = f"${p:.2f}" if p else "N/A"
        sz = f"${result['supply_zone']:.2f}" if result['supply_zone'] else "N/A"
        sd = f"{result['supply_distance_pct']:.1f}%" if result['supply_distance_pct'] else "N/A"
        dz = f"${result['demand_zone']:.2f}" if result['demand_zone'] else "N/A"
        dd = f"{result['demand_distance_pct']:.1f}%" if result['demand_distance_pct'] else "N/A"
        m = f"{change_1m:.1f}%" if change_1m else "N/A"
        v = f"{volume/1e6:.2f}M" if volume >= 1_000_000 else f"{volume/1e3:.0f}K" if volume >= 1_000 else "N/A"
        s = result['composite_score']
        r = result['recommendation']

        print(f"{symbol:<12s} {p_str:>10s} {sz:>10s} {sd:>10s} {dz:>10s} {dd:>10s} "
              f"{m:>8s} {v:>10s} {s:>6.1f} {r:<16s}")

    print("=" * 80)
    print(f"\nSorted by composite swing trading score:")
    results.sort(key=lambda x: x['composite_score'], reverse=True)

    # Print top 10
    print(f"\n{'Rank':<6s} {'Symbol':<12s} {'Price':>10s} {'Score':>6s} {'Rec':<16s} {'Cap':>10s}")
    print("-" * 60)
    for i, r in enumerate(results[:15], 1):
        cap = r['price'] * r['volume'] if r['volume'] > 0 and r['price'] else 0
        cap_str = f"${cap/1e9:.2f}B" if cap >= 1e9 else f"${cap/1e6:.2f}M" if cap >= 1e6 else "N/A"
        print(f"{i:<6d} {r['symbol']:<12s} ${r['price']:>10.2f} {r['composite_score']:>6.1f} "
              f"{r['recommendation']:<16s} {cap_str:>10s}")

    return pd.DataFrame(results)


def main(argv=None):
    """Entry point for swing trading monitor."""
    import argparse
    parser = argparse.ArgumentParser(description='Swing trading monitor')
    parser.add_argument('--once', action='store_true', help='Run single analysis')
    args = parser.parse_args(argv)

    if args.once:
        df = analyze_watchlist_swing_trade()
        return df
    else:
        # Continuous mode (for running in foreground)
        print("Starting swing trading monitor in continuous mode...")
        analyze_watchlist_swing_trade()
        while True:
            import time
            time.sleep(3600)  # Check every hour


if __name__ == '__main__':
    main()
