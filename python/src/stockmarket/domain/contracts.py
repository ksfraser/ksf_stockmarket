"""Core domain contracts for stockmarket system.

All DTOs and repository interfaces live here so the rest of the
codebase depends on abstractions, not infrastructure details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ── Events ──────────────────────────────────────────────────────────

@dataclass
class Event:
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    occurred_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    status: str = "pending"  # pending | running | completed | failed


# Typed event payloads -----------------------------------------------
@dataclass
class TransactionAddedPayload:
    transaction_id: int
    user_id: int
    symbol: str
    quantity: float
    price: float
    transaction_type: str  # buy | sell | dividend | split
    transaction_date: str
    account_id: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class SymbolActivatedPayload:
    symbol: str
    exchange: Optional[str] = None
    source: str = "manual_transaction"  # manual_transaction | screener | import


@dataclass
class PricesRequestedPayload:
    symbols: List[str]
    source: str = "symbol_activation"


@dataclass
class IndicatorsCalculatedPayload:
    symbol: str
    calculation_date: str
    indicator_count: int = 0


@dataclass
class AnalysisCompletedPayload:
    symbol: str
    analysis_type: str
    result: Dict[str, Any]


# ── Repository Interfaces (DI contract) ────────────────────────────

class ITransactionRepository(ABC):
    @abstractmethod
    def add_transaction(self, transaction: Dict) -> int:
        """Insert a new transaction, return transaction_id."""
        ...

    @abstractmethod
    def get_symbols_for_user(self, user_id: int) -> List[str]:
        """Get distinct symbols from a user's portfolio/transactions."""
        ...


class ISymbolRepository(ABC):
    @abstractmethod
    def upsert_symbol(self, symbol: str, data: Dict) -> bool:
        """Create or update a symbol in symbol_master."""
        ...

    @abstractmethod
    def get_active_symbols(self) -> List[str]:
        """Get all symbols marked is_active=1."""
        ...


class IPriceRepository(ABC):
    @abstractmethod
    def get_latest_price_date(self, symbol: str) -> Optional[str]:
        """Return latest price_date string or None."""
        ...

    @abstractmethod
    def insert_prices(self, symbol: str, rows: List[tuple]) -> int:
        """Bulk insert price rows, return count inserted."""
        ...


class IIndicatorRepository(ABC):
    @abstractmethod
    def get_latest_indicator_date(self, symbol: str) -> Optional[str]:
        ...

    @abstractmethod
    def insert_indicators(self, symbol: str, rows: List[tuple]) -> int:
        ...


class IEventRepository(ABC):
    @abstractmethod
    def enqueue(self, event: Event) -> bool:
        ...

    @abstractmethod
    def dequeue(self, limit: int = 10) -> List[Event]:
        ...

    @abstractmethod
    def mark_completed(self, event_id: str) -> None:
        ...

    @abstractmethod
    def mark_failed(self, event_id: str, error: str) -> None:
        ...
