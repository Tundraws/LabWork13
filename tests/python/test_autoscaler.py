from __future__ import annotations

from app.infrastructure.event_store import InMemoryEventStore
from app.models.supply_chain import EventRecord
from app.services.autoscaler import AutoscalerConfig, AutoscalerService


def test_autoscaler_increases_desired_replicas_after_dispatch_burst() -> None:
    events = InMemoryEventStore()
    for _ in range(6):
        events.append(
            EventRecord(
                trace_id="trace-1",
                level="INFO",
                message="dispatch task",
                payload={"role": "forecast"},
            )
        )
    autoscaler = AutoscalerService(events, AutoscalerConfig(threshold_per_agent=3, max_replicas=4))

    decision = autoscaler.evaluate("forecast")

    assert decision["current_replicas"] == 1
    assert decision["desired_replicas"] == 3
    assert decision["scaled"] is True
