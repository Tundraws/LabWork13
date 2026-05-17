from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

AgentRole = Literal["forecast", "ordering", "tracking", "risk"]


class DemandRequest(BaseModel):
    """Input for supply chain planning."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(min_length=2, max_length=64)
    avg_daily_sales: float = Field(gt=0)
    seasonality_index: float = Field(default=1.0, gt=0, le=5)
    planning_days: int = Field(default=14, ge=1, le=365)
    current_stock: int = Field(ge=0)
    unit_price: float = Field(default=11.5, gt=0)


class AgentTask(BaseModel):
    id: str
    trace_id: str
    type: AgentRole
    payload: dict[str, Any]
    pipeline_log: list[dict[str, Any]] = Field(default_factory=list)


class AgentResult(BaseModel):
    task_id: str
    trace_id: str
    agent: str
    role: AgentRole
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    pipeline_log: list[dict[str, Any]] = Field(default_factory=list)


class BidRequest(BaseModel):
    task_id: str
    type: AgentRole
    payload: dict[str, Any]


class AgentBid(BaseModel):
    task_id: str
    agent: str
    role: AgentRole
    cost: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class AuctionResponse(BaseModel):
    task_id: str
    role: AgentRole
    bids: list[AgentBid]
    winner: AgentBid | None = None


class LLMTask(BaseModel):
    id: str
    trace_id: str
    sku: str
    context: dict[str, Any] = Field(default_factory=dict)


class LLMResult(BaseModel):
    task_id: str
    trace_id: str
    agent: str
    success: bool
    recommendation: str
    provider: str
    error: str | None = None


class PipelineResponse(BaseModel):
    trace_id: UUID = Field(default_factory=uuid4)
    sku: str
    status: Literal["completed", "failed"]
    results: list[AgentResult]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class EventRecord(BaseModel):
    trace_id: str
    level: Literal["INFO", "ERROR"]
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScalingDecision(BaseModel):
    role: AgentRole
    current_replicas: int = Field(ge=1)
    desired_replicas: int = Field(ge=1)
    scaled: bool
    implementation: str
