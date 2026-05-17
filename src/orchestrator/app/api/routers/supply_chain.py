from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_orchestrator
from app.models.supply_chain import AgentRole, AuctionResponse, DemandRequest, EventRecord, PipelineResponse
from app.services.orchestrator import SupplyChainOrchestrator

router = APIRouter(prefix="/api/v1", tags=["supply-chain"])


@router.post("/pipeline", response_model=PipelineResponse)
async def run_pipeline(
    request: DemandRequest,
    orchestrator: SupplyChainOrchestrator = Depends(get_orchestrator),
) -> PipelineResponse:
    return await orchestrator.run_pipeline(request)


@router.post("/auction/{role}", response_model=AuctionResponse)
async def collect_bids(
    role: AgentRole,
    request: DemandRequest,
    orchestrator: SupplyChainOrchestrator = Depends(get_orchestrator),
) -> AuctionResponse:
    return await orchestrator.collect_bids(request, role)


@router.get("/events", response_model=list[EventRecord])
async def recent_events(
    limit: int = Query(default=50, ge=1, le=200),
    orchestrator: SupplyChainOrchestrator = Depends(get_orchestrator),
) -> list[EventRecord]:
    return orchestrator.recent_events(limit)
