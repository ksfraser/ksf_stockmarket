"""Event provider selection for the stockmarket domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repository import EventRepository
    from .publisher import EventPublisher


def get_event_repository(db):  # -> EventRepository
    from .repository import EventRepository
    return EventRepository(db)


def get_event_publisher(db):  # -> EventPublisher
    from .publisher import EventPublisher
    return EventPublisher(db)
