"""Repository helpers for symbol lifecycle state."""

from __future__ import annotations

import logging
from typing import Iterable

from .state import SymbolState

logger = logging.getLogger(__name__)


class SymbolLifecycleRepository:
    def __init__(self, db) -> None:
        self.db = db

    def get_state(self, symbol: str) -> SymbolState | None:
        row = self.db.fetchone(
            "SELECT pipeline_state FROM symbol_master WHERE symbol = %s",
            (symbol,),
        )
        if not row:
            return None
        state = row.get("pipeline_state") if isinstance(row, dict) else None
        if not state:
            return None
        return SymbolState(state)

    def get_symbols_needing_backfill(self) -> list[str]:
        rows = self.db.fetchall(
            "SELECT symbol FROM symbol_master "
            "WHERE is_active = 1 AND pipeline_state IN (%s, %s) "
            "ORDER BY last_updated ASC",
            (SymbolState.CANDIDATE.value, SymbolState.PENDING_BACKFILL.value),
        )
        return [row["symbol"] if isinstance(row, dict) else row[0] for row in rows]

    def get_symbols_for_analysis(self) -> list[str]:
        rows = self.db.fetchall(
            "SELECT symbol FROM symbol_master "
            "WHERE is_active = 1 AND pipeline_state = %s",
            (SymbolState.ANALYSIS_ELIGIBLE.value,),
        )
        return [row["symbol"] if isinstance(row, dict) else row[0] for row in rows]

    def set_state(self, symbol: str, state: SymbolState) -> None:
        self.db.execute(
            "UPDATE symbol_master SET pipeline_state = %s, last_state_transition = NOW() "
            "WHERE symbol = %s",
            (state.value, symbol),
        )

    @staticmethod
    def symbol_is_complete(row) -> bool:
        latest_price = row.get("latest_price_date") if isinstance(row, dict) else None
        latest_indicator = (
            row.get("latest_indicator_date") if isinstance(row, dict) else None
        )
        return bool(latest_price and latest_indicator)

    def bootstrap_existing_symbols(self) -> None:
        for state, symbols in {
            SymbolState.CANDIDATE: self._symbols_missing_prices(),
            SymbolState.ANALYSIS_ELIGIBLE: self._symbols_complete(),
        }.items():
            for symbol in symbols:
                try:
                    self.set_state(symbol, state)
                except Exception:
                    logger.exception("Failed to bootstrap state for %s", symbol)

    def _symbols_missing_prices(self) -> list[str]:
        rows = self.db.fetchall(
            "SELECT symbol FROM symbol_master WHERE is_active = 1"
        )
        symbols: list[str] = []
        for row in rows:
            symbol = row["symbol"] if isinstance(row, dict) else row[0]
            latest = self.db.fetchone(
                "SELECT MAX(price_date) AS latest_price_date, "
                "MAX(indicator_date) AS latest_indicator_date "
                "FROM ("
                "  SELECT MAX(price_date) AS price_date, NULL AS indicator_date "
                "  FROM stockprices WHERE symbol = %s "
                "  UNION ALL "
                "  SELECT NULL, MAX(indicator_date) AS indicator_date "
                "  FROM ta_indicators WHERE symbol = %s"
                ") AS combined",
                (symbol, symbol),
            )
            if not self.symbol_is_complete(latest):
                symbols.append(symbol)
        return symbols

    def _symbols_complete(self) -> list[str]:
        rows = self.db.fetchall(
            "SELECT symbol FROM symbol_master WHERE is_active = 1"
        )
        symbols: list[str] = []
        for row in rows:
            symbol = row["symbol"] if isinstance(row, dict) else row[0]
            latest = self.db.fetchone(
                "SELECT MAX(price_date) AS latest_price_date, "
                "MAX(indicator_date) AS latest_indicator_date "
                "FROM ("
                "  SELECT MAX(price_date) AS price_date, NULL AS indicator_date "
                "  FROM stockprices WHERE symbol = %s "
                "  UNION ALL "
                "  SELECT NULL, MAX(indicator_date) AS indicator_date "
                "  FROM ta_indicators WHERE symbol = %s"
                ") AS combined",
                (symbol, symbol),
            )
            if self.symbol_is_complete(latest):
                symbols.append(symbol)
        return symbols
