from __future__ import annotations

from fastapi import APIRouter

from app.models.supply_chain import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="supply-chain-orchestrator")
