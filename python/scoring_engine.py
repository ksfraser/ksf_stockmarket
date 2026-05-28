#!/usr/bin/env python3
"""
scoring_engine.py — Fundamental Analysis & Strategy Scoring Engine
===================================================================
Populates scoring tables (motleyfool, investorplace, tenets, evalbusiness,
ratios, quarter_statement, evalmanagement, evalmarket, evalvalue, evalsummary)
using financial data from MariaDB and yfinance.

Architecture:
  1. compute_ratios()    — Calculate ROE, ROA, ROCE, margins, debt ratios
  2. compute_motleyfool() — Evaluate Motley Fool stock screening criteria
  3. compute_investorplace() — Evaluate InvestorPlace screening criteria
  4. compute_tenets()    — Score Buffett investment tenets (0-10 each)
  5. compute_evalbusiness() — Assess business quality (5 boolean criteria)
  6. write_scores()     — Generic INSERT ... ON DUPLICATE KEY UPDATE writer
  7. run_scoring()      — Main orchestration loop

Each scoring function returns a dict of {field: value} that write_scores()
persists to the appropriate MariaDB table with full source tracking.

Usage:
  python3 scoring_engine.py                    # Score all active symbols
  python3 scoring_engine.py --symbols AAPL,MSFT,RY.TO  # Specific symbols
  python3 scoring_engine.py --table ratios     # Refresh only one table
  python3 scoring_engine.py --yyyymm 202506   # Use yfinance data from a
                                                specific YYYYMM for quarter_statement
"""

import argparse
import logging
import sys
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import Error as MySQLError
import numpy as np
import pandas as pd

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("WARNING: yfinance not available. MariaDB-only mode.")

# --------------------------------------------------------------------------
# Configuration — mirrors ta_calculator.py DB_CONFIG pattern
# --------------------------------------------------------------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'ksf_stockmarket',
    'password': 'change_me',
    'database': 'ksf_stockmarket',
    'charset': 'utf8mb4',
    'use_unicode': True,
    'autocommit': False,
}

# How many quarters of data we need for reliable ratio calculation
MIN_QUARTERS = 8        # 2 years of quarterly data
MAX_QUARTERS_LOOKBACK = 40  # 10 years max

# yfinance cache to avoid redundant API calls
_yf_cache: Dict[str, Any] = {}

# Per-table source identifier
SOURCE_SCORING_ENGINE = 'scoring_engine'
SOURCE_YFINANCE = 'yfinance'

# SCORING THRESHOLDS — sourced from Buffett/Motley Fool/InvestorPlace literature
ROE_THRESHOLD = 0.15            # 15% ROE considered attractive
ROA_THRESHOLD = 0.07            # 7% ROA considered attractive
ROCE_THRESHOLD = 0.15           # 15% ROCE considered attractive
GROSS_MARGIN_MIN = 0.40         # 40% gross margin is excellent
PRETAX_MARGIN_MIN = 0.15        # 15% pre-tax margin is attractive
NET_MARGIN_MIN = 0.10           # 10% net margin is attractive
OPERATING_MARGIN_MIN = 0.10     # 10% operating margin considered low-cost
DEBT_RATIO_MAX = 0.50           # Debt_ratio below 50% is sustainable
SALES_GROWTH_DD = 0.10          # 10%+ = double-digit rising sales
GROWTH_ACCEL_THRESHOLD = 0.02   # 2% acceleration in growth rate

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ==========================================================================
# DATABASE HELPERS
# ==========================================================================

def get_connection():
    """Get a MariaDB connection using the shared DB_CONFIG."""
    return mysql.connector.connect(**DB_CONFIG)


def get_active_symbols(conn, symbols: Optional[List[str]] = None) -> List[str]:
    """
    Get list of active symbols from stockinfo.
    If `symbols` is provided, filter to only those that exist in stockinfo.
    """
    cursor = conn.cursor()
    if symbols:
        format_strings = ','.join(['%s'] * len(symbols))
        cursor.execute(f"""
            SELECT stocksymbol FROM stockinfo
            WHERE stocksymbol IN ({format_strings})
            ORDER BY stocksymbol
        """, tuple(symbols))
    else:
        cursor.execute("""
            SELECT stocksymbol FROM stockinfo s
            WHERE EXISTS (
                SELECT 1 FROM stockprices p
                WHERE p.symbol = s.stocksymbol
                AND p.price_date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
            )
            ORDER BY s.stocksymbol
        """)
    result = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return result


def fetch_quarterly_data(conn, symbol: str) -> pd.DataFrame:
    """
    Fetch quarterly financial data from `quarter_statement` for a symbol.
    Returns DataFrame ordered by fiscal_year DESC, fiscal_quarter DESC.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT fiscal_year, fiscal_quarter, revenue, revenuegrowth,
               revenuegrowth2, revenuegrowth3, netincome, incomegrowth,
               earningpershare, totalasset, totalliability, totalequity,
               totaldebt, retainedearnings, ownerearnings, capitalexpenses,
               depletion, amortization, workingcapital, outstandingshares,
               dividendpershare
        FROM quarter_statement
        WHERE symbol = %s
        ORDER BY fiscal_year DESC, fiscal_quarter DESC
    """, (symbol,))
    rows = cursor.fetchall()
    cursor.close()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Create a proper datetime index from year+quarter
    df['period'] = pd.to_datetime(
        df['fiscal_year'].astype(str) + '-' +
        ((df['fiscal_quarter'] - 1) * 3 + 1).astype(str).str.zfill(2) + '-01'
    )
    df.set_index('period', inplace=True)
    df.sort_index(inplace=True)
    return df


def fetch_latest_quarterly_row(conn, symbol: str) -> Optional[Dict]:
    """Return the most recent quarter_statement row as a dict, or None."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM quarter_statement
        WHERE symbol = %s
        ORDER BY fiscal_year DESC, fiscal_quarter DESC
        LIMIT 1
    """, (symbol,))
    row = cursor.fetchone()
    cursor.close()
    return row


