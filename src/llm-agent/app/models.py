from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LLMTask(BaseModel):
    id: str
    trace_id: str
    sku: str
    context: dict[str, Any] = Field(default_factory=dict)


class LLMResult(BaseModel):
    task_id: str
    trace_id: str
    agent: str = "python-llm-risk-advisor"
    success: bool
    recommendation: str
    provider: str
    error: str | None = None
