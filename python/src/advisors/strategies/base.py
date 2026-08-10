"""Advisor strategy contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from events import EventRepository


@dataclass
class AdvisorContext:
    slug: str
    user_id: int
    start_date: date
    current_date: date
    currency: str = "CAD"
    region: Optional[str] = None
    sector: Optional[str] = None
    frequency: str = "daily"


class BaseStrategy(ABC):
    context: AdvisorContext

    def __init__(self, context: AdvisorContext) -> None:
        self.context = context

    @abstractmethod
    def select_universe(self) -> List[str]:
        """Return candidate symbols for this advisor on the current date."""

    @abstractmethod
    def decide(self, symbol: str, as_of: date) -> Dict[str, object]:
        """Return one of BUY/SELL/HOLD with sizing and notes."""
