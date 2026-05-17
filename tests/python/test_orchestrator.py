from __future__ import annotations

import asyncio

import pytest

from app.infrastructure.event_store import InMemoryEventStore
from app.infrastructure.nats_gateway import FakeNATSGateway
from app.models.supply_chain import DemandRequest
from app.services.orchestrator import SupplyChainOrchestrator


def build_request() -> DemandRequest:
    return DemandRequest(
        sku="SKU-42",
        avg_daily_sales=8,
        seasonality_index=1.1,
        planning_days=10,
        current_stock=15,
        unit_price=9.5,
    )


@pytest.mark.asyncio
async def test_pipeline_success() -> None:
    bus = FakeNATSGateway()
    orchestrator = SupplyChainOrchestrator(bus, InMemoryEventStore(), timeout_seconds=1, retry_attempts=1)
    await orchestrator.start()

    async def complete_published_tasks() -> None:
        expected_roles = ["forecast", "ordering", "tracking", "risk"]
        for role in expected_roles:
            while not bus.published or bus.published[-1][0] != f"supply.tasks.{role}":
                await asyncio.sleep(0)
            _, task = bus.published[-1]
            output = {
                "forecast": {"forecast_units": 88, "reorder_units": 73},
                "ordering": {"order_id": "PO-1", "ordered_units": 73, "eta_days": 4},
                "tracking": {"shipment_id": "SHIP-1", "status": "in_transit", "eta_days": 4},
                "risk": {"risk_score": 0.42, "risk_level": "medium"},
            }[role]
            await bus.emit_result(
                {
                    "task_id": task["id"],
                    "trace_id": task["trace_id"],
                    "agent": role,
                    "role": role,
                    "success": True,
                    "output": output,
                    "pipeline_log": task["pipeline_log"] + [{"agent": role, "output": output}],
                }
            )

    worker = asyncio.create_task(complete_published_tasks())
    response = await orchestrator.run_pipeline(build_request())
    await worker

    assert response.status == "completed"
    assert [result.role for result in response.results] == ["forecast", "ordering", "tracking", "risk"]


@pytest.mark.asyncio
async def test_pipeline_returns_failed_status_after_timeout() -> None:
    bus = FakeNATSGateway()
    orchestrator = SupplyChainOrchestrator(bus, InMemoryEventStore(), timeout_seconds=0.01, retry_attempts=2)
    await orchestrator.start()

    response = await orchestrator.run_pipeline(build_request())

    assert response.status == "failed"
    assert response.results[0].role == "forecast"
    assert "Timeout" in response.results[0].error or "timeout" in response.results[0].error


@pytest.mark.asyncio
async def test_auction_selects_lowest_cost_bid() -> None:
    bus = FakeNATSGateway()
    orchestrator = SupplyChainOrchestrator(bus, InMemoryEventStore(), timeout_seconds=1, retry_attempts=1)
    await orchestrator.start()

    async def send_bids() -> None:
        while not bus.published:
            await asyncio.sleep(0)
        _, request = bus.published[-1]
        await bus.emit_bid(
            {
                "task_id": request["task_id"],
                "agent": "expensive-agent",
                "role": "forecast",
                "cost": 18,
                "confidence": 0.95,
            }
        )
        await bus.emit_bid(
            {
                "task_id": request["task_id"],
                "agent": "cheap-agent",
                "role": "forecast",
                "cost": 9,
                "confidence": 0.88,
            }
        )

    worker = asyncio.create_task(send_bids())
    response = await orchestrator.collect_bids(build_request(), "forecast")
    await worker

    assert response.winner is not None
    assert response.winner.agent == "cheap-agent"
    assert len(response.bids) == 2
