#!/usr/bin/env python3
"""
Stock price repository interface.

Single source of truth for persistence operations on price bars.
Calculators/fetchers should only ever touch this interface, never raw SQL.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Sequence

from .stock_price_dto import StockPriceDTO


class StockPriceRepository(ABC):
    """Read/write price bars."""

    @abstractmethod
    def save(self, dto: StockPriceDTO) -> None:
        """Upsert a single bar. Must be idempotent."""

    @abstractmethod
    def save_all(self, dtos: Sequence[StockPriceDTO]) -> int:
        """Upsert many bars. Returns count affected."""

    @abstractmethod
    def get_latest(self, symbol: str, n: int = 1) -> List[StockPriceDTO]:
        """Most-recent N bars for a symbol, ordered oldest→newest."""

    @abstractmethod
    def get_by_range(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> List[StockPriceDTO]:
        """All bars in a date window."""

    @abstractmethod
    def exists(self, symbol: str, price_date: date) -> bool:
        """Hit-test a specific bar."""
