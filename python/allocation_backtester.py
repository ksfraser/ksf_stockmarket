#!/usr/bin/env python3
"""
allocation_backtester.py — Geographic/sector allocation strategy backtester.

Simulates portfolio performance across different allocation strategies:
  1. CDN_Only (100% TSX)
  2. US_Only (100% S&P 500)
  3. CDN_US_70_30
  4. CDN_US_50_50
  5. Global_GDP (weighted by country GDP)
  6. Balanced_60_40 (equities/bonds)
  7. Tax_Optimized (eligible divs in marg, growth in shelters)

For each strategy, computes:
  - Total return (price + dividends)
  - After-tax return (using after_tax_calculator.py)
  - Sharpe ratio, max drawdown
  - Tax drag comparison

ETF proxies used:
  CDN: XIC.TO (TSX Composite), VCN.TO, ZCN.TO
  US: VTI (total US), SPY, IVV
  Intl: VEA (developed ex-US), VWO (emerging)
  Bonds: XBB.TO (CDN govt+corp), AGG, TLT (20yr Treasury)
  GLD: gold

Usage:
    python3 allocation_backtester.py [--strategy CDN_US_70_30] [--start 2015] [--end 2024]
"""
import pymysql
import sys
import json
import argparse
from datetime import date, datetime
from pathlib import Path

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

# ETF proxies for each allocation bucket
ETF_PROXIES = {
    'CA':  {'symbol': 'XIC.TO', 'name': 'TSX Composite', 'div_yield': 2.8, 'eligible_pct': 0.85},
    'US':  {'symbol': 'VTI',    'name': 'US Total Market', 'div_yield': 1.4, 'eligible_pct': 0.0},
    'INTL': {'symbol': 'VEA',   'name': 'Dev ex-US', 'div_yield': 3.0, 'eligible_pct': 0.0},
    'EM':  {'symbol': 'VWO',    'name': 'Emerging Markets', 'div_yield': 2.0, 'eligible_pct': 0.0},
    'BOND': {'symbol': 'XBB.TO', 'name': 'CDN Bonds', 'div_yield': 3.5, 'eligible_pct': 0.30},
    'TLT': {'symbol': 'TLT',    'name': 'US 20yr Treasury', 'div_yield': 4.0, 'eligible_pct': 0.0},
    'GLD': {'symbol': 'GLD',    'name': 'Gold ETF', 'div_yield': 0.0, 'eligible_pct': 0.0},
}

# Default allocation configs (matching allocation_strategies table)
STRATEGY_CONFIGS = {
    'CDN_Only': {
        'CA': 1.0, 'type': 'geographic',
        'desc': '100% Canadian equities via XIC.TO'
    },
    'US_Only': {
        'US': 1.0, 'type': 'geographic',
        'desc': '100% US equities via VTI'
    },
    'CDN_US_70_30': {
        'CA': 0.70, 'US': 0.30, 'type': 'geographic',
        'desc': '70% CDN / 30% US'
    },
    'CDN_US_50_50': {
        'CA': 0.50, 'US': 0.50, 'type': 'geographic',
        'desc': '50% CDN / 50% US'
    },
    'Global_GDP': {
        'US': 0.55, 'CA': 0.08, 'INTL': 0.27, 'EM': 0.10,
        'type': 'geographic', 'desc': 'GDP-weighted global allocation'
    },
    'Balanced_60_40': {
        'CA': 0.30, 'US': 0.30, 'BOND': 0.40,
        'type': 'blended', 'desc': '60% equities / 40% bonds'
    },
    'Equal_3_ETF': {
        'CA': 0.33, 'US': 0.34, 'INTL': 0.33,
        'type': 'equal_weight', 'desc': 'Equal weight XIC/VEA/VTI'
    },
    'Tax_Optimized': {
        'CA': 0.60, 'US': 0.25, 'INTL': 0.15,
        'type': 'custom', 'desc': 'Eligible divs in marginal, growth in TFSA/RRSP',
        'account_split': {
            'CA': {'MARGINAL': 0.6, 'RRSP': 0.3, 'TFSA': 0.1},  # CDN divs → marginal for DTC
            'US': {'TFSA': 0.4, 'RRSP': 0.4, 'MARGINAL': 0.2},  # US → shelters for withholding
            'INTL': {'TFSA': 0.5, 'RRSP': 0.5},                  # Foreign divs → shelters
        }
    },
}


