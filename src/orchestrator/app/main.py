from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routers import dashboard, health, supply_chain
from app.core.settings import get_settings
from app.infrastructure.event_store import InMemoryEventStore
from app.infrastructure.nats_gateway import NATSGateway
from app.services.orchestrator import SupplyChainOrchestrator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    bus = NATSGateway(settings.nats_url)
    await bus.connect()
    events = InMemoryEventStore()
    orchestrator = SupplyChainOrchestrator(
        bus=bus,
        events=events,
        timeout_seconds=settings.task_timeout_seconds,
        retry_attempts=settings.task_retry_attempts,
    )
    await orchestrator.start()
    app.state.bus = bus
    app.state.orchestrator = orchestrator
    try:
        yield
    finally:
        await bus.close()


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
