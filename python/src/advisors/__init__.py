"""Advisor package: strategy registry shortcuts."""
from __future__ import annotations

from advisors.base import AdvisorBase, Signal
from advisors.strategies import (
    BuffettQualityStrategy,
    DividendGrowthStrategy,
    MomentumStrategy,
)

__all__ = [
    "AdvisorBase",
    "Signal",
    "BuffettQualityStrategy",
    "DividendGrowthStrategy",
    "MomentumStrategy",
]
