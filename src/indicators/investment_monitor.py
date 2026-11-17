#!/usr/bin/env python3
"""
Investment Monitoring Agent - v3 Enhanced Edition
===================================================
Modules:
  1. Technical Analysis (trend duration, signal strength, divergence, etc.)
  2. Fundamental Analysis (EPS, dividends, FCF, ROE, ratios, quality scoring)
  3. Sector Comparison (peer contrast, best performer analysis)
  4. News & Events (recent news, upcoming earnings, guidance, dividends)
  5. Backtesting Engine (historical signal accuracy vs sector/market)
  6. TSX/NYSE Symbol Disambiguation (auto-detect and correct)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import re
import time

# ============================================================================
# SYMBOL RESOLVER - TSX/NYSE Disambiguation
# ============================================================================

class SymbolResolver:
    """
    Resolves ambiguous ticker symbols by detecting whether a symbol
    belongs to TSX (Toronto Stock Exchange) or US exchange.
    
    Strategy:
    1. If symbol already has .TO suffix, use as-is
    2. If symbol ends in .UN (TSX trust), use as-is
    3. Try .TO version first for known Canadian patterns
    4. Compare both versions and pick the one that matches expected characteristics
    5. Cache results to avoid repeated lookups
    """
    
    # Known TSX tickers that are commonly ambiguous
    KNOWN_TSX = {
        'CM', 'CNR', 'RY', 'TD', 'BMO', 'BNS', 'ENB', 'TRP', 'SU', 'CVE',
        'ABX', 'BCE', 'T', 'RCI', 'QSR', 'DOL', 'ATD', 'L', 'MRU',
        'FTS', 'EMA', 'BIP.UN', 'HR.UN', 'SRU.UN', 'REI.UN', 'CAR.UN',
        'WJX', 'MTY', 'TFII', 'RUS', 'CDZ', 'PDC', 'PZA', 'KEG.UN',
        'SRV.UN', 'BPF.UN', 'NPI', 'XIC', 'ZCN', 'VUN', 'XEF', 'XUU',
        'XSP', 'XQQ', 'XEG', 'XFN', 'XIT', 'XMA', 'XUT', 'XRE',
    }
    
    # Known US tickers that should NOT get .TO
    KNOWN_US = {
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VEA', 'VWO',
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA',
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA',
        'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'LLY',
        'XOM', 'CVX', 'COP', 'SLB', 'OXY',
        'GLD', 'SLV', 'USO', 'UNG',
        'FEZ', 'IEV', 'SPEU', 'RGLD', 'MX', 'UL', 'PDC', 'PZA',
        'MICC', 'CEF',
    }
    
    def __init__(self):
        self.cache = {}
    
    def resolve(self, symbol: str) -> str:
        """Resolve a symbol to its canonical yfinance ticker.

        Delegates to the single canonical resolver (python/src/symbol_resolver.py)
        so the whole codebase shares ONE curated, deterministic disambiguation
        rule. The previous hand-rolled KNOWN_TSX/KNOWN_US lists re-introduced the
        dual-listed hijack the canonical resolver was built to prevent
        (e.g. RY/CM are NYSE tickers, not RY.TO/CM.TO; AGF.B must become AGF-B.TO).
        """
        if symbol in self.cache:
            return self.cache[symbol]
        import os as _os
        import sys as _sys
        _py_src = _os.path.abspath(
            _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), '..', 'python', 'src')
        )
        if _py_src not in _sys.path:
            _sys.path.insert(0, _py_src)
        from symbol_resolver import resolve_for_yfinance
        resolved = resolve_for_yfinance(symbol)
        self.cache[symbol] = resolved
        return resolved
    
    def _detect_exchange(self, symbol: str) -> str:
        """Detect whether a symbol is TSX or US by comparing both versions."""
        try:
            # Quick check: try .TO version
            stock_to = yf.Ticker(symbol + '.TO')
            info_to = stock_to.info

            to_has_name = bool(info_to.get('longName') or info_to.get('shortName'))
            to_currency = info_to.get('currency', '')
            to_exchange = info_to.get('exchange', '')

            if to_has_name and to_currency == 'CAD' and to_exchange == 'TOR':
                return symbol + '.TO'

            # If .TO exists but is USD/TSX-listed secondary (e.g., TFII.TO),
            # check if the primary US version has data too
            if to_has_name:
                stock_us = yf.Ticker(symbol)
                info_us = stock_us.info
                us_has_name = bool(info_us.get('longName') or info_us.get('shortName'))
                us_currency = info_us.get('currency', '')

                # If both exist, prefer US for USD primary, TSX for CAD primary
                if us_has_name and us_currency == 'USD':
                    return symbol  # US primary
                if to_currency == 'CAD':
                    return symbol + '.TO'  # TSX primary

            # Fall back to US version
            return symbol

        except Exception:
            return symbol
    
    def resolve_portfolio(self, symbols: List[str]) -> Dict[str, str]:
        """Resolve a list of symbols. Returns {original: resolved} mapping."""
        mapping = {}
        for sym in symbols:
            mapping[sym] = self.resolve(sym)
        return mapping


# ============================================================================
# TECHNICAL ANALYSIS MODULE
# ============================================================================

class TechnicalAnalyzer:
    """Comprehensive technical analysis with trend duration and signal strength."""
    
    @staticmethod
    def calculate(hist: pd.DataFrame) -> Dict:
        if hist.empty or len(hist) < 20:
            return {}
        
        close = hist['Close']
        high = hist['High']
        low = hist['Low']
        volume = hist['Volume']
        indicators = {}
        
        try:
            # Moving Averages
            indicators['sma_20'] = close.rolling(20).mean().iloc[-1]
            indicators['sma_50'] = close.rolling(50).mean().iloc[-1] if len(hist) >= 50 else None
            indicators['sma_200'] = close.rolling(200).mean().iloc[-1] if len(hist) >= 200 else None
            indicators['ema_12'] = close.ewm(span=12).mean().iloc[-1]
            indicators['ema_26'] = close.ewm(span=26).mean().iloc[-1]
            
            # Trend Duration
            sma20 = close.rolling(20).mean()
            indicators['trend_sma20_duration'], indicators['trend_sma20_direction'] = \
                TechnicalAnalyzer._trend_duration(close > sma20)
            
            if len(hist) >= 50:
                sma50 = close.rolling(50).mean()
                indicators['trend_sma50_duration'], indicators['trend_sma50_direction'] = \
                    TechnicalAnalyzer._trend_duration(close > sma50)
                
                # MA Alignment
                bullish = sma20 > sma50
                indicators['ma_alignment_duration'], _ = TechnicalAnalyzer._trend_duration(bullish)
                indicators['ma_alignment'] = 'BULLISH' if bullish.iloc[-1] else 'BEARISH'
            
            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
            indicators['rsi'] = rsi_series.iloc[-1]
            
            if indicators['rsi'] > 70:
                indicators['rsi_overbought_duration'] = TechnicalAnalyzer._consecutive(rsi_series, lambda x: x > 70)
            elif indicators['rsi'] < 30:
                indicators['rsi_oversold_duration'] = TechnicalAnalyzer._consecutive(rsi_series, lambda x: x < 30)
            
            indicators['rsi_divergence'] = TechnicalAnalyzer._divergence(close, rsi_series)
            
            # MACD
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line
            
            indicators['macd'] = macd_line.iloc[-1]
            indicators['macd_signal'] = signal_line.iloc[-1]
            indicators['macd_histogram'] = histogram.iloc[-1]
            indicators['macd_histogram_trend'] = 'INCREASING' if histogram.iloc[-1] > histogram.iloc[-2] else 'DECREASING'
            
            crossover = TechnicalAnalyzer._crossover(macd_line, signal_line)
            indicators['macd_crossover_days_ago'] = crossover['days_ago']
            indicators['macd_crossover_direction'] = crossover['direction']
            
            # Bollinger Bands
            sma20_bb = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_upper = sma20_bb + 2 * std20
            bb_lower = sma20_bb - 2 * std20
            bb_width = (bb_upper - bb_lower) / sma20_bb
            
            indicators['bb_upper'] = bb_upper.iloc[-1]
            indicators['bb_middle'] = sma20_bb.iloc[-1]
            indicators['bb_lower'] = bb_lower.iloc[-1]
            indicators['bb_position'] = (close.iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]) if (bb_upper.iloc[-1] - bb_lower.iloc[-1]) > 0 else 0.5
            indicators['bb_squeeze'] = bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1] * 0.5
            
            # Stochastic
            ll14 = low.rolling(14).min()
            hh14 = high.rolling(14).max()
            stoch_k = ((close - ll14) / (hh14 - ll14) * 100)
            indicators['stoch_k'] = stoch_k.iloc[-1]
            indicators['stoch_d'] = stoch_k.rolling(3).mean().iloc[-1]
            
            # Volume
            vol_sma = volume.rolling(20).mean()
            indicators['volume_sma'] = vol_sma.iloc[-1]
            indicators['volume_ratio'] = volume.iloc[-1] / vol_sma.iloc[-1] if vol_sma.iloc[-1] > 0 else 1
            vol5 = volume.tail(5).mean()
            vol20 = volume.tail(20).mean()
            indicators['volume_trend'] = 'INCREASING' if vol5 > vol20 * 1.2 else ('DECREASING' if vol5 < vol20 * 0.8 else 'STABLE')
            
            # OBV
            obv = (np.sign(close.diff()) * volume).cumsum()
            indicators['obv_trend'] = 'RISING' if obv.iloc[-1] > obv.rolling(20).mean().iloc[-1] else 'FALLING'
            
            # Price Changes
            indicators['price_change_1d'] = ((close.iloc[-1] / close.iloc[-2]) - 1) * 100 if len(hist) >= 2 else 0
            indicators['price_change_1w'] = ((close.iloc[-1] / close.iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0
            indicators['price_change_1m'] = ((close.iloc[-1] / close.iloc[-20]) - 1) * 100 if len(hist) >= 20 else 0
            indicators['price_change_3m'] = ((close.iloc[-1] / close.iloc[-60]) - 1) * 100 if len(hist) >= 60 else 0
            indicators['price_change_6m'] = ((close.iloc[-1] / close.iloc[0]) - 1) * 100 if len(hist) > 0 else 0
            
            # Volatility
            returns = close.pct_change().dropna()
            indicators['volatility_20d'] = returns.tail(20).std() * np.sqrt(252) * 100
            
            # Support/Resistance
            indicators['resistance_20d'] = high.tail(20).max()
            indicators['support_20d'] = low.tail(20).min()
            indicators['distance_to_resistance'] = ((indicators['resistance_20d'] - close.iloc[-1]) / close.iloc[-1]) * 100
            indicators['distance_to_support'] = ((close.iloc[-1] - indicators['support_20d']) / close.iloc[-1]) * 100
            
        except Exception as e:
            pass
        
        return indicators
    
    @staticmethod
    def _trend_duration(condition: pd.Series):
        if condition.empty:
            return 0, 'neutral'
        current = condition.iloc[-1]
        dur = 0
        for i in range(len(condition) - 1, -1, -1):
            if condition.iloc[i] == current:
                dur += 1
            else:
                break
        return dur, 'above' if current else 'below'
    
    @staticmethod
    def _consecutive(series, condition):
        count = 0
        for i in range(len(series) - 1, -1, -1):
            if condition(series.iloc[i]):
                count += 1
            else:
                break
        return count
    
    @staticmethod
    def _divergence(price, indicator, lookback=14):
        try:
            p = price.tail(lookback)
            ind = indicator.tail(lookback)
            p_trend = np.polyfit(range(len(p)), p.values, 1)[0]
            i_trend = np.polyfit(range(len(ind)), ind.values, 1)[0]
            if p_trend < 0 and i_trend > 0:
                return 'BULLISH_DIVERGENCE'
            elif p_trend > 0 and i_trend < 0:
                return 'BEARISH_DIVERGENCE'
            return 'NONE'
        except:
            return 'NONE'
    
    @staticmethod
    def _crossover(s1, s2):
        diff = s1 - s2
        sign = np.sign(diff)
        for i in range(len(sign) - 1, 0, -1):
            if sign.iloc[i] != sign.iloc[i-1]:
                return {'days_ago': len(sign) - 1 - i, 'direction': 'BULLISH' if sign.iloc[i] > 0 else 'BEARISH'}
        return {'days_ago': 999, 'direction': 'NONE'}


# ============================================================================
# FUNDAMENTAL ANALYSIS MODULE
# ============================================================================

class FundamentalAnalyzer:
    """Comprehensive fundamental analysis with quality scoring."""
    
    @staticmethod
    def fetch(ticker: str) -> Dict:
        try:
            info = yf.Ticker(ticker).info
            f = {}
            
            f['company_name'] = info.get('longName', ticker)
            f['sector'] = info.get('sector')
            f['industry'] = info.get('industry')
            
            # Valuation
            f['pe_trailing'] = info.get('trailingPE')
            f['pe_forward'] = info.get('forwardPE')
            f['peg_ratio'] = info.get('pegRatio')
            f['price_to_book'] = info.get('priceToBook')
            f['price_to_sales'] = info.get('priceToSalesTrailing12Months')
            f['ev_to_revenue'] = info.get('enterpriseToRevenue')
            f['ev_to_ebitda'] = info.get('enterpriseToEbitda')
            
            # Profitability
            f['profit_margin'] = info.get('profitMargins')
            f['operating_margin'] = info.get('operatingMargins')
            f['gross_margin'] = info.get('grossMargins')
            f['roe'] = info.get('returnOnEquity')
            f['roa'] = info.get('returnOnAssets')
            
            # Per-share
            f['eps_trailing'] = info.get('trailingEps')
            f['eps_forward'] = info.get('forwardEps')
            f['book_value'] = info.get('bookValue')
            f['cash_per_share'] = info.get('totalCashPerShare')
            
            # Dividends
            f['dividend_rate'] = info.get('dividendRate')
            f['dividend_yield'] = info.get('dividendYield')
            f['payout_ratio'] = info.get('payoutRatio')
            f['five_year_avg_yield'] = info.get('fiveYearAvgDividendYield')
            
            # Cash Flow
            f['free_cash_flow'] = info.get('freeCashflow')
            f['operating_cash_flow'] = info.get('operatingCashflow')
            
            # Balance Sheet
            f['total_debt'] = info.get('totalDebt')
            f['total_cash'] = info.get('totalCash')
            f['debt_to_equity'] = info.get('debtToEquity')
            f['current_ratio'] = info.get('currentRatio')
            f['quick_ratio'] = info.get('quickRatio')
            
            # Growth
            f['revenue_growth'] = info.get('revenueGrowth')
            f['earnings_growth'] = info.get('earningsGrowth')
            
            # Other
            f['beta'] = info.get('beta')
            f['market_cap'] = info.get('marketCap')
            f['shares_outstanding'] = info.get('sharesOutstanding')
            f['analyst_target'] = info.get('targetMeanPrice')
            f['analyst_recommendation'] = info.get('recommendationKey')
            f['num_analysts'] = info.get('numberOfAnalystOpinions')
            f['short_ratio'] = info.get('shortRatio')
            
            # Derived
            if f['free_cash_flow'] and f['shares_outstanding']:
                f['fcf_per_share'] = f['free_cash_flow'] / f['shares_outstanding']
            if f['free_cash_flow'] and f['market_cap']:
                f['fcf_yield'] = (f['free_cash_flow'] / f['market_cap']) * 100
            
            return f
        except Exception as e:
            return {}
    
    @staticmethod
    def analyze(f: Dict) -> Dict:
        if not f:
            return {'quality_score': 0, 'rating': 'N/A'}
        
        score, max_score = 0, 0
        strengths, concerns = [], []
        
        # ROE
        roe = f.get('roe')
        if roe is not None:
            max_score += 2
            if roe > 0.15: score += 2; strengths.append(f"Strong ROE: {roe:.1%}")
            elif roe > 0.10: score += 1
            else: concerns.append(f"Low ROE: {roe:.1%}")
        
        # ROA
        roa = f.get('roa')
        if roa is not None:
            max_score += 1
            if roa > 0.05: score += 1; strengths.append(f"Good ROA: {roa:.1%}")
        
        # Profit Margin
        pm = f.get('profit_margin')
        if pm is not None:
            max_score += 1
            if pm > 0.15: score += 1; strengths.append(f"Healthy profit margin: {pm:.1%}")
            elif pm < 0: concerns.append(f"Negative profit margin: {pm:.1%}")
        
        # Forward P/E
        pe = f.get('pe_forward')
        if pe is not None:
            max_score += 1
            if 0 < pe < 15: score += 1; strengths.append(f"Attractive forward P/E: {pe:.1f}")
            elif pe > 30: concerns.append(f"High forward P/E: {pe:.1f}")
        
        # P/B
        pb = f.get('price_to_book')
        if pb is not None:
            max_score += 1
            if pb < 3: score += 1
            elif pb > 10: concerns.append(f"High P/B: {pb:.1f}")
        
        # Debt/Equity
        de = f.get('debt_to_equity')
        if de is not None:
            max_score += 1
            if de < 1: score += 1; strengths.append(f"Low D/E: {de:.2f}")
            elif de > 2: concerns.append(f"High D/E: {de:.2f}")
        
        # Current Ratio
        cr = f.get('current_ratio')
        if cr is not None:
            max_score += 1
            if cr > 1.5: score += 1
            elif cr < 1: concerns.append(f"Low current ratio: {cr:.2f}")
        
        # FCF
        fcf = f.get('free_cash_flow')
        if fcf is not None:
            max_score += 2
            if fcf > 0:
                score += 1
                fcf_yield = f.get('fcf_yield')
                if fcf_yield and fcf_yield > 5:
                    score += 1; strengths.append(f"Strong FCF yield: {fcf_yield:.1f}%")
            else:
                concerns.append("Negative FCF")
        
        # Dividend
        dy = f.get('dividend_yield')
        if dy is not None:
            max_score += 1
            if dy > 2: score += 1; strengths.append(f"Attractive div yield: {dy:.2f}%")
        
        payout = f.get('payout_ratio')
        if payout is not None:
            max_score += 1
            if payout < 0.6: score += 1; strengths.append(f"Sustainable payout: {payout:.1%}")
            elif payout > 0.9: concerns.append(f"High payout: {payout:.1%}")
        
        # Revenue Growth
        rg = f.get('revenue_growth')
        if rg is not None:
            max_score += 1
            if rg > 0.1: score += 1; strengths.append(f"Strong revenue growth: {rg:.1%}")
            elif rg < 0: concerns.append(f"Declining revenue: {rg:.1%}")
        
        qs = (score / max_score * 100) if max_score > 0 else 0
        return {
            'quality_score': qs,
            'rating': 'EXCELLENT' if qs >= 80 else 'GOOD' if qs >= 60 else 'FAIR' if qs >= 40 else 'WEAK',
            'strengths': strengths,
            'concerns': concerns
        }


# ============================================================================
# NEWS & EVENTS MODULE
# ============================================================================

class NewsAnalyzer:
    """Fetches recent news and upcoming events for holdings."""
    
    @staticmethod
    def fetch(ticker: str) -> Dict:
        result = {'recent_news': [], 'upcoming_events': [], 'earnings': {}, 'dividends': {}}
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # === Recent News ===
            try:
                news = stock.news
                if news:
                    for article in news[:10]:
                        content = article.get('content', article)
                        title = content.get('title', article.get('title', ''))
                        pub_date = content.get('pubDate', article.get('pubDate', ''))
                        provider = content.get('provider', {}).get('displayName', article.get('publisher', ''))
                        url = content.get('canonicalUrl', {}).get('url', article.get('link', ''))
                        summary = content.get('summary', article.get('summary', ''))
                        
                        # Parse date
                        try:
                            if pub_date:
                                if isinstance(pub_date, str):
                                    pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                                    days_ago = (datetime.now(pub_dt.tzinfo) - pub_dt).days
                                else:
                                    days_ago = 0
                            else:
                                days_ago = 0
                        except:
                            days_ago = 0
                        
                        result['recent_news'].append({
                            'title': title,
                            'provider': provider,
                            'url': url,
                            'summary': summary[:200] if summary else '',
                            'days_ago': days_ago,
                        })
            except Exception:
                pass
            
            # === Upcoming Events from Calendar ===
            try:
                cal = stock.calendar
                if cal is not None and not (isinstance(cal, dict) and not cal):
                    if hasattr(cal, 'columns'):
                        # It's a DataFrame
                        for col in cal.columns:
                            val = cal[col].iloc[0] if len(cal) > 0 else None
                            if val is not None:
                                result['upcoming_events'].append({
                                    'event': str(col),
                                    'date': str(val),
                                    'type': 'calendar'
                                })
                    elif isinstance(cal, dict):
                        for k, v in cal.items():
                            result['upcoming_events'].append({
                                'event': str(k),
                                'date': str(v),
                                'type': 'calendar'
                            })
            except Exception:
                pass
            
            # === Earnings Dates ===
            try:
                ed = stock.earnings_dates
                if ed is not None and len(ed) > 0:
                    # Get next upcoming earnings
                    now = datetime.now()
                    for idx, row in ed.iterrows():
                        if hasattr(idx, 'tz_localize'):
                            earnings_date = idx.tz_localize(None) if idx.tzinfo else idx
                        else:
                            earnings_date = idx
                        
                        if isinstance(earnings_date, (datetime, date)) and earnings_date > now:
                            days_until = (earnings_date - now).days
                            result['earnings'] = {
                                'next_date': str(earnings_date.date() if hasattr(earnings_date, 'date') else earnings_date),
                                'days_until': days_until,
                                'eps_estimate': row.get('EPS Estimate', None),
                                'reported_eps': row.get('Reported EPS', None),
                            }
                            break
                    
                    # Last earnings
                    for idx, row in ed.iterrows():
                        if hasattr(idx, 'tz_localize'):
                            earnings_date = idx.tz_localize(None) if idx.tzinfo else idx
                        else:
                            earnings_date = idx
                        if isinstance(earnings_date, (datetime, date)) and earnings_date <= now:
                            result['earnings']['last_date'] = str(earnings_date.date() if hasattr(earnings_date, 'date') else earnings_date)
                            result['earnings']['last_reported_eps'] = row.get('Reported EPS', None)
                            result['earnings']['last_surprise'] = row.get('Surprise(%)', None)
                            break
            except Exception:
                pass
            
            # === Dividend Info ===
            try:
                if info.get('dividendDate'):
                    result['dividends']['next_date'] = str(info['dividendDate'])
                if info.get('exDividendDate'):
                    result['dividends']['ex_date'] = str(info['exDividendDate'])
                if info.get('dividendRate'):
                    result['dividends']['rate'] = info['dividendRate']
                if info.get('dividendYield'):
                    result['dividends']['yield'] = info['dividendYield']
            except Exception:
                pass
            
            # === Corporate Actions (splits, etc.) ===
            try:
                actions = stock.actions
                if actions is not None and len(actions) > 0:
                    recent_actions = actions.tail(5)
                    for idx, row in recent_actions.iterrows():
                        if row.get('Stock Splits', 0) != 0:
                            result['upcoming_events'].append({
                                'event': f"Stock Split: {row['Stock Splits']}",
                                'date': str(idx),
                                'type': 'action'
                            })
            except Exception:
                pass
                
        except Exception as e:
            pass
        
        return result


# ============================================================================
# SECTOR COMPARISON MODULE
# ============================================================================

class SectorComparator:
    """Compares holdings to sector peers and best performers."""
    
    SECTOR_ETFS = {
        'Technology': 'XLK', 'Healthcare': 'XLV', 'Financial Services': 'XLF',
        'Consumer Cyclical': 'XLY', 'Consumer Defensive': 'XLP', 'Energy': 'XLE',
        'Industrials': 'XLI', 'Utilities': 'XLU', 'Real Estate': 'XLRE',
        'Communication Services': 'XLC', 'Basic Materials': 'XLB',
    }
    
    @staticmethod
    def compare(ticker: str, fundamentals: Dict, indicators: Dict) -> Dict:
        result = {'sector': fundamentals.get('sector'), 'industry': fundamentals.get('industry')}
        sector = fundamentals.get('sector')
        
        if not sector:
            return result
        
        etf_symbol = SectorComparator.SECTOR_ETFS.get(sector)
        if not etf_symbol:
            return result
        
        try:
            etf = yf.Ticker(etf_symbol)
            etf_hist = etf.history(period="6mo")
            etf_info = etf.info
            
            if etf_hist.empty:
                return result
            
            result['etf_symbol'] = etf_symbol
            result['etf_name'] = etf_info.get('longName', etf_symbol)
            result['etf_pe'] = etf_info.get('trailingPE')
            result['sector_perf_1m'] = ((etf_hist['Close'].iloc[-1] / etf_hist['Close'].iloc[-20]) - 1) * 100 if len(etf_hist) >= 20 else None
            result['sector_perf_3m'] = ((etf_hist['Close'].iloc[-1] / etf_hist['Close'].iloc[-60]) - 1) * 100 if len(etf_hist) >= 60 else None
            result['sector_perf_6m'] = ((etf_hist['Close'].iloc[-1] / etf_hist['Close'].iloc[0]) - 1) * 100
            
            # Stock vs Sector
            for period, key in [('1m', 'price_change_1m'), ('3m', 'price_change_3m'), ('6m', 'price_change_6m')]:
                stock_val = indicators.get(key)
                sector_val = result.get(f'sector_perf_{period}')
                if stock_val is not None and sector_val is not None:
                    result[f'vs_sector_{period}'] = {
                        'stock': stock_val, 'sector': sector_val,
                        'outperformance': stock_val - sector_val
                    }
            
            # Peer comparison via ETF holdings
            peers = []
            try:
                holders = etf.institutional_holders
                if holders is not None and len(holders) > 0:
                    peer_syms = holders['Holder'].head(10).tolist() if 'Holder' in holders.columns else holders.index.tolist()[:10]
                    
                    for ps in peer_syms:
                        try:
                            ps_stock = yf.Ticker(ps)
                            ps_info = ps_stock.info
                            ps_hist = ps_stock.history(period="6mo")
                            if not ps_hist.empty:
                                peers.append({
                                    'symbol': ps,
                                    'name': ps_info.get('longName', ps),
                                    'pe': ps_info.get('trailingPE'),
                                    'div_yield': ps_info.get('dividendYield'),
                                    'roe': ps_info.get('returnOnEquity'),
                                    'profit_margin': ps_info.get('profitMargins'),
                                    'rev_growth': ps_info.get('revenueGrowth'),
                                    'perf_1m': ((ps_hist['Close'].iloc[-1] / ps_hist['Close'].iloc[-20]) - 1) * 100 if len(ps_hist) >= 20 else None,
                                    'perf_3m': ((ps_hist['Close'].iloc[-1] / ps_hist['Close'].iloc[-60]) - 1) * 100 if len(ps_hist) >= 60 else None,
                                    'perf_6m': ((ps_hist['Close'].iloc[-1] / ps_hist['Close'].iloc[0]) - 1) * 100,
                                })
                        except:
                            continue
            except:
                pass
            
            result['peers'] = peers
            
            # Best performers
            if peers:
                for period in ['1m', '3m', '6m']:
                    key = f'perf_{period}'
                    valid = [p for p in peers if p.get(key) is not None]
                    if valid:
                        best = max(valid, key=lambda x: x[key])
                        result[f'best_{period}'] = {'symbol': best['symbol'], 'name': best['name'], 'perf': best[key]}
            
            # Compare to peer averages
            for metric in ['pe', 'div_yield', 'roe', 'profit_margin', 'rev_growth']:
                vals = [p[metric] for p in peers if p.get(metric) is not None]
                if vals:
                    stock_val = fundamentals.get({
                        'pe': 'pe_trailing', 'div_yield': 'dividend_yield',
                        'roe': 'roe', 'profit_margin': 'profit_margin', 'rev_growth': 'revenue_growth'
                    }.get(metric))
                    avg = np.mean(vals)
                    all_vals = sorted(vals + ([stock_val] if stock_val else []))
                    pctile = (all_vals.index(stock_val) / len(all_vals) * 100) if stock_val else None
                    result[f'peer_avg_{metric}'] = avg
                    result[f'peer_pctile_{metric}'] = pctile
                    if stock_val and avg:
                        result[f'vs_peer_{metric}'] = ((stock_val - avg) / abs(avg)) * 100
            
        except Exception as e:
            result['error'] = str(e)
        
        return result


# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

class BacktestEngine:
    """
    Backtests trading signals against historical data.
    
    For each holding, goes back 12, 9, 6, 3, 2, 1 months and:
    1. Calculates what the signal WOULD HAVE BEEN at that date
    2. Compares the recommendation to actual future performance
    3. Scores accuracy (win/loss) against sector and market
    """
    
    LOOKBACK_PERIODS = [12, 9, 6, 3, 2, 1]  # months
    BENCHMARK = '^GSPC'  # S&P 500
    
    def __init__(self):
        self.results = {}
    
    def run(self, ticker: str, sector_etf: str = None) -> Dict:
        """Run backtest for a single ticker."""
        result = {'ticker': ticker, 'periods': [], 'accuracy': {}, 'summary': {}}
        
        try:
            # Fetch extended history
            stock = yf.Ticker(ticker)
            hist = stock.history(period="18mo")
            
            if hist.empty or len(hist) < 250:
                return {'error': 'Insufficient history'}
            
            # Fetch benchmark
            try:
                bench = yf.Ticker(self.BENCHMARK).history(period="18mo")
            except:
                bench = None
            
            # Fetch sector ETF if provided
            sector_hist = None
            if sector_etf:
                try:
                    sector_hist = yf.Ticker(sector_etf).history(period="18mo")
                except:
                    pass
            
            wins, losses, holds = 0, 0, 0
            sector_wins, sector_losses = 0, 0
            market_wins, market_losses = 0, 0
            
            for months_back in self.LOOKBACK_PERIODS:
                # Find the index for this lookback period
                target_date = hist.index[-1] - pd.DateOffset(months=months_back)
                idx = hist.index.get_indexer([target_date], method='nearest')[0]
                
                if idx < 60:  # Need at least 60 days of prior data
                    continue
                
                # Historical data up to that point
                hist_at_date = hist.iloc[:idx+1]
                
                # Calculate indicators at that date
                indicators = TechnicalAnalyzer.calculate(hist_at_date)
                
                if not indicators:
                    continue
                
                # Generate signal at that date
                signal = self._generate_historical_signal(indicators)
                
                # Actual future performance (1 month later)
                future_idx = min(idx + 21, len(hist) - 1)
                price_at_signal = hist['Close'].iloc[idx]
                price_1m_future = hist['Close'].iloc[future_idx]
                actual_return = ((price_1m_future / price_at_signal) - 1) * 100
                
                # Determine if signal was correct
                outcome = self._evaluate_outcome(signal['signal'], actual_return)
                
                # Benchmark comparison
                bench_return = None
                if bench is not None and len(bench) > 0:
                    bench_idx = bench.index.get_indexer([target_date], method='nearest')[0]
                    bench_future = min(bench_idx + 21, len(bench) - 1)
                    if bench_idx < len(bench):
                        bench_return = ((bench['Close'].iloc[bench_future] / bench['Close'].iloc[bench_idx]) - 1) * 100
                
                # Sector comparison
                sector_return = None
                if sector_hist is not None and len(sector_hist) > 0:
                    sec_idx = sector_hist.index.get_indexer([target_date], method='nearest')[0]
                    sec_future = min(sec_idx + 21, len(sector_hist) - 1)
                    if sec_idx < len(sector_hist):
                        sector_return = ((sector_hist['Close'].iloc[sec_future] / sector_hist['Close'].iloc[sec_idx]) - 1) * 100
                
                period_result = {
                    'date': str(hist.index[idx].date()),
                    'months_back': months_back,
                    'signal': signal['signal'],
                    'confidence': signal['confidence'],
                    'signal_reasons': signal.get('reasons', []),
                    'signal_details': signal.get('details', []),
                    'buy_score': signal.get('buy_score', 0),
                    'sell_score': signal.get('sell_score', 0),
                    'price_at_signal': price_at_signal,
                    'price_1m_future': price_1m_future,
                    'actual_1m_return': actual_return,
                    'outcome': outcome,
                    'outcome_explanation': self._outcome_explanation(signal['signal'], actual_return, outcome),
                    'benchmark_return': bench_return,
                    'sector_return': sector_return,
                    'vs_benchmark': (actual_return - bench_return) if bench_return is not None else None,
                    'vs_sector': (actual_return - sector_return) if sector_return is not None else None,
                }
                
                result['periods'].append(period_result)
                
                # Track accuracy
                if outcome == 'WIN':
                    wins += 1
                elif outcome == 'LOSS':
                    losses += 1
                else:
                    holds += 1
                
                # Track vs benchmark
                if bench_return is not None:
                    if actual_return > bench_return:
                        market_wins += 1
                    elif actual_return < bench_return:
                        market_losses += 1
                
                # Track vs sector
                if sector_return is not None:
                    if actual_return > sector_return:
                        sector_wins += 1
                    elif actual_return < sector_return:
                        sector_losses += 1
            
            # Summary
            total = wins + losses
            result['accuracy'] = {
                'wins': wins,
                'losses': losses,
                'holds': holds,
                'win_rate': (wins / total * 100) if total > 0 else 0,
                'total_signals': total,
            }
            result['vs_market'] = {
                'wins': market_wins, 'losses': market_losses,
                'beat_rate': (market_wins / (market_wins + market_losses) * 100) if (market_wins + market_losses) > 0 else 0
            }
            result['vs_sector'] = {
                'wins': sector_wins, 'losses': sector_losses,
                'beat_rate': (sector_wins / (sector_wins + sector_losses) * 100) if (sector_wins + sector_losses) > 0 else 0
            }
            
            # Outcome sequence for pattern analysis
            result['outcome_sequence'] = [p['outcome'] for p in result['periods']]
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _generate_historical_signal(self, indicators: Dict) -> Dict:
        """Generate signal from historical indicators.
        
        Returns the full signal dict (signal, confidence, reasons, details,
        buy_score, sell_score) so the backtest can display what the recommendation
        was based on.
        """
        # Use the full SignalGenerator for consistency with live signals
        return SignalGenerator.generate(indicators)
    
    def _evaluate_outcome(self, signal: str, actual_return: float) -> str:
        """Evaluate if a signal was correct."""
        if signal == 'BUY':
            return 'WIN' if actual_return > 0 else 'LOSS'
        elif signal == 'SELL':
            return 'WIN' if actual_return < 0 else 'LOSS'
        return 'HOLD'

    def _outcome_explanation(self, signal: str, actual_return: float, outcome: str) -> str:
        """Generate a human-readable explanation of what the outcome means."""
        if signal == 'BUY':
            if outcome == 'WIN':
                return f"BUY was correct — stock gained {actual_return:+.1f}% over the next month"
            else:
                return f"BUY was incorrect — stock lost {actual_return:+.1f}% over the next month"
        elif signal == 'SELL':
            if outcome == 'WIN':
                return f"SELL was correct — stock fell {actual_return:+.1f}% over the next month"
            else:
                return f"SELL was incorrect — stock rose {actual_return:+.1f}% over the next month"
        else:
            return f"HOLD — stock moved {actual_return:+.1f}% over the next month (no directional call)"


# ============================================================================
# SIGNAL GENERATOR
# ============================================================================

# ============================================================================
# MACRO REGIME FILTER
# ============================================================================

class MacroRegimeFilter:
    """
    Assesses the broader market environment to calibrate signal confidence.
    
    Indicators:
    - VIX level and trend (fear gauge)
    - S&P 500 vs its own SMA200 (market direction)
    - SMA200 slope (is the trend accelerating or flattening?)
    
    Outputs a regime score from 0.0 (very bearish) to 1.0 (very bullish)
    and a confidence multiplier to dampen signals in hostile environments.
    """
    
    VIX_LOW = 15
    VIX_NORMAL = 20
    VIX_HIGH = 25
    VIX_EXTREME = 30
    
    @staticmethod
    def analyze(hist: pd.DataFrame, vix_value: float = None, market_hist: pd.DataFrame = None) -> Dict:
        result = {
            'regime': 'NEUTRAL',
            'regime_score': 0.5,
            'confidence_multiplier': 1.0,
            'vix_regime': 'UNKNOWN',
            'market_direction': 'UNKNOWN',
            'sma200_slope': 'FLAT',
            'warnings': [],
            'boosters': [],
        }
        
        if hist.empty or len(hist) < 200:
            return result
        
        close = hist['Close']
        
        # SMA200 Slope
        sma200 = close.rolling(200).mean()
        if len(sma200) >= 21:
            sma200_current = sma200.iloc[-1]
            sma200_20ago = sma200.iloc[-21]
            slope_pct = ((sma200_current - sma200_20ago) / sma200_20ago) * 100
            
            if slope_pct > 2:
                result['sma200_slope'] = 'RISING'
                result['regime_score'] += 0.15
                result['boosters'].append(f"SMA200 rising ({slope_pct:+.1f}% over 20d)")
            elif slope_pct < -2:
                result['sma200_slope'] = 'FALLING'
                result['regime_score'] -= 0.20
                result['warnings'].append(f"SMA200 falling ({slope_pct:+.1f}% over 20d)")
            else:
                result['sma200_slope'] = 'FLAT'
                result['regime_score'] -= 0.05
                result['warnings'].append("SMA200 flat — no clear trend")
        
        # VIX Analysis
        if vix_value is not None:
            if vix_value <= MacroRegimeFilter.VIX_LOW:
                result['vix_regime'] = 'LOW'
                result['regime_score'] += 0.05
            elif vix_value <= MacroRegimeFilter.VIX_NORMAL:
                result['vix_regime'] = 'NORMAL'
                result['regime_score'] += 0.10
                result['boosters'].append(f"VIX normal ({vix_value:.1f})")
            elif vix_value <= MacroRegimeFilter.VIX_HIGH:
                result['vix_regime'] = 'ELEVATED'
                result['regime_score'] -= 0.15
                result['warnings'].append(f"VIX elevated ({vix_value:.1f}) — reduce confidence")
            elif vix_value <= MacroRegimeFilter.VIX_EXTREME:
                result['vix_regime'] = 'HIGH'
                result['regime_score'] -= 0.25
                result['warnings'].append(f"VIX high ({vix_value:.1f}) — signals less reliable")
            else:
                result['vix_regime'] = 'EXTREME'
                result['regime_score'] -= 0.15
                result['warnings'].append(f"VIX extreme ({vix_value:.1f}) — panic, contrarian BUY possible")
        
        # Market Direction
        if market_hist is not None and not market_hist.empty and len(market_hist) >= 200:
            mkt_close = market_hist['Close']
            mkt_sma200 = mkt_close.rolling(200).mean()
            if mkt_close.iloc[-1] > mkt_sma200.iloc[-1]:
                result['market_direction'] = 'ABOVE_SMA200'
                result['regime_score'] += 0.10
                result['boosters'].append("S&P 500 above SMA200 — bullish regime")
            else:
                result['market_direction'] = 'BELOW_SMA200'
                result['regime_score'] -= 0.20
                result['warnings'].append("S&P 500 below SMA200 — bearish regime")
        
        # Confidence multiplier: 0.6 (bearish) to 1.1 (bullish)
        score = max(0.0, min(1.0, result['regime_score'] + 0.5))
        result['confidence_multiplier'] = 0.6 + score * 0.5
        
        if result['regime_score'] > 0.25:
            result['regime'] = 'BULLISH'
        elif result['regime_score'] < -0.15:
            result['regime'] = 'BEARISH'
        else:
            result['regime'] = 'NEUTRAL'
        
        return result


# ============================================================================
# MARKET-RELATIVE INDICATORS
# ============================================================================

class MarketRelativeIndicators:
    """
    Measures how a stock behaves relative to the broader market and its sector.
    
    Indicators:
    - Stock return vs sector return (1M, 3M, 6M)
    - Stock return vs S&P 500 return (1M, 3M, 6M)
    - Correlation coefficient (stock vs market, 60-day)
    - Relative strength rank (leading or lagging?)
    - Inverse ETF trend (SH rising = market falling)
    """
    
    def __init__(self):
        self._cache = {}
    
    def analyze(self, ticker: str, hist: pd.DataFrame, sector_etf: str = None,
                resolved_ticker: str = None) -> Dict:
        result = {
            'vs_market_1m': None, 'vs_market_3m': None, 'vs_market_6m': None,
            'vs_sector_1m': None, 'vs_sector_3m': None, 'vs_sector_6m': None,
            'correlation_60d': None,
            'relative_strength': 'NEUTRAL',
            'stock_direction': 'NEUTRAL',
            'market_direction': 'NEUTRAL',
            'alignment': 'NEUTRAL',
            'inverse_etf_trend': None,
            'reasons': [],
            'details': [],
        }
        
        if hist.empty or len(hist) < 60:
            return result
        
        close = hist['Close']
        stock_1m = ((close.iloc[-1] / close.iloc[-20]) - 1) * 100 if len(hist) >= 20 else None
        stock_3m = ((close.iloc[-1] / close.iloc[-60]) - 1) * 100 if len(hist) >= 60 else None
        stock_6m = ((close.iloc[-1] / close.iloc[0]) - 1) * 100 if len(hist) >= 120 else None
        
        if stock_1m is not None:
            if stock_1m > 2:
                result['stock_direction'] = 'RISING'
            elif stock_1m < -2:
                result['stock_direction'] = 'FALLING'
            else:
                result['stock_direction'] = 'FLAT'
        
        # Market comparison
        try:
            mkt = self._get_market_hist()
            if mkt is not None and not mkt.empty:
                mkt_close = mkt['Close']
                mkt_1m = ((mkt_close.iloc[-1] / mkt_close.iloc[-20]) - 1) * 100 if len(mkt) >= 20 else None
                mkt_3m = ((mkt_close.iloc[-1] / mkt_close.iloc[-60]) - 1) * 100 if len(mkt) >= 60 else None
                mkt_6m = ((mkt_close.iloc[-1] / mkt_close.iloc[0]) - 1) * 100
                
                if mkt_1m is not None and stock_1m is not None:
                    result['vs_market_1m'] = stock_1m - mkt_1m
                if mkt_3m is not None and stock_3m is not None:
                    result['vs_market_3m'] = stock_3m - mkt_3m
                if stock_6m is not None:
                    result['vs_market_6m'] = stock_6m - mkt_6m
                
                if mkt_1m is not None:
                    if mkt_1m > 1:
                        result['market_direction'] = 'RISING'
                    elif mkt_1m < -1:
                        result['market_direction'] = 'FALLING'
                    else:
                        result['market_direction'] = 'FLAT'
                
                # Correlation
                stock_returns = close.tail(60).pct_change().dropna()
                mkt_aligned = mkt_close.tail(len(stock_returns)).pct_change().dropna()
                min_len = min(len(stock_returns), len(mkt_aligned))
                if min_len >= 20:
                    corr = np.corrcoef(stock_returns.tail(min_len).values, mkt_aligned.tail(min_len).values)[0, 1]
                    result['correlation_60d'] = corr
                
                # Alignment
                if stock_1m is not None and mkt_1m is not None:
                    if (stock_1m > 1 and mkt_1m > 0.5) or (stock_1m < -1 and mkt_1m < -0.5):
                        result['alignment'] = 'ALIGNED'
                        result['details'].append(f"Stock and market aligned (both {'up' if stock_1m > 0 else 'down'})")
                    elif (stock_1m > 2 and mkt_1m < -0.5) or (stock_1m < -2 and mkt_1m > 0.5):
                        result['alignment'] = 'DIVERGENT'
                        result['reasons'].append(f"Stock diverging from market — stock {stock_1m:+.1f}% vs S&P {mkt_1m:+.1f}% (1M)")
        except Exception as e:
            result['details'].append(f"Market comparison unavailable: {e}")
        
        # Sector comparison
        if sector_etf:
            try:
                sec = self._get_sector_hist(sector_etf)
                if sec is not None and not sec.empty:
                    sec_close = sec['Close']
                    sec_1m = ((sec_close.iloc[-1] / sec_close.iloc[-20]) - 1) * 100 if len(sec) >= 20 else None
                    sec_3m = ((sec_close.iloc[-1] / sec_close.iloc[-60]) - 1) * 100 if len(sec) >= 60 else None
                    sec_6m = ((sec_close.iloc[-1] / sec_close.iloc[0]) - 1) * 100
                    if sec_1m is not None and stock_1m is not None:
                        result['vs_sector_1m'] = stock_1m - sec_1m
                    if sec_3m is not None and stock_3m is not None:
                        result['vs_sector_3m'] = stock_3m - sec_3m
                    if stock_6m is not None:
                        result['vs_sector_6m'] = stock_6m - sec_6m
            except Exception:
                pass
        
        # Relative Strength
        vs_mkt = result.get('vs_market_1m')
        vs_sec = result.get('vs_sector_1m')
        if vs_mkt is not None and vs_sec is not None:
            if vs_mkt > 2 and vs_sec > 1:
                result['relative_strength'] = 'STRONG_OUTPERFORM'
                result['reasons'].append(f"Outperforming: +{vs_mkt:.1f}% vs S&P, +{vs_sec:.1f}% vs sector (1M)")
            elif vs_mkt < -2 and vs_sec < -1:
                result['relative_strength'] = 'WEAK_UNDERPERFORM'
                result['reasons'].append(f"Underperforming: {vs_mkt:.1f}% vs S&P, {vs_sec:.1f}% vs sector (1M)")
            else:
                result['relative_strength'] = 'IN_LINE'
        
        # Inverse ETF check
        try:
            sh_hist = yf.Ticker('SH').history(period='3mo')
            if not sh_hist.empty and len(sh_hist) >= 20:
                sh_1m = ((sh_hist['Close'].iloc[-1] / sh_hist['Close'].iloc[-20]) - 1) * 100
                if sh_1m > 3:
                    result['inverse_etf_trend'] = 'SH_RISING_MARKET_FALLING'
                    result['reasons'].append(f"SH (inverse S&P) up +{sh_1m:.1f}% — confirms market weakness")
                elif sh_1m < -3:
                    result['inverse_etf_trend'] = 'SH_FALLING_MARKET_RISING'
                    result['details'].append(f"SH (inverse S&P) down {sh_1m:.1f}% — confirms market strength")
                else:
                    result['inverse_etf_trend'] = 'NEUTRAL'
        except Exception:
            pass
        
        return result
    
    def _get_market_hist(self):
        if 'SPY' in self._cache:
            return self._cache['SPY']
        try:
            h = yf.Ticker('SPY').history(period='18mo')
            self._cache['SPY'] = h
            return h
        except:
            return None
    
    def _get_sector_hist(self, etf):
        if etf in self._cache:
            return self._cache[etf]
        try:
            h = yf.Ticker(etf).history(period='6mo')
            self._cache[etf] = h
            return h
        except:
            return None


# ============================================================================
# VOLUME PROFILE / OPTIONS-STYLE LEVELS
# ============================================================================

class VolumeProfileAnalyzer:
    """
    Identifies key support/resistance levels from volume profile.
    
    - Point of Control (POC): Price level with highest volume
    - Value Area High/Low (VAH/VAL): Range containing ~70% of volume
    - VWAP: Volume-Weighted Average Price
    - Nearest support/resistance from volume clusters
    """
    
    @staticmethod
    def analyze(hist: pd.DataFrame, lookback: int = 60) -> Dict:
        result = {
            'poc': None, 'vah': None, 'val': None,
            'vwap': None, 'vwap_current': None,
            'nearest_support': None, 'nearest_resistance': None,
            'price_vs_vwap': None,
            'levels': [], 'reasons': [], 'details': [],
        }
        
        if hist.empty or len(hist) < 20:
            return result
        
        h = hist.tail(lookback).copy()
        
        # VWAP
        typical_price = (h['High'] + h['Low'] + h['Close']) / 3
        cum_vol = h['Volume'].cumsum()
        cum_tp_vol = (typical_price * h['Volume']).cumsum()
        vwap_series = cum_tp_vol / cum_vol
        result['vwap'] = vwap_series.iloc[-1]
        result['vwap_current'] = result['vwap']
        
        current_price = h['Close'].iloc[-1]
        result['price_vs_vwap'] = ((current_price / result['vwap']) - 1) * 100 if result['vwap'] > 0 else 0
        
        if result['price_vs_vwap'] > 2:
            result['details'].append(f"Price {result['price_vs_vwap']:+.1f}% above VWAP — overextended")
        elif result['price_vs_vwap'] < -2:
            result['details'].append(f"Price {result['price_vs_vwap']:+.1f}% below VWAP — below fair value")
        else:
            result['details'].append(f"Price near VWAP ({result['price_vs_vwap']:+.1f}%) — fair value")
        
        # Volume Profile (binned)
        n_bins = 20
        price_min = h['Low'].min()
        price_max = h['High'].max()
        if price_max <= price_min:
            return result
        
        bin_width = (price_max - price_min) / n_bins
        bins = [price_min + i * bin_width for i in range(n_bins + 1)]
        
        volume_by_price = {}
        for i in range(len(h)):
            row = h.iloc[i]
            low, high, vol = row['Low'], row['High'], row['Volume']
            price_range = high - low if high > low else 1
            for j in range(n_bins):
                bin_low, bin_high = bins[j], bins[j + 1]
                overlap_low, overlap_high = max(low, bin_low), min(high, bin_high)
                if overlap_high > overlap_low:
                    fraction = (overlap_high - overlap_low) / price_range
                    bin_mid = (bin_low + bin_high) / 2
                    volume_by_price[bin_mid] = volume_by_price.get(bin_mid, 0) + vol * fraction
        
        if not volume_by_price:
            return result
        
        poc = max(volume_by_price, key=volume_by_price.get)
        result['poc'] = poc
        
        # Value Area (70% of volume)
        sorted_levels = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        total_vol = sum(volume_by_price.values())
        cum_vol_pct = 0
        va_levels = []
        for price, vol in sorted_levels:
            cum_vol_pct += vol / total_vol
            va_levels.append(price)
            if cum_vol_pct >= 0.70:
                break
        
        if va_levels:
            result['vah'] = max(va_levels)
            result['val'] = min(va_levels)
        
        # Nearest support/resistance
        levels_below = [(p, v) for p, v in volume_by_price.items() if p < current_price]
        levels_above = [(p, v) for p, v in volume_by_price.items() if p > current_price]
        
        if levels_below:
            result['nearest_support'] = max(levels_below, key=lambda x: x[0])[0]
        if levels_above:
            result['nearest_resistance'] = min(levels_above, key=lambda x: x[0])[0]
        
        if result['nearest_support'] is not None:
            dist = ((current_price - result['nearest_support']) / current_price) * 100
            if dist < 3:
                result['reasons'].append(f"Near volume support at ${result['nearest_support']:.2f} ({dist:.1f}% below)")
        
        if result['nearest_resistance'] is not None:
            dist = ((result['nearest_resistance'] - current_price) / current_price) * 100
            if dist < 3:
                result['reasons'].append(f"Near volume resistance at ${result['nearest_resistance']:.2f} ({dist:.1f}% above)")
        
        if result['poc']:
            if current_price > result['poc']:
                result['details'].append(f"Price above POC (${result['poc']:.2f}) — bullish conviction zone")
            else:
                result['details'].append(f"Price below POC (${result['poc']:.2f}) — bearish conviction zone")
        
        result['levels'] = sorted(volume_by_price.items(), key=lambda x: -x[1])[:5]
        
        return result


# ============================================================================
# CALIBRATED SIGNAL GENERATOR (v4)
# ============================================================================

class SignalGenerator:
    """
    V4: Calibrated buy/sell/hold signals with:
    - Macro regime filtering (VIX, market direction, SMA200 slope)
    - Market-relative indicators (stock vs sector, correlation)
    - Volume profile levels (POC, VWAP, value area)
    - Inverse ETF confirmation (SH)
    - Confidence calibration (dampen in hostile regimes)
    - Minimum trend duration thresholds
    - Divergence contradiction detection
    """
    
    MIN_ALIGNMENT_DURATION = 20
    
    @staticmethod
    def generate(indicators: Dict, macro: Dict = None, relative: Dict = None,
                 volume_profile: Dict = None) -> Dict:
        if not indicators:
            return {'signal': 'HOLD', 'confidence': 0, 'reasons': ['No data']}
        
        signals, reasons, details = [], [], []
        buy_signals, sell_signals = [], []
        
        sma20 = indicators.get('sma_20')
        sma50 = indicators.get('sma_50')
        sma200 = indicators.get('sma_200')
        rsi = indicators.get('rsi')
        macd = indicators.get('macd')
        macd_sig = indicators.get('macd_signal')
        stoch = indicators.get('stoch_k')
        bb_pos = indicators.get('bb_position')
        bb_squeeze = indicators.get('bb_squeeze')
        vol_ratio = indicators.get('volume_ratio', 1)
        
        # === TREND (with duration threshold) ===
        if sma20 and sma50:
            align = indicators.get('ma_alignment', '')
            align_dur = indicators.get('ma_alignment_duration', 0)
            if align == 'BULLISH':
                base_strength = min(0.3 + align_dur / 100, 0.5)
                if align_dur < SignalGenerator.MIN_ALIGNMENT_DURATION:
                    base_strength *= 0.7
                    details.append(f"Short MA alignment ({align_dur}d < {SignalGenerator.MIN_ALIGNMENT_DURATION}d) — reduced")
                signals.append(('BUY', base_strength))
                buy_signals.append('MA_ALIGN')
                reasons.append(f"Bullish MA alignment for {align_dur} days")
            elif align == 'BEARISH':
                base_strength = min(0.3 + align_dur / 100, 0.5)
                if align_dur < SignalGenerator.MIN_ALIGNMENT_DURATION:
                    base_strength *= 0.7
                    details.append(f"Short MA alignment ({align_dur}d < {SignalGenerator.MIN_ALIGNMENT_DURATION}d) — reduced")
                signals.append(('SELL', base_strength))
                sell_signals.append('MA_ALIGN')
                reasons.append(f"Bearish MA alignment for {align_dur} days")
        
        if sma200:
            if indicators.get('trend_sma20_direction') == 'above' and sma20 and sma20 > sma200:
                signals.append(('BUY', 0.1))
                buy_signals.append('SMA200')
                reasons.append("Price above SMA200 (long-term uptrend)")
            elif indicators.get('trend_sma20_direction') == 'below' and sma20 and sma20 < sma200:
                signals.append(('SELL', 0.15))
                sell_signals.append('SMA200')
                reasons.append("Price below SMA200 (long-term downtrend)")
        
        # === RSI ===
        if rsi:
            if rsi > 70:
                dur = indicators.get('rsi_overbought_duration', 0)
                signals.append(('SELL', min(0.2 + dur * 0.05, 0.35)))
                sell_signals.append('RSI_OB')
                reasons.append(f"RSI overbought at {rsi:.1f} for {dur} days")
            elif rsi < 30:
                dur = indicators.get('rsi_oversold_duration', 0)
                signals.append(('BUY', min(0.2 + dur * 0.05, 0.35)))
                buy_signals.append('RSI_OS')
                reasons.append(f"RSI oversold at {rsi:.1f} for {dur} days")
            
            div = indicators.get('rsi_divergence', 'NONE')
            if div == 'BULLISH_DIVERGENCE':
                signals.append(('BUY', 0.25))
                buy_signals.append('RSI_DIV')
                reasons.append("Bullish RSI divergence")
            elif div == 'BEARISH_DIVERGENCE':
                signals.append(('SELL', 0.25))
                sell_signals.append('RSI_DIV')
                reasons.append("Bearish RSI divergence")
        
        # === DIVERGENCE CONTRADICTION ===
        if 'MA_ALIGN' in buy_signals and 'RSI_DIV' in sell_signals:
            details.append("CONFLICT: MA bullish but RSI bearish divergence — confidence capped")
            signals = [(s, w * 0.7) if s == 'BUY' else (s, w) for s, w in signals]
        elif 'MA_ALIGN' in sell_signals and 'RSI_DIV' in buy_signals:
            details.append("CONFLICT: MA bearish but RSI bullish divergence — confidence capped")
            signals = [(s, w * 0.7) if s == 'SELL' else (s, w) for s, w in signals]
        
        # === MACD ===
        if macd is not None and macd_sig is not None:
            cross = indicators.get('macd_crossover_direction', 'NONE')
            cross_days = indicators.get('macd_crossover_days_ago', 999)
            if macd > macd_sig:
                if cross == 'BULLISH' and cross_days <= 5:
                    signals.append(('BUY', 0.25))
                    reasons.append(f"MACD bullish crossover ({cross_days} days ago)")
                else:
                    signals.append(('BUY', 0.15))
                buy_signals.append('MACD')
                if indicators.get('macd_histogram_trend') == 'INCREASING':
                    details.append("MACD histogram increasing")
            else:
                if cross == 'BEARISH' and cross_days <= 5:
                    signals.append(('SELL', 0.25))
                    reasons.append(f"MACD bearish crossover ({cross_days} days ago)")
                else:
                    signals.append(('SELL', 0.15))
                sell_signals.append('MACD')
                if indicators.get('macd_histogram_trend') == 'DECREASING':
                    details.append("MACD histogram decreasing")
        
        # === BOLLINGER ===
        if bb_pos is not None:
            if bb_pos > 1:
                signals.append(('SELL', 0.15))
                sell_signals.append('BB')
                reasons.append("Price above upper BB")
            elif bb_pos < 0:
                signals.append(('BUY', 0.15))
                buy_signals.append('BB')
                reasons.append("Price below lower BB")
            if bb_squeeze:
                details.append("BB squeeze detected")
        
        # === STOCHASTIC ===
        if stoch:
            if stoch > 80:
                signals.append(('SELL', 0.1))
                sell_signals.append('STOCH')
                reasons.append(f"Stochastic overbought at {stoch:.1f}")
            elif stoch < 20:
                signals.append(('BUY', 0.1))
                buy_signals.append('STOCH')
                reasons.append(f"Stochastic oversold at {stoch:.1f}")
        
        # === VOLUME ===
        if vol_ratio > 1.5:
            details.append(f"High volume ({vol_ratio:.1f}x avg)")
        elif vol_ratio < 0.5:
            details.append(f"Low volume ({vol_ratio:.1f}x avg)")
        
        # === VOLUME PROFILE ===
        if volume_profile:
            if volume_profile.get('price_vs_vwap') is not None:
                pv = volume_profile['price_vs_vwap']
                if pv > 3:
                    signals.append(('SELL', 0.1))
                    sell_signals.append('VWAP')
                    reasons.append(f"Price {pv:+.1f}% above VWAP — overextended")
                elif pv < -3:
                    signals.append(('BUY', 0.1))
                    buy_signals.append('VWAP')
                    reasons.append(f"Price {pv:+.1f}% below VWAP — below fair value")
            
            if volume_profile.get('poc'):
                details.append(f"Volume POC: ${volume_profile['poc']:.2f} | VAH: ${volume_profile.get('vah', 0):.2f} | VAL: ${volume_profile.get('val', 0):.2f}")
            
            for r in volume_profile.get('reasons', []):
                details.append(f"Volume profile: {r}")
        
        # === MARKET-RELATIVE ===
        if relative:
            if relative.get('relative_strength') == 'STRONG_OUTPERFORM':
                signals = [(s, min(w + 0.05, 0.5)) for s, w in signals]
                details.append("Relative strength: outperforming market + sector")
            elif relative.get('relative_strength') == 'WEAK_UNDERPERFORM':
                signals = [(s, w * 0.85) for s, w in signals]
                details.append("Relative weakness: underperforming — reduced confidence")
            
            corr = relative.get('correlation_60d')
            if corr is not None:
                if corr > 0.8:
                    details.append(f"High market correlation ({corr:.2f}) — follows market closely")
                elif corr < 0.3:
                    details.append(f"Low market correlation ({corr:.2f}) — stock-specific movement")
                    signals = [(s, min(w * 1.05, 0.5)) for s, w in signals]
            
            if relative.get('inverse_etf_trend') == 'SH_RISING_MARKET_FALLING':
                details.append("Inverse ETF (SH) rising — confirms market weakness")
                signals = [(s, min(w * 1.1, 0.5)) if s == 'SELL' else (s, w * 0.9) for s, w in signals]
            elif relative.get('inverse_etf_trend') == 'SH_FALLING_MARKET_RISING':
                details.append("Inverse ETF (SH) falling — confirms market strength")
                signals = [(s, min(w * 1.1, 0.5)) if s == 'BUY' else (s, w * 0.9) for s, w in signals]
            
            for r in relative.get('reasons', []):
                if r not in reasons:
                    reasons.append(r)
        
        # === COMPUTE RAW SIGNAL ===
        if not signals:
            return {
                'signal': 'HOLD', 'confidence': 0.5, 'strength': 'NEUTRAL',
                'reasons': ['No clear signals'], 'details': details,
                'buy_score': 0, 'sell_score': 0,
                'indicators': indicators,
                'macro_regime': macro.get('regime', 'UNKNOWN') if macro else 'UNKNOWN',
                'confidence_multiplier': macro.get('confidence_multiplier', 1.0) if macro else 1.0,
            }
        
        buy_w = sum(c for s, c in signals if s == 'BUY')
        sell_w = sum(c for s, c in signals if s == 'SELL')
        total = buy_w + sell_w
        
        if buy_w > sell_w * 1.3:
            sig, conf = 'BUY', min(buy_w / total, 0.95)
        elif sell_w > buy_w * 1.3:
            sig, conf = 'SELL', min(sell_w / total, 0.95)
        else:
            sig, conf = 'HOLD', 0.5
        
        # === APPLY MACRO MULTIPLIER ===
        if macro:
            multiplier = macro.get('confidence_multiplier', 1.0)
            conf = min(conf * multiplier, 0.95)
            if multiplier < 0.85:
                details.append(f"Macro dampening: {macro.get('regime', 'UNKNOWN')} (x{multiplier:.2f})")
            elif multiplier > 1.0:
                details.append(f"Macro boosting: {macro.get('regime', 'UNKNOWN')} (x{multiplier:.2f})")
        
        strength = 'STRONG' if conf >= 0.8 else 'MODERATE' if conf >= 0.6 else 'WEAK' if conf >= 0.4 else 'NEUTRAL'
        
        return {
            'signal': sig, 'confidence': conf, 'strength': strength,
            'reasons': reasons, 'details': details,
            'buy_score': buy_w, 'sell_score': sell_w,
            'indicators': indicators,
            'macro_regime': macro.get('regime', 'UNKNOWN') if macro else 'UNKNOWN',
            'confidence_multiplier': macro.get('confidence_multiplier', 1.0) if macro else 1.0,
        }


# ============================================================================
# MAIN INVESTMENT MONITOR
# ============================================================================

class InvestmentMonitor:
    def __init__(self):
        self.setup_logging()
        self.portfolio = {}
        self.resolver = SymbolResolver()
        self.market_data = {}
        self.fundamental_data = {}
        self.sector_data = {}
        self.news_data = {}
        self.backtest_data = {}
        self.symbol_map = {}  # original -> resolved
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/root/.hermes/logs/investment-monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('InvestmentMonitor')
    
    def resolve_symbols(self, symbols: List[str]) -> Dict[str, str]:
        """Resolve all symbols for TSX/NYSE disambiguation."""
        self.symbol_map = self.resolver.resolve_portfolio(symbols)
        for orig, resolved in self.symbol_map.items():
            if orig != resolved:
                self.logger.info(f"Symbol resolved: {orig} -> {resolved}")
        return self.symbol_map
    
    def fetch_all_data(self, tickers: List[str]):
        """Fetch all data for the portfolio."""
        # Resolve symbols first
        self.resolve_symbols(tickers)
        resolved_tickers = [self.symbol_map.get(t, t) for t in tickers]
        
        # Market data
        self.logger.info("Fetching market data...")
        for orig, resolved in self.symbol_map.items():
            try:
                hist = yf.Ticker(resolved).history(period="18mo")
                if not hist.empty:
                    self.market_data[orig] = {
                        'resolved': resolved,
                        'hist': hist,
                        'current_price': hist['Close'].iloc[-1],
                        'currency': yf.Ticker(resolved).info.get('currency', 'USD'),
                        'indicators': TechnicalAnalyzer.calculate(hist)
                    }
            except Exception as e:
                self.logger.error(f"Error fetching {resolved}: {e}")
        
        # Fundamentals
        self.logger.info("Fetching fundamentals...")
        for orig, resolved in self.symbol_map.items():
            self.fundamental_data[orig] = FundamentalAnalyzer.fetch(resolved)
        
        # News & Events
        self.logger.info("Fetching news and events...")
        for orig, resolved in self.symbol_map.items():
            self.news_data[orig] = NewsAnalyzer.fetch(resolved)
        
        # Sector comparison
        self.logger.info("Fetching sector data...")
        for orig in tickers:
            if orig in self.market_data and orig in self.fundamental_data:
                try:
                    self.sector_data[orig] = SectorComparator.compare(
                        self.symbol_map.get(orig, orig),
                        self.fundamental_data[orig],
                        self.market_data[orig]['indicators']
                    )
                except Exception as e:
                    self.logger.warning(f"Sector data failed for {orig}: {e}")
        
        # === NEW: Macro Regime, Market-Relative, Volume Profile ===
        self.logger.info("Computing macro regime and market-relative indicators...")
        
        vix_value = None
        try:
            vix_hist = yf.Ticker('^VIX').history(period='5d')
            if not vix_hist.empty:
                vix_value = vix_hist['Close'].iloc[-1]
                self.logger.info(f"VIX: {vix_value:.2f}")
        except Exception:
            pass
        
        market_hist = None
        try:
            market_hist = yf.Ticker('SPY').history(period='18mo')
        except Exception:
            pass
        
        self.macro_regime = {}
        self.market_relative = {}
        self.volume_profile = {}
        mri = MarketRelativeIndicators()
        
        for orig in tickers:
            if orig not in self.market_data:
                continue
            hist = self.market_data[orig]['hist']
            resolved = self.symbol_map.get(orig, orig)
            
            # Macro regime (per-ticker + market)
            try:
                self.macro_regime[orig] = MacroRegimeFilter.analyze(
                    hist, vix_value=vix_value, market_hist=market_hist
                )
            except Exception as e:
                self.logger.warning(f"Macro regime failed for {orig}: {e}")
                self.macro_regime[orig] = {'regime': 'UNKNOWN', 'confidence_multiplier': 1.0}
            
            # Market-relative indicators
            sector_etf = None
            if orig in self.sector_data:
                sector_etf = self.sector_data[orig].get('etf_symbol')
            try:
                self.market_relative[orig] = mri.analyze(
                    orig, hist, sector_etf=sector_etf, resolved_ticker=resolved
                )
            except Exception as e:
                self.logger.warning(f"Market-relative failed for {orig}: {e}")
            
            # Volume profile
            try:
                self.volume_profile[orig] = VolumeProfileAnalyzer.analyze(hist)
            except Exception as e:
                self.logger.warning(f"Volume profile failed for {orig}: {e}")


    def run_backtests(self, tickers: List[str]):
        """Run backtesting for all holdings."""
        self.logger.info("Running backtests...")
        bt = BacktestEngine()
        
        for orig in tickers:
            if orig not in self.market_data:
                continue
            
            resolved = self.symbol_map.get(orig, orig)
            sector_etf = None
            if orig in self.sector_data:
                sector_etf = self.sector_data[orig].get('etf_symbol')
            
            try:
                self.backtest_data[orig] = bt.run(resolved, sector_etf)
            except Exception as e:
                self.logger.warning(f"Backtest failed for {orig}: {e}")
    
    def generate_report(self) -> Dict:
        """Generate comprehensive report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_summary': self._portfolio_summary(),
            'holdings': {},
            'news_summary': {},
            'backtest_summary': {},
            'action_items': [],
            'market_overview': self._market_overview(),
        }
        
        for ticker in self.portfolio:
            if ticker not in self.market_data:
                continue
            
            indicators = self.market_data[ticker]['indicators']
            macro = self.macro_regime.get(ticker)
            relative = self.market_relative.get(ticker)
            vol_profile = self.volume_profile.get(ticker)
            
            # NEW: calibrated signal with all context
            signal = SignalGenerator.generate(
                indicators, macro=macro, relative=relative, volume_profile=vol_profile
            )
            
            fund = FundamentalAnalyzer.analyze(self.fundamental_data.get(ticker, {}))
            
            pos = self.portfolio[ticker]
            price = self.market_data[ticker]['current_price']
            mv = pos['shares'] * price
            cb = pos['shares'] * pos['cost_basis']
            pnl = mv - cb
            pnl_pct = (pnl / cb * 100) if cb > 0 else 0
            
            report['holdings'][ticker] = {
                'position': {'shares': pos['shares'], 'cost_basis': pos['cost_basis'],
                             'current_price': price, 'market_value': mv, 'pnl': pnl, 'pnl_pct': pnl_pct},
                'signal': signal,
                'fundamentals': fund,
                'sector': self.sector_data.get(ticker, {}),
                'news': self.news_data.get(ticker, {}),
                'backtest': self.backtest_data.get(ticker, {}),
                'macro_regime': macro,
                'market_relative': relative,
                'volume_profile': vol_profile,
            }
            
            if signal['signal'] in ['BUY', 'SELL'] and signal['confidence'] > 0.6:
                report['action_items'].append({
                    'ticker': ticker, 'action': signal['signal'],
                    'confidence': signal['confidence'], 'strength': signal.get('strength', ''),
                    'reasons': signal['reasons'], 'details': signal.get('details', []),
                    'priority': 'HIGH' if signal['confidence'] > 0.8 else 'MEDIUM',
                    'macro_regime': signal.get('macro_regime', 'UNKNOWN'),
                })
        
        report['action_items'].sort(key=lambda x: (x['priority'] == 'HIGH', x['confidence']), reverse=True)
        return report

    def _portfolio_summary(self) -> Dict:
        total_mv = sum(h['shares'] * self.market_data.get(t, {}).get('current_price', 0) for t, h in self.portfolio.items() if t in self.market_data)
        total_cb = sum(h['shares'] * h['cost_basis'] for h in self.portfolio.values())
        return {'total_market_value': total_mv, 'total_cost_basis': total_cb, 'total_pnl': total_mv - total_cb, 'position_count': len(self.portfolio)}
    
    def _market_overview(self) -> Dict:
        overview = {}
        for sym, name in [('^GSPC', 'S&P 500'), ('^DJI', 'Dow Jones'), ('^IXIC', 'NASDAQ'), ('^GSPTSE', 'TSX'), ('^VIX', 'VIX')]:
            try:
                h = yf.Ticker(sym).history(period="5d")
                if not h.empty:
                    overview[name] = {'price': h['Close'].iloc[-1], 'change_pct': ((h['Close'].iloc[-1] / h['Close'].iloc[-2]) - 1) * 100}
            except:
                pass
        return overview
    
    def format_report(self, report: Dict) -> str:
        """Format report as text."""
        L = []
        L.append("=" * 72)
        L.append("COMPREHENSIVE INVESTMENT PORTFOLIO ANALYSIS REPORT")
        L.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        L.append("=" * 72)
        L.append("")
        
        # Summary
        s = report['portfolio_summary']
        L.append("PORTFOLIO SUMMARY")
        L.append("-" * 72)
        L.append(f"Positions: {s['position_count']} | Value: ${s['total_market_value']:,.2f} | P&L: ${s['total_pnl']:,.2f}")
        L.append("")
        
        # Market
        L.append("MARKET OVERVIEW")
        L.append("-" * 72)
        for n, d in report['market_overview'].items():
            L.append(f"  {n:<18} {d['price']:>10,.2f} ({d['change_pct']:+.2f}%)")
        L.append("")
        
        # Holdings
        L.append("=" * 72)
        L.append("DETAILED HOLDINGS ANALYSIS")
        L.append("=" * 72)
        
        for ticker in sorted(report['holdings'].keys()):
            h = report['holdings'][ticker]
            sig = h['signal']
            ind = sig.get('indicators', {})
            pos = h['position']
            fund = h['fundamentals']
            sec = h['sector']
            news = h['news']
            bt = h['backtest']
            
            name = self.fundamental_data.get(ticker, {}).get('company_name', ticker)
            resolved = self.symbol_map.get(ticker, ticker)
            
            L.append("")
            L.append(f"{'─' * 72}")
            L.append(f"  {ticker}" + (f" ({resolved})" if resolved != ticker else "") + f" - {name}")
            L.append(f"{'─' * 72}")
            L.append(f"  Shares: {pos['shares']:,.0f} | Price: ${pos['current_price']:,.2f} | Value: ${pos['market_value']:,.2f} | P&L: ${pos['pnl']:,.2f} ({pos['pnl_pct']:+.1f}%)")
            L.append("")
            L.append(f"  SIGNAL: {sig['signal']} | Confidence: {sig['confidence']:.0%} | Strength: {sig.get('strength', '')}")
            macro_regime = sig.get('macro_regime', 'UNKNOWN')
            conf_mult = sig.get('confidence_multiplier', 1.0)
            if macro_regime != 'UNKNOWN':
                L.append(f"  Macro Regime: {macro_regime} | Confidence Multiplier: x{conf_mult:.2f}")
            L.append(f"  Buy: {sig.get('buy_score', 0):.2f} | Sell: {sig.get('sell_score', 0):.2f}")
            L.append("")
            
            L.append("  TECHNICAL:")
            for r in sig.get('reasons', []):
                L.append(f"    • {r}")
            for d in sig.get('details', []):
                L.append(f"    ℹ {d}")
            L.append(f"    RSI: {ind.get('rsi', 0):.1f} | MACD: {ind.get('macd', 0):.3f} | SMA20: ${ind.get('sma_20', 0) or 0:.2f}")
            L.append(f"    Perf: 1D {ind.get('price_change_1d', 0):+.1f}% | 1M {ind.get('price_change_1m', 0):+.1f}% | 3M {ind.get('price_change_3m', 0):+.1f}% | 6M {ind.get('price_change_6m', 0):+.1f}%")
            L.append("")
            
            L.append("  FUNDAMENTALS:")
            L.append(f"    Quality: {fund.get('quality_score', 0):.0f}/100 ({fund.get('rating', 'N/A')})")
            for s in fund.get('strengths', [])[:4]:
                L.append(f"    ✓ {s}")
            for c in fund.get('concerns', [])[:3]:
                L.append(f"    ⚠ {c}")
            f_data = self.fundamental_data.get(ticker, {})
            if f_data.get('pe_trailing'):
                L.append(f"    P/E: {f_data['pe_trailing']:.1f} (fwd {f_data.get('pe_forward', 'N/A')}) | P/B: {f_data.get('price_to_book', 'N/A')} | EPS: ${f_data.get('eps_trailing', 'N/A')}")
            if f_data.get('dividend_yield'):
                L.append(f"    Div: {f_data['dividend_yield']:.2f}% | Rate: ${f_data.get('dividend_rate', 'N/A')} | Payout: {f_data.get('payout_ratio', 'N/A')}")
            if f_data.get('free_cash_flow'):
                L.append(f"    FCF: ${f_data['free_cash_flow']:,.0f} | FCF Yield: {f_data.get('fcf_yield', 'N/A')}")
            if f_data.get('roe'):
                L.append(f"    ROE: {f_data['roe']:.1%} | Margin: {f_data.get('profit_margin', 'N/A')} | D/E: {f_data.get('debt_to_equity', 'N/A')}")
            if f_data.get('analyst_target'):
                L.append(f"    Analyst: ${f_data['analyst_target']:.2f} target ({f_data.get('num_analysts', 0)} analysts, {f_data.get('analyst_recommendation', 'N/A')})")
            L.append("")
            
            # News
            if news.get('recent_news') or news.get('upcoming_events') or news.get('earnings'):
                L.append("  NEWS & EVENTS:")
                e = news.get('earnings', {})
                if e.get('next_date'):
                    L.append(f"    📅 Next Earnings: {e['next_date']} ({e.get('days_until', '?')} days) | Est EPS: {e.get('eps_estimate', 'N/A')}")
                if e.get('last_date'):
                    L.append(f"    Last Earnings: {e['last_date']} | Reported: ${e.get('last_reported_eps', 'N/A')} | Surprise: {e.get('last_surprise', 'N/A')}%")
                if news.get('dividends', {}).get('next_date'):
                    L.append(f"    💰 Dividend: {news['dividends']['next_date']} | Rate: ${news['dividends'].get('rate', 'N/A')} | Yield: {news['dividends'].get('yield', 'N/A')}%")
                for evt in news.get('upcoming_events', [])[:3]:
                    L.append(f"    📌 {evt['event']}: {evt['date']}")
                for article in news.get('recent_news', [])[:3]:
                    days = article.get('days_ago', '?')
                    L.append(f"    📰 [{days}d ago] {article['title'][:80]} ({article.get('provider', '')})")
                    if article.get('url'):
                        L.append(f"       {article['url']}")
                L.append("")
            
            # Sector
            if sec.get('peers') or sec.get('sector_perf_1m') is not None:
                L.append("  SECTOR COMPARISON:")
                L.append(f"    Sector: {sec.get('sector', 'N/A')} | ETF: {sec.get('etf_symbol', 'N/A')}")
                if sec.get('sector_perf_1m') is not None:
                    L.append(f"    Sector Perf: 1M {sec['sector_perf_1m']:+.1f}% | 3M {sec.get('sector_perf_3m', 0) or 0:+.1f}% | 6M {sec.get('sector_perf_6m', 0) or 0:+.1f}%")
                for period in ['1m', '3m', '6m']:
                    vs = sec.get(f'vs_sector_{period}')
                    if vs:
                        L.append(f"    vs Sector {period}: Stock {vs['stock']:+.1f}% vs Sector {vs['sector']:+.1f}% ({vs['outperformance']:+.1f}%)")
                for period in ['1m', '3m', '6m']:
                    best = sec.get(f'best_{period}')
                    if best:
                        L.append(f"    Best {period}: {best['symbol']} ({best['name']}) +{best['perf']:.1f}%")
                if sec.get('peer_avg_pe'):
                    L.append(f"    Peer Avg P/E: {sec['peer_avg_pe']:.1f} | Stock P/E: {f_data.get('pe_trailing', 'N/A')} | Percentile: {sec.get('peer_pctile_pe', 'N/A')}")
                L.append("")
            
            # === NEW: Macro Regime ===
            macro = h.get('macro_regime')
            if macro:
                L.append("  MACRO REGIME:")
                L.append(f"    Regime: {macro.get('regime', 'UNKNOWN')} | VIX: {macro.get('vix_regime', 'N/A')} | Market: {macro.get('market_direction', 'N/A')}")
                L.append(f"    SMA200 Slope: {macro.get('sma20_slope', 'N/A')} | Confidence Multiplier: x{macro.get('confidence_multiplier', 1.0):.2f}")
                for b in macro.get('boosters', [])[:2]:
                    L.append(f"    ✓ {b}")
                for w in macro.get('warnings', [])[:2]:
                    L.append(f"    ⚠ {w}")
                L.append("")
            
            # === NEW: Market-Relative ===
            rel = h.get('market_relative')
            if rel:
                L.append("  MARKET-RELATIVE:")
                vs_mkt = rel.get('vs_market_1m')
                vs_sec = rel.get('vs_sector_1m')
                if vs_mkt is not None:
                    L.append(f"    vs S&P 500 (1M): {vs_mkt:+.1f}% | vs Sector (1M): {vs_sec:+.1f}%" if vs_sec is not None else f"    vs S&P 500 (1M): {vs_mkt:+.1f}%")
                L.append(f"    Relative Strength: {rel.get('relative_strength', 'N/A')} | Alignment: {rel.get('alignment', 'N/A')}")
                corr = rel.get('correlation_60d')
                if corr is not None:
                    L.append(f"    60d Correlation: {corr:.2f}")
                if rel.get('inverse_etf_trend') and rel['inverse_etf_trend'] != 'NEUTRAL':
                    L.append(f"    Inverse ETF: {rel['inverse_etf_trend']}")
                for r in rel.get('reasons', [])[:2]:
                    L.append(f"    • {r}")
                L.append("")
            
            # === NEW: Volume Profile ===
            vp = h.get('volume_profile')
            if vp:
                L.append("  VOLUME PROFILE (60d):")
                if vp.get('poc'):
                    L.append(f"    POC: ${vp['poc']:.2f} | VAH: ${vp.get('vah', 0):.2f} | VAL: ${vp.get('val', 0):.2f}")
                if vp.get('vwap'):
                    L.append(f"    VWAP: ${vp['vwap']:.2f} | Price vs VWAP: {vp.get('price_vs_vwap', 0):+.1f}%")
                if vp.get('nearest_support'):
                    L.append(f"    Support: ${vp['nearest_support']:.2f}")
                if vp.get('nearest_resistance'):
                    L.append(f"    Resistance: ${vp['nearest_resistance']:.2f}")
                for d in vp.get('details', [])[:2]:
                    L.append(f"    ℹ {d}")
                L.append("")

            # Backtest
            if bt.get('accuracy'):
                L.append("  BACKTEST (Historical Signal Accuracy):")
                L.append(f"    ┌─ Methodology ─────────────────────────────────────────────")
                L.append(f"    │  For each historical date, we calculate what the technical")
                L.append(f"    │  indicators would have shown, generate a BUY/SELL/HOLD")
                L.append(f"    │  signal, then check the actual 1-month forward return.")
                L.append(f"    │  WIN = signal direction matched price movement")
                L.append(f"    │  LOSS = signal direction was opposite to price movement")
                L.append(f"    │  HOLD = no directional signal was generated")
                L.append(f"    └────────────────────────────────────────────────────────")
                a = bt['accuracy']
                L.append(f"")
                L.append(f"    Overall Win Rate: {a['win_rate']:.0f}% ({a['wins']}W / {a['losses']}L / {a['holds']}H)")
                L.append(f"    Outcome Sequence (oldest → newest): {' → '.join(bt.get('outcome_sequence', []))}")
                if bt.get('vs_market'):
                    L.append(f"    vs S&P 500: {bt['vs_market']['beat_rate']:.0f}% beat rate ({bt['vs_market']['wins']}W / {bt['vs_market']['losses']}L)")
                if bt.get('vs_sector'):
                    L.append(f"    vs Sector:   {bt['vs_sector']['beat_rate']:.0f}% beat rate ({bt['vs_sector']['wins']}W / {bt['vs_sector']['losses']}L)")
                L.append(f"")
                L.append(f"    {'Date':<12} {'Signal':<8} {'Conf':<6} {'Price':>10} {'1M Later':>10} {'Return':>8} {'Outcome':<10} {'Explanation'}")
                L.append(f"    {'─' * 12} {'─' * 8} {'─' * 6} {'─' * 10} {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 40}")
                for p in bt.get('periods', []):
                    price_str = f"${p['price_at_signal']:,.2f}" if p.get('price_at_signal') else "N/A"
                    future_str = f"${p['price_1m_future']:,.2f}" if p.get('price_1m_future') else "N/A"
                    L.append(f"    {p['date']:<12} {p['signal']:<8} {p['confidence']:.0%}   {price_str:>10} {future_str:>10} {p['actual_1m_return']:>+7.1f}% {p['outcome']:<10} {p.get('outcome_explanation', '')}")
                    # Show signal reasons indented
                    for r in p.get('signal_reasons', [])[:3]:
                        L.append(f"    {'':>12} ↳ {r}")
                L.append("")
        
        # Action Items
        L.append("=" * 72)
        L.append("ACTION ITEMS")
        L.append("=" * 72)
        for item in report.get('action_items', []):
            L.append(f"\n  [{item['priority']}] {item['action']} {item['ticker']} - {item['confidence']:.0%} ({item['strength']})")
            for r in item.get('reasons', []):
                L.append(f"    • {r}")
            for d in item.get('details', []):
                L.append(f"    ℹ {d}")
        
        L.append("")
        L.append("=" * 72)
        L.append("DISCLAIMER: For informational purposes only. Not financial advice.")
        L.append("=" * 72)
        
        return "\n".join(L)


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    import json
    
    # Load portfolio
    with open('/tmp/portfolio_from_email.json', 'r') as f:
        portfolio_shares = json.load(f)
    
    portfolio = {sym: {'shares': s, 'cost_basis': 0, 'cost_basis_total': 0} for sym, s in portfolio_shares.items()}
    
    monitor = InvestmentMonitor()
    monitor.portfolio = portfolio
    tickers = list(portfolio.keys())
    
    print(f"Analyzing {len(tickers)} positions...")
    
    # Fetch all data
    monitor.fetch_all_data(tickers)
    
    # Run backtests
    monitor.run_backtests(tickers)
    
    # Generate report
    report = monitor.generate_report()
    text = monitor.format_report(report)
    print(text)
    
    with open('/tmp/full_v3_report.txt', 'w') as f:
        f.write(text)
    print(f"\nSaved to /tmp/full_v3_report.txt")

if __name__ == "__main__":
    main()