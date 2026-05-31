#!/usr/bin/env python3
"""
layer0_screener.py — Universe Screener (Layer 0)

Weekly run. Filters 404-symbol universe through:
  1. Global hard filters (price, volume, exchange eligibility)
  2. Per-sleeve screener (Buffett quality, dividend, swing, speculative)
  3. Buffett fundamentals evaluator (ROE, D/E, FCF, margins)
  4. CIBC Investor's Edge eligibility
  5. Dividend calendar mapping (for income sleeve)

Usage:
    python3 layer0_screener.py [--max 50] [--sleeve all] [--verbose]
"""
import pymysql
import json
import sys
import os
import argparse
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import time

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

MYSQL_CFG = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
                 password='Zaqwsx9sm1@', database='ksfraser_stock_market',
                 charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


@dataclass
class Fundamentals:
    symbol: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    geography: str = "US"
    market_cap: float = 0.0
    price: float = 0.0
    beta: float = 1.0
    avg_volume: float = 0.0
    pe: float = 0.0
    forward_pe: float = 0.0
    pb: float = 0.0
    # Profitability
    roe: float = 0.0
    roic: float = 0.0
    roa: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    # Growth
    revenue: float = 0.0
    revenue_growth_3y: float = 0.0
    # Balance sheet
    total_debt: float = 0.0
    total_equity: float = 0.0
    debt_equity: float = 0.0
    current_ratio: float = 0.0
    # Cash flow
    fcf: float = 0.0
    fcf_5y_streak: int = 0
    # Dividend
    div_yield: float = 0.0
    div_payout_ratio: float = 0.0
    div_years_streak: int = 0
    div_growth_5y: float = 0.0
    ex_div_date: str = ""
    div_frequency: str = ""  # monthly, quarterly, semi, annual
    # 52-week range
    high_52w: float = 0.0
    low_52w: float = 0.0
    # Calculated
    buffet_score: float = 0.0
    quality_flags: list = field(default_factory=list)
    red_flags: list = field(default_factory=list)
    cibc_eligible: bool = True
    cibc_note: str = ""
    cibc_cost: float = 0.0
    volatility_annual: float = 0.0


class BuffettEvaluator:
    """Score stocks on Buffett-style quality (0-100)."""

    def evaluate(self, f: Fundamentals, cfg) -> tuple:
        score = 0.0
        flags, red = [], []
        sc = cfg.sleeves.core_buffett.screener

        # ROE (max 20 pts)
        if f.roe >= sc.min_roe:
            score += 20; flags.append(f"ROE={f.roe:.0%}")
        elif f.roe >= 0.10:
            score += 10
        elif f.roe < 0.05:
            red.append(f"ROE={f.roe:.0%}")

        # ROIC (max 15 pts)
        if f.roic >= sc.min_roic:
            score += 15; flags.append(f"ROIC={f.roic:.0%}")
        elif f.roic >= 0.08:
            score += 8
        elif f.roic < 0.05:
            red.append(f"ROIC={f.roic:.0%}")

        # Debt/Equity (max 15 pts)
        if f.debt_equity <= sc.max_debt_equity:
            score += 15; flags.append(f"D/E={f.debt_equity:.1f}")
        elif f.debt_equity <= 0.5:
            score += 8
        elif f.debt_equity > 0.8:
            red.append(f"D/E={f.debt_equity:.1f}")

        # FCF streak (max 15 pts)
        if f.fcf > 0 and f.fcf_5y_streak >= sc.min_fcf_5yr_streak:
            score += 15; flags.append(f"FCF {f.fcf_5y_streak}yr")
        elif f.fcf > 0:
            score += 7
        elif f.fcf < 0:
            red.append("negative FCF")

        # Gross Margin (max 10)
        if f.gross_margin >= sc.min_gross_margin:
            score += 10; flags.append(f"margin={f.gross_margin:.0%}")
        elif f.gross_margin < 0.20:
            red.append(f"margin={f.gross_margin:.0%}")

        # Revenue Growth (max 10)
        if f.revenue_growth_3y >= sc.min_revenue_growth_3y:
            score += 10; flags.append(f"rev+{f.revenue_growth_3y:.0%}")
        elif f.revenue_growth_3y < 0:
            red.append(f"rev-{abs(f.revenue_growth_3y):.0%}")

        # P/E sanity (max 10)
        if 0 < f.pe < sc.max_pe:
            score += 10; flags.append(f"PE={f.pe:.1f}")
        elif f.pe > 40 or f.pe < 0:
            red.append(f"PE={f.pe:.0f}")

        # Min market cap
        if f.market_cap >= sc.min_market_cap:
            score += 5
        else:
            red.append(f"cap=${f.market_cap/1e9:.1f}B")

        return (max(0, min(100, score)), flags, red)


