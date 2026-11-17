"""
Single-responsibility technical-indicator calculators.

Each class owns exactly ONE indicator family and is a thin wrapper around
``talib`` (TA-Lib) plus a few metrics TA-Lib does not provide (price change,
realized volatility, support/resistance, trend durations). Every calculator
accepts a ``pandas.DataFrame`` of OHLCV history (no I/O, no yfinance) and
returns a plain dict.

The OUTPUT KEYS of ``TechnicalAnalysisService.analyze`` are kept byte-for-byte
identical to the legacy ``TechnicalAnalyzer.calculate`` in
``investment_monitor.py`` (40 keys). This is deliberate: when the monster is
rewired onto this service, downstream consumers that read those dict keys must
not break. The *values* shift because TA-Lib (Wilder RSI, EMA-based MACD, …)
differs from the monster's hand-rolled pandas — that is the intended upgrade.

``TechnicalAnalysisService`` composes the calculators. The list is injectable
(Dependency Injection) — tests can swap in a fake.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, runtime_checkable

import numpy as np
import pandas as pd
import talib


# --------------------------------------------------------------------------- #
# Shared DRY helpers                                                           #
# --------------------------------------------------------------------------- #
def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def _last(series: pd.Series) -> Optional[float]:
    if series is None or len(series) == 0:
        return None
    s = series.dropna()
    return float(s.iloc[-1]) if len(s) else None


def _trend_duration(series: pd.Series, direction: str) -> int:
    s = series.dropna()
    if len(s) < 2:
        return 0
    if direction == "up":
        return int((s.diff().dropna() > 0)[::-1].cumprod().sum())
    return int((s.diff().dropna() < 0)[::-1].cumprod().sum())


def _consecutive(series: pd.Series, predicate) -> int:
    count = 0
    for v in [predicate(x) for x in series.dropna().tolist()[::-1]]:
        if v:
            count += 1
        else:
            break
    return count


def _pct_change(series: pd.Series, bars: int) -> Optional[float]:
    if series is None or len(series) <= bars:
        return None
    past, curr = series.iloc[-(bars + 1)], series.iloc[-1]
    if past in (0, None) or pd.isna(past):
        return None
    return float((curr / past - 1) * 100)


def _divergence(price: pd.Series, osc: pd.Series, window: int = 20) -> str:
    if price is None or osc is None or len(price) < window * 2:
        return "NONE"
    p1, p0 = price.iloc[-window], price.iloc[-1]
    o1, o0 = osc.iloc[-window], osc.iloc[-1]
    if p0 > p1 and o0 < o1:
        return "BEARISH_DIVERGENCE"
    if p0 < p1 and o0 > o1:
        return "BULLISH_DIVERGENCE"
    return "NONE"


def _crossover_days_ago(a: pd.Series, b: pd.Series) -> int:
    diff = (a - b).dropna()
    if len(diff) < 2:
        return 0
    sign = np.sign(diff)
    # find last index where sign changed
    for i in range(len(sign) - 1, 0, -1):
        if sign.iloc[i] != sign.iloc[i - 1] and sign.iloc[i - 1] != 0:
            return int(len(sign) - i - 1)
    return 0


# --------------------------------------------------------------------------- #
# Calculator interface                                                         #
# --------------------------------------------------------------------------- #
@runtime_checkable
class Calculator(Protocol):
    name: str

    def calculate(self, df: pd.DataFrame) -> Dict: ...


def _require(df: pd.DataFrame, min_rows: int = 2) -> Optional[pd.DataFrame]:
    if df is None or df.empty or len(df) < min_rows:
        return None
    return df


# --------------------------------------------------------------------------- #
# SRP: moving averages                                                         #
# --------------------------------------------------------------------------- #
class MovingAverages:
    name = "moving_averages"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 2) is None:
            return {}
        close = df["Close"]
        price = float(close.iloc[-1])
        out: Dict = {}
        for w in (20, 50, 200):
            if len(close) >= w:
                out[f"sma_{w}"] = _last(_sma(close, w))
        if len(close) >= 12:
            out["ema_12"] = _last(talib.EMA(close, timeperiod=12))
        if len(close) >= 26:
            out["ema_26"] = _last(talib.EMA(close, timeperiod=26))

        if "sma_20" in out and out["sma_20"]:
            sma20 = out["sma_20"]
            above = close > sma20
            out["trend_sma20_direction"] = "above" if above.iloc[-1] else "below"
            out["trend_sma20_duration"] = _consecutive(above, lambda v: v)
        if "sma_50" in out and out["sma_50"]:
            sma50 = out["sma_50"]
            above = close > sma50
            out["trend_sma50_direction"] = "above" if above.iloc[-1] else "below"
            out["trend_sma50_duration"] = _consecutive(above, lambda v: v)

        if "sma_20" in out and "sma_50" in out and "sma_200" in out:
            a, b, c = out["sma_20"], out["sma_50"], out["sma_200"]
            if a and b and c:
                if a > b > c:
                    align = "BULLISH"
                elif a < b < c:
                    align = "BEARISH"
                else:
                    align = "NEUTRAL"
                out["ma_alignment"] = align
                aligned = (a > b > c) | (a < b < c)
                out["ma_alignment_duration"] = _consecutive(pd.Series([aligned] * len(close)), lambda v: v)
        return out


# --------------------------------------------------------------------------- #
# SRP: RSI                                                                     #
# --------------------------------------------------------------------------- #
class RSIIndicator:
    name = "rsi"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 15) is None:
            return {}
        close = df["Close"]
        rsi = talib.RSI(close, timeperiod=14)
        out = {"rsi": _last(rsi), "rsi_divergence": _divergence(close, rsi, window=20)}
        return out


# --------------------------------------------------------------------------- #
# SRP: MACD                                                                    #
# --------------------------------------------------------------------------- #
class MACDIndicator:
    name = "macd"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 35) is None:
            return {}
        close = df["Close"]
        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        out = {
            "macd": _last(macd),
            "macd_signal": _last(signal),
            "macd_histogram": _last(hist),
        }
        if len(hist.dropna()) >= 2:
            out["macd_histogram_trend"] = "INCREASING" if hist.dropna().iloc[-1] > hist.dropna().iloc[-2] else "DECREASING"
        else:
            out["macd_histogram_trend"] = "FLAT"
        m, s = _last(macd), _last(signal)
        out["macd_crossover_direction"] = "BULLISH" if (m or 0) > (s or 0) else "BEARISH" if (m or 0) < (s or 0) else "NONE"
        out["macd_crossover_days_ago"] = _crossover_days_ago(macd.dropna(), signal.dropna())
        return out


# --------------------------------------------------------------------------- #
# SRP: Bollinger Bands                                                         #
# --------------------------------------------------------------------------- #
class BollingerBands:
    name = "bollinger"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 20) is None:
            return {}
        close = df["Close"]
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        price = float(close.iloc[-1])
        u, m, l = _last(upper), _last(middle), _last(lower)
        out = {"bb_upper": u, "bb_middle": m, "bb_lower": l}
        if u and l and u > l:
            out["bb_position"] = float((price - l) / (u - l))
            width = (u - l) / m if m else None
            out["bb_squeeze"] = bool(width is not None and width < 0.05)
        else:
            out["bb_position"] = None
            out["bb_squeeze"] = False
        return out


# --------------------------------------------------------------------------- #
# SRP: Stochastic                                                              #
# --------------------------------------------------------------------------- #
class StochasticIndicator:
    name = "stochastic"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 14) is None or "High" not in df or "Low" not in df:
            return {}
        high, low, close = df["High"], df["Low"], df["Close"]
        k, d = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3)
        return {"stoch_k": _last(k), "stoch_d": _last(d)}


# --------------------------------------------------------------------------- #
# SRP: Volume                                                                  #
# --------------------------------------------------------------------------- #
class VolumeIndicator:
    name = "volume"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 20) is None or "Volume" not in df:
            return {}
        vol = df["Volume"].replace(0, np.nan)
        vsma = _sma(vol, 20)
        out = {"volume_sma": _last(vsma)}
        if out["volume_sma"]:
            out["volume_ratio"] = float(vol.iloc[-1] / out["volume_sma"])
        vt = _trend_duration(vsma, "up")
        out["volume_trend"] = "INCREASING" if vt > 0 else "DECREASING" if vt < 0 else "STABLE"
        out["obv_trend"] = "RISING" if _trend_duration(talib.OBV(df["Close"], vol), "up") > 0 else "FALLING"
        return out


# --------------------------------------------------------------------------- #
# SRP: Price change (not a TA-Lib function)                                    #
# --------------------------------------------------------------------------- #
class PriceChangeIndicator:
    name = "price_change"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 2) is None:
            return {}
        close = df["Close"]
        return {
            "price_change_1d": _pct_change(close, 1),
            "price_change_1w": _pct_change(close, 5),
            "price_change_1m": _pct_change(close, 20),
            "price_change_3m": _pct_change(close, 60),
            "price_change_6m": _pct_change(close, 120),
        }


# --------------------------------------------------------------------------- #
# SRP: Realized volatility (not a TA-Lib function)                             #
# --------------------------------------------------------------------------- #
class VolatilityIndicator:
    name = "volatility"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 21) is None:
            return {}
        returns = np.log(df["Close"] / df["Close"].shift(1)).dropna()
        if len(returns) < 2:
            return {}
        ann = float(returns.std() * np.sqrt(252) * 100)
        return {"volatility_20d": ann}


# --------------------------------------------------------------------------- #
# SRP: Support / Resistance (not a TA-Lib function)                            #
# --------------------------------------------------------------------------- #
class SupportResistance:
    name = "support_resistance"

    def calculate(self, df: pd.DataFrame) -> Dict:
        if _require(df, 20) is None:
            return {}
        close = df["Close"]
        window = min(20, len(close))
        recent = close.iloc[-window:]
        price = float(close.iloc[-1])
        support = float(recent.min())
        resistance = float(recent.max())
        return {
            "support_20d": support,
            "resistance_20d": resistance,
            "distance_to_support": float((price / support - 1) * 100) if support else None,
            "distance_to_resistance": float((price / resistance - 1) * 100) if resistance else None,
        }


# --------------------------------------------------------------------------- #
# Composition service (DI seam)                                                 #
# --------------------------------------------------------------------------- #
DEFAULT_CALCULATORS: List[Calculator] = [
    MovingAverages(),
    RSIIndicator(),
    MACDIndicator(),
    BollingerBands(),
    StochasticIndicator(),
    VolumeIndicator(),
    PriceChangeIndicator(),
    VolatilityIndicator(),
    SupportResistance(),
]


class TechnicalAnalysisService:
    """Composes the indicator calculators into one technical dict."""

    def __init__(self, calculators: Optional[List[Calculator]] = None):
        self.calculators = list(calculators) if calculators is not None else list(DEFAULT_CALCULATORS)

    def analyze(self, df: pd.DataFrame) -> Dict:
        result: Dict = {}
        for calc in self.calculators:
            result.update(calc.calculate(df))
        return result

    # Backwards-compatible alias used by the parity contract test.
    calculate = analyze
