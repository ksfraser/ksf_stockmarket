"""Alert domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class Alert:
    symbol: str
    alert_type: str
    severity: str
    payload: Dict[str, Any]
    triggered_at: Optional[str] = field(default=None)

    def to_queue_dict(self) -> Dict[str, Any]:
        if not self.triggered_at:
            self.triggered_at = datetime.now().isoformat()
        return {
            "symbol": self.symbol,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "payload": self.payload,
            "triggered_at": self.triggered_at,
        }


@dataclass
class DetectionResult:
    alert: Optional[Alert]
    skipped: bool = False
    skip_reason: Optional[str] = None
