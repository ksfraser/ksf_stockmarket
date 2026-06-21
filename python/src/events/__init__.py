"""Public event API for the stockmarket domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .provider import EventRepository, EventPublisher


def get_event_repository(db):  # returns EventRepository
    from .provider import get_event_repository as _get
    return _get(db)


def get_event_publisher(db):  # returns EventPublisher
    from .provider import get_event_publisher as _get
    return _get(db)
