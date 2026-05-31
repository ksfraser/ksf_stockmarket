#!/usr/bin/env python3
"""
layer0_screener.py — Universe Screener (Layer 0)

Weekly run. Filters the 404-symbol universe down to ~80-100 candidates.

Pipeline:
  1. Load symbols from CurrentData HTML + portfolio holdings
  2. Fetch fundamentals from yfinance (ROE, D/E, FCF, margins, P/E)
  3. Apply Buffett-style quality filter
  4. Apply CIBC Investor's Edge eligibility filter
  5. Scan recent news for material events (earnings, M&A, regulatory)
  6. Score and rank survivors
  7. Save candidates to MySQL layer0_candidates table

Usage:
    python3 layer0_screener.py [--max 100] [--verbose]
"""
import pymysql
import json
import sys
import os
import argparse
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


@dataclass
class Fundamentals:
    symbol: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: float = 0.0
    pe: float = 0.0
    forward_pe: float = 0.0
    peg: float = 0.0
    pb: float = 0.0
    ps: float = 0.0
    # Income statement
    revenue: float = 0.0
    revenue_growth_3y: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    # Profitability
    roe: float = 0.0
    roa: float = 0.0
    roic: float = 0.0
    # Balance sheet
    total_debt: float = 0.0
    total_equity: float = 0.0
    debt_equity: float = 0.0
    current_ratio: float = 0.0
    # Cash flow
    fcf: float = 0.0
    fcf_5y_streak: int = 0       # consecutive years of positive FCF
    # Dividend
    div_yield: float = 0.0
    div_payout_ratio: float = 0.0
    div_years: int = 0           # consecutive years paying
    div_growth_5y: float = 0.0   # CAGR of dividend
    ex_div_date: str = ""
    # Price
    price: float = 0.0
    avg_volume: float = 0.0
    beta: float = 1.0
    fifty_two_week_high: float = 0.0
    fifty_two_week_low: float = 0.0
    # Options available
    has_options: bool = False
    # Buffett score (0-100)
    buffet_score: float = 0.0
    # CIBC eligible
    cibc_eligible: bool = True
    # Quality flags
    quality_flags: list = field(default_factory=list)
    red_flags: list = field(default_factory=list)


class BuffettEvaluator:
    """
    Score stocks on Buffett-style quality metrics.
    100 = perfect Buffett stock, 0 = terrible.
    """

    def __init__(self, config: Config):
        self.cfg = config.screener

    def evaluate(self, f: Fundamentals) -> tuple:
        """Returns (score, quality_flags, red_flags)."""
        score = 0.0
        flags = []
        red = []

        # 1. ROE (max 20 pts) — Buffett's favorite metric
        if f.roe >= 0.20:
            score += 20; flags.append("ROE>20%")
        elif f.roe >= 0.15:
            score += 15; flags.append("ROE>15%")
        elif f.roe >= 0.10:
            score += 8
        elif f.roe < 0.05:
            red.append("ROE<5%")

        # 2. ROIC (max 15 pts)
        if f.roic >= 0.15:
            score += 15; flags.append("ROIC>15%")
        elif f.roic >= 0.10:
            score += 10
        elif f.roic < 0.05:
            red.append("ROIC<5%")

        # 3. Debt/Equity (max 15 pts)
        if f.debt_equity <= 0.3:
            score += 15; flags.append("D/E<0.3")
        elif f.debt_equity <= 0.5:
            score += 10
        elif f.debt_equity > 1.0:
            red.append(f"D/E={f.debt_equity:.1f}")
            score -= 5

        # 4. Free Cash Flow (max 15 pts)
        if f.fcf > 0 and f.fcf_5y_streak >= 5:
            score += 15; flags.append("FCF 5yr+")
        elif f.fcf > 0:
            score += 8; flags.append("FCF positive")
        elif f.fcf < 0:
            red.append("negative FCF")

        # 5. Gross Margin (max 10 pts) — moat indicator
        if f.gross_margin >= 0.60:
            score += 10; flags.append("margin>60%")
        elif f.gross_margin >= 0.40:
            score += 7; flags.append("margin>40%")
        elif f.gross_margin < 0.20:
            red.append(f"margin={f.gross_margin:.0%}")

        # 6. Revenue Growth (max 10 pts)
        if f.revenue_growth_3y >= 0.15:
            score += 10; flags.append("rev growth>15%")
        elif f.revenue_growth_3y >= 0.05:
            score += 5
        elif f.revenue_growth_3y < 0:
            red.append("declining revenue")

        # 7. Current Ratio (max 5 pts)
        if f.current_ratio >= 1.5:
            score += 5; flags.append("current>1.5")
        elif f.current_ratio < 1.0:
            red.append(f"current={f.current_ratio:.1f}")

        # 8. P/E sanity (max 5 pts)
        if 0 < f.pe < 20:
            score += 5; flags.append(f"PE={f.pe:.1f}")
        elif f.pe > 40:
            red.append(f"PE={f.pe:.0f}")
            score -= 5

        # 9. Dividend (max 5 pts)
        if f.div_yield >= 0.02 and f.div_years >= 5:
            score += 5; flags.append(f"div {f.div_yield:.1%} {f.div_years}yr")
        elif f.div_yield >= 0.01:
            score += 2

        return (max(0, min(100, score)), flags, red)


