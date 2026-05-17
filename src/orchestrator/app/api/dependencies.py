from __future__ import annotations

from fastapi import Request

from app.services.orchestrator import SupplyChainOrchestrator


def get_orchestrator(request: Request) -> SupplyChainOrchestrator:
    """Resolve orchestrator from FastAPI application state."""

    return request.app.state.orchestrator