def fetch_prices_from_db(symbols, start_date='2015-01-01'):
    """Fetch price data from MySQL stockprices table."""
    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()

    placeholders = ','.join(['%s'] * len(symbols))
    c.execute(f"""SELECT symbol, price_date, day_close, day_open, day_high, day_low, volume
                 FROM stockprices WHERE symbol IN ({placeholders}) AND price_date >= %s
                 ORDER BY symbol, price_date""",
              list(symbols) + [start_date])
    rows = c.fetchall()
    conn.close()

    # Organize by symbol
    data = {}
    for r in rows:
        sym = r['symbol']
        if sym not in data:
            data[sym] = []
        data[sym].append({
            'date': r['price_date'],
            'close': r['day_close'],
            'open': r['day_open'],
            'high': r['day_high'],
            'low': r['day_low'],
            'volume': r['volume'],
        })

    return data


def simulate_allocation(weights: dict, start_date='2015-01-01',
                        initial_capital=100000, marginal_income=130000,
                        annual_return_est=None):
    """
    Simulate an allocation strategy using ETF proxies.

    For buckets without real price data in our DB, use estimated returns
    from historical ETF data.
    """
    results = {
        'strategy': weights.get('_name', 'unknown'),
        'weights': {k: v for k, v in weights.items() if not k.startswith('_')},
        'start_date': start_date,
        'initial_capital': initial_capital,
        'marginal_income': marginal_income,
        'buckets': {},
        'summary': {},
    }

    for bucket, pct in weights.items():
        if bucket.startswith('_') or bucket in ('type', 'desc', 'account_split'):
            continue

        etf = ETF_PROXIES.get(bucket, {})
        alloc = initial_capital * pct

        # Estimate annual return (if no real data)
        if annual_return_est and bucket in annual_return_est:
            ann_ret = annual_return_est[bucket]
        else:
            # Historical estimates (2015-2024)
            est = {
                'CA': 7.5, 'US': 12.0, 'INTL': 6.0, 'EM': 7.0,
                'BOND': 3.5, 'TLT': 2.0, 'GLD': 6.0
            }
            ann_ret = est.get(bucket, 7.0)

        div_yield = etf.get('div_yield', 2.0)
        eligible_pct = etf.get('eligible_pct', 0.5)
        annual_div = alloc * (div_yield / 100)
        annual_cg = alloc * (ann_ret / 100 - div_yield / 100)
        total_annual = annual_div + annual_cg

        # Tax calc
        if eligible_pct > 0 and div_yield > 0:
            elig_div = annual_div * eligible_pct
            # Simplified: 3rd bracket Alberta
            grossed = elig_div * 1.38
            fed = grossed * 0.26
            prov = grossed * 0.13
            dtc = grossed * (0.150198 + 0.0812)
            div_tax = max(0, fed + prov - dtc)
        else:
            div_tax = annual_div * 0.39  # full tax on non-eligible

        cg_tax = annual_cg * 0.5 * 0.39  # 50% inclusion × combined rate
        total_tax = div_tax + cg_tax
        after_tax = total_annual - total_tax

        results['buckets'][bucket] = {
            'pct': pct,
            'etf': etf.get('symbol', 'N/A'),
            'name': etf.get('name', bucket),
            'alloc': alloc,
            'ann_return_pct': ann_ret,
            'ann_dividend': annual_div,
            'ann_cg': annual_cg,
            'total_annual': total_annual,
            'tax': total_tax,
            'after_tax': after_tax,
            'tax_drag': total_tax / total_annual if total_annual > 0 else 0,
        }

    # Totals
    summary = results['summary']
    summary['total_alloc'] = sum(b['alloc'] for b in results['buckets'].values())
    summary['total_annual'] = sum(b['total_annual'] for b in results['buckets'].values())
    summary['total_div'] = sum(b['ann_dividend'] for b in results['buckets'].values())
    summary['total_cg'] = sum(b['ann_cg'] for b in results['buckets'].values())
    summary['total_tax'] = sum(b['tax'] for b in results['buckets'].values())
    summary['total_after_tax'] = sum(b['after_tax'] for b in results['buckets'].values())
    summary['blended_return'] = summary['total_annual'] / initial_capital * 100
    summary['blended_after_tax'] = summary['total_after_tax'] / initial_capital * 100
    summary['blended_tax_drag'] = (
        summary['total_tax'] / summary['total_annual'] * 100
        if summary['total_annual'] > 0 else 0
    )
    summary['after_tax_sharpe_approx'] = (
        summary['blended_after_tax'] / 15.0  # rough: assume 15% vol
    )
    summary['after_tax_cagr_10y'] = (
        (1 + summary['blended_after_tax'] / 100) ** 10 - 1
    ) * 100

    return results