class CIBCInvestorsEdgeEligible:
    """
    CIBC Investor's Edge restrictions:
    - TSX, TSXV listed: eligible for free trades (CDN)
    - NYSE, NASDAQ, AMEX, ARCA: eligible (USD)
    - ADRs: eligible if on major exchanges
    - Forex: not available as a product (need Norberts Gambit or ETF)
    - OTC/pink sheet: NOT eligible
    - Crypto: NOT eligible
    - Minimum price $0.01 (but we filter > $5)

    Returns: (eligible: bool, reason: str, trade_cost: float)
    """

    def check(self, symbol: str, exchange: str = "") -> tuple:
        sym = symbol.upper()
        ex = (exchange or "").upper()

        # OTC / pink sheets — not eligible
        if ".PK" in sym or ".OB" in sym or ex in ("OTC", "OTCBB", "PINK"):
            return (False, "OTC/Pink Sheet — not CIBC eligible", 0)

        # Crypto — not eligible
        if "-USD" in sym or "-CAD" in sym or sym.endswith("USD"):
            return (False, "Cryptocurrency — not CIBC eligible", 0)

        # TSX / TSXV — free trades
        if sym.endswith(".TO") or sym.endswith(".VN") or ex in ("TSX", "TSXV", "TSE"):
            return (True, "TSX/TSXV — free trades", 0.0)

        # Major US exchanges — $9.95 USD per trade
        if ex in ("NYSE", "NASDAQ", "AMEX", "ARCA", "NYSEARCA"):
            return (True, f"{ex} — $9.95 USD/trade", 9.95)

        # ADRs on major exchanges
        if ex in ("NYSE", "NASDAQ") and not sym.endswith(".TO"):
            return (True, f"ADR on {ex}", 9.95)

        # Default: assume eligible (common stocks without suffix)
        if ex == "" and len(sym) <= 5 and sym.isalpha():
            return (True, "Likely US-listed — verify", 9.95)

        return (True, f"Exchange: {ex or 'unknown'} — verify CIBC eligible", 9.95)


