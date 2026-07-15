"""Advisor package: strategy registry shortcuts."""
from __future__ import annotations

from advisors.base import AdvisorBase, Signal
from advisors.strategies import (
    BuffettQualityStrategy,
    DividendGrowthStrategy,
    MomentumStrategy,
    SectorStrategy,
    BondBasketStrategy,
    BalancedFundStrategy,
    VectorVestSafeStockStrategy,
)

STRATEGY_MAP: dict[str, type] = {
    "buffett_quality": BuffettQualityStrategy,
    "dividend_growth": DividendGrowthStrategy,
    "momentum": MomentumStrategy,
    "sector": SectorStrategy,
    "bond_basket": BondBasketStrategy,
    "balanced_fund": BalancedFundStrategy,
    "vectorvest_safe": VectorVestSafeStockStrategy,
}

__all__ = [
    "AdvisorBase",
    "Signal",
    "BuffettQualityStrategy",
    "DividendGrowthStrategy",
    "MomentumStrategy",
    "SectorStrategy",
    "BondBasketStrategy",
    "BalancedFundStrategy",
    "VectorVestSafeStockStrategy",
    "STRATEGY_MAP",
]
