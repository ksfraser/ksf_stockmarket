#!/usr/bin/env python3
"""
Enhanced Fundamental Analyzer & News Monitor
==============================================

Improvements:
1. Fundamental: payout ratio severity tiers, beta-based position sizing,
   52-week range context, ex-dividend timing, short ratio, analyst consensus
2. News: analyst target change tracking, price correlation, historical storage
"""

import sys
import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import yfinance as yf
from investment_monitor import SymbolResolver
from analysis_db import get_db


# ============================================================================
# ENHANCED FUNDAMENTAL ANALYZER
# ============================================================================

class EnhancedFundamentalAnalyzer:
    """
    Comprehensive fundamental analysis incorporating all CIBC-style stats.
    """

    # Sector-specific payout ratio thresholds
    # Some sectors (utilities, REITs, energy trusts) naturally have higher payouts
    SECTOR_PAYOUT_THRESHOLDS = {
        'Utilities':    {'warning': 0.80, 'critical': 0.95},
        'Energy':       {'warning': 0.85, 'critical': 1.00},
        'Financials':   {'warning': 0.70, 'critical': 0.85},
        'Real Estate':  {'warning': 0.90, 'critical': 1.10},  # REITs pay out >100% of earnings (FFO-based)
        'Consumer':     {'warning': 0.70, 'critical': 0.85},
        'Industrials':  {'warning': 0.65, 'critical': 0.80},
        'Materials':    {'warning': 0.70, 'critical': 0.85},
        'Technology':   {'warning': 0.50, 'critical': 0.70},
        'Healthcare':   {'warning': 0.60, 'critical': 0.75},
        'default':      {'warning': 0.70, 'critical': 0.90},
    }

    @staticmethod
    def fetch(ticker: str, resolved_ticker: str = None) -> Dict:
        """Fetch all available fundamental data from yfinance."""
        for t in [resolved_ticker, ticker]:
            if not t:
                continue
            try:
                stock = yf.Ticker(t)
                info = stock.info
                if not info:
                    continue

                f = {}
                f['ticker'] = ticker
                f['resolved'] = t
                f['company_name'] = info.get('longName', ticker)
                f['sector'] = info.get('sector', 'Unknown')
                f['industry'] = info.get('industry', 'Unknown')

                # Price data
                f['current_price'] = info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose')))
                f['open'] = info.get('open', info.get('regularMarketOpen'))
                f['previous_close'] = info.get('previousClose')
                f['52w_high'] = info.get('fiftyTwoWeekHigh')
                f['52w_low'] = info.get('fiftyTwoWeekLow')
                f['52w_range_pct'] = None
                if f['52w_high'] and f['52w_low'] and f['52w_high'] > 0:
                    f['52w_range_pct'] = (f['current_price'] - f['52w_low']) / (f['52w_high'] - f['52w_low']) if f['52w_high'] != f['52w_low'] else 0.5

                # Volume
                f['daily_volume'] = info.get('volume', info.get('regularMarketVolume'))
                f['avg_volume'] = info.get('averageVolume')
                f['avg_volume_10d'] = info.get('averageVolume10days')
                f['volume_ratio'] = (f['daily_volume'] / f['avg_volume']) if f['daily_volume'] and f['avg_volume'] and f['avg_volume'] > 0 else None

                # Market cap
                f['market_cap'] = info.get('marketCap')
                f['enterprise_value'] = info.get('enterpriseValue')

                # Valuation
                f['pe_trailing'] = info.get('trailingPE')
                f['pe_forward'] = info.get('forwardPE')
                f['peg_ratio'] = info.get('pegRatio')
                f['price_to_book'] = info.get('priceToBook')
                f['price_to_sales'] = info.get('priceToSalesTrailing12Months')
                f['ev_to_revenue'] = info.get('enterpriseToRevenue')
                f['ev_to_ebitda'] = info.get('enterpriseToEbitda')

                # Earnings
                f['eps_trailing'] = info.get('trailingEps')
                f['eps_forward'] = info.get('forwardEps')
                f['eps_growth'] = info.get('earningsGrowth')
                f['revenue_growth'] = info.get('revenueGrowth')

                # Profitability
                f['profit_margin'] = info.get('profitMargins')
                f['operating_margin'] = info.get('operatingMargins')
                f['gross_margin'] = info.get('grossMargins')
                f['roe'] = info.get('returnOnEquity')
                f['roa'] = info.get('returnOnAssets')

                # Balance sheet
                f['book_value'] = info.get('bookValue')
                f['cash_per_share'] = info.get('totalCashPerShare')
                f['total_debt'] = info.get('totalDebt')
                f['total_cash'] = info.get('totalCash')
                f['debt_to_equity'] = info.get('debtToEquity')
                f['current_ratio'] = info.get('currentRatio')
                f['quick_ratio'] = info.get('quickRatio')

                # Cash flow
                f['free_cash_flow'] = info.get('freeCashflow')
                f['operating_cash_flow'] = info.get('operatingCashflow')
                if f['free_cash_flow'] and info.get('sharesOutstanding'):
                    f['fcf_per_share'] = f['free_cash_flow'] / info['sharesOutstanding']
                if f['free_cash_flow'] and f['market_cap']:
                    f['fcf_yield'] = (f['free_cash_flow'] / f['market_cap']) * 100

                # Dividends
                f['dividend_rate'] = info.get('dividendRate')
                f['dividend_yield'] = info.get('dividendYield')
                f['payout_ratio'] = info.get('payoutRatio')
                f['five_year_avg_yield'] = info.get('fiveYearAvgDividendYield')
                f['dividend_date'] = info.get('dividendDate')  # timestamp
                f['ex_dividend_date'] = info.get('exDividendDate')  # timestamp

                # Risk
                f['beta'] = info.get('beta')
                f['beta_5yr'] = info.get('beta')  # yfinance only provides one beta

                # Short interest
                f['short_ratio'] = info.get('shortRatio')
                f['short_percent'] = info.get('shortPercentOfFloat')
                f['short_interest'] = info.get('sharesShort')

                # Analyst consensus
                f['analyst_target'] = info.get('targetMeanPrice')
                f['analyst_target_high'] = info.get('targetHighPrice')
                f['analyst_target_low'] = info.get('targetLowPrice')
                f['analyst_recommendation'] = info.get('recommendationKey')
                f['num_analysts'] = info.get('numberOfAnalystOpinions')

                # Analyst target vs current price
                if f['analyst_target'] and f['current_price'] and f['current_price'] > 0:
                    f['target_upside'] = ((f['analyst_target'] - f['current_price']) / f['current_price']) * 100

                # Shares
                f['shares_outstanding'] = info.get('sharesOutstanding')
                f['float_shares'] = info.get('floatShares')

                return f
            except Exception as e:
                continue
        return {}

    @staticmethod
    def analyze(f: Dict) -> Dict:
        """Comprehensive fundamental quality analysis."""
        if not f:
            return {'quality_score': 0, 'rating': 'N/A', 'strengths': [], 'concerns': [], 'warnings': []}

        score, max_score = 0, 0
        strengths, concerns, warnings = [], [], []

        sector = f.get('sector', 'default')
        thresholds = EnhancedFundamentalAnalyzer.SECTOR_PAYOUT_THRESHOLDS.get(
            sector, EnhancedFundamentalAnalyzer.SECTOR_PAYOUT_THRESHOLDS['default']
        )

        # === ROE (0-2 points) ===
        roe = f.get('roe')
        if roe is not None:
            max_score += 2
            if roe > 0.15:
                score += 2
                strengths.append(f"Strong ROE: {roe:.1%}")
            elif roe > 0.10:
                score += 1
            else:
                concerns.append(f"Low ROE: {roe:.1%}")

        # === ROA (0-1 point) ===
        roa = f.get('roa')
        if roa is not None:
            max_score += 1
            if roa > 0.05:
                score += 1
                strengths.append(f"Good ROA: {roa:.1%}")

        # === Profit Margin (0-1 point) ===
        pm = f.get('profit_margin')
        if pm is not None:
            max_score += 1
            if pm > 0.15:
                score += 1
                strengths.append(f"Healthy profit margin: {pm:.1%}")
            elif pm < 0:
                concerns.append(f"Negative profit margin: {pm:.1%}")

        # === Forward P/E (0-1 point) ===
        pe = f.get('pe_forward')
        if pe is not None:
            max_score += 1
            if 0 < pe < 15:
                score += 1
                strengths.append(f"Attractive forward P/E: {pe:.1f}")
            elif pe > 30:
                concerns.append(f"High forward P/E: {pe:.1f}")

        # === P/B (0-1 point) ===
        pb = f.get('price_to_book')
        if pb is not None:
            max_score += 1
            if pb < 3:
                score += 1
            elif pb > 10:
                concerns.append(f"High P/B: {pb:.1f}")

        # === Debt/Equity (0-1 point) ===
        de = f.get('debt_to_equity')
        if de is not None:
            max_score += 1
            if de < 1:
                score += 1
                strengths.append(f"Low D/E: {de:.2f}")
            elif de > 2:
                concerns.append(f"High D/E: {de:.2f}")

        # === Current Ratio (0-1 point) ===
        cr = f.get('current_ratio')
        if cr is not None:
            max_score += 1
            if cr > 1.5:
                score += 1
            elif cr < 1:
                concerns.append(f"Low current ratio: {cr:.2f}")

        # === FCF (0-2 points) ===
        fcf = f.get('free_cash_flow')
        if fcf is not None:
            max_score += 2
            if fcf > 0:
                score += 1
                fcf_yield = f.get('fcf_yield')
                if fcf_yield and fcf_yield > 5:
                    score += 1
                    strengths.append(f"Strong FCF yield: {fcf_yield:.1f}%")
            else:
                concerns.append("Negative FCF")

        # === Payout Ratio (0-2 points, sector-adjusted) ===
        payout = f.get('payout_ratio')
        if payout is not None:
            max_score += 2
            if payout < 0:
                # Negative means negative earnings but still paying dividend
                warnings.append(f"⚠️ Payout ratio negative ({payout:.1%}) — paying dividend from cash reserves or debt while losing money")
                score += 0
            elif payout > 1.0:
                warnings.append(f"🚨 Payout ratio >100% ({payout:.1%}) — unsustainable, dividend cut likely")
                score += 0
            elif payout > thresholds['critical']:
                warnings.append(f"🚨 Payout ratio critical ({payout:.1%}) — well above sector threshold ({thresholds['critical']:.0%})")
                score += 0
            elif payout > thresholds['warning']:
                warnings.append(f"⚠️ Payout ratio high ({payout:.1%}) — above sector threshold ({thresholds['warning']:.0%})")
                score += 0.5
            elif payout < 0.6:
                score += 2
                strengths.append(f"Sustainable payout: {payout:.1%}")
            else:
                score += 1
                strengths.append(f"Moderate payout: {payout:.1%}")

        # === Dividend Yield (0-1 point) ===
        dy = f.get('dividend_yield')
        if dy is not None:
            max_score += 1
            if dy > 2:
                score += 1
                strengths.append(f"Attractive div yield: {dy:.2f}%")

        # === Revenue Growth (0-1 point) ===
        rg = f.get('revenue_growth')
        if rg is not None:
            max_score += 1
            if rg > 0.1:
                score += 1
                strengths.append(f"Strong revenue growth: {rg:.1%}")
            elif rg < 0:
                concerns.append(f"Declining revenue: {rg:.1%}")

        # === Beta — not scored, but flagged ===
        beta = f.get('beta')
        beta_note = None
        if beta is not None:
            if beta > 1.5:
                beta_note = f"High beta: {beta:.2f} — volatile, use smaller position size and wider stops"
            elif beta < 0.5:
                beta_note = f"Low beta: {beta:.2f} — defensive, can use larger position size"
            else:
                beta_note = f"Beta: {beta:.2f} — market-like volatility"

        # === 52-Week Range — not scored, but flagged ===
        range_pct = f.get('52w_range_pct')
        range_note = None
        if range_pct is not None:
            if range_pct > 0.9:
                range_note = f"Near 52w high ({range_pct:.0%} of range) — limited upside, consider waiting for pullback"
            elif range_pct < 0.1:
                range_note = f"Near 52w low ({range_pct:.0%} of range) — potential value opportunity or value trap"
            elif range_pct < 0.3:
                range_note = f"In lower 30% of 52w range — below average price"

        # === Short Ratio — flagged ===
        short_ratio = f.get('short_ratio')
        short_pct = f.get('short_percent')
        short_note = None
        if short_ratio and short_ratio > 5:
            short_note = f"High short ratio: {short_ratio:.1f} — significant bearish positioning"
        elif short_pct and short_pct > 0.15:
            short_note = f"High short interest: {short_pct:.1%} of float — potential squeeze risk or fundamental concern"

        # === Analyst Consensus — flagged ===
        target_upside = f.get('target_upside')
        analyst_rec = f.get('analyst_recommendation')
        num_analysts = f.get('num_analysts')
        analyst_note = None
        if target_upside is not None:
            if target_upside > 20:
                analyst_note = f"Analyst target implies {target_upside:.1f}% upside ({num_analysts} analysts)"
            elif target_upside < -10:
                analyst_note = f"Analyst target implies {target_upside:.1f}% downside ({num_analysts} analysts) — bearish consensus"
            else:
                analyst_note = f"Analyst target: {target_upside:+.1f}% ({num_analysts} analysts)"

        # === Ex-Dividend Date — timing flag ===
        ex_div = f.get('ex_dividend_date')
        ex_div_note = None
        if ex_div:
            try:
                if isinstance(ex_div, (int, float)):
                    ex_dt = datetime.fromtimestamp(ex_div)
                else:
                    ex_dt = datetime.strptime(str(ex_div)[:10], '%Y-%m-%d')
                days_to_ex = (ex_dt.date() - date.today()).days
                if 0 <= days_to_ex <= 5:
                    ex_div_note = f"Ex-dividend in {days_to_ex} days ({ex_dt.strftime('%Y-%m-%d')}) — price will drop by ~dividend amount"
                elif days_to_ex < 0 and days_to_ex >= -5:
                    ex_div_note = f"Just went ex-dividend {abs(days_to_ex)} days ago"
            except:
                pass

        # === Quality Score ===
        qs = (score / max_score * 100) if max_score > 0 else 0
        rating = 'EXCELLENT' if qs >= 80 else 'GOOD' if qs >= 60 else 'FAIR' if qs >= 40 else 'WEAK'

        return {
            'quality_score': round(qs, 1),
            'rating': rating,
            'strengths': strengths,
            'concerns': concerns,
            'warnings': warnings,
            'beta_note': beta_note,
            'range_note': range_note,
            'short_note': short_note,
            'analyst_note': analyst_note,
            'ex_dividend_note': ex_div_note,
            'raw_data': f,
        }


