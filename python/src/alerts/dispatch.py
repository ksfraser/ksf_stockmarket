"""Alert dispatch layer.

Canonical alert dispatch should go through this module so that downstream
code (monitor_daemon, bots, scheduled jobs) does not hardcode transport.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .discord_sender import send_alert_to_discord

logger = logging.getLogger(__name__)


def dispatch(alert: Dict[str, Any], target: str = "discord", **kwargs: Any) -> bool:
    if target == "discord":
        return send_alert_to_discord(alert, **kwargs)
    logger.warning("Unsupported dispatch target: %s", target)
    return False