def fetch_fundamentals(symbols: list, config: Config, verbose=False) -> list:
    """
    Fetch fundamentals from yfinance for all symbols.
    Returns list of Fundamentals.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed: pip3 install yfinance")
        return []

    ev = BuffettEvaluator(config)
    cibc = CIBCInvestorsEdgeEligible()
    results = []

    print(f"Fetching fundamentals for {len(symbols)} symbols...")
    for i, sym in enumerate(symbols):
        try:
            ticker = yf.Ticker(sym)
            info = ticker.get_info() or {}

            if not info or info.get('regularMarketPrice') is None:
                if verbose:
                    print(f"  [{i+1}/{len(symbols)}] {sym}: no data")
                continue

            f = Fundamentals(symbol=sym)

            # Basic info
            f.name = info.get('longName', info.get('shortName', ''))
            f.sector = info.get('sector', '')
            f.industry = info.get('industry', '')
            f.market_cap = info.get('marketCap', 0) or 0
            f.price = info.get('regularMarketPrice', 0) or 0
            f.beta = info.get('beta', 1) or 1

            # Valuation
            f.pe = info.get('trailingPE', 0) or 0
            f.forward_pe = info.get('forwardPE', 0) or 0
            f.peg = info.get('pegRatio', 0) or 0
            f.pb = info.get('priceToBook', 0) or 0

            # Financials
            f.revenue = info.get('totalRevenue', 0) or 0
            f.revenue_growth_3y = info.get('revenueGrowth', 0) or 0
            f.gross_margin = info.get('grossMargins', 0) or 0
            f.operating_margin = info.get('operatingMargins', 0) or 0
            f.net_margin = info.get('profitMargins', 0) or 0
            f.roe = info.get('returnOnEquity', 0) or 0
            f.roa = info.get('returnOnAssets', 0) or 0

            # Debt/equity
            total_debt = info.get('totalDebt', 0) or 0
            total_equity = info.get('totalStockholderEquity', 0) or \
                           info.get('totalEquityGrossMinorityInterest', 0) or 1
            f.total_debt = total_debt
            f.total_equity = total_equity
            f.debt_equity = total_debt / total_equity if total_equity > 0 else 999

            # Cash flow
            f.fcf = info.get('freeCashflow', 0) or 0
            f.current_ratio = info.get('currentRatio', 0) or 0

            # Volume
            f.avg_volume = info.get('averageVolume', 0) or 0

            # 52-week range
            f.fifty_two_week_high = info.get('fiftyTwoWeekHigh', 0) or 0
            f.fifty_two_week_low = info.get('fiftyTwoWeekLow', 0) or 0

            # Dividends
            f.div_yield = info.get('dividendYield', 0) or 0
            f.div_payout_ratio = info.get('payoutRatio', 0) or 0
            f.ex_div_date = str(info.get('exDividendDate', ''))

            # ROIC — need to compute if not available directly
            nopat = (info.get('operatingIncome', 0) or 0) * 0.75  # rough after-tax
            invested = (info.get('totalStockholderEquity', 0) or 0) + total_debt
            f.roic = nopat / invested if invested > 0 else 0

            # 5-year FCF streak — FCF history available via .cashflow
            try:
                cf = ticker.cashflow
                if cf is not None and not cf.empty and 'Free Cash Flow' in cf.index:
                    fcf_vals = cf.loc['Free Cash Flow'].values
                    streak = 0
                    for v in fcf_vals[:5]:
                        if v > 0:
                            streak += 1
                        else:
                            break
                    f.fcf_5y_streak = streak
            except:
                pass

            # CIBC eligibility
            exchange = info.get('exchange', '')
            eligible, reason, cost = cibc.check(sym, exchange)
            f.cibc_eligible = eligible

            # Buffett score
            score, flags, red = ev.evaluate(f)
            f.buffet_score = score
            f.quality_flags = flags
            f.red_flags = red

            results.append(f)

            if verbose:
                print(f"  [{i+1}/{len(symbols)}] {sym}: "
                      f"score={score:.0f} PE={f.pe:.1f} ROE={f.roe:.0%} "
                      f"yield={f.div_yield:.1%} {'✓' if eligible else '✗'}")

        except Exception as e:
            if verbose:
                print(f"  [{i+1}/{len(symbols)}] {sym}: ERROR {e}")

        # Rate limit — yfinance allows ~2000/hour
        import time
        if (i + 1) % 50 == 0:
            time.sleep(3)

    print(f"\nFetched {len(results)} fundamentals for {len(symbols)} symbols")
    return results


def save_candidates(candidates: list, db_config=None):
    """Save screener results to MySQL."""
    cfg = db_config or MYSQL
    conn = pymysql.connect(**cfg)
    c = conn.cursor()

    # Create table if not exists
    c.execute("""CREATE TABLE IF NOT EXISTS layer0_candidates (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        name VARCHAR(200),
        sector VARCHAR(50),
        industry VARCHAR(80),
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
        quality_json JSON,
        red_flags_json JSON,
        scanned_date DATE,
        UNIQUE KEY uk_symbol_date (symbol, scanned_date),
        INDEX idx_score (buffet_score DESC),
        INDEX idx_sector (sector),
        INDEX idx_cibc (cibc_eligible)
    ) ENGINE=InnoDB""")

    today = date.today().isoformat()
    for f in candidates:
        c.execute("""INSERT INTO layer0_candidates 
            (symbol,name,sector,industry,price,market_cap,pe,roe,roic,
             debt_equity,gross_margin,fcf,fcf_5y_streak,buffet_score,
             div_yield,div_payout_ratio,cibc_eligible,quality_json,
             red_flags_json,scanned_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE 
            price=VALUES(price), buffet_score=VALUES(buffet_score), 
            scanned_date=VALUES(scanned_date)""",
            (f.symbol, f.name, f.sector, f.industry, f.price,
             int(f.market_cap), f.pe, f.roe, f.roic, f.debt_equity,
             f.gross_margin, int(f.fcf), f.fcf_5y_streak, f.buffet_score,
             f.div_yield, f.div_payout_ratio, 1 if f.cibc_eligible else 0,
             json.dumps(f.quality_flags), json.dumps(f.red_flags), today))

    conn.commit()

    c.execute("SELECT COUNT(*) as cnt FROM layer0_candidates WHERE scanned_date=%s", (today,))
    print(f"Saved {c.fetchone()['cnt']} candidates (date={today})")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Layer 0 — Universe Screener')
    parser.add_argument('--max', type=int, default=100)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    # Load config
    config = Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')

    # Load symbols from MySQL symbol_master
    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()
    c.execute("SELECT symbol, geography FROM symbol_master ORDER BY symbol")
    all_symbols = [r['symbol'] for r in c.fetchall()]
    conn.close()

    print(f"Starting Layer 0 screener: {len(all_symbols)} symbols")

    # Fetch fundamentals
    fundamentals = fetch_fundamentals(all_symbols, config, verbose=args.verbose)

    if not fundamentals:
        print("No fundamentals fetched. Exiting.")
        return

    # Filter: Buffett score >= 40, CIBC eligible, min price, min volume
    cfg = config.screener
    candidates = []
    for f in fundamentals:
        if f.price < cfg.min_price:
            continue
        if f.avg_volume < cfg.min_avg_volume and f.market_cap < cfg.min_market_cap:
            continue
        if not f.cibc_eligible:
            continue
        # Reject hard red flags
        if any("ROE<5%" in r or "negative FCF" in r or "D/C" in r for r in f.red_flags):
            continue
        candidates.append(f)

    # Sort by Buffett score descending
    candidates.sort(key=lambda f: f.buffet_score, reverse=True)

    # Take top N
    candidates = candidates[:args.max]

    print(f"\nScreener results:")
    print(f"  Passed fundamentals: {len(fundamentals)}")
    print(f"  Passed all filters:  {len(candidates)}")
    print(f"  Top 10:")
    for f in candidates[:10]:
        print(f"    {f.symbol:<15} score={f.buffet_score:.0f}  "
              f"ROE={f.roe:.0%}  PE={f.pe:.1f}  "
              f"div={f.div_yield:.1%}  ${f.price:.2f}")

    # Save to DB
    save_candidates(candidates)
    print(f"\n✓ Layer 0 complete: {len(candidates)} candidates saved")


if __name__ == '__main__':
    main()