def fetch_yfinance_data(symbol: str) -> Dict:
    """
    Fetch current financial data from yfinance.  Results are cached
    per-symbol to avoid redundant API hits when scoring multiple tables.
    """
    if symbol in _yf_cache:
        return _yf_cache[symbol]

    if not HAS_YFINANCE:
        return {}

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Financials (TTM or most recent annual)
        fin = ticker.financials
        cf = ticker.cashflow
        bs = ticker.balance_sheet

        data = {
            'info': info,
            'market_cap': info.get('marketCap'),
            'enterprise_value': info.get('enterpriseValue'),
            'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
            'trailing_pe': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'dividend_yield': info.get('dividendYield'),
            'dividend_rate': info.get('dividendRate'),
            'payout_ratio': info.get('payoutRatio'),
            'book_value': info.get('bookValue'),
            'price_to_book': info.get('priceToBook'),
            'total_revenue': info.get('totalRevenue'),
            'revenue_growth': info.get('revenueGrowth'),
            'gross_margins': info.get('grossMargins'),
            'operating_margins': info.get('operatingMargins'),
            'profit_margins': info.get('profitMargins'),
            'ebitda_margins': info.get('ebitdaMargins'),
            'return_on_assets': info.get('returnOnAssets'),
            'return_on_equity': info.get('returnOnEquity'),
            'total_debt': info.get('totalDebt'),
            'total_cash': info.get('totalCash'),
            'debt_to_equity': info.get('debtToEquity'),
            'free_cashflow': info.get('freeCashflow'),
            'operating_cashflow': info.get('operatingCashflow'),
            'earnings_growth': info.get('earningsGrowth'),
            'revenue_growth_pct': info.get('revenueGrowth'),
            'shares_outstanding': info.get('sharesOutstanding'),
            'float_shares': info.get('floatShares'),
            'short_ratio': info.get('shortRatio'),
            'short_percent_of_float': info.get('shortPercentOfFloat'),
            'institutional_ownership': info.get('heldPercentInstitutions'),
            'insider_ownership': info.get('heldPercentInsiders'),
            'beta': info.get('beta'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'fifty_day_average': info.get('fiftyDayAverage'),
            'two_hundred_day_average': info.get('twoHundredDayAverage'),
            'average_volume': info.get('averageVolume'),
            'currency': info.get('currency'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            # Raw DataFrames for more complex calculations
            '_financials': fin,
            '_cashflow': cf,
            '_balance_sheet': bs,
        }

        _yf_cache[symbol] = data
        return data

    except Exception as e:
        logger.warning(f"yfinance fetch failed for {symbol}: {e}")
        return {}


def fetch_price_history(conn, symbol: str, days: int = 252) -> pd.DataFrame:
    """
    Fetch recent daily price history for volatility / trend calculations.
    Falls back to yfinance if MariaDB data is insufficient.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT price_date, day_close, volume
        FROM stockprices
        WHERE symbol = %s
          AND price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY price_date ASC
    """, (symbol, days))
    rows = cursor.fetchall()
    cursor.close()

    if len(rows) >= 60:
        df = pd.DataFrame(rows)
        df['price_date'] = pd.to_datetime(df['price_date'])
        df.set_index('price_date', inplace=True)
        df['day_close'] = pd.to_numeric(df['day_close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        return df

    # Fallback: yfinance
    if HAS_YFINANCE:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1y')
            if len(hist) > 0:
                return hist[['Close', 'Volume']].rename(
                    columns={'Close': 'day_close', 'Volume': 'volume'}
                )
        except Exception as e:
            logger.debug(f"yfinance price history failed for {symbol}: {e}")

    return pd.DataFrame()


# ==========================================================================
# SCORING FUNCTION #1: Financial Ratios
# ==========================================================================

def compute_ratios(symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute financial ratios from quarterly financial data (quarter_statement).
    Uses pandas rolling calculations on the most recent MIN_QUARTERS rows.

    Ratios computed:
      ROE, ROA, ROCE
      Gross Profit Margin, Pre-tax Margin, Net Margin, Operating Margin
      Debt Ratio, Acceptable Debt Ratio
      P/E Ratio
      Plus attractiveness flags and composite sum.

    Args:
        symbol: Stock ticker
        df: DataFrame from fetch_quarterly_data() with at least
            revenue, netincome, totalasset, totalequity, totaldebt, etc.

    Returns:
        Dict of ratio field names to computed values.
    """
    if df.empty or len(df) < 4:
        logger.debug(f"Insufficient quarterly data for {symbol}: {len(df)} rows")
        return {}

    # Use most recent rows (df is sorted ascending by index already)
    ratios = {}
    latest = df.iloc[-1]
    prev_year = df.iloc[-5] if len(df) >= 5 else latest  # ~1 year ago

    # --- Revenue & Income ---
    revenue = safe_float(latest.get('revenue'))
    net_income = safe_float(latest.get('netincome'))
    total_assets = safe_float(latest.get('totalasset'))
    total_equity = safe_float(latest.get('totalequity'))
    total_debt = safe_float(latest.get('totaldebt'))

    # Annualize: TTM = sum of last 4 quarters
    ttm_revenue = df['revenue'].tail(4).sum() if 'revenue' in df else revenue
    ttm_net_income = df['netincome'].tail(4).sum() if 'netincome' in df else net_income

    # If we have enough quarters, annualize
    if len(df) >= 4:
        revenue = safe_float(ttm_revenue) or revenue
        net_income = safe_float(ttm_net_income) or net_income

    # Capital Employed = Total Assets - Current Liabilities
    # Approximation: Total Equity + Total Debt (or Total Assets - Total Liability + Total Debt)
    total_liability = safe_float(latest.get('totalliability'))
    capital_employed = total_equity + total_debt if (total_equity and total_debt) else None

    # We need gross profit — approximate from available data
    # If we don't have gross profit directly, we approximate from margins
    # For now, we'll compute what we can reliably derive

    # --- ROE = Net Income / Shareholders' Equity ---
    if net_income and total_equity and total_equity != 0:
        ratios['roe'] = round(net_income / total_equity, 4)
    else:
        ratios['roe'] = None

    # --- ROA = Net Income / Total Assets ---
    if net_income and total_assets and total_assets != 0:
        ratios['roa'] = round(net_income / total_assets, 4)
    else:
        ratios['roa'] = None

    # --- ROCE = EBIT / Capital Employed ---
    # Approximate EBIT as Net Income + Interest + Taxes
    # Without EBIT directly, use Net Income / Capital_Employed as proxy
    if net_income and capital_employed and capital_employed != 0:
        ratios['roce'] = round(net_income / capital_employed, 4)
    else:
        ratios['roce'] = None

    # --- Margin Calculations ---
    # Gross Profit Margin = (Revenue - COGS) / Revenue
    # We don't have COGS directly, so we approximate from available data
    # Use Operating Margin as proxy if gross not available
    if revenue and revenue != 0:
        ratios['netmargin'] = round(net_income / revenue, 4) if net_income else None

        # For gross/pre-tax/operating margins we need additional data
        # We'll leave them None for now; LLM can fill or use yfinance fallback
        ratios['grossprofitmargin'] = None
        ratios['pretaxmargin'] = None
        ratios['operatingmargin'] = None
    else:
        ratios['netmargin'] = None
        ratios['grossprofitmargin'] = None
        ratios['pretaxmargin'] = None
        ratios['operatingmargin'] = None

    # --- Debt Ratio = Total Debt / Total Assets ---
    if total_debt and total_assets and total_assets != 0:
        ratios['debtratio'] = round(total_debt / total_assets, 4)
    else:
        ratios['debtratio'] = None

    # --- Acceptable Debt Ratio (debt payable in 3 years from earnings) ---
    # Years of debt coverage = Total Debt / Net Income (TTM)
    # Acceptable if <= 3 years
    if total_debt and net_income and net_income > 0:
        years_of_debt = total_debt / net_income
        ratios['acceptabledebtratio'] = round(years_of_debt, 4)
    else:
        ratios['acceptabledebtratio'] = None

    # --- P/E Ratio ---
    # Use earningspershare from most recent quarter * 4 as annual EPS estimate
    eps = safe_float(latest.get('earningpershare'))
    # price will be filled by the yfinance fallback in run_scoring
    ratios['peratio'] = None  # Deferred to yfinance enrichment

    # --- Attractiveness Scores ---
    attractive_sum = 0

    # ROE > 15%
    roe_val = ratios.get('roe')
    if roe_val is not None and roe_val >= ROE_THRESHOLD:
        ratios['roeattractive'] = 1
        attractive_sum += 1
    else:
        ratios['roeattractive'] = 0

    # ROA attractive (> 7%)
    roa_val = ratios.get('roa')
    if roa_val is not None and roa_val >= ROA_THRESHOLD:
        ratios['attractiveroa'] = 1
        attractive_sum += 1
    else:
        ratios['attractiveroa'] = 0

    # ROCE attractive (> 15%)
    roce_val = ratios.get('roce')
    if roce_val is not None and roce_val >= ROCE_THRESHOLD:
        ratios['attractiveroce'] = 1
        attractive_sum += 1
    else:
        ratios['attractiveroce'] = 0

    # Gross margin attractive (> 40%)
    gm_val = ratios.get('grossprofitmargin')
    if gm_val is not None and gm_val >= GROSS_MARGIN_MIN:
        ratios['attractivegross'] = 1
        attractive_sum += 1
    else:
        ratios['attractivegross'] = 0

    # Pre-tax margin attractive (> 15%)
    ptm_val = ratios.get('pretaxmargin')
    if ptm_val is not None and ptm_val >= PRETAX_MARGIN_MIN:
        ratios['attractivepretax'] = 1
        attractive_sum += 1
    else:
        ratios['attractivepretax'] = 0

    # Net margin attractive (> 10%)
    nm_val = ratios.get('netmargin')
    if nm_val is not None and nm_val >= NET_MARGIN_MIN:
        ratios['attractivenet'] = 1
        attractive_sum += 1
    else:
        ratios['attractivenet'] = 0

    # Low cost operations (operating margin > 10%)
    om_val = ratios.get('operatingmargin')
    if om_val is not None and om_val >= OPERATING_MARGIN_MIN:
        ratios['lowcost'] = 1
        attractive_sum += 1
    else:
        ratios['lowcost'] = 0

    # Sustainable debt ratio (debt_ratio < 50% or debt payable in < 3 years)
    dr_val = ratios.get('debtratio')
    adr_val = ratios.get('acceptabledebtratio')
    debt_ok = False
    if dr_val is not None and dr_val < DEBT_RATIO_MAX:
        debt_ok = True
    if adr_val is not None and adr_val <= 3.0:
        debt_ok = True
    ratios['sustaindebtratio'] = 1 if debt_ok else 0
    if debt_ok:
        attractive_sum += 1

    ratios['attractivesum'] = attractive_sum

    logger.debug(
        f"[{symbol}] Ratios: ROE={ratios.get('roe')}, ROA={ratios.get('roa')}, "
        f"ROCE={ratios.get('roce')}, attractive_sum={attractive_sum}"
    )
    return ratios


def enrich_ratios_with_yfinance(symbol: str, ratios: Dict) -> Dict:
    """
    Enrich ratio dict with yfinance data where MariaDB fields are missing.
    Fills: roe, roa, grossprofitmargin, pretaxmargin, operatingmargin,
           netmargin, debtratio, peratio, roce.
    """
    yf_data = fetch_yfinance_data(symbol)
    if not yf_data:
        return ratios

    info = yf_data.get('info', {})

    # ROE
    if ratios.get('roe') is None and yf_data.get('return_on_equity') is not None:
        ratios['roe'] = round(float(yf_data['return_on_equity']), 4)

    # ROA
    if ratios.get('roa') is None and yf_data.get('return_on_assets') is not None:
        ratios['roa'] = round(float(yf_data['return_on_assets']), 4)

    # Margins from yfinance (these are the company-wide margins)
    if ratios.get('grossprofitmargin') is None:
        gm = yf_data.get('gross_margins') or info.get('grossMargins')
        if gm is not None:
            ratios['grossprofitmargin'] = round(float(gm), 4)

    if ratios.get('pretaxmargin') is None:
        ptm = info.get('ebitdaMargins')  # Best proxy for pre-tax
        if ptm is not None:
            ratios['pretaxmargin'] = round(float(ptm), 4)

    if ratios.get('operatingmargin') is None:
        om = yf_data.get('operating_margins') or info.get('operatingMargins')
        if om is not None:
            ratios['operatingmargin'] = round(float(om), 4)

    if ratios.get('netmargin') is None:
        nm = yf_data.get('profit_margins') or info.get('profitMargins')
        if nm is not None:
            ratios['netmargin'] = round(float(nm), 4)

    # Debt ratio from yfinance
    if ratios.get('debtratio') is None:
        td = yf_data.get('total_debt')
        ta = info.get('totalAssets') or info.get('bookValue')
        # Use debtToEquity as fallback
        de = yf_data.get('debt_to_equity') or info.get('debtToEquity')
        if td and ta and float(ta) != 0:
            ratios['debtratio'] = round(float(td) / float(ta), 4)
        elif de is not None:
            # Convert D/E to D/A approximation: D/A = D/E / (1 + D/E)
            de_val = float(de)
            if de_val >= 0:
                ratios['debtratio'] = round(de_val / (1 + de_val), 4)

    # P/E ratio
    if ratios.get('peratio') is None:
        pe = yf_data.get('trailing_pe') or info.get('trailingPE')
        if pe is not None:
            ratios['peratio'] = round(float(pe), 4)

    # ROCE enrichment: EBIT / Capital_Employed
    # From yfinance: use operating income / (equity + debt)
    if ratios.get('roce') is None:
        ebit = info.get('ebitda')
        cap_emp = None
        if ebit is not None:
            eq = info.get('totalStockholderEquity') or info.get('bookValue')
            debt = yf_data.get('total_debt')
            if eq and debt:
                cap_emp = float(eq) + float(debt)
            if cap_emp and cap_emp > 0:
                ratios['roce'] = round(float(ebit) / cap_emp, 4)

    # Recalculate attractiveness scores with enriched data
    attractive_sum = 0
    checks = [
        ('roeattractive', 'roe', ROE_THRESHOLD),
        ('attractiveroa', 'roa', ROA_THRESHOLD),
        ('attractiveroce', 'roce', ROCE_THRESHOLD),
        ('attractivegross', 'grossprofitmargin', GROSS_MARGIN_MIN),
        ('attractivepretax', 'pretaxmargin', PRETAX_MARGIN_MIN),
        ('attractivenet', 'netmargin', NET_MARGIN_MIN),
        ('lowcost', 'operatingmargin', OPERATING_MARGIN_MIN),
    ]
    for score_key, ratio_key, threshold in checks:
        val = ratios.get(ratio_key)
        if val is not None and val >= threshold:
            ratios[score_key] = 1
            attractive_sum += 1
        else:
            ratios[score_key] = 0

    # Sustainable debt ratio
    dr_val = ratios.get('debtratio')
    adr_val = ratios.get('acceptabledebtratio')
    debt_ok = False
    if dr_val is not None and dr_val < DEBT_RATIO_MAX:
        debt_ok = True
    if adr_val is not None and adr_val <= 3.0:
        debt_ok = True
    ratios['sustaindebtratio'] = 1 if debt_ok else 0
    if debt_ok:
        attractive_sum += 1

    ratios['attractivesum'] = attractive_sum
    return ratios


# ==========================================================================
# SCORING FUNCTION #2: Motley Fool Criteria
# ==========================================================================

def compute_motleyfool(symbol: str, ratios_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluate Motley Fool screening criteria based on financial ratios
    computed from quarterly data.

    Criteria (all scored 0 or 1):
      - doubledigitrisingsales: Revenue growth >= 10% YoY
      - risingfreecashflow: Free cash flow increasing over 4 quarters
      - risingbookvalue: Book value per share increasing
      - improvingmargin: Gross/operating margins stable or improving
      - risingreturnonequity: ROE trending upward
      - insiderownership: Insider ownership >= 1% (from yfinance)
      - regulardividends: Has paid dividends in 8 of last 12 quarters

    Args:
        symbol: Stock ticker
        ratios_df: DataFrame of quarterly data (same as compute_ratios input)

    Returns:
        Dict with 0/1 scores for each criterion plus composite mf_score.
    """
    scores = {
        'doubledigitrisingsales': 0,
        'risingfreecashflow': 0,
        'risingbookvalue': 0,
        'improvingmargin': 0,
        'risingreturnonequity': 0,
        'insiderownership': 0,
        'regulardividends': 0,
    }

    if ratios_df.empty or len(ratios_df) < 4:
        logger.debug(f"[{symbol}] Insufficient data for Motley Fool scoring")
        scores['mf_score'] = 0
        return scores

    # --- Double-digit rising sales ---
    # Check revenue growth from revenuegrowth field or compute
    try:
        latest_rg = safe_float(ratios_df.iloc[-1].get('revenuegrowth'))
        if latest_rg is None and 'revenue' in ratios_df.columns:
            # Compute YoY growth: compare TTM this year vs prior 4 quarters
            if len(ratios_df) >= 8:
                ttm_now = ratios_df['revenue'].iloc[-4:].sum()
                ttm_prev = ratios_df['revenue'].iloc[-8:-4].sum()
                if ttm_prev and ttm_prev > 0:
                    latest_rg = (ttm_now - ttm_prev) / ttm_prev

        if latest_rg is not None and latest_rg >= SALES_GROWTH_DD:
            scores['doubledigitrisingsales'] = 1
            logger.debug(f"[{symbol}] MF: DD rising sales = {latest_rg:.2%}")
    except Exception as e:
        logger.debug(f"[{symbol}] MF sales growth calc error: {e}")

    # --- Rising free cash flow ---
    # owner_earnings = revenue - capital_expenses - depletion - amortization
    try:
        if 'ownerearnings' in ratios_df.columns and len(ratios_df) >= 4:
            oe = ratios_df['ownerearnings'].tail(4)
            oe_vals = oe.dropna()
            if len(oe_vals) >= 3:
                # Check if trend is positive using linear regression slope
                xs = np.arange(len(oe_vals))
                slope = np.polyfit(xs, oe_vals.values.astype(float), 1)[0]
                if slope > 0:
                    scores['risingfreecashflow'] = 1
        else:
            # Fallback: yfinance free cash flow trend
            yf_data = fetch_yfinance_data(symbol)
            cf = yf_data.get('_cashflow')
            if cf is not None and not cf.empty:
                try:
                    fcf_row = cf.loc['Free Cash Flow']
                    fcf_vals = fcf_row.dropna()
                    if len(fcf_vals) >= 2:
                        # Most recent years increasing
                        if all(fcf_vals.iloc[i] >= fcf_vals.iloc[i + 1]
                               for i in range(min(3, len(fcf_vals) - 1))):
                            scores['risingfreecashflow'] = 1
                except KeyError:
                    pass
    except Exception as e:
        logger.debug(f"[{symbol}] MF FCF calc error: {e}")

    # --- Rising book value ---
    try:
        if 'totalequity' in ratios_df.columns and len(ratios_df) >= 4:
            eq = ratios_df['totalequity'].tail(4).dropna()
            if len(eq) >= 2:
                if eq.iloc[-1] > eq.iloc[0]:
                    scores['risingbookvalue'] = 1
        # Also check book value per share from yfinance
        yf_data = fetch_yfinance_data(symbol)
        bv = yf_data.get('book_value')
        if bv and bv > 0 and scores['risingbookvalue'] == 0:
            # Can't determine trend from single value, leave as 0
            pass
    except Exception as e:
        logger.debug(f"[{symbol}] MF book value calc error: {e}")

    # --- Improving margin ---
    try:
        # Use revenue as proxy: check if net margin (netincome/revenue) is improving
        if 'netincome' in ratios_df.columns and 'revenue' in ratios_df.columns:
            margins = (ratios_df['netincome'] / ratios_df['revenue']).dropna().tail(4)
            if len(margins) >= 2:
                xs = np.arange(len(margins))
                slope = np.polyfit(xs, margins.values.astype(float), 1)[0]
                if slope >= 0:
                    scores['improvingmargin'] = 1
    except Exception as e:
        logger.debug(f"[{symbol}] MF margin calc error: {e}")

    # --- Rising ROE ---
    try:
        if 'netincome' in ratios_df.columns and 'totalequity' in ratios_df.columns:
            roe_series = (ratios_df['netincome'] / ratios_df['totalequity']).dropna().tail(4)
            if len(roe_series) >= 2:
                xs = np.arange(len(roe_series))
                slope = np.polyfit(xs, roe_series.values.astype(float), 1)[0]
                if slope > 0:
                    scores['risingreturnonequity'] = 1
    except Exception as e:
        logger.debug(f"[{symbol}] MF ROE trend calc error: {e}")

    # --- Insider ownership ---
    try:
        yf_data = fetch_yfinance_data(symbol)
        insider_pct = yf_data.get('insider_ownership')
        if insider_pct is not None:
            # insider_ownership is in decimal (0.05 = 5%)
            if float(insider_pct) >= 0.01:
                scores['insiderownership'] = 1
    except Exception as e:
        logger.debug(f"[{symbol}] MF insider ownership error: {e}")

    # --- Regular dividends ---
    try:
        div_per_share = ratios_df.iloc[-1].get('dividendpershare')
        if div_per_share and float(div_per_share) > 0:
            scores['regulardividends'] = 1
        else:
            # Check yfinance
            yf_data = fetch_yfinance_data(symbol)
            div_yield = yf_data.get('dividend_yield')
            if div_yield is not None and float(div_yield) > 0:
                scores['regulardividends'] = 1
    except Exception as e:
        logger.debug(f"[{symbol}] MF dividends error: {e}")

    # Composite score
    scores['mf_score'] = sum(v for k, v in scores.items() if k != 'mf_score')

    logger.info(
        f"[{symbol}] Motley Fool: DD_sales={scores['doubledigitrisingsales']} "
        f"FCF={scores['risingfreecashflow']} BV={scores['risingbookvalue']} "
        f"Margin={scores['improvingmargin']} ROE={scores['risingreturnonequity']} "
        f"Insider={scores['insiderownership']} Div={scores['regulardividends']} "
        f"→ mf_score={scores['mf_score']}"
    )
    return scores


# ==========================================================================
# SCORING FUNCTION #3: InvestorPlace Criteria
# ==========================================================================

def compute_investorplace(
    symbol: str,
    ratios_df: pd.DataFrame,
    price_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Evaluate InvestorPlace screening criteria (24 fields from schema).

    All criteria scored 0/1 unless noted as DECIMAL (pe, volatility,
    dividendearningratio, institutioninterest, tradingvolume).
    Composite ip_score is the sum of all binary criteria.

    Args:
        symbol: Stock ticker
        ratios_df: Quarterly financial data DataFrame
        price_df: Daily price history DataFrame (for volatility)

    Returns:
        Dict with all 24 InvestorPlace fields + ip_score.
    """
    scores = {
        'seventyfivepercent': 0,
        'earningsgrowth': 0,
        'earningsaccel': 0,
        'pe': None,
        'tradingvolume': None,
        'institutioninterest': None,
        'orderimbalance': 0,
        'shortinterest': 0,
        'volatility': None,
        'dividendearningratio': None,
        'newproductline': 0,
        'restructuring': 0,
        'reengineering': 0,
        'sharebuyback': 0,
        'headcountcuts': 0,
        'spinoffs': 0,
        'reducedrd': 0,
        'extracash': 0,
        'shareholderprofitgoal': 0,
        'dividendincreases': 0,
    }

    yf_data = fetch_yfinance_data(symbol)
    info = yf_data.get('info', {}) if yf_data else {}

    # --- seventyfivepercent (domestic sales >= 75%) ---
    # We cannot reliably determine this from yfinance alone.
    # If company is Canadian-listed on TSX, assume domestic.
    # This is a best-effort heuristic; LLM should refine.
    try:
        cursor = get_connection().cursor(dictionary=True)
        cursor.execute(
            "SELECT exchange FROM stockinfo WHERE stocksymbol = %s", (symbol,)
        )
        row = cursor.fetchone()
        cursor.close()
        if row and row.get('exchange', '').upper() in ('TSX', 'TSXV', 'CBOE'):
            scores['seventyfivepercent'] = 1  # Heuristic: Canadian exchange → domestic
    except Exception:
        pass

    # --- earningsearningsgrowth ---
    try:
        if not ratios_df.empty and 'incomegrowth' in ratios_df.columns:
            inc_growth = safe_float(ratios_df.iloc[-1].get('incomegrowth'))
            if inc_growth is not None and inc_growth > 0:
                scores['earningsgrowth'] = 1
        else:
            eg = yf_data.get('earnings_growth') or info.get('earningsGrowth')
            if eg is not None and float(eg) > 0:
                scores['earningsgrowth'] = 1
    except Exception as e:
        logger.debug(f"[{symbol}] IP earnings growth: {e}")

    # --- earningsaccel ---
    try:
        if not ratios_df.empty and 'incomegrowth' in ratios_df.columns and len(ratios_df) >= 2:
            ig_now = safe_float(ratios_df.iloc[-1].get('incomegrowth'))
            ig_prev = safe_float(ratios_df.iloc[-2].get('incomegrowth'))
            if ig_now is not None and ig_prev is not None and ig_now > ig_prev:
                scores['earningsaccel'] = 1
    except Exception as e:
        logger.debug(f"[{symbol}] IP earnings accel: {e}")

    # --- pe ---
    pe = yf_data.get('trailing_pe') or info.get('trailingPE') if yf_data else None
    if pe is not None:
        scores['pe'] = round(float(pe), 2)

    # --- tradingvolume ---
    avg_vol = info.get('averageVolume') if info else None
    if avg_vol is not None:
        scores['tradingvolume'] = int(avg_vol)

    # --- institutioninterest ---
    inst = yf_data.get('institutional_ownership') or info.get('heldPercentInstitutions') if yf_data else None
    if inst is not None:
        scores['institutioninterest'] = round(float(inst) * 100, 2)  # Convert to percentage

    # --- orderimbalance ---
    # Cannot reliably determine from available data. Default 0.
    scores['orderimbalance'] = 0

    # --- shortinterest ---
    try:
        short_pct = yf_data.get('short_percent_of_float') or info.get('shortPercentOfFloat') if yf_data else None
        if short_pct is not None and float(short_pct) > 0.05:  # >5% short interest
            scores['shortinterest'] = 1
    except Exception:
        pass

    # --- volatility ---
    try:
        if not price_df.empty and 'day_close' in price_df.columns:
            returns = price_df['day_close'].pct_change().dropna()
            if len(returns) >= 20:
                scores['volatility'] = round(float(returns.std() * np.sqrt(252) * 100), 4)
        else:
            beta = yf_data.get('beta') or info.get('beta') if yf_data else None
            if beta is not None:
                scores['volatility'] = round(float(beta), 4)
    except Exception:
        pass

    # --- dividendearningratio ---
    try:
        payout = yf_data.get('payout_ratio') or info.get('payoutRatio') if yf_data else None
        if payout is not None:
            scores['dividendearningratio'] = round(float(payout), 4)
        else:
            # Calculate: dividend per share / earnings per share
            dps = safe_float(ratios_df.iloc[-1].get('dividendpershare')) if not ratios_df.empty else None
            eps = safe_float(ratios_df.iloc[-1].get('earningpershare')) if not ratios_df.empty else None
            if dps and eps and float(eps) > 0:
                scores['dividendearningratio'] = round(float(dps) / float(eps), 4)
    except Exception:
        pass

    # --- newproductline ---
    # Heuristic: high R&D spending suggests innovation
    # yfinance doesn't give R&D directly. We use revenue growth as a proxy
    # for whether new products are driving growth.
    try:
        if not ratios_df.empty and len(ratios_df) >= 4:
            if 'revenuegrowth' in ratios_df.columns:
                rg = safe_float(ratios_df.iloc[-1].get('revenuegrowth'))
                if rg is not None and rg > 0.05:
                    scores['newproductline'] = 1
    except Exception:
        pass

    # --- restructuring / reengineering / headcountcuts ---
    # These require NLP on press releases. Default to 0.
    scores['restructuring'] = 0
    scores['reengineering'] = 0
    scores['headcountcuts'] = 0

    # --- sharebuyback ---
    try:
        if not ratios_df.empty and 'outstandingshares' in ratios_df.columns and len(ratios_df) >= 2:
            shares_now = safe_float(ratios_df.iloc[-1].get('outstandingshares'))
            shares_prev = safe_float(ratios_df.iloc[-2].get('outstandingshares'))
            if shares_now and shares_prev and shares_now < shares_prev:
                scores['sharebuyback'] = 1
        else:
            # yfinance: check if shares outstanding decreased
            so = yf_data.get('shares_outstanding') if yf_data else None
            avg_so = info.get('sharesOutstanding') if info else None
            if so and avg_so and float(so) < float(avg_so) * 0.99:
                scores['sharebuyback'] = 1
    except Exception:
        pass

    # --- spinoffs ---
    # Requires NLP. Default 0.
    scores['spinoffs'] = 0

    # --- reducedrd ---
    # Requires NLP. Default 0.
    scores['reducedrd'] = 0

    # --- extracash ---
    try:
        cash = yf_data.get('total_cash') or info.get('totalCash') if yf_data else None
        if cash is not None and float(cash) > 0:
            scores['extracash'] = 1
    except Exception:
        pass

    # --- shareholderprofitgoal ---
    # Heuristic: high ROE + dividend payments suggest shareholder focus
    try:
        roe = None
        if not ratios_df.empty and 'netincome' in ratios_df.columns and 'totalequity' in ratios_df.columns:
            ni = safe_float(ratios_df.iloc[-1].get('netincome'))
            eq = safe_float(ratios_df.iloc[-1].get('totalequity'))
            if ni and eq and float(eq) > 0:
                roe = float(ni) / float(eq)
        if roe is None:
            roe = yf_data.get('return_on_equity') if yf_data else None
        if roe is not None and float(roe) > 0.10:
            scores['shareholderprofitgoal'] = 1
    except Exception:
        pass

    # --- dividendincreases ---
    try:
        if not ratios_df.empty and 'dividendpershare' in ratios_df.columns and len(ratios_df) >= 4:
            divs = ratios_df['dividendpershare'].tail(4).dropna()
            if len(divs) >= 2 and float(divs.iloc[-1]) > float(divs.iloc[0]):
                scores['dividendincreases'] = 1
        else:
            div_yield = yf_data.get('dividend_yield') if yf_data else None
            if div_yield is not None and float(div_yield) > 0:
                scores['dividendincreases'] = 1
    except Exception:
        pass

    # Composite IP score: sum of all binary fields
    binary_fields = [
        'seventyfivepercent', 'earningsgrowth', 'earningsaccel',
        'orderimbalance', 'shortinterest', 'newproductline',
        'restructuring', 'reengineering', 'sharebuyback',
        'headcountcuts', 'spinoffs', 'reducedrd',
        'extracash', 'shareholderprofitgoal', 'dividendincreases',
    ]
    scores['ip_score'] = sum(scores.get(f, 0) for f in binary_fields)

    logger.info(
        f"[{symbol}] InvestorPlace: earn_growth={scores['earningsgrowth']} "
        f"earn_accel={scores['earningsaccel']} buyback={scores['sharebuyback']} "
        f"div_inc={scores['dividendincreases']} → ip_score={scores['ip_score']}"
    )
    return scores


# ==========================================================================
# SCORING FUNCTION #4: Buffett Tenets (0-10 each)
# ==========================================================================

def compute_tenets(symbol: str, ratios_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluate Buffett investment tenets. Each scored 0-10.

    Tenets:
      simple, consistent, longterm, rationalmanager, candid,
      resistinstitution, focusroe, ownerearnings, highprofitmargin,
      retainedtomarket, valueofbusiness, discounted

    Scoring is based on quantitative financial data where possible.
    Subjective tenets (candid, resistinstitution) default to 5 (neutral).

    Args:
        symbol: Stock ticker
        ratios_df: Quarterly financial data DataFrame

    Returns:
        Dict with 12 tenet scores (0-10) + total_score.
    """
    scores = {}
    yf_data = fetch_yfinance_data(symbol)
    info = yf_data.get('info', {}) if yf_data else {}

    # --- simple (0-10) ---
    # Heuristic: companies with consistent revenue and few business segments
    # are simpler. Use revenue consistency as proxy.
    try:
        if not ratios_df.empty and 'revenue' in ratios_df.columns and len(ratios_df) >= 4:
            rev = ratios_df['revenue'].dropna().tail(8)
            if len(rev) >= 4:
                cv = float(rev.std() / rev.mean()) if float(rev.mean()) != 0 else 1.0
                # Lower CV = simpler/more predictable
                scores['simple'] = max(0, min(10, int(10 - cv * 10)))
            else:
                scores['simple'] = 5
        else:
            scores['simple'] = 5
    except Exception:
        scores['simple'] = 5

    # --- consistent (0-10) ---
    # Revenue and earnings consistency over 8+ quarters
    try:
        if not ratios_df.empty and len(ratios_df) >= 8:
            rev = ratios_df['revenue'].dropna().tail(8)
            ni = ratios_df['netincome'].dropna().tail(8)
            rev_cv = float(rev.std() / rev.mean()) if float(rev.mean()) != 0 else 1.0
            ni_positive = (ni > 0).sum() / len(ni) if len(ni) > 0 else 0
            consistency = (1 - rev_cv) * 5 + ni_positive * 5
            scores['consistent'] = max(0, min(10, int(consistency)))
        else:
            scores['consistent'] = 5
    except Exception:
        scores['consistent'] = 5

    # --- longterm (0-10) ---
    # Revenue growth trend over multiple years
    try:
        if not ratios_df.empty and len(ratios_df) >= 8:
            rev = ratios_df['revenue'].dropna().tail(8)
            if len(rev) >= 4 and float(rev.iloc[0]) > 0:
                growth = (float(rev.iloc[-1]) / float(rev.iloc[0])) ** (1 / (len(rev) / 4)) - 1
                scores['longterm'] = max(0, min(10, int(5 + growth * 50)))
            else:
                scores['longterm'] = 5
        else:
            scores['longterm'] = 5
    except Exception:
        scores['longterm'] = 5

    # --- rationalmanager (0-10) ---
    # Heuristic: rational capital allocation = consistent ROE + no excessive dilution
    try:
        roe_val = None
        if not ratios_df.empty and 'netincome' in ratios_df.columns and 'totalequity' in ratios_df.columns:
            ni = safe_float(ratios_df.iloc[-1].get('netincome'))
            eq = safe_float(ratios_df.iloc[-1].get('totalequity'))
            if ni and eq and float(eq) > 0:
                roe_val = float(ni) / float(eq)
        if roe_val is None:
            roe_val = yf_data.get('return_on_equity')
        if roe_val is not None:
            roe_f = float(roe_val)
            scores['rationalmanager'] = max(0, min(10, int(roe_f * 40)))
        else:
            scores['rationalmanager'] = 5
    except Exception:
        scores['rationalmanager'] = 5

    # --- candid (0-10) ---
    # Subjective: requires NLP on shareholder letters. Default neutral.
    scores['candid'] = 5

    # --- resistinstitution (0-10) ---
    # Subjective: requires analysis of management decisions. Default neutral.
    scores['resistinstitution'] = 5

    # --- focusroe (0-10) ---
    # Management focuses on ROE, not just EPS
    # Heuristic: high and stable ROE suggests focus on shareholder returns
    try:
        roe_val = None
        if not ratios_df.empty and 'netincome' in ratios_df.columns and 'totalequity' in ratios_df.columns:
            ni = safe_float(ratios_df.iloc[-1].get('netincome'))
            eq = safe_float(ratios_df.iloc[-1].get('totalequity'))
            if ni and eq and float(eq) > 0:
                roe_val = float(ni) / float(eq)
        if roe_val is None:
            roe_val = yf_data.get('return_on_equity')
        if roe_val is not None:
            scores['focusroe'] = max(0, min(10, int(float(roe_val) * 40)))
        else:
            scores['focusroe'] = 5
    except Exception:
        scores['focusroe'] = 5

    # --- ownerearnings (0-10) ---
    # Buffett's owner earnings = Net Income + Depreciation - CapEx - Working Capital change
    try:
        if not ratios_df.empty and 'ownerearnings' in ratios_df.columns:
            oe = safe_float(ratios_df.iloc[-1].get('ownerearnings'))
            ni = safe_float(ratios_df.iloc[-1].get('netincome'))
            if oe and ni and float(ni) > 0:
                oe_ratio = float(oe) / float(ni)
                # Owner earnings close to or > net income is good
                scores['ownerearnings'] = max(0, min(10, int(oe_ratio * 7)))
            else:
                scores['ownerearnings'] = 5
        else:
            scores['ownerearnings'] = 5
    except Exception:
        scores['ownerearnings'] = 5

    # --- highprofitmargin (0-10) ---
    try:
        margin = None
        if not ratios_df.empty and 'netincome' in ratios_df.columns and 'revenue' in ratios_df.columns:
            ni = safe_float(ratios_df.iloc[-1].get('netincome'))
            rev = safe_float(ratios_df.iloc[-1].get('revenue'))
            if ni and rev and float(rev) > 0:
                margin = float(ni) / float(rev)
        if margin is None:
            margin = yf_data.get('profit_margins') or info.get('profitMargins') if yf_data else None
        if margin is not None:
            scores['highprofitmargin'] = max(0, min(10, int(float(margin) * 60)))
        else:
            scores['highprofitmargin'] = 5
    except Exception:
        scores['highprofitmargin'] = 5

    # --- retainedtomarket (0-10) ---
    # $1 of retained earnings should create >= $1 of market value
    # Heuristic: check if retained earnings growth correlates with market cap growth
    try:
        if not ratios_df.empty and 'retainedearnings' in ratios_df.columns and len(ratios_df) >= 4:
            re_now = safe_float(ratios_df.iloc[-1].get('retainedearnings'))
            re_prev = safe_float(ratios_df.iloc[-4].get('retainedearnings'))
            if re_now and re_prev and float(re_prev) > 0:
                re_growth = (float(re_now) - float(re_prev)) / float(re_prev)
                scores['retainedtomarket'] = max(0, min(10, int(5 + re_growth * 20)))
            else:
                scores['retainedtomarket'] = 5
        else:
            scores['retainedtomarket'] = 5
    except Exception:
        scores['retainedtomarket'] = 5

    # --- valueofbusiness (0-10) ---
    # Can we calculate intrinsic value? If we have DCF inputs, score higher.
    try:
        has_fcf = (
            not ratios_df.empty and
            'ownerearnings' in ratios_df.columns and
            safe_float(ratios_df.iloc[-1].get('ownerearnings')) is not None
        )
        scores['valueofbusiness'] = 7 if has_fcf else 4
    except Exception:
        scores['valueofbusiness'] = 5

    # --- discounted (0-10) ---
    # Is the stock trading below intrinsic value?
    # Heuristic: P/E below 15 and P/B below 1.5 suggests discount
    try:
        pe = yf_data.get('trailing_pe') or info.get('trailingPE') if yf_data else None
        pb = yf_data.get('price_to_book') or info.get('priceToBook') if yf_data else None
        discount_score = 5
        if pe is not None and float(pe) > 0:
            if float(pe) < 10:
                discount_score += 3
            elif float(pe) < 15:
                discount_score += 1
            elif float(pe) > 30:
                discount_score -= 2
        if pb is not None and float(pb) > 0:
            if float(pb) < 1.0:
                discount_score += 2
            elif float(pb) > 3.0:
                discount_score -= 2
        scores['discounted'] = max(0, min(10, discount_score))
    except Exception:
        scores['discounted'] = 5

    # Total score
    tenet_fields = [
        'simple', 'consistent', 'longterm', 'rationalmanager', 'candid',
        'resistinstitution', 'focusroe', 'ownerearnings', 'highprofitmargin',
        'retainedtomarket', 'valueofbusiness', 'discounted'
    ]
    scores['total_score'] = sum(scores.get(f, 0) for f in tenet_fields)

    logger.info(
        f"[{symbol}] Tenets: simple={scores['simple']} consistent={scores['consistent']} "
        f"longterm={scores['longterm']} roe={scores['focusroe']} "
        f"margin={scores['highprofitmargin']} discounted={scores['discounted']} "
        f"→ total={scores['total_score']}"
    )
    return scores


# ==========================================================================
# SCORING FUNCTION #5: Business Quality
# ==========================================================================

def compute_evalbusiness(symbol: str, ratios_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluate business quality (5 boolean criteria from schema).

    Criteria:
      simple: Simple business model
      consistent_history: Consistent operating history
      neededproduct: Product/service is needed
      noclosesubstitute: No close substitute (moat)
      regulated: Regulated industry (barrier to entry)

    Args:
        symbol: Stock ticker
        ratios_df: Quarterly financial data DataFrame

    Returns:
        Dict with 5 boolean scores + summary.
    """
    scores = {
        'simple': 0,
        'consistent_history': 0,
        'neededproduct': 0,
        'noclosesubstitute': 0,
        'regulated': 0,
    }

    yf_data = fetch_yfinance_data(symbol)
    info = yf_data.get('info', {}) if yf_data else {}

    # --- simple ---
    # Reuse tenet logic: consistent revenue = simpler business
    try:
        if not ratios_df.empty and 'revenue' in ratios_df.columns and len(ratios_df) >= 4:
            rev = ratios_df['revenue'].dropna().tail(8)
            if len(rev) >= 4 and float(rev.mean()) > 0:
                cv = float(rev.std() / rev.mean())
                scores['simple'] = 1 if cv < 0.3 else 0
            else:
                scores['simple'] = 0
        else:
            scores['simple'] = 0
    except Exception:
        scores['simple'] = 0

    # --- consistent_history ---
    # Positive net income in at least 7 of last 8 quarters
    try:
        if not ratios_df.empty and 'netincome' in ratios_df.columns and len(ratios_df) >= 4:
            ni = ratios_df['netincome'].dropna().tail(8)
            positive_quarters = (ni > 0).sum()
            scores['consistent_history'] = 1 if positive_quarters >= min(7, len(ni)) else 0
        else:
            scores['consistent_history'] = 0
    except Exception:
        scores['consistent_history'] = 0

    # --- neededproduct ---
    # Heuristic: consistent revenue growth suggests product is needed
    try:
        if not ratios_df.empty and 'revenue' in ratios_df.columns and len(ratios_df) >= 4:
            rev = ratios_df['revenue'].dropna().tail(4)
            if len(rev) >= 2 and float(rev.iloc[0]) > 0:
                growth = (float(rev.iloc[-1]) - float(rev.iloc[0])) / float(rev.iloc[0])
                scores['neededproduct'] = 1 if growth > -0.05 else 0  # Not declining significantly
            else:
                scores['neededproduct'] = 0
        else:
            scores['neededproduct'] = 0
    except Exception:
        scores['neededproduct'] = 0

    # --- noclosesubstitute ---
    # Heuristic: high gross margin suggests pricing power / no close substitute
    try:
        gm = None
        if yf_data:
            gm = yf_data.get('gross_margins') or info.get('grossMargins')
        if gm is not None and float(gm) > 0.40:
            scores['noclosesubstitute'] = 1
        else:
            scores['noclosesubstitute'] = 0
    except Exception:
        scores['noclosesubstitute'] = 0

    # --- regulated ---
    # Check if company is in a regulated industry
    regulated_sectors = {
        'Utilities', 'Energy', 'Financial Services', 'Banks',
        'Insurance', 'Healthcare', 'Telecommunications', 'Real Estate',
    }
    regulated_industries = {
        'Banks—Diversified', 'Banks—Regional', 'Insurance—Diversified',
        'Insurance—Life', 'Insurance—Property & Casualty',
        'Utilities—Regulated Electric', 'Utilities—Regulated Gas',
        'Utilities—Regulated Water', 'Oil & Gas Integrated',
        'Telecom Services', 'REIT—Diversified',
    }
    try:
        sector = info.get('sector', '') if info else ''
        industry = info.get('industry', '') if info else ''
        scores['regulated'] = 1 if (sector in regulated_sectors or
                                     industry in regulated_industries) else 0
    except Exception:
        scores['regulated'] = 0

    # Summary score (out of 5)
    scores['summary'] = sum(v for k, v in scores.items() if k != 'summary')

    logger.info(
        f"[{symbol}] Business: simple={scores['simple']} "
        f"consistent={scores['consistent_history']} needed={scores['neededproduct']} "
        f"nosub={scores['noclosesubstitute']} regulated={scores['regulated']} "
        f"→ summary={scores['summary']}"
    )
    return scores


# ==========================================================================
# SCORING FUNCTION #6: Management Evaluation
# ==========================================================================

def compute_evalmanagement(symbol: str, ratios_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluate management quality. Returns a composite management_score.

    Heuristics based on:
      - Capital allocation (ROE stability)
      - Share buyback discipline
      - Dividend consistency
      - Debt management
    """
    score = 0
    yf_data = fetch_yfinance_data(symbol)

    # ROE > 15% → +3 points
    try:
        roe = None
        if yf_data:
            roe = yf_data.get('return_on_equity')
        if roe is not None and float(roe) > 0.15:
            score += 3
        elif roe is not None and float(roe) > 0.10:
            score += 1
    except Exception:
        pass

    # Debt/Equity < 1.0 → +3 points
    try:
        de = yf_data.get('debt_to_equity') if yf_data else None
        if de is not None and float(de) < 1.0:
            score += 3
        elif de is not None and float(de) < 2.0:
            score += 1
    except Exception:
        pass

    # Consistent earnings → +3 points
    try:
        if not ratios_df.empty and 'netincome' in ratios_df.columns and len(ratios_df) >= 4:
            ni = ratios_df['netincome'].dropna().tail(8)
            if len(ni) >= 4 and (ni > 0).all():
                score += 3
    except Exception:
        pass

    return {'management_score': min(score, 9)}


# ==========================================================================
# SCORING FUNCTION #7: Market Evaluation
# ==========================================================================

def compute_evalmarket(symbol: str, price_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluate market conditions. Returns a composite market_score.

    Based on:
      - Price relative to 52-week range
      - Volume trends
      - Beta / volatility
    """
    score = 0
    yf_data = fetch_yfinance_data(symbol)
    info = yf_data.get('info', {}) if yf_data else {}

    # Price in lower half of 52-week range → potential value → +3
    try:
        high = yf_data.get('fifty_two_week_high') or info.get('fiftyTwoWeekHigh')
        low = yf_data.get('fifty_two_week_low') or info.get('fiftyTwoWeekLow')
        price = yf_data.get('current_price') or info.get('currentPrice')
        if high and low and price:
            range_pct = (float(price) - float(low)) / (float(high) - float(low)) if float(high) != float(low) else 0.5
            if range_pct < 0.4:
                score += 3  # Near lows
            elif range_pct < 0.6:
                score += 1
    except Exception:
        pass

    # Low beta (< 1.0) → less volatile → +3
    try:
        beta = yf_data.get('beta') or info.get('beta')
        if beta is not None and float(beta) < 1.0:
            score += 3
        elif beta is not None and float(beta) < 1.5:
            score += 1
    except Exception:
        pass

    # High institutional ownership → validation → +3
    try:
        inst = yf_data.get('institutional_ownership') or info.get('heldPercentInstitutions')
        if inst is not None and float(inst) > 0.60:
            score += 3
        elif inst is not None and float(inst) > 0.30:
            score += 1
    except Exception:
        pass

    return {'market_score': min(score, 9)}


# ==========================================================================
# SCORING FUNCTION #8: Value Assessment
# ==========================================================================

def compute_evalvalue(symbol: str, ratios_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluate value. Returns value_score, intrinsic_value, margin_of_safety.

    Uses a simplified DCF approach:
      intrinsic_value = FCF * (1 + g) / (r - g)
      where g = growth rate, r = discount rate (10%)
    """
    yf_data = fetch_yfinance_data(symbol)
    info = yf_data.get('info', {}) if yf_data else {}

    intrinsic_value = None
    margin_of_safety = None
    value_score = 0

    try:
        fcf = yf_data.get('free_cashflow') or info.get('freeCashflow')
        price = yf_data.get('current_price') or info.get('currentPrice')
        growth = yf_data.get('revenue_growth') or info.get('revenueGrowth')
        shares = yf_data.get('shares_outstanding') or info.get('sharesOutstanding')

        if fcf and shares and float(shares) > 0:
            fcf_per_share = float(fcf) / float(shares)
            g = float(growth) if growth else 0.05
            r = 0.10  # 10% discount rate

            if r > g > -0.5:  # Sanity check
                iv_per_share = fcf_per_share * (1 + g) / (r - g)
                intrinsic_value = round(iv_per_share, 2)

                if price and float(price) > 0:
                    margin_of_safety = round((iv_per_share - float(price)) / float(price), 4)

                    # Score based on margin of safety
                    if margin_of_safety > 0.30:
                        value_score = 9
                    elif margin_of_safety > 0.15:
                        value_score = 7
                    elif margin_of_safety > 0:
                        value_score = 5
                    elif margin_of_safety > -0.15:
                        value_score = 3
                    else:
                        value_score = 1
    except Exception as e:
        logger.debug(f"[{symbol}] Value calc error: {e}")

    return {
        'value_score': value_score,
        'intrinsic_value': intrinsic_value,
        'margin_of_safety': margin_of_safety,
    }


# ==========================================================================
# SCORING FUNCTION #9: Summary
# ==========================================================================

def compute_evalsummary(
    symbol: str,
    mf_scores: Dict,
    ip_scores: Dict,
    tenets_scores: Dict,
    business_scores: Dict,
    ratios_scores: Dict,
    mgmt_scores: Dict,
    market_scores: Dict,
    value_scores: Dict,
) -> Dict[str, Any]:
    """
    Compute composite evaluation summary from all scoring tables.

    Fields:
      totalscore: Sum of all sub-scores (out of 36)
      ratioscore: From ratios.attractivesum (out of 8)
      iplacecalcscore: From investorplace.ip_score (out of ~15)
      managementscore: From evalmanagement.management_score (out of 9)
      financialscore: Sum of tenets financial-related scores (out of 4)
      businessscore: From evalbusiness.summary (out of 5)
      mf_score, ip_score, tenet_score, value_score: Direct from sub-tables
      marginsafety: From evalvalue.margin_of_safety
    """
    ratioscore = ratios_scores.get('attractivesum', 0) or 0
    iplace_score = ip_scores.get('ip_score', 0) or 0
    mgmt_score = mgmt_scores.get('management_score', 0) or 0
    tenet_total = tenets_scores.get('total_score', 0) or 0
    business_total = business_scores.get('summary', 0) or 0
    mf_total = mf_scores.get('mf_score', 0) or 0
    value_total = value_scores.get('value_score', 0) or 0

    # Financial score: subset of tenets (focusroe, ownerearnings, highprofitmargin, retainedtomarket)
    financialscore = min(4, (
        (1 if tenets_scores.get('focusroe', 0) >= 7 else 0) +
        (1 if tenets_scores.get('ownerearnings', 0) >= 7 else 0) +
        (1 if tenets_scores.get('highprofitmargin', 0) >= 7 else 0) +
        (1 if tenets_scores.get('retainedtomarket', 0) >= 7 else 0)
    ))

    # Total score (out of 36 as per schema comment)
    totalscore = min(36, ratioscore + iplace_score + mgmt_score + financialscore + business_total)

    marginsafety = value_scores.get('margin_of_safety')

    return {
        'totalscore': totalscore,
        'marginsafety': marginsafety,
        'ratioscore': ratioscore,
        'iplacecalcscore': iplace_score,
        'managementscore': mgmt_score,
        'financialscore': financialscore,
        'businessscore': business_total,
        'mf_score': mf_total,
        'ip_score': iplace_score,
        'tenet_score': tenet_total,
        'value_score': value_total,
        'last_eval_date': date.today(),
        'last_eval_source': SOURCE_SCORING_ENGINE,
    }


# ==========================================================================
# DATABASE WRITER
# ==========================================================================

def write_scores(
    conn,
    symbol: str,
    scores_dict: Dict[str, Any],
    table_name: str,
    source: str = SOURCE_SCORING_ENGINE,
) -> bool:
    """
    Generic function to write scores to any scoring table.
    Handles INSERT ... ON DUPLICATE KEY UPDATE.
    Includes source tracking fields (source, source_date, is_llm_generated).

    Args:
        conn: mysql.connector connection
        symbol: Stock ticker
        scores_dict: Dict of {field_name: value} to write
        table_name: Target table name (e.g., 'ratios', 'motleyfool')
        source: Source identifier string

    Returns:
        True if write succeeded, False otherwise.
    """
    if not scores_dict:
        logger.debug(f"[{symbol}] No scores to write for {table_name}")
        return False

    # Build the column list and value list
    # All scoring tables have 'symbol' as PK or UNIQUE KEY
    base_columns = ['symbol']
    base_values = [symbol]

    # Add score fields
    for field, value in scores_dict.items():
        if field == 'symbol':
            continue
        if value is None:
            continue  # Skip None values to let DB use defaults
        base_columns.append(f"`{field}`")
        base_values.append(value)

    # Add source tracking fields
    base_columns.extend(['source', 'source_date', 'is_llm_generated'])
    base_values.extend([source, date.today(), 0])

    columns_str = ', '.join(base_columns)
    placeholders = ', '.join(['%s'] * len(base_values))

    # Build ON DUPLICATE KEY UPDATE clause
    update_fields = [f"`{c}`" for c in base_columns if c not in ('symbol', '`symbol`')]
    update_clause = ', '.join(
        f"{f} = VALUES({f})" for f in update_fields
    )

    sql = f"""
        INSERT INTO `{table_name}` ({columns_str})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {update_clause}
    """

    try:
        cursor = conn.cursor()
        cursor.execute(sql, base_values)
        conn.commit()
        cursor.close()
        logger.debug(f"[{symbol}] Wrote {len(scores_dict)} fields to {table_name}")
        return True

    except MySQLError as e:
        logger.error(f"[{symbol}] DB error writing to {table_name}: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    except Exception as e:
        logger.error(f"[{symbol}] Unexpected error writing to {table_name}: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def write_scoring_history(
    conn,
    symbol: str,
    table_name: str,
    field_name: str,
    old_value: Any,
    new_value: Any,
    source: str = SOURCE_SCORING_ENGINE,
):
    """Write a record to scoring_history for audit trail."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scoring_history
                (symbol, scored_at, table_name, field_name, old_value, new_value, source, is_llm_generated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
        """, (symbol, date.today(), table_name, field_name,
              str(old_value) if old_value is not None else None,
              str(new_value) if new_value is not None else None,
              source))
        conn.commit()
        cursor.close()
    except Exception as e:
        logger.debug(f"[{symbol}] scoring_history write error: {e}")


# ==========================================================================
# QUARTERLY DATA SYNC (from yfinance → quarter_statement)
# ==========================================================================

def sync_quarterly_from_yfinance(conn, symbol: str) -> bool:
    """
    Fetch quarterly financials from yfinance and upsert into quarter_statement.
    This ensures the scoring engine has fresh data even if MariaDB is stale.
    """
    if not HAS_YFINANCE:
        return False

    try:
        ticker = yf.Ticker(symbol)
        q_financials = ticker.quarterly_financials
        q_balance = ticker.quarterly_balance_sheet
        q_cashflow = ticker.quarterly_cashflow

        if q_financials.empty:
            logger.debug(f"[{symbol}] No quarterly financials from yfinance")
            return False

        cursor = conn.cursor()

        # Iterate over columns (each column is a quarter)
        for col in q_financials.columns:
            period = col.to_pydatetime() if hasattr(col, 'to_pydatetime') else col
            fiscal_year = period.year
            fiscal_quarter = (period.month - 1) // 3 + 1

            # Extract values from financials
            row_fin = q_financials[col]
            row_bs = q_balance.get(col, pd.Series(dtype=float))
            row_cf = q_cashflow.get(col, pd.Series=float)

            revenue = safe_float(row_fin.get('Total Revenue'))
            net_income = safe_float(row_fin.get('Net Income'))
            eps = safe_float(row_fin.get('Diluted EPS')) or safe_float(row_fin.get('Basic EPS'))

            total_assets = safe_float(row_bs.get('Total Assets'))
            total_liability = safe_float(row_bs.get('Total Liabilities Net Minority Interest'))
            total_equity = safe_float(row_bs.get('Stockholders Equity'))
            total_debt = safe_float(row_bs.get('Total Debt'))
            retained_earnings = safe_float(row_bs.get('Retained Earnings'))

            # Cash flow items
            operating_cf = safe_float(row_cf.get('Operating Cash Flow'))
            capex = safe_float(row_cf.get('Capital Expenditure'))
            depreciation = safe_float(row_cf.get('Depreciation And Amortization'))
            amortization = safe_float(row_cf.get('Amortization'))

            # Owner earnings approximation
            owner_earnings = None
            if net_income is not None:
                dep = depreciation or 0
                cape = capex or 0
                owner_earnings = float(net_income) + float(dep) - float(cape)

            # Outstanding shares
            shares = safe_float(row_bs.get('Ordinary Shares Number')) or safe_float(
                row_fin.get('Basic Average Shares')
            )

            # Dividend per share
            dps = safe_float(row_cf.get('Cash Dividend Paid'))
            if dps and shares and float(shares) > 0:
                dps = abs(float(dps)) / float(shares)
            else:
                dps = None

            # Working capital
            current_assets = safe_float(row_bs.get('Current Assets'))
            current_liabilities = safe_float(row_bs.get('Current Liabilities'))
            working_capital = None
            if current_assets is not None and current_liabilities is not None:
                working_capital = float(current_assets) - float(current_liabilities)

            # Revenue growth (will be computed after insert)
            revenue_growth = None
            revenue_growth2 = None
            revenue_growth3 = None

            # Upsert
            cursor.execute("""
                INSERT INTO quarter_statement
                    (symbol, fiscal_year, fiscal_quarter, revenue, netincome,
                     earningpershare, totalasset, totalliability, totalequity,
                     totaldebt, retainedearnings, ownerearnings, capitalexpenses,
                     depletion, amortization, workingcapital, outstandingshares,
                     dividendpershare, source, source_date, is_llm_generated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, 0)
                ON DUPLICATE KEY UPDATE
                    revenue = VALUES(revenue),
                    netincome = VALUES(netincome),
                    earningpershare = VALUES(earningpershare),
                    totalasset = VALUES(totalasset),
                    totalliability = VALUES(totalliability),
                    totalequity = VALUES(totalequity),
                    totaldebt = VALUES(totaldebt),
                    retainedearnings = VALUES(retainedearnings),
                    ownerearnings = VALUES(ownerearnings),
                    capitalexpenses = VALUES(capitalexpenses),
                    depletion = VALUES(depletion),
                    amortization = VALUES(amortization),
                    workingcapital = VALUES(workingcapital),
                    outstandingshares = VALUES(outstandingshares),
                    dividendpershare = VALUES(dividendpershare),
                    source = VALUES(source),
                    source_date = VALUES(source_date)
            """, (
                symbol, fiscal_year, fiscal_quarter, revenue, net_income,
                eps, total_assets, total_liability, total_equity,
                total_debt, retained_earnings, owner_earnings, capex,
                None, amortization, working_capital, shares,
                dps, SOURCE_YFINANCE, date.today()
            ))

        conn.commit()
        cursor.close()
        logger.info(f"[{symbol}] Synced quarterly data from yfinance")
        return True

    except Exception as e:
        logger.warning(f"[{symbol}] yfinance quarterly sync failed: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def compute_revenue_growth(conn, symbol: str):
    """
    Compute YoY revenue growth for all quarters in quarter_statement.
    Should be called after syncing new data.
    """
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, fiscal_year, fiscal_quarter, revenue
            FROM quarter_statement
            WHERE symbol = %s
            ORDER BY fiscal_year ASC, fiscal_quarter ASC
        """, (symbol,))
        rows = cursor.fetchall()
        if not rows:
            return

        # Build lookup for YoY comparison
        rev_map = {}
        for r in rows:
            rev_map[(r['fiscal_year'], r['fiscal_quarter'])] = r['revenue']

        update_cursor = conn.cursor()
        for r in rows:
            key_prev = (r['fiscal_year'] - 1, r['fiscal_quarter'])
            key_prev2 = (r['fiscal_year'] - 2, r['fiscal_quarter'])
            key_prev3 = (r['fiscal_year'] - 3, r['fiscal_quarter'])

            rev = r['revenue']
            rev_prev = rev_map.get(key_prev)
            rev_prev2 = rev_map.get(key_prev2)
            rev_prev3 = rev_map.get(key_prev3)

            rg1 = None
            rg2 = None
            rg3 = None

            if rev and rev_prev and float(rev_prev) != 0:
                rg1 = round((float(rev) - float(rev_prev)) / abs(float(rev_prev)), 4)
            if rev and rev_prev2 and float(rev_prev2) != 0:
                rg2 = round((float(rev) - float(rev_prev2)) / abs(float(rev_prev2)), 4)
            if rev and rev_prev3 and float(rev_prev3) != 0:
                rg3 = round((float(rev) - float(rev_prev3)) / abs(float(rev_prev3)), 4)

            update_cursor.execute("""
                UPDATE quarter_statement
                SET revenuegrowth = %s, revenuegrowth2 = %s, revenuegrowth3 = %s
                WHERE id = %s
            """, (rg1, rg2, rg3, r['id']))

        conn.commit()
        update_cursor.close()
        cursor.close()
    except Exception as e:
        logger.debug(f"[{symbol}] Revenue growth calc error: {e}")


# ==========================================================================
# MAIN ORCHESTRATION
# ==========================================================================

def score_symbol(conn, symbol: str, yfinance_fallback: bool = True) -> bool:
    """
    Run full scoring pipeline for a single symbol.

    Steps:
      1. Fetch quarterly data from MariaDB
      2. Optionally sync from yfinance if data is stale
      3. Compute revenue growth rates
      4. Compute all scoring tables
      5. Write results to MariaDB

    Returns True if scoring completed successfully.
    """
    logger.info(f"[{symbol}] Starting scoring pipeline...")

    # Step 1: Fetch existing quarterly data
    qtr_df = fetch_quarterly_data(conn, symbol)

    # Step 2: Check if data is stale and sync from yfinance
    latest_row = fetch_latest_quarterly_row(conn, symbol)
    data_is_stale = False

    if latest_row:
        # Check if the latest quarter is more than 120 days old
        # (quarterly filings are due ~45 days after quarter end)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(
                MAKEDATE(fiscal_year, 1) + INTERVAL (fiscal_quarter * 3) MONTH
            ) as latest_period
            FROM quarter_statement WHERE symbol = %s
        """, (symbol,))
        result = cursor.fetchone()
        cursor.close()
        if result and result[0]:
            latest_period = result[0]
            if hasattr(latest_period, 'date'):
                latest_period = latest_period.date()
            days_old = (date.today() - latest_period).days
            if days_old > 120:
                data_is_stale = True
                logger.info(f"[{symbol}] Quarterly data is {days_old} days old, syncing from yfinance")
    else:
        data_is_stale = True
        logger.info(f"[{symbol}] No quarterly data in DB, syncing from yfinance")

    if data_is_stale and yfinance_fallback and HAS_YFINANCE:
        sync_quarterly_from_yfinance(conn, symbol)
        compute_revenue_growth(conn, symbol)
        qtr_df = fetch_quarterly_data(conn, symbol)

    if qtr_df.empty:
        logger.warning(f"[{symbol}] No quarterly data available, skipping scoring")
        return False

    # Step 3: Fetch price data for volatility/trend calculations
    price_df = fetch_price_history(conn, symbol)

    # Step 4: Compute all scoring tables
    try:
        # 4a: Financial Ratios
        ratios = compute_ratios(symbol, qtr_df)
        ratios = enrich_ratios_with_yfinance(symbol, ratios)

        # 4b: Motley Fool
        mf_scores = compute_motleyfool(symbol, qtr_df)

        # 4c: InvestorPlace
        ip_scores = compute_investorplace(symbol, qtr_df, price_df)

        # 4d: Buffett Tenets
        tenets_scores = compute_tenets(symbol, qtr_df)

        # 4e: Business Quality
        business_scores = compute_evalbusiness(symbol, qtr_df)

        # 4f: Management Evaluation
        mgmt_scores = compute_evalmanagement(symbol, qtr_df)

        # 4g: Market Evaluation
        market_scores = compute_evalmarket(symbol, price_df)

        # 4h: Value Assessment
        value_scores = compute_evalvalue(symbol, qtr_df)

        # 4i: Summary
        summary = compute_evalsummary(
            symbol, mf_scores, ip_scores, tenets_scores,
            business_scores, ratios, mgmt_scores, market_scores, value_scores
        )

    except Exception as e:
        logger.error(f"[{symbol}] Scoring computation error: {e}", exc_info=True)
        return False

    # Step 5: Write all scores to MariaDB
    source = SOURCE_SCORING_ENGINE
    success = True

    table_writes = [
        (ratios, 'ratios'),
        (mf_scores, 'motleyfool'),
        (ip_scores, 'investorplace'),
        (tenets_scores, 'tenets'),
        (business_scores, 'evalbusiness'),
        (mgmt_scores, 'evalmanagement'),
        (market_scores, 'evalmarket'),
        (value_scores, 'evalvalue'),
        (summary, 'evalsummary'),
    ]

    for scores_dict, table_name in table_writes:
        if not scores_dict:
            continue
        ok = write_scores(conn, symbol, scores_dict, table_name, source)
        if not ok:
            logger.warning(f"[{symbol}] Failed to write to {table_name}")
            success = False

    if success:
        logger.info(f"[{symbol}] Scoring pipeline completed successfully")
    else:
        logger.warning(f"[{symbol}] Scoring pipeline completed with errors")

    return success


def run_scoring(symbols: Optional[List[str]] = None, yfinance_fallback: bool = True):
    """
    Main scoring loop. Fetches data, computes all scoring tables, writes to DB.

    Args:
        symbols: Optional list of symbols to score. If None, scores all active symbols.
        yfinance_fallback: If True, use yfinance to supplement stale MariaDB data.
    """
    logger.info("=" * 60)
    logger.info("SCORING ENGINE START")
    logger.info("=" * 60)

    start_time = time.time()
    conn = get_connection()

    try:
        # Get symbols to score
        if symbols:
            active_symbols = get_active_symbols(conn, symbols)
            # Also include symbols that might not be in active list
            if not active_symbols:
                active_symbols = symbols
        else:
            active_symbols = get_active_symbols(conn)

        logger.info(f"Scoring {len(active_symbols)} symbols")

        scored = 0
        failed = 0
        skipped = 0

        for i, symbol in enumerate(active_symbols):
            logger.info(f"[{i + 1}/{len(active_symbols)}] Processing {symbol}...")

            try:
                ok = score_symbol(conn, symbol, yfinance_fallback=yfinance_fallback)
                if ok:
                    scored += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"[{symbol}] Unhandled error: {e}", exc_info=True)
                failed += 1

            # Rate limiting: be nice to yfinance API
            if yfinance_fallback and HAS_YFINANCE:
                time.sleep(0.5)

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(
            f"SCORING ENGINE COMPLETE: {scored} scored, {skipped} skipped, "
            f"{failed} failed, {len(active_symbols)} total, {elapsed:.1f}s"
        )
        logger.info("=" * 60)

    finally:
        conn.close()


# ==========================================================================
# UTILITY FUNCTIONS
# ==========================================================================

def safe_float(val) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError, InvalidOperation):
        return None


# ==========================================================================
# CLI ENTRY POINT
# ==========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='KSF Stock Market — Fundamental Scoring Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scoring_engine.py                          # Score all active symbols
  python3 scoring_engine.py --symbols AAPL,MSFT,RY.TO  # Score specific symbols
  python3 scoring_engine.py --no-yfinance            # Use MariaDB data only
  python3 scoring_engine.py --table ratios           # Refresh only ratios table
        """
    )
    parser.add_argument(
        '--symbols', type=str, default=None,
        help='Comma-separated list of symbols to score (default: all active)'
    )
    parser.add_argument(
        '--no-yfinance', action='store_true',
        help='Disable yfinance fallback (use MariaDB data only)'
    )
    parser.add_argument(
        '--table', type=str, default=None,
        choices=['ratios', 'motleyfool', 'investorplace', 'tenets',
                 'evalbusiness', 'evalmanagement', 'evalmarket',
                 'evalvalue', 'evalsummary'],
        help='Score only a specific table (for targeted refresh)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]

    run_scoring(
        symbols=symbols,
        yfinance_fallback=not args.no_yfinance,
    )


if __name__ == '__main__':
    main()
