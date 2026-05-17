from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routers import dashboard, health, supply_chain
from app.core.settings import get_settings
from app.core.tracing import configure_tracing
from app.infrastructure.event_store import InMemoryEventStore
from app.infrastructure.nats_gateway import NATSGateway
from app.services.autoscaler import AutoscalerService
from app.services.orchestrator import SupplyChainOrchestrator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    shutdown_tracing = configure_tracing("python-supply-chain-orchestrator", settings.jaeger_endpoint)
    bus = NATSGateway(settings.nats_url)
    await bus.connect()
    events = InMemoryEventStore()
    autoscaler = AutoscalerService(events)
    autoscaler_stop = asyncio.Event()
    autoscaler_task = asyncio.create_task(autoscaler.run(autoscaler_stop))
    orchestrator = SupplyChainOrchestrator(
        bus=bus,
        events=events,
        timeout_seconds=settings.task_timeout_seconds,
        retry_attempts=settings.task_retry_attempts,
    )
    await orchestrator.start()
    app.state.bus = bus
    app.state.orchestrator = orchestrator
    app.state.autoscaler = autoscaler
    try:
        yield
    finally:
        autoscaler_stop.set()
        await autoscaler_task
        await bus.close()
        shutdown_tracing()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Supply Chain MAS Orchestrator",
        description="Оркестратор мультиагентной системы управления цепочками поставок.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(supply_chain.router)
    app.include_router(dashboard.router)
    return app


app = create_app()