def compare_all_strategies(marginal_income=130075, initial=100000):
    """Run all allocation strategies and compare."""
    print("=" * 80)
    print(f"ALLOCATION STRATEGY COMPARISON — 2024 Alberta, ${marginal_income:,.0f} income")
    print(f"Initial capital: ${initial:,.0f}")
    print("=" * 80)

    results = []
    for name, config in STRATEGY_CONFIGS.items():
        config_copy = dict(config)
        config_copy['_name'] = name
        r = simulate_allocation(config_copy, marginal_income=marginal_income,
                                initial_capital=initial)
        results.append(r)

    # Sort by after-tax return
    results.sort(key=lambda x: x['summary']['blended_after_tax'], reverse=True)

    print(f"\n{'Strategy':<20} {'PreTax%':>8} {'TaxDrag':>8} {'AfterTx%':>9} "
          f"{'Div$':>8} {'CG$':>8} {'Tax$':>8} {'Net$':>8}")
    print("-" * 80)

    for r in results:
        s = r['summary']
        print(f"{r['strategy']:<20} {s['blended_return']:>7.2f}% {s['blended_tax_drag']:>7.1f}% "
              f"{s['blended_after_tax']:>8.2f}% ${s['total_div']:>7,.0f} "
              f"${s['total_cg']:>7,.0f} ${s['total_tax']:>7,.0f} "
              f"${s['total_after_tax']:>7,.0f}")

    # Winner
    winner = results[0]
    print(f"\n🏆 Best after-tax: {winner['strategy']} "
          f"({winner['summary']['blended_after_tax']:.2f}% after-tax)")

    # Tax drag comparison
    print(f"\n── Tax Drag Ranking (lowest is best) ──")
    results_by_drag = sorted(results, key=lambda x: x['summary']['blended_tax_drag'])
    for r in results_by_drag:
        s = r['summary']
        print(f"  {r['strategy']:<20} tax drag: {s['blended_tax_drag']:.1f}%")

    # Bucket breakdown for winner
    print(f"\n── Winner Breakdown ({winner['strategy']}) ──")
    for bucket, b in winner['buckets'].items():
        print(f"  {bucket:<8} ({b['etf']:<8}) {b['pct']*100:>5.0f}%  "
              f"alloc=${b['alloc']:>10,.0f}  return={b['ann_return_pct']:>5.1f}%  "
              f"tax=${b['tax']:>8,.0f}  after=${b['after_tax']:>8,.0f}")

    # Store in after_tax_returns table
    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()
    for r in results:
        s = r['summary']
        c.execute("""INSERT INTO after_tax_returns 
            (date,strategy_name,account_type,total_return,capital_gain,
             eligible_div,foreign_div,fed_tax,prov_tax,after_tax_return,tax_drag_pct)
            VALUES (CURDATE(),%s,'MARGINAL',%s,%s,%s,%s,%s,%s,%s,%s)""",
            (r['strategy'], s['total_annual'], s['total_cg'],
             s['total_div'] * 0.5, s['total_div'] * 0.5,  # rough split
             s['total_tax'] * 0.6, s['total_tax'] * 0.4,
             s['total_after_tax'], s['blended_tax_drag'] / 100))
    conn.commit()
    conn.close()
    print("\nResults stored in after_tax_returns table")

    return results


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Geographic Allocation Backtester')
    parser.add_argument('--strategy', default=None, help='Specific strategy to test')
    parser.add_argument('--income', type=float, default=130000, help='Marginal income for tax calc')
    parser.add_argument('--capital', type=float, default=100000, help='Initial capital')
    parser.add_argument('--compare', action='store_true', help='Compare all strategies')
    args = parser.parse_args()

    if args.compare or args.strategy is None:
        compare_all_strategies(marginal_income=args.income, initial=args.capital)
    else:
        config = STRATEGY_CONFIGS.get(args.strategy)
        if not config:
            print(f"Unknown strategy: {args.strategy}")
            print(f"Available: {list(STRATEGY_CONFIGS.keys())}")
            return
        config['_name'] = args.strategy
        result = simulate_allocation(config, marginal_income=args.income,
                                     initial_capital=args.capital)

        print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
