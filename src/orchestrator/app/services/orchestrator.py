from __future__ import annotations

import asyncio
import logging
from contextlib import nullcontext
from typing import Protocol
from uuid import uuid4

try:
    from opentelemetry import trace
except ModuleNotFoundError:
    trace = None

from app.infrastructure.event_store import InMemoryEventStore
from app.models.supply_chain import (
    AgentBid,
    AgentResult,
    AgentRole,
    AgentTask,
    AuctionResponse,
    BidRequest,
    DemandRequest,
    EventRecord,
    LLMResult,
    LLMTask,
    PipelineResponse,
)
from app.services.llm_advisor import RiskAdvisor

LOGGER = logging.getLogger(__name__)

PIPELINE: tuple[AgentRole, ...] = ("forecast", "ordering", "tracking", "risk")


class MessageBus(Protocol):
    async def publish_json(self, subject: str, payload: dict) -> None: ...

    async def subscribe(self, subject: str, callback) -> None: ...


class SupplyChainOrchestrator:
    """Coordinates distributed supply chain agents through NATS."""

    def __init__(
        self,
        bus: MessageBus,
        events: InMemoryEventStore,
        timeout_seconds: float,
        retry_attempts: int,
        advisor: RiskAdvisor | None = None,
    ) -> None:
        self._bus = bus
        self._events = events
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = retry_attempts
        self._advisor = advisor or RiskAdvisor()
        self._pending: dict[str, asyncio.Future[AgentResult]] = {}
        self._pending_llm: dict[str, asyncio.Future[LLMResult]] = {}
        self._bid_windows: dict[str, list[AgentBid]] = {}
        self._lock = asyncio.Lock()
        self._tracer = trace.get_tracer("python-supply-chain-orchestrator") if trace else None

    async def start(self) -> None:
        await self._bus.subscribe("supply.results", self._on_result)
        await self._bus.subscribe("supply.auction.reply", self._on_bid)
        await self._bus.subscribe("supply.llm.results", self._on_llm_result)

    async def run_pipeline(self, request: DemandRequest) -> PipelineResponse:
        with self._span("orchestrator.pipeline"):
            trace_id = str(uuid4())
            payload = request.model_dump()
            results: list[AgentResult] = []
            pipeline_log: list[dict] = []

            self._record(trace_id, "INFO", "pipeline started", {"sku": request.sku})
            for role in PIPELINE:
                result = await self._dispatch_with_retry(trace_id, role, payload, pipeline_log)
                results.append(result)
                if not result.success:
                    self._record(trace_id, "ERROR", "pipeline failed", {"role": role, "error": result.error})
                    return PipelineResponse(trace_id=trace_id, sku=request.sku, status="failed", results=results)
                payload = {**payload, **result.output}
                pipeline_log = result.pipeline_log

            recommendation = await self._request_llm_recommendation(trace_id, request.sku, payload)
            results[-1].output["llm_advisor_recommendation"] = recommendation.recommendation
            results[-1].output["llm_provider"] = recommendation.provider
            self._record(trace_id, "INFO", "pipeline completed", {"sku": request.sku})
            return PipelineResponse(trace_id=trace_id, sku=request.sku, status="completed", results=results)

    async def _dispatch_with_retry(
        self,
        trace_id: str,
        role: AgentRole,
        payload: dict,
        pipeline_log: list[dict],
    ) -> AgentResult:
        last_error: Exception | None = None
        for attempt in range(1, self._retry_attempts + 1):
            task = AgentTask(
                id=str(uuid4()),
                trace_id=trace_id,
                type=role,
                payload=payload,
                pipeline_log=pipeline_log,
            )
            self._record(trace_id, "INFO", "dispatch task", {"role": role, "attempt": attempt})
            try:
                with self._span(f"orchestrator.dispatch.{role}"):
                    return await self._send_task(task)
            except TimeoutError as exc:
                last_error = exc
                self._record(trace_id, "ERROR", "task timeout", {"role": role, "attempt": attempt})
            except Exception as exc:  # noqa: BLE001 - failures become pipeline results.
                last_error = exc
                self._record(trace_id, "ERROR", "task failed", {"role": role, "error": str(exc)})

        error_message = (str(last_error) or "task timeout exceeded") if last_error else "unknown orchestration error"
        return AgentResult(
            task_id="",
            trace_id=trace_id,
            agent="orchestrator",
            role=role,
            success=False,
            error=error_message,
        )

    async def _send_task(self, task: AgentTask) -> AgentResult:
        future: asyncio.Future[AgentResult] = asyncio.get_running_loop().create_future()
        async with self._lock:
            self._pending[task.id] = future
        try:
            await self._bus.publish_json(f"supply.tasks.{task.type}", task.model_dump())
            return await asyncio.wait_for(future, timeout=self._timeout_seconds)
        finally:
            async with self._lock:
                self._pending.pop(task.id, None)

    async def _on_result(self, data: bytes) -> None:
        result = AgentResult.model_validate_json(data)
        async with self._lock:
            future = self._pending.get(result.task_id)
        if future is None or future.done():
            LOGGER.warning("received orphan result", extra={"task_id": result.task_id})
            return
        future.set_result(result)

    async def _on_bid(self, data: bytes) -> None:
        bid = AgentBid.model_validate_json(data)
        async with self._lock:
            window = self._bid_windows.get(bid.task_id)
            if window is not None:
                window.append(bid)

    async def _on_llm_result(self, data: bytes) -> None:
        result = LLMResult.model_validate_json(data)
        async with self._lock:
            future = self._pending_llm.get(result.task_id)
        if future is not None and not future.done():
            future.set_result(result)

    async def _request_llm_recommendation(self, trace_id: str, sku: str, context: dict) -> LLMResult:
        task = LLMTask(id=str(uuid4()), trace_id=trace_id, sku=sku, context=context)
        future: asyncio.Future[LLMResult] = asyncio.get_running_loop().create_future()
        async with self._lock:
            self._pending_llm[task.id] = future
        try:
            with self._span("orchestrator.llm_recommendation"):
                await self._bus.publish_json("supply.tasks.llm", task.model_dump())
                return await asyncio.wait_for(future, timeout=self._timeout_seconds)
        except TimeoutError:
            text = self._advisor.build_recommendation(context)
            return LLMResult(
                task_id=task.id,
                trace_id=trace_id,
                agent="orchestrator-fallback",
                success=False,
                recommendation=text,
                provider="orchestrator-offline-fallback",
                error="llm agent timeout",
            )
        finally:
            async with self._lock:
                self._pending_llm.pop(task.id, None)

    async def collect_bids(self, request: DemandRequest, role: AgentRole) -> AuctionResponse:
        bid_request = BidRequest(task_id=str(uuid4()), type=role, payload=request.model_dump())
        async with self._lock:
            self._bid_windows[bid_request.task_id] = []
        await self._bus.publish_json("supply.auction.bid", bid_request.model_dump())
        self._record(str(uuid4()), "INFO", "auction requested", {"role": role, "task_id": bid_request.task_id})
        await asyncio.sleep(0.25)
        async with self._lock:
            bids = self._bid_windows.pop(bid_request.task_id, [])
        winner = min(bids, key=lambda bid: (bid.cost, -bid.confidence), default=None)
        return AuctionResponse(task_id=bid_request.task_id, role=role, bids=bids, winner=winner)

    def recent_events(self, limit: int = 50) -> list[EventRecord]:
        return self._events.list_recent(limit)

    def _span(self, name: str):
        if self._tracer is None:
            return nullcontext()
        return self._tracer.start_as_current_span(name)

    def _record(self, trace_id: str, level: str, message: str, payload: dict) -> None:
        event = EventRecord(trace_id=trace_id, level=level, message=message, payload=payload)
        self._events.append(event)
        log_method = LOGGER.error if level == "ERROR" else LOGGER.info
        log_method(message, extra={"trace_id": trace_id, "payload": payload})
