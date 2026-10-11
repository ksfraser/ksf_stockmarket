"""
Expanded TA-Lib SRP wrappers (the "rest" of TA-Lib beyond the 9 monster-compat
indicators) + a ``TASuite`` that applies ALL of them to a price-history frame.

Design rules (same as ``technical_indicators.py``):
- Every class is a thin wrapper: it takes a price-history ``pd.DataFrame`` and
  calls TA-Lib (canonical math). No I/O, no yfinance.
- Each class is single-responsibility (one indicator, or a tightly-coupled pair
  like AROON up/down that TA-Lib computes together).
- ``TASuite`` composes the 9 monster-compat calculators (from
  ``technical_indicators``) PLUS every wrapper here, so "apply all of the
  calculations to our data" is a single ``TASuite().analyze(df)`` call.

IMPORTANT — candlestick patterns are INTENTIONALLY EXCLUDED:
    TA-Lib's CDL* functions (CDLENGULFING, CDLHAMMER, ...) are NOT wrapped or
    applied. Prior experiments on this dataset found the CDL signals to be
    *contra-wins* — they predicted the opposite of subsequent price action, so
    including them would degrade signal quality. They remain excluded pending
    further research. (See ``EXCLUDED_FROM_APPLY_ALL``.)
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
import talib

from src.indicators.technical_indicators import (
    BollingerBands, MACDIndicator, MovingAverages, PriceChangeIndicator,
    RSIIndicator, StochasticIndicator, SupportResistance, VolatilityIndicator,
    VolumeIndicator,
)


def _last(arr) -> float | None:
    if arr is None:
        return None
    s = pd.Series(arr).dropna()
    return float(s.iloc[-1]) if len(s) else None


def _ohlc(df: pd.DataFrame):
    """Return (open, high, low, close, volume) Series, or raise if insufficient."""
    for col in ("Open", "High", "Low", "Close"):
        if col not in df:
            raise ValueError(f"missing required column {col}")
    o = df["Open"]
    h = df["High"]
    l = df["Low"]
    c = df["Close"]
    v = df["Volume"] if "Volume" in df else None
    return o, h, l, c, v


# --------------------------------------------------------------------------- #
# Overlap studies (beyond the SMA/EMA already in technical_indicators)          #
# --------------------------------------------------------------------------- #
class DEMAWrapper:
    name = "dema"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"dema": _last(talib.DEMA(c, timeperiod=30))}


class TEMAWrapper:
    name = "tema"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"tema": _last(talib.TEMA(c, timeperiod=30))}


class TRIMAWrapper:
    name = "trima"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"trima": _last(talib.TRIMA(c, timeperiod=30))}


class WMAWrapper:
    name = "wma"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"wma": _last(talib.WMA(c, timeperiod=30))}


class KAMAWrapper:
    name = "kama"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"kama": _last(talib.KAMA(c, timeperiod=30))}


class T3Wrapper:
    name = "t3"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"t3": _last(talib.T3(c, timeperiod=5, vfactor=0.7))}


class MIDPRICEWrapper:
    name = "midprice"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"midprice": _last(talib.MIDPRICE(h, l, timeperiod=14))}


class MIDPOINTWrapper:
    name = "midpoint"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"midpoint": _last(talib.MIDPOINT(c, timeperiod=14))}


class PriceTransform:
    name = "price_transform"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {
            "avg_price": _last(talib.AVGPRICE(o, h, l, c)),
            "median_price": _last(talib.MEDPRICE(h, l)),
            "typical_price": _last(talib.TYPPRICE(h, l, c)),
            "weighted_close": _last(talib.WCLPRICE(h, l, c)),
        }


# --------------------------------------------------------------------------- #
# Momentum (beyond RSI, already in technical_indicators)                       #
# --------------------------------------------------------------------------- #
class ROCWrapper:
    name = "roc"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"roc": _last(talib.ROC(c, timeperiod=10)),
                "roc_pct": _last(talib.ROCP(c, timeperiod=10))}


class MOMWrapper:
    name = "mom"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"mom": _last(talib.MOM(c, timeperiod=10))}


class WILLRWrapper:
    name = "willr"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"williams_r": _last(talib.WILLR(h, l, c, timeperiod=14))}


class CCIWrapper:
    name = "cci"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"cci": _last(talib.CCI(h, l, c, timeperiod=20))}


class CMOWrapper:
    name = "cmo"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"cmo": _last(talib.CMO(c, timeperiod=14))}


class APOPPOWrapper:
    name = "apo_ppo"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"apo": _last(talib.APO(c, fastperiod=12, slowperiod=26, matype=0)),
                "ppo": _last(talib.PPO(c, fastperiod=12, slowperiod=26, matype=0))}


class BOPWrapper:
    name = "bop"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"bop": _last(talib.BOP(o, h, l, c))}


# --------------------------------------------------------------------------- #
# Volatility (beyond the realized-vol in technical_indicators)                 #
# --------------------------------------------------------------------------- #
class ATRWrapper:
    name = "atr"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"atr": _last(talib.ATR(h, l, c, timeperiod=14)),
                "natr": _last(talib.NATR(h, l, c, timeperiod=14))}


# --------------------------------------------------------------------------- #
# Volume (beyond OBV, already in technical_indicators)                         #
# --------------------------------------------------------------------------- #
class ADWrapper:
    name = "chaikin_ad"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        if v is None:
            return {}
        return {"chaikin_ad": _last(talib.AD(h, l, c, v))}


class ADOSCWrapper:
    name = "adosc"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        if v is None:
            return {}
        return {"adosc": _last(talib.ADOSC(h, l, c, v, fastperiod=3, slowperiod=10))}


class MFIWrapper:
    name = "mfi"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        if v is None:
            return {}
        return {"mfi": _last(talib.MFI(h, l, c, v, timeperiod=14))}


# NOTE: EMV (Ease of Movement) is intentionally absent — TA-Lib's Python binding
# (0.7.0) does not expose talib.EMV, so it cannot be wrapped. A pandas port of
# EMV would be hand-rolled math, which belongs in a separate module, not here.


# --------------------------------------------------------------------------- #
# Trend / cycle                                                               #
# --------------------------------------------------------------------------- #
class ADXWrapper:
    name = "adx"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"adx": _last(talib.ADX(h, l, c, timeperiod=14)),
                "adxr": _last(talib.ADXR(h, l, c, timeperiod=14))}


class AROONWrapper:
    name = "aroon"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        up, down = talib.AROON(h, l, timeperiod=14)
        return {"aroon_up": _last(up), "aroon_down": _last(down),
                "aroon_osc": _last(talib.AROONOSC(h, l, timeperiod=14))}


class DirectionalMovementWrapper:
    name = "directional_movement"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"plus_di": _last(talib.PLUS_DI(h, l, c, timeperiod=14)),
                "minus_di": _last(talib.MINUS_DI(h, l, c, timeperiod=14)),
                "dx": _last(talib.DX(h, l, c, timeperiod=14))}


class SARWrapper:
    name = "sar"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"sar": _last(talib.SAR(h, l, acceleration=0.02, maximum=0.2))}


class TRIXWrapper:
    name = "trix"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"trix": _last(talib.TRIX(c, timeperiod=30))}


class ULTOSCWrapper:
    name = "ultosc"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"ultosc": _last(talib.ULTOSC(h, l, c, timeperiod1=7, timeperiod2=14, timeperiod3=28))}


class HilbertTransform:
    name = "hilbert"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        dcperiod = _last(talib.HT_DCPERIOD(c))
        dcphase = _last(talib.HT_DCPHASE(c))
        ph = talib.HT_PHASOR(c)
        sine = talib.HT_SINE(c)
        trendmode = _last(talib.HT_TRENDMODE(c))
        inphase = _last(ph[0]) if isinstance(ph, tuple) else None
        quadrature = _last(ph[1]) if isinstance(ph, tuple) else None
        sine_vals = _last(sine[0]) if isinstance(sine, tuple) else None
        lead_sine = _last(sine[1]) if isinstance(sine, tuple) else None
        return {
            "ht_dcperiod": dcperiod, "ht_dcphase": dcphase,
            "ht_inphase": inphase, "ht_quadrature": quadrature,
            "ht_sine": sine_vals, "ht_lead_sine": lead_sine,
            "ht_trendmode": trendmode,
        }


# --------------------------------------------------------------------------- #
# Statistic functions (single series)                                          #
# --------------------------------------------------------------------------- #
class LinearRegWrapper:
    name = "linear_reg"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {
            "linearreg": _last(talib.LINEARREG(c, timeperiod=14)),
            "linearreg_angle": _last(talib.LINEARREG_ANGLE(c, timeperiod=14)),
            "linearreg_intercept": _last(talib.LINEARREG_INTERCEPT(c, timeperiod=14)),
            "linearreg_slope": _last(talib.LINEARREG_SLOPE(c, timeperiod=14)),
            "tsf": _last(talib.TSF(c, timeperiod=14)),
        }


class StatDevWrapper:
    name = "stat_dev"
    def calculate(self, df):
        o, h, l, c, v = _ohlc(df)
        return {"stddev": _last(talib.STDDEV(c, timeperiod=20, nbdev=1)),
                "variance": _last(talib.VAR(c, timeperiod=20, nbdev=1))}


# --------------------------------------------------------------------------- #
# Composition: apply ALL the calculations to our data                          #
# --------------------------------------------------------------------------- #
EXPANDED_CALCULATORS: List = [
    DEMAWrapper(), TEMAWrapper(), TRIMAWrapper(), WMAWrapper(), KAMAWrapper(),
    T3Wrapper(), MIDPRICEWrapper(), MIDPOINTWrapper(), PriceTransform(),
    ROCWrapper(), MOMWrapper(), WILLRWrapper(), CCIWrapper(), CMOWrapper(),
    APOPPOWrapper(), BOPWrapper(), ATRWrapper(), ADWrapper(), ADOSCWrapper(),
 MFIWrapper(), ADXWrapper(), AROONWrapper(),
    DirectionalMovementWrapper(), SARWrapper(), TRIXWrapper(), ULTOSCWrapper(),
    HilbertTransform(), LinearRegWrapper(), StatDevWrapper(),
]

# CDL* (candlestick patterns) are deliberately NOT in this list — see module docstring.
EXCLUDED_FROM_APPLY_ALL = "TA-Lib CDL* candlestick patterns (contra-wins in prior experiments)"


class TASuite:
    """Applies the monster-compat indicators AND every TA-Lib wrapper to a frame."""

    def __init__(self, calculators: List = None):
        base = [MovingAverages(), RSIIndicator(), MACDIndicator(), BollingerBands(),
                StochasticIndicator(), VolumeIndicator(), PriceChangeIndicator(),
                VolatilityIndicator(), SupportResistance()]
        self.calculators = list(calculators) if calculators is not None else base + EXPANDED_CALCULATORS

    def analyze(self, df: pd.DataFrame) -> Dict:
        result: Dict = {}
        for calc in self.calculators:
            try:
                result.update(calc.calculate(df))
            except Exception:
                # a single unavailable indicator must not sink the whole suite
                continue
        return result