class CIBCInvestorsEdge:
    """CIBC Investor's Edge eligibility and cost."""

    def check(self, sym: str, exchange: str = "") -> tuple:
        s, e = sym.upper(), (exchange or "").upper()
        if any(x in s for x in ['.PK', '.OB']) or e in ("OTC", "OTCBB", "PINK"):
            return False, "OTC/Pink — not eligible", 0
        if any(x in s for x in ['-USD', '-CAD']) and not s.startswith('BTC'):
            return False, "Crypto — not eligible", 0
        if any(s.endswith(x) for x in ['.TO', '.VN']) or e in ("TSX", "TSXV"):
            return True, "TSX/TSXV — free trades", 0.0
        if e in ("NYSE", "NASDAQ", "AMEX", "ARCA", "NYSEARCA"):
            return True, f"{e} — $9.95 USD/trade", 9.95
        if e == "" and s.isalpha() and len(s) <= 5:
            return True, "Likely US-listed — $9.95 USD/trade", 9.95
        return True, f"Exchange: {e or 'unknown'} — verify", 9.95


def fetch_fundamentals(symbols: list, cfg: Config, verbose=False) -> list:
    """Fetch fundamentals from yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("pip3 install yfinance required"); return []

    ev = BuffettEvaluator()
    cibc = CIBCInvestorsEdge()
    results = []

    print(f"Fetching {len(symbols)} symbols...")
    for i, sym in enumerate(symbols):
        try:
            t = yf.Ticker(sym)
            info = t.get_info() or {}
            if not info or not info.get('regularMarketPrice'):
                if verbose: print(f"  [{i+1}/{len(symbols)}] {sym}: no price"); continue

            f = Fundamentals(symbol=sym)
            f.name = info.get('longName', info.get('shortName', ''))
            f.sector = info.get('sector', '')
            f.industry = info.get('industry', '')
            f.market_cap = info.get('marketCap', 0) or 0
            f.price = info.get('regularMarketPrice', 0) or 0
            f.beta = info.get('beta', 1) or 1
            f.pe = info.get('trailingPE', 0) or 0
            f.forward_pe = info.get('forwardPE', 0) or 0
            f.pb = info.get('priceToBook', 0) or 0
            f.revenue = info.get('totalRevenue', 0) or 0
            f.revenue_growth_3y = info.get('revenueGrowth', 0) or 0
            f.gross_margin = info.get('grossMargins', 0) or 0
            f.operating_margin = info.get('operatingMargins', 0) or 0
            f.net_margin = info.get('profitMargins', 0) or 0
            f.roe = info.get('returnOnEquity', 0) or 0
            f.roa = info.get('returnOnAssets', 0) or 0
            f.avg_volume = info.get('averageVolume', 0) or 0
            f.high_52w = info.get('fiftyTwoWeekHigh', 0) or 0
            f.low_52w = info.get('fiftyTwoWeekLow', 0) or 0
            f.div_yield = info.get('dividendYield', 0) or 0
            f.div_payout_ratio = info.get('payoutRatio', 0) or 0
            f.ex_div_date = str(info.get('exDividendDate', ''))
            f.div_frequency = info.get('dividendFrequency', '') or ''
            f.current_ratio = info.get('currentRatio', 0) or 0

            td = info.get('totalDebt', 0) or 0
            te = info.get('totalStockholderEquity', 0) or \
                 info.get('totalEquityGrossMinorityInterest', 0) or 1
            f.total_debt, f.total_equity = td, te
            f.debt_equity = td / te if te > 0 else 999

            f.fcf = info.get('freeCashflow', 0) or 0
            nopat = (info.get('operatingIncome', 0) or 0) * 0.75
            invested = (info.get('totalStockholderEquity', 0) or 0) + td
            f.roic = nopat / invested if invested > 0 else 0

            # FCF 5yr streak
            try:
                cf = t.cashflow
                if cf is not None and not cf.empty and 'Free Cash Flow' in cf.index:
                    streak = sum(1 for v in list(cf.loc['Free Cash Flow'].values)[:5] if v > 0)
                    f.fcf_5y_streak = streak
            except:
                pass

            # Volatility (estimated from beta × market vol ~15%)
            f.volatility_annual = abs(f.beta) * 0.15

            # Geography
            geo = info.get('country', '')
            if any(sym.endswith(x) for x in ['.TO', '.VN']): geo = 'CA'
            elif geo in ('Canada',): geo = 'CA'
            elif geo in ('United States',): geo = 'US'
            f.geography = geo

            # CIBC eligibility
            ex = info.get('exchange', '')
            elig, note, cost = cibc.check(sym, ex)
            f.cibc_eligible = elig
            f.cibc_note = note
            f.cibc_cost = cost

            # Buffett score
            score, flags, red = ev.evaluate(f, cfg)
            f.buffet_score = score
            f.quality_flags = flags
            f.red_flags = red

            results.append(f)
            if verbose:
                print(f"  [{i+1}/{len(symbols)}] {sym}: score={score:.0f} "
                      f"PE={f.pe:.1f} ROE={f.roe:.0%} "
                      f"div={f.div_yield:.1%} {'✓' if elig else '✗'}")
        except Exception as e:
            if verbose: print(f"  [{i+1}/{len(symbols)}] {sym}: {e}")
        if (i + 1) % 50 == 0:
            time.sleep(3)

    print(f"Fetched {len(results)} fundamentals")
    return results


def screen_for_sleeve(fundamentals: list, sleeve_name: str, cfg: Config) -> list:
    """Filter fundamentals for a specific sleeve."""
    sc = getattr(cfg.sleeves, sleeve_name, None)
    if sc is None:
        return []

    candidates = []
    for f in fundamentals:
        # Hard reject
        if f.price < cfg.screener.min_price:
            continue
        if f.avg_volume < cfg.screener.min_avg_volume:
            continue
        if f.market_cap < cfg.screener.min_market_cap:
            continue
        if not f.cibc_eligible:
            continue
        if any(r in ["negative FCF", "D/C=999"] for r in f.red_flags):
            continue

        # Sleeve-specific filters
        if sleeve_name == "core_buffett":
            if f.buffet_score < 40: continue
            if f.debt_equity > sc.max_debt_equity * 1.5: continue
            if f.market_cap < sc.min_market_cap: continue
            if f.beta > sc.max_beta: continue

        elif sleeve_name == "tactical_swing":
            if f.volatility_annual < sc.min_volatility_annual: continue
            if f.volatility_annual > sc.max_volatility_annual: continue
            if f.market_cap < sc.min_market_cap: continue
            if f.avg_volume < sc.min_avg_volume: continue
            # Reject if fundamentals are terrible
            if f.roe < sc.min_roe: continue
            if f.debt_equity > sc.max_debt_equity: continue

        elif sleeve_name == "income_dividend":
            if f.div_yield < sc.min_div_yield: continue
            if f.div_payout_ratio > sc.max_payout_ratio: continue
            if f.market_cap < sc.min_market_cap: continue
            if f.roe < sc.min_roe: continue

        elif sleeve_name == "satellite_spec":
            if f.market_cap < sc.min_market_cap: continue
            if f.volatility_annual < sc.min_volatility_annual: continue
            if f.avg_volume < sc.min_avg_volume: continue

        candidates.append(f)

    return candidates


def save_results(all_candidates: dict, db_config=None):
    """Save per-sleeve candidates to MySQL."""
    cfg = db_config or MYSQL_CFG
    conn = pymysql.connect(**cfg)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS layer0_candidates (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        name VARCHAR(200),
        sector VARCHAR(50),
        geography VARCHAR(8),
        price DECIMAL(12,4),
        market_cap BIGINT,
        pe DECIMAL(8,2),
        roe DECIMAL(6,4),
        roic DECIMAL(6,4),
        debt_equity DECIMAL(8,2),
        gross_margin DECIMAL(6,4),
        fcf BIGINT,
        fcf_5y_streak INT,
        buffet_score DECIMAL(5,1),
        div_yield DECIMAL(6,4),
        div_payout_ratio DECIMAL(6,4),
        cibc_eligible TINYINT,
        sleeve VARCHAR(30),
        quality_json JSON,
        red_flags_json JSON,
        scanned_date DATE,
        INDEX idx_sleeve_score (sleeve, buffet_score DESC),
        INDEX idx_symbol (symbol),
        INDEX idx_date (scanned_date)
    ) ENGINE=InnoDB""")

    today = date.today().isoformat()
    total = 0
    for sleeve_name, candidates in all_candidates.items():
        for f in candidates:
            c.execute("""INSERT INTO layer0_candidates 
                (symbol,name,sector,geography,price,market_cap,pe,roe,roic,
                 debt_equity,gross_margin,fcf,fcf_5y_streak,buffet_score,
                 div_yield,div_payout_ratio,cibc_eligible,sleeve,
                 quality_json,red_flags_json,scanned_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE buffet_score=VALUES(buffet_score)""",
                (f.symbol, f.name, f.sector, f.geography, f.price,
                 int(f.market_cap), f.pe, f.roe, f.roic, f.debt_equity,
                 f.gross_margin, int(f.fcf), f.fcf_5y_streak, f.buffet_score,
                 f.div_yield, f.div_payout_ratio, 1 if f.cibc_eligible else 0,
                 sleeve_name, json.dumps(f.quality_flags),
                 json.dumps(f.red_flags), today))
            total += 1

    conn.commit()
    for sleeve in all_candidates:
        c.execute("SELECT COUNT(*) as cnt FROM layer0_candidates WHERE sleeve=%s AND scanned_date=%s",
                  (sleeve, today))
        print(f"  {sleeve}: {c.fetchone()['cnt']} candidates")
    conn.close()
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-per-sleeve', type=int, default=50)
    parser.add_argument('--sleeves', default='all')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    cfg = Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')

    # Load symbols
    conn = pymysql.connect(**MYSQL_CFG)
    c = conn.cursor()
    c.execute("SELECT symbol, geography FROM symbol_master ORDER BY symbol")
    all_syms = [r['symbol'] for r in c.fetchall()]
    conn.close()
    print(f"Layer 0: {len(all_syms)} symbols")

    # Fetch once
    fundamentals = fetch_fundamentals(all_syms, cfg, verbose=args.verbose)

    # Screen per sleeve
    active = cfg.sleeves if hasattr(cfg, 'sleeves') else {}
    sleeve_names = list(active.keys()) if args.sleeves == 'all' else args.sleeves.split(',')
    all_candidates = {}
    for name in sleeve_names:
        if not getattr(active.get(name, {}), 'enabled', True):
            continue
        cands = screen_for_sleeve(fundamentals, name, cfg)
        cands.sort(key=lambda f: f.buffet_score, reverse=True)
        cands = cands[:args.max_per_sleeve]
        all_candidates[name] = cands
        print(f"  {name}: {len(cands)} pass")

    total = save_results(all_candidates)
    print(f"\n✓ Layer 0 complete: {total} total candidates")


if __name__ == '__main__':
    main()
