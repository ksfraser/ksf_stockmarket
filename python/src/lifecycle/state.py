"""Symbol lifecycle state enum and transition helper."""

from __future__ import annotations

from enum import Enum
from typing import Literal


class SymbolState(str, Enum):
    UNKNOWN = "unknown"
    CANDIDATE = "candidate"
    PENDING_BACKFILL = "pending_backfill"
    PRICES_LOADED = "prices_loaded"
    TA_READY = "ta_ready"
    ANALYSIS_ELIGIBLE = "analysis_eligible"
    INACTIVE = "inactive"


TERMINAL_STATES = {SymbolState.INACTIVE, SymbolState.ANALYSIS_ELIGIBLE}


def advance_state(current: SymbolState | None, target: SymbolState) -> SymbolState:
    if current in TERMINAL_STATES or current == target:
        return current
    return target
