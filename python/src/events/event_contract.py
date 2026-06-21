"""Event contract for the stockmarket domain."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    event_id: str
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    status: str = "pending"
    attempts: int = 0
    last_error: Optional[str] = None
