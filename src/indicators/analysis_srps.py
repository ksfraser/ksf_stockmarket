"""
Pure-logic single-responsibility analyzers extracted from the monolithic
``investment_monitor.py``.

Every class here:
  * takes its inputs as arguments (DataFrames / dicts) — NO network, NO yfinance,
  * performs exactly one analytical responsibility,
  * is trivially unit-testable and injectable.

The I/O that feeds these (yfinance fetches) lives behind the ports in
``market_data_port.py`` / ``src/common/market_data.py`` and is injected, so these
SRPs never open a connection or call the data layer directly.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from src.indicators.technical_indicators import TechnicalAnalysisService


# --------------------------------------------------------------------------- #
# SRP: fundamental quality scoring                                             #
# --------------------------------------------------------------------------- #
class FundamentalScorer:
    """Scores a fundamentals dict into quality_score / rating / strengths / concerns."""

    @staticmethod
    def analyze(f: Dict) -> Dict:
        if not f:
            return {"quality_score": 0, "rating": "N/A"}
        score, max_score = 0, 0
        strengths, concerns = [], []

        roe = f.get("roe")
        if roe is not None:
            max_score += 2
            if roe > 0.15:
                score += 2
                strengths.append(f"Strong ROE: {roe:.1%}")
            elif roe > 0.10:
                score += 1
            else:
                concerns.append(f"Low ROE: {roe:.1%}")

        roa = f.get("roa")
        if roa is not None:
            max_score += 1
            if roa > 0.05:
                score += 1
                strengths.append(f"Good ROA: {roa:.1%}")

        pm = f.get("profit_margin")
        if pm is not None:
            max_score += 1
            if pm > 0.15:
                score += 1
                strengths.append(f"Healthy profit margin: {pm:.1%}")
            elif pm < 0:
                concerns.append(f"Negative profit margin: {pm:.1%}")

        pe = f.get("pe_forward")
        if pe is not None:
            max_score += 1
            if 0 < pe < 15:
                score += 1
                strengths.append(f"Attractive forward P/E: {pe:.1f}")
            elif pe > 30:
                concerns.append(f"High forward P/E: {pe:.1f}")

        pb = f.get("price_to_book")
        if pb is not None:
            max_score += 1
            if pb < 3:
                score += 1
            elif pb > 10:
                concerns.append(f"High P/B: {pb:.1f}")

        de = f.get("debt_to_equity")
        if de is not None:
            max_score += 1
            if de < 1:
                score += 1
                strengths.append(f"Low D/E: {de:.2f}")
            elif de > 2:
                concerns.append(f"High D/E: {de:.2f}")

        cr = f.get("current_ratio")
        if cr is not None:
            max_score += 1
            if cr > 1.5:
                score += 1
            elif cr < 1:
                concerns.append(f"Low current ratio: {cr:.2f}")

        fcf = f.get("free_cash_flow")
        if fcf is not None:
            max_score += 2
            if fcf > 0:
                score += 1
                fcf_yield = f.get("fcf_yield")
                if fcf_yield and fcf_yield > 5:
                    score += 1
                    strengths.append(f"Strong FCF yield: {fcf_yield:.1f}%")
            else:
                concerns.append("Negative FCF")

        dy = f.get("dividend_yield")
        if dy is not None:
            max_score += 1
            if dy > 2:
                score += 1
                strengths.append(f"Attractive div yield: {dy:.2f}%")

        payout = f.get("payout_ratio")
        if payout is not None:
            max_score += 1
            if payout < 0.6:
                score += 1
                strengths.append(f"Sustainable payout: {payout:.1%}")
            elif payout > 0.9:
                concerns.append(f"High payout: {payout:.1%}")

        rg = f.get("revenue_growth")
        if rg is not None:
            max_score += 1
            if rg > 0.1:
                score += 1
                strengths.append(f"Strong revenue growth: {rg:.1%}")
            elif rg < 0:
                concerns.append(f"Declining revenue: {rg:.1%}")

        qs = (score / max_score * 100) if max_score > 0 else 0
        return {
            "quality_score": qs,
            "rating": "EXCELLENT" if qs >= 80 else "GOOD" if qs >= 60 else "FAIR" if qs >= 40 else "WEAK",
            "strengths": strengths,
            "concerns": concerns,
        }


# --------------------------------------------------------------------------- #
# SRP: sector comparison (pure)                                                #
# --------------------------------------------------------------------------- #
_METRIC_MAP = {
    "pe": "pe_trailing", "div_yield": "dividend_yield",
    "roe": "roe", "profit_margin": "profit_margin", "rev_growth": "revenue_growth",
}


class SectorPerformanceAnalyzer:
    """Computes sector / peer relative performance from injected sector inputs."""

    @staticmethod
    def analyze(ticker: str, fundamentals: Dict, indicators: Dict, sector_inputs: Dict) -> Dict:
        result = {"sector": fundamentals.get("sector"), "industry": fundamentals.get("industry")}
        sector = fundamentals.get("sector")
        if not sector or not sector_inputs:
            return result

        etf_hist = sector_inputs.get("etf_hist")
        if etf_hist is None or getattr(etf_hist, "empty", True):
            return result

        close = etf_hist["Close"]
        result["etf_symbol"] = sector_inputs.get("etf_symbol")
        result["etf_name"] = sector_inputs.get("etf_name")
        result["etf_pe"] = sector_inputs.get("etf_pe")
        result["sector_perf_1m"] = ((close.iloc[-1] / close.iloc[-20]) - 1) * 100 if len(close) >= 20 else None
        result["sector_perf_3m"] = ((close.iloc[-1] / close.iloc[-60]) - 1) * 100 if len(close) >= 60 else None
        result["sector_perf_6m"] = ((close.iloc[-1] / close.iloc[0]) - 1) * 100

        for period, key in [("1m", "price_change_1m"), ("3m", "price_change_3m"), ("6m", "price_change_6m")]:
            stock_val = indicators.get(key)
            sector_val = result.get(f"sector_perf_{period}")
            if stock_val is not None and sector_val is not None:
                result[f"vs_sector_{period}"] = {
                    "stock": stock_val, "sector": sector_val, "outperformance": stock_val - sector_val,
                }

        peers = []
        for p in sector_inputs.get("peers", []):
            ph = p.get("hist")
            if ph is None or getattr(ph, "empty", True):
                continue
            pc = ph["Close"]
            peers.append({
                "symbol": p["symbol"], "name": p.get("name", p["symbol"]),
                "pe": p.get("pe"), "div_yield": p.get("div_yield"),
                "roe": p.get("roe"), "profit_margin": p.get("profit_margin"),
                "rev_growth": p.get("rev_growth"),
                "perf_1m": ((pc.iloc[-1] / pc.iloc[-20]) - 1) * 100 if len(pc) >= 20 else None,
                "perf_3m": ((pc.iloc[-1] / pc.iloc[-60]) - 1) * 100 if len(pc) >= 60 else None,
                "perf_6m": ((pc.iloc[-1] / pc.iloc[0]) - 1) * 100,
            })
        result["peers"] = peers

        if peers:
            for period in ["1m", "3m", "6m"]:
                key = f"perf_{period}"
                valid = [p for p in peers if p.get(key) is not None]
                if valid:
                    best = max(valid, key=lambda x: x[key])
                    result[f"best_{period}"] = {"symbol": best["symbol"], "name": best["name"], "perf": best[key]}

            for metric in ["pe", "div_yield", "roe", "profit_margin", "rev_growth"]:
                vals = [p[metric] for p in peers if p.get(metric) is not None]
                if vals:
                    stock_val = fundamentals.get(_METRIC_MAP[metric])
                    avg = float(np.mean(vals))
                    all_vals = sorted(vals + ([stock_val] if stock_val else []))
                    pctile = (all_vals.index(stock_val) / len(all_vals) * 100) if stock_val is not None else None
                    result[f"peer_avg_{metric}"] = avg
                    result[f"peer_pctile_{metric}"] = pctile
                    if stock_val and avg:
                        result[f"vs_peer_{metric}"] = ((stock_val - avg) / abs(avg)) * 100
        return result


# --------------------------------------------------------------------------- #
# SRP: backtest engine (pure)                                                  #
# --------------------------------------------------------------------------- #
class BacktestRunner:
    """Backtests a signal function against historical price action. Pure given data."""

    LOOKBACK_PERIODS = [12, 9, 6, 3, 2, 1]

    def __init__(
        self,
        indicator_fn: Optional[Callable[[pd.DataFrame], Dict]] = None,
        signal_fn: Optional[Callable[[Dict], Dict]] = None,
    ):
        self._indicator_fn = indicator_fn or TechnicalAnalysisService().analyze
        self._signal_fn = signal_fn or (lambda ind: {
            "signal": "HOLD", "confidence": 0, "reasons": [], "details": [],
            "buy_score": 0, "sell_score": 0,
        })

    def run(self, hist: pd.DataFrame, bench_hist: Optional[pd.DataFrame] = None,
            sector_hist: Optional[pd.DataFrame] = None) -> Dict:
        result = {"ticker": getattr(hist, "name", ""), "periods": [], "accuracy": {}, "summary": {}}
        if hist is None or hist.empty or len(hist) < 250:
            return {"error": "Insufficient history"}

        wins = losses = holds = 0
        m_wins = m_losses = s_wins = s_losses = 0

        for months_back in self.LOOKBACK_PERIODS:
            target_date = hist.index[-1] - pd.DateOffset(months=months_back)
            idx = hist.index.get_indexer([target_date], method="nearest")[0]
            if idx < 60:
                continue
            hist_at_date = hist.iloc[: idx + 1]
            indicators = self._indicator_fn(hist_at_date)
            if not indicators:
                continue
            signal = self._signal_fn(indicators)

            future_idx = min(idx + 21, len(hist) - 1)
            price_at_signal = hist["Close"].iloc[idx]
            price_1m_future = hist["Close"].iloc[future_idx]
            actual_return = ((price_1m_future / price_at_signal) - 1) * 100

            outcome = self._evaluate_outcome(signal["signal"], actual_return)

            bench_return = self._rel_return(bench_hist, target_date, hist.index)
            sector_return = self._rel_return(sector_hist, target_date, hist.index)

            period_result = {
                "date": str(hist.index[idx].date()), "months_back": months_back,
                "signal": signal["signal"], "confidence": signal["confidence"],
                "signal_reasons": signal.get("reasons", []), "signal_details": signal.get("details", []),
                "buy_score": signal.get("buy_score", 0), "sell_score": signal.get("sell_score", 0),
                "price_at_signal": price_at_signal, "price_1m_future": price_1m_future,
                "actual_1m_return": actual_return, "outcome": outcome,
                "outcome_explanation": self._outcome_explanation(signal["signal"], actual_return, outcome),
                "benchmark_return": bench_return, "sector_return": sector_return,
                "vs_benchmark": (actual_return - bench_return) if bench_return is not None else None,
                "vs_sector": (actual_return - sector_return) if sector_return is not None else None,
            }
            result["periods"].append(period_result)

            if outcome == "WIN":
                wins += 1
            elif outcome == "LOSS":
                losses += 1
            else:
                holds += 1
            if bench_return is not None:
                m_wins += actual_return > bench_return
                m_losses += actual_return < bench_return
            if sector_return is not None:
                s_wins += actual_return > sector_return
                s_losses += actual_return < sector_return

        total = wins + losses
        result["accuracy"] = {
            "wins": wins, "losses": losses, "holds": holds,
            "win_rate": (wins / total * 100) if total > 0 else 0, "total_signals": total,
        }
        result["vs_market"] = {
            "wins": m_wins, "losses": m_losses,
            "beat_rate": (m_wins / (m_wins + m_losses) * 100) if (m_wins + m_losses) > 0 else 0,
        }
        result["vs_sector"] = {
            "wins": s_wins, "losses": s_losses,
            "beat_rate": (s_wins / (s_wins + s_losses) * 100) if (s_wins + s_losses) > 0 else 0,
        }
        result["outcome_sequence"] = [p["outcome"] for p in result["periods"]]
        return result

    @staticmethod
    def _rel_return(other: Optional[pd.DataFrame], target_date, idx_index) -> Optional[float]:
        if other is None or other.empty:
            return None
        oi = other.index.get_indexer([target_date], method="nearest")[0]
        if oi < 0 or oi >= len(other):
            return None
        future = min(oi + 21, len(other) - 1)
        return ((other["Close"].iloc[future] / other["Close"].iloc[oi]) - 1) * 100

    @staticmethod
    def _evaluate_outcome(signal: str, actual_return: float) -> str:
        if signal == "BUY":
            return "WIN" if actual_return > 0 else "LOSS"
        if signal == "SELL":
            return "WIN" if actual_return < 0 else "LOSS"
        return "HOLD"

    @staticmethod
    def _outcome_explanation(signal: str, actual_return: float, outcome: str) -> str:
        if signal == "BUY":
            return (f"BUY was correct — stock gained {actual_return:+.1f}% over the next month"
                    if outcome == "WIN"
                    else f"BUY was incorrect — stock lost {actual_return:+.1f}% over the next month")
        if signal == "SELL":
            return (f"SELL was correct — stock fell {actual_return:+.1f}% over the next month"
                    if outcome == "WIN"
                    else f"SELL was incorrect — stock rose {actual_return:+.1f}% over the next month")
        return f"HOLD — stock moved {actual_return:+.1f}% over the next month (no directional call)"


# --------------------------------------------------------------------------- #
# SRP: macro regime filter (pure)                                              #
# --------------------------------------------------------------------------- #
class MacroRegimeAnalyzer:
    VIX_LOW, VIX_NORMAL, VIX_HIGH, VIX_EXTREME = 15, 20, 25, 30

    @staticmethod
    def analyze(hist: pd.DataFrame, vix_value: float = None, market_hist: pd.DataFrame = None) -> Dict:
        result = {
            "regime": "NEUTRAL", "regime_score": 0.5, "confidence_multiplier": 1.0,
            "vix_regime": "UNKNOWN", "market_direction": "UNKNOWN", "sma200_slope": "FLAT",
            "warnings": [], "boosters": [],
        }
        if hist is None or hist.empty or len(hist) < 200:
            return result
        close = hist["Close"]

        sma200 = close.rolling(200).mean()
        if len(sma200) >= 21:
            cur, ago = sma200.iloc[-1], sma200.iloc[-21]
            slope_pct = ((cur - ago) / ago) * 100 if ago else 0
            if slope_pct > 2:
                result["sma200_slope"] = "RISING"
                result["regime_score"] += 0.15
                result["boosters"].append(f"SMA200 rising ({slope_pct:+.1f}% over 20d)")
            elif slope_pct < -2:
                result["sma200_slope"] = "FALLING"
                result["regime_score"] -= 0.20
                result["warnings"].append(f"SMA200 falling ({slope_pct:+.1f}% over 20d)")
            else:
                result["sma200_slope"] = "FLAT"
                result["regime_score"] -= 0.05
                result["warnings"].append("SMA200 flat — no clear trend")

        if vix_value is not None:
            if vix_value <= MacroRegimeAnalyzer.VIX_LOW:
                result["vix_regime"] = "LOW"
                result["regime_score"] += 0.05
            elif vix_value <= MacroRegimeAnalyzer.VIX_NORMAL:
                result["vix_regime"] = "NORMAL"
                result["regime_score"] += 0.10
                result["boosters"].append(f"VIX normal ({vix_value:.1f})")
            elif vix_value <= MacroRegimeAnalyzer.VIX_HIGH:
                result["vix_regime"] = "ELEVATED"
                result["regime_score"] -= 0.15
                result["warnings"].append(f"VIX elevated ({vix_value:.1f}) — reduce confidence")
            elif vix_value <= MacroRegimeAnalyzer.VIX_EXTREME:
                result["vix_regime"] = "HIGH"
                result["regime_score"] -= 0.25
                result["warnings"].append(f"VIX high ({vix_value:.1f}) — signals less reliable")
            else:
                result["vix_regime"] = "EXTREME"
                result["regime_score"] -= 0.15
                result["warnings"].append(f"VIX extreme ({vix_value:.1f}) — panic, contrarian BUY possible")

        if market_hist is not None and not market_hist.empty and len(market_hist) >= 200:
            mkt_close = market_hist["Close"]
            mkt_sma200 = mkt_close.rolling(200).mean()
            if mkt_close.iloc[-1] > mkt_sma200.iloc[-1]:
                result["market_direction"] = "ABOVE_SMA200"
                result["regime_score"] += 0.10
                result["boosters"].append("S&P 500 above SMA200 — bullish regime")
            else:
                result["market_direction"] = "BELOW_SMA200"
                result["regime_score"] -= 0.20
                result["warnings"].append("S&P 500 below SMA200 — bearish regime")

        score = max(0.0, min(1.0, result["regime_score"] + 0.5))
        result["confidence_multiplier"] = 0.6 + score * 0.5
        if result["regime_score"] > 0.25:
            result["regime"] = "BULLISH"
        elif result["regime_score"] < -0.15:
            result["regime"] = "BEARISH"
        else:
            result["regime"] = "NEUTRAL"
        return result


# --------------------------------------------------------------------------- #
# SRP: market-relative indicators (pure)                                       #
# --------------------------------------------------------------------------- #
class MarketRelativeAnalyzer:
    """Stock vs market / sector relative strength. I/O (SPY/SH/sector hist) injected."""

    @staticmethod
    def analyze(ticker: str, hist: pd.DataFrame, market_hist: pd.DataFrame = None,
                sector_etf_hist: pd.DataFrame = None, inverse_etf_hist: pd.DataFrame = None) -> Dict:
        result = {
            "vs_market_1m": None, "vs_market_3m": None, "vs_market_6m": None,
            "vs_sector_1m": None, "vs_sector_3m": None, "vs_sector_6m": None,
            "correlation_60d": None, "relative_strength": "NEUTRAL",
            "stock_direction": "NEUTRAL", "market_direction": "NEUTRAL",
            "alignment": "NEUTRAL", "inverse_etf_trend": None, "reasons": [], "details": [],
        }
        if hist is None or hist.empty or len(hist) < 60:
            return result
        close = hist["Close"]
        stock_1m = ((close.iloc[-1] / close.iloc[-20]) - 1) * 100 if len(hist) >= 20 else None
        stock_3m = ((close.iloc[-1] / close.iloc[-60]) - 1) * 100 if len(hist) >= 60 else None
        stock_6m = ((close.iloc[-1] / close.iloc[0]) - 1) * 100 if len(hist) >= 120 else None

        if stock_1m is not None:
            result["stock_direction"] = "RISING" if stock_1m > 2 else "FALLING" if stock_1m < -2 else "FLAT"

        if market_hist is not None and not market_hist.empty:
            mkt = market_hist["Close"]
            mkt_1m = ((mkt.iloc[-1] / mkt.iloc[-20]) - 1) * 100 if len(mkt) >= 20 else None
            mkt_3m = ((mkt.iloc[-1] / mkt.iloc[-60]) - 1) * 100 if len(mkt) >= 60 else None
            mkt_6m = ((mkt.iloc[-1] / mkt.iloc[0]) - 1) * 100
            if mkt_1m is not None and stock_1m is not None:
                result["vs_market_1m"] = stock_1m - mkt_1m
            if mkt_3m is not None and stock_3m is not None:
                result["vs_market_3m"] = stock_3m - mkt_3m
            if stock_6m is not None:
                result["vs_market_6m"] = stock_6m - mkt_6m
            if mkt_1m is not None:
                result["market_direction"] = "RISING" if mkt_1m > 1 else "FALLING" if mkt_1m < -1 else "FLAT"

            stock_ret = close.tail(60).pct_change().dropna()
            mkt_aligned = mkt.tail(len(stock_ret)).pct_change().dropna()
            min_len = min(len(stock_ret), len(mkt_aligned))
            if min_len >= 20:
                corr = np.corrcoef(stock_ret.tail(min_len).values, mkt_aligned.tail(min_len).values)[0, 1]
                result["correlation_60d"] = corr

            if stock_1m is not None and mkt_1m is not None:
                if (stock_1m > 1 and mkt_1m > 0.5) or (stock_1m < -1 and mkt_1m < -0.5):
                    result["alignment"] = "ALIGNED"
                    result["details"].append(f"Stock and market aligned (both {'up' if stock_1m > 0 else 'down'})")
                elif (stock_1m > 2 and mkt_1m < -0.5) or (stock_1m < -2 and mkt_1m > 0.5):
                    result["alignment"] = "DIVERGENT"
                    result["reasons"].append(f"Stock diverging from market — stock {stock_1m:+.1f}% vs S&P {mkt_1m:+.1f}% (1M)")

        if sector_etf_hist is not None and not sector_etf_hist.empty:
            sec = sector_etf_hist["Close"]
            sec_1m = ((sec.iloc[-1] / sec.iloc[-20]) - 1) * 100 if len(sec) >= 20 else None
            sec_3m = ((sec.iloc[-1] / sec.iloc[-60]) - 1) * 100 if len(sec) >= 60 else None
            sec_6m = ((sec.iloc[-1] / sec.iloc[0]) - 1) * 100
            if sec_1m is not None and stock_1m is not None:
                result["vs_sector_1m"] = stock_1m - sec_1m
            if sec_3m is not None and stock_3m is not None:
                result["vs_sector_3m"] = stock_3m - sec_3m
            if stock_6m is not None:
                result["vs_sector_6m"] = stock_6m - sec_6m

        vs_mkt = result.get("vs_market_1m")
        vs_sec = result.get("vs_sector_1m")
        if vs_mkt is not None and vs_sec is not None:
            if vs_mkt > 2 and vs_sec > 1:
                result["relative_strength"] = "STRONG_OUTPERFORM"
                result["reasons"].append(f"Outperforming: +{vs_mkt:.1f}% vs S&P, +{vs_sec:.1f}% vs sector (1M)")
            elif vs_mkt < -2 and vs_sec < -1:
                result["relative_strength"] = "WEAK_UNDERPERFORM"
                result["reasons"].append(f"Underperforming: {vs_mkt:.1f}% vs S&P, {vs_sec:.1f}% vs sector (1M)")
            else:
                result["relative_strength"] = "IN_LINE"

        if inverse_etf_hist is not None and not inverse_etf_hist.empty and len(inverse_etf_hist) >= 20:
            sh = inverse_etf_hist["Close"]
            sh_1m = ((sh.iloc[-1] / sh.iloc[-20]) - 1) * 100
            if sh_1m > 3:
                result["inverse_etf_trend"] = "SH_RISING_MARKET_FALLING"
                result["reasons"].append(f"SH (inverse S&P) up +{sh_1m:.1f}% — confirms market weakness")
            elif sh_1m < -3:
                result["inverse_etf_trend"] = "SH_FALLING_MARKET_RISING"
                result["details"].append(f"SH (inverse S&P) down {sh_1m:.1f}% — confirms market strength")
            else:
                result["inverse_etf_trend"] = "NEUTRAL"
        return result


# --------------------------------------------------------------------------- #
# SRP: volume profile / VWAP levels (pure)                                     #
# --------------------------------------------------------------------------- #
class VolumeProfileAnalyzer:
    @staticmethod
    def analyze(hist: pd.DataFrame, lookback: int = 60) -> Dict:
        result = {
            "poc": None, "vah": None, "val": None, "vwap": None, "vwap_current": None,
            "nearest_support": None, "nearest_resistance": None,
            "price_vs_vwap": None, "levels": [], "reasons": [], "details": [],
        }
        if hist is None or hist.empty or len(hist) < 20:
            return result
        h = hist.tail(lookback).copy()
        typical_price = (h["High"] + h["Low"] + h["Close"]) / 3
        cum_vol = h["Volume"].cumsum()
        cum_tp_vol = (typical_price * h["Volume"]).cumsum()
        vwap_series = cum_tp_vol / cum_vol
        result["vwap"] = vwap_series.iloc[-1]
        result["vwap_current"] = result["vwap"]

        current_price = h["Close"].iloc[-1]
        result["price_vs_vwap"] = ((current_price / result["vwap"]) - 1) * 100 if result["vwap"] > 0 else 0
        if result["price_vs_vwap"] > 2:
            result["details"].append(f"Price {result['price_vs_vwap']:+.1f}% above VWAP — overextended")
        elif result["price_vs_vwap"] < -2:
            result["details"].append(f"Price {result['price_vs_vwap']:+.1f}% below VWAP — below fair value")
        else:
            result["details"].append(f"Price near VWAP ({result['price_vs_vwap']:+.1f}%) — fair value")

        n_bins = 20
        price_min, price_max = h["Low"].min(), h["High"].max()
        if price_max <= price_min:
            return result
        bin_width = (price_max - price_min) / n_bins
        bins = [price_min + i * bin_width for i in range(n_bins + 1)]

        volume_by_price = {i: 0.0 for i in range(n_bins)}
        for i in range(len(h)):
            row = h.iloc[i]
            low, high, vol = row["Low"], row["High"], row["Volume"]
            price_range = high - low if high > low else 1
            for j in range(n_bins):
                if bins[j] <= high and bins[j + 1] >= low:
                    overlap = min(high, bins[j + 1]) - max(low, bins[j])
                    volume_by_price[j] += vol * (overlap / price_range) if price_range else 0
        if volume_by_price:
            poc_bin = max(volume_by_price, key=lambda k: volume_by_price[k])
            result["poc"] = (bins[poc_bin] + bins[poc_bin + 1]) / 2
            total_vol = sum(volume_by_price.values())
            cum = 0.0
            for j in range(n_bins):
                cum += volume_by_price[j]
                if cum >= 0.15 * total_vol:
                    result["val"] = (bins[j] + bins[j + 1]) / 2
                    break
            cum = 0.0
            for j in range(n_bins - 1, -1, -1):
                cum += volume_by_price[j]
                if cum >= 0.15 * total_vol:
                    result["vah"] = (bins[j] + bins[j + 1]) / 2
                    break
            if result["poc"] is not None:
                result["nearest_support"] = result["val"]
                result["nearest_resistance"] = result["vah"]
        return result


# --------------------------------------------------------------------------- #
# SRP: news normalization (pure)                                               #
# --------------------------------------------------------------------------- #
def parse_news_date(pub_date) -> int:
    """Return days_ago for a yfinance news pubDate string/object, else 0."""
    if not pub_date:
        return 0
    try:
        if isinstance(pub_date, str):
            pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            return (datetime.now(pub_dt.tzinfo) - pub_dt).days
        return 0
    except Exception:
        return 0


class NewsProcessor:
    """Normalizes a raw yfinance ``.news`` list into a clean, testable structure."""

    @staticmethod
    def normalize(news_list: List[Dict]) -> List[Dict]:
        items = []
        for article in (news_list or [])[:10]:
            content = article.get("content", article)
            title = content.get("title", article.get("title", ""))
            pub_date = content.get("pubDate", article.get("pubDate", ""))
            provider = content.get("provider", {}).get("displayName", article.get("publisher", ""))
            url = content.get("canonicalUrl", {}).get("url", article.get("link", ""))
            summary = content.get("summary", article.get("summary", ""))
            items.append({
                "title": title, "provider": provider, "url": url,
                "summary": summary[:200] if summary else "", "days_ago": parse_news_date(pub_date),
            })
        return items
