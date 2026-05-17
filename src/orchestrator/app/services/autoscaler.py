from __future__ import annotations

from dataclasses import dataclass
import asyncio

from app.infrastructure.event_store import InMemoryEventStore
from app.models.supply_chain import AgentRole, EventRecord


@dataclass(frozen=True)
class AutoscalerConfig:
    threshold_per_agent: int = 3
    max_replicas: int = 4


class AutoscalerService:
    """Calculates and records scaling decisions for Go agent replicas."""

    def __init__(self, events: InMemoryEventStore, config: AutoscalerConfig | None = None) -> None:
        self._events = events
        self._config = config or AutoscalerConfig()
        self._replicas: dict[AgentRole, int] = {
            "forecast": 1,
            "ordering": 1,
            "tracking": 1,
            "risk": 1,
        }
        self._roles: tuple[AgentRole, ...] = ("forecast", "ordering", "tracking", "risk")

    async def run(self, stop_event: asyncio.Event, interval_seconds: float = 20.0) -> None:
        """Periodically evaluate load and record scaling decisions."""

        while not stop_event.is_set():
            for role in self._roles:
                self.evaluate(role)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            except TimeoutError:
                continue

    def evaluate(self, role: AgentRole) -> dict[str, int | str | bool]:
        recent_dispatches = [
            event
            for event in self._events.list_recent(100)
            if event.message == "dispatch task" and event.payload.get("role") == role
        ]
        current = self._replicas[role]
        desired = min(
            self._config.max_replicas,
            max(1, (len(recent_dispatches) // self._config.threshold_per_agent) + 1),
        )
        scaled = desired != current
        self._replicas[role] = desired
        self._events.append(
            EventRecord(
                trace_id="autoscaler",
                level="INFO",
                message="scaling decision",
                payload={"role": role, "current": current, "desired": desired, "scaled": scaled},
            )
        )
        return {
            "role": role,
            "current_replicas": current,
            "desired_replicas": desired,
            "scaled": scaled,
            "implementation": "compose-compatible decision; run docker compose up --scale <service>=N",
        }