# ============================================================================
# ENHANCED NEWS MONITOR — Analyst Target Tracking
# ============================================================================

class EnhancedNewsMonitor:
    """
    Enhanced news monitoring with analyst target change detection.
    Tracks target price changes over time and correlates with price movements.
    """

    # Keywords for significant events
    SIGNIFICANT_KEYWORDS = [
        'earnings', 'dividend', 'split', 'acquisition', 'merger',
        'bankruptcy', 'restructuring', 'layoffs', 'ceo', 'resign',
        'upgrade', 'downgrade', 'target price', 'buyback', 'buy-out',
        'takeover', 'proxy', 'SEC', 'investigation', 'recall',
        'guidance', 'outlook', 'forecast', 'warning', 'initiates',
        'reiterates', 'raises', 'lowers', 'maintains',
    ]

    # Keywords specifically for analyst actions
    ANALYST_KEYWORDS = [
        'target price', 'price target', 'raises target', 'lowers target',
        'initiates coverage', 'reiterates', 'upgrade', 'downgrade',
        'overweight', 'underweight', 'equal weight', 'outperform',
        'underperform', 'neutral', 'buy', 'sell', 'hold',
    ]

    def __init__(self, db: sqlite3.Connection = None):
        self.db = db or get_db()
        self._ensure_tables()

    def _ensure_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS analyst_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                bank TEXT,
                target_price REAL,
                previous_target REAL,
                change_pct REAL,
                recommendation TEXT,
                current_price REAL,
                source TEXT,
                UNIQUE(ticker, date, bank)
            );
            CREATE TABLE IF NOT EXISTS news_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                title TEXT,
                provider TEXT,
                url TEXT,
                event_type TEXT,
                price_at_event REAL,
                price_5d_after REAL,
                price_21d_after REAL,
                UNIQUE(ticker, date, title)
            );
            CREATE INDEX IF NOT EXISTS idx_analyst_ticker ON analyst_targets(ticker);
            CREATE INDEX IF NOT EXISTS idx_news_ticker ON news_events(ticker);
        """)
        self.db.commit()

    def check(self, ticker: str, resolved_ticker: str = None) -> Dict:
        """Check recent news and analyst actions."""
        result = {
            'articles': [],
            'significant_events': [],
            'analyst_actions': [],
            'sentiment': 'NEUTRAL',
            'has_earnings_soon': False,
            'has_corporate_action': False,
            'has_analyst_change': False,
        }

        for t in [resolved_ticker, ticker]:
            if not t:
                continue
            try:
                stock = yf.Ticker(t)
                news = stock.news
                if not news:
                    continue

                current_price = None
                try:
                    hist = stock.history(period='5d')
                    if not hist.empty:
                        current_price = float(hist.iloc[-1]['Close'])
                except:
                    pass

                for article in news[:15]:
                    content = article.get('content', article)
                    title = content.get('title', article.get('title', ''))
                    pub_date = content.get('pubDate', article.get('pubDate', ''))
                    provider = content.get('provider', {}).get('displayName', article.get('publisher', ''))
                    url = content.get('canonicalUrl', {}).get('url', article.get('link', ''))

                    days_ago = None
                    date_str = None
                    try:
                        if pub_date:
                            pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                            days_ago = (datetime.now(pub_dt.tzinfo) - pub_dt).days
                            date_str = pub_dt.strftime('%Y-%m-%d')
                    except:
                        pass

                    article_data = {
                        'title': title,
                        'provider': provider,
                        'url': url,
                        'days_ago': days_ago,
                        'date': date_str,
                        'significant': False,
                        'is_analyst': False,
                    }

                    title_lower = title.lower()

                    # Check for analyst-specific actions
                    is_analyst = False
                    for kw in self.ANALYST_KEYWORDS:
                        if kw in title_lower:
                            is_analyst = True
                            article_data['is_analyst'] = True
                            result['has_analyst_change'] = True

                            # Try to extract target price from title
                            target_price = self._extract_target_price(title)
                            if target_price and current_price:
                                change_pct = ((target_price - current_price) / current_price) * 100
                                action = {
                                    'bank': provider,
                                    'date': date_str,
                                    'target': target_price,
                                    'current_price': current_price,
                                    'implied_change': round(change_pct, 1),
                                    'title': title[:100],
                                    'url': url,
                                }
                                result['analyst_actions'].append(action)

                                # Store in DB
                                if date_str:
                                    self.db.execute("""
                                        INSERT OR REPLACE INTO analyst_targets
                                        (ticker, date, bank, target_price, current_price, source)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (ticker, date_str, provider, target_price, current_price, url))
                            break

                    # Check for general significant keywords
                    for kw in self.SIGNIFICANT_KEYWORDS:
                        if kw in title_lower:
                            article_data['significant'] = True
                            result['significant_events'].append(f"[{kw.upper()}] {title[:80]}")
                            if kw in ['earnings', 'guidance', 'outlook']:
                                result['has_earnings_soon'] = True
                            if kw in ['dividend', 'split', 'acquisition', 'merger', 'buyback']:
                                result['has_corporate_action'] = True
                            break

                    # Store news event
                    if date_str and article_data['significant']:
                        self.db.execute("""
                            INSERT OR REPLACE INTO news_events
                            (ticker, date, title, provider, url, event_type, price_at_event)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (ticker, date_str, title[:200], provider, url,
                              'analyst' if is_analyst else 'news', current_price))

                    result['articles'].append(article_data)

                self.db.commit()
                if result['articles']:
                    break

            except Exception:
                continue

        return result

    def _extract_target_price(self, title: str) -> Optional[float]:
        """Extract target price from a news title like 'Bank raises target to $14.00'."""
        import re
        # Match patterns like: $14, $14.00, to $14, at $14, target of $14
        patterns = [
            r'(?:target|to|at|raises?|lowers?|set)\s+(?:a\s+)?(?:price\s+)?(?:target\s+)?(?:of\s+)?\$(\d+\.?\d*)',
            r'\$(\d+\.?\d*)\s+(?:target|price target)',
            r'(?:raises?|lowers?)\s+(?:its\s+)?(?:price\s+)?target\s+(?:to\s+)?\$(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, title.lower())
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        return None

    def get_target_history(self, ticker: str, days: int = 90) -> List[Dict]:
        """Get recent analyst target history for a ticker."""
        rows = self.db.execute("""
            SELECT date, bank, target_price, current_price, change_pct
            FROM analyst_targets
            WHERE ticker = ? AND date >= ?
            ORDER BY date DESC
        """, (ticker, (date.today() - timedelta(days=days)).isoformat())).fetchall()

        return [{'date': r[0], 'bank': r[1], 'target': r[2], 'price': r[3], 'change': r[4]} for r in rows]

    def get_recent_target_changes(self, ticker: str, days: int = 30) -> List[Dict]:
        """Get recent target changes with price impact analysis."""
        history = self.get_target_history(ticker, days)
        if len(history) < 2:
            return history

        # Calculate changes
        for i in range(len(history) - 1):
            current = history[i]
            previous = history[i + 1]
            if current['target'] and previous['target']:
                current['target_change_pct'] = round(
                    ((current['target'] - previous['target']) / previous['target']) * 100, 1
                )
                current['previous_target'] = previous['target']
                current['previous_date'] = previous['date']

        return history


# ============================================================================
# TEST / DEMO
# ============================================================================

def demo():
    """Demonstrate enhanced analysis on PZA."""
    resolver = SymbolResolver()

    print("=" * 80)
    print("ENHANCED FUNDAMENTAL ANALYSIS — PZA (Pizza Pizza)")
    print("=" * 80)

    resolved = resolver.resolve('PZA')
    f = EnhancedFundamentalAnalyzer.fetch('PZA', resolved)
    analysis = EnhancedFundamentalAnalyzer.analyze(f)

    print(f"\nCompany: {f.get('company_name')}")
    print(f"Sector: {f.get('sector')} | Industry: {f.get('industry')}")
    print(f"Price: ${f.get('current_price'):.2f} | 52w: ${f.get('52w_low'):.2f} - ${f.get('52w_high'):.2f}")
    print(f"Position in range: {f.get('52w_range_pct', 0):.0%}")
    print(f"Market cap: ${f.get('market_cap', 0)/1e6:.0f}M")
    print(f"P/E (TTM): {f.get('pe_trailing', 'N/A')} | Forward: {f.get('pe_forward', 'N/A')}")
    print(f"EPS (TTM): ${f.get('eps_trailing', 'N/A')} | Forward: ${f.get('eps_forward', 'N/A')}")
    print(f"Beta: {f.get('beta', 'N/A')}")
    print(f"Dividend yield: {f.get('dividend_yield', 0):.2f}%" if f.get('dividend_yield') else "No dividend")
    print(f"Payout ratio: {f.get('payout_ratio', 0):.1%}" if f.get('payout_ratio') else "N/A")
    print(f"Analyst target: ${f.get('analyst_target', 'N/A')} ({analysis.get('analyst_note', '')})")
    print(f"Short ratio: {f.get('short_ratio', 'N/A')}")

    print(f"\nQuality Score: {analysis['quality_score']}/100 ({analysis['rating']})")

    if analysis['strengths']:
        print("\nStrengths:")
        for s in analysis['strengths']:
            print(f"  ✅ {s}")

    if analysis['concerns']:
        print("\nConcerns:")
        for c in analysis['concerns']:
            print(f"  ⚠️ {c}")

    if analysis['warnings']:
        print("\nWarnings:")
        for w in analysis['warnings']:
            print(f"  🚨 {w}")

    if analysis.get('beta_note'):
        print(f"\n  📊 {analysis['beta_note']}")
    if analysis.get('range_note'):
        print(f"  📈 {analysis['range_note']}")
    if analysis.get('short_note'):
        print(f"  📉 {analysis['short_note']}")
    if analysis.get('ex_dividend_note'):
        print(f"  💰 {analysis['ex_dividend_note']}")

    # News check
    print("\n" + "=" * 80)
    print("NEWS & ANALYST ACTIONS")
    print("=" * 80)

    db = get_db()
    monitor = EnhancedNewsMonitor(db)
    news = monitor.check('PZA', resolved)

    if news['analyst_actions']:
        print("\nAnalyst Actions:")
        for a in news['analyst_actions']:
            print(f"  🏦 {a['bank']}: target ${a['target']:.2f} (implied {a['implied_change']:+.1f}%)")
            print(f"     {a['title']}")

    if news['significant_events']:
        print("\nSignificant Events:")
        for e in news['significant_events'][:5]:
            print(f"  📰 {e}")

    # Target history
    history = monitor.get_target_history('PZA', days=90)
    if history:
        print(f"\nTarget History (last 90 days):")
        for h in history[:10]:
            change_str = f" (change: {h.get('target_change_pct', 'N/A')}%)" if h.get('target_change_pct') else ""
            print(f"  {h['date']}: {h['bank']} → ${h['target']:.2f}{change_str}")


if __name__ == '__main__':
    demo()
