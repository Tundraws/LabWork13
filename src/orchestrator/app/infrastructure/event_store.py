from __future__ import annotations

from collections import deque
from threading import Lock

from app.models.supply_chain import EventRecord


class InMemoryEventStore:
    """Small ring-buffer event store used by the monitoring dashboard."""

    def __init__(self, max_events: int = 200) -> None:
        self._events: deque[EventRecord] = deque(maxlen=max_events)
        self._lock = Lock()

    def append(self, event: EventRecord) -> None:
        with self._lock:
            self._events.appendleft(event)

    def list_recent(self, limit: int = 50) -> list[EventRecord]:
        with self._lock:
            return list(self._events)[:limit]
