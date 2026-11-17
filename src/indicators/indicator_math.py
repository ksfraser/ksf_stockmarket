#!/usr/bin/env python3
"""Canonical indicator math — single implementation of RSI / NATR.

Previously duplicated in detection_triggers (NATR, returning np.ndarray) and
stock_alert_detection (RSI + NATR, returning pd.Series). This module is the one
implementation; both callers import from here. Returns pandas Series so callers
use ``.iloc`` indexing consistently.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(n).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_natr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    if len(close) < n:
        return pd.Series([np.nan] * len(close))
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    natr = (tr.rolling(n).mean() / close) * 100
    return natr
