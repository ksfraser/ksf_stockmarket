"""Base advisor class and signal dataclass."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    symbol: str
    action: str  # BUY | SELL | HOLD
    weight: float = 0.0
    reason: str = ""
    confidence: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "weight": self.weight,
            "reason": self.reason,
            "confidence": self.confidence,
            "meta": self.meta,
        }


class AdvisorBase:
    """Abstract base for advisor strategies.

    Subclasses implement selection, screening, and position sizing.
    """

    name: str = "base"
    slug: str = "base"

    def __init__(self, db: Any, config: dict[str, Any] | None = None) -> None:
        self.db = db
        self.config = config or {}
        self.table_prefix = config.get("table_prefix", "") if config else ""

    def _t(self, name: str) -> str:
        """Return a prefixed table name so tests can use a scratch schema."""
        return f"{self.table_prefix}{name}"

    # ------------------------------------------------------------------
    # Eligibility / scheduling
    # ------------------------------------------------------------------
    def should_run_today(self, run_date: date) -> bool:
        """Return True if the advisor is eligible for ``run_date``."""
        schedule = self.config.get("schedule", "daily")
        weekday = run_date.strftime("%A").lower()
        if schedule == "daily":
            return True
        return schedule == weekday

    # ------------------------------------------------------------------
    # Core strategy contract
    # ------------------------------------------------------------------
    def select_universe(self, run_date: date) -> list[str]:
        """Return candidate symbols to evaluate for ``run_date``."""
        raise NotImplementedError

    def score(self, symbol: str, run_date: date) -> float:
        """Return a score (higher = better) for a symbol on a given date."""
        raise NotImplementedError

    def generate_signals(self, run_date: date, max_positions: int = 20) -> list[Signal]:
        """Produce a ranked list of BUY/SELL/HOLD signals."""
        try:
            universe = self.select_universe(run_date)
        except NotImplementedError:
            universe = []
        if not universe:
            logger.info("Advisor %s universe is empty on %s", self.slug, run_date)
            return []

        scored: list[tuple[str, float]] = []
        for symbol in universe:
            try:
                s = self.score(symbol, run_date)
            except Exception:
                logger.exception("Scoring failed for %s on %s", symbol, run_date)
                continue
            if s > 0:
                scored.append((symbol, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        selected = scored[:max_positions]

        signals: list[Signal] = []
        for rank, (symbol, score) in enumerate(selected, start=1):
            signals.append(
                Signal(
                    symbol=symbol,
                    action="BUY",
                    weight=1.0 / max_positions,
                    reason=f"rank={rank} score={score:.2f}",
                    confidence=min(score / 100.0, 1.0),
                    meta={"rank": rank, "score": score},
                )
            )
        return signals

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def on_run_start(self, run_date: date) -> None:
        logger.info("Advisor %s starting run for %s", self.slug, run_date)

    def on_run_complete(self, run_date: date, signals: list[Signal]) -> None:
        logger.info(
            "Advisor %s completed run for %s; generated %d signals",
            self.slug,
            run_date,
            len(signals),
        )

    def on_run_error(self, run_date: date, error: Exception) -> None:
        logger.exception("Advisor %s failed on %s: %s", self.slug, run_date, error)
