from __future__ import annotations

import asyncio
import logging
import signal

import nats
from opentelemetry import trace

from app.models import LLMResult, LLMTask
from app.provider import OfflineRiskProvider, OllamaProvider, RecommendationProvider
from app.settings import Settings
from app.tracing import configure_tracing

LOGGER = logging.getLogger(__name__)


def build_provider(settings: Settings) -> RecommendationProvider:
    if settings.ollama_url:
        return OllamaProvider(settings.ollama_url, settings.ollama_model, settings.request_timeout_seconds)
    return OfflineRiskProvider()


async def run() -> None:
    settings = Settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    shutdown_tracing = configure_tracing("python-llm-risk-advisor", settings.jaeger_endpoint)
    provider = build_provider(settings)
    nc = await nats.connect(settings.nats_url)
    stop_event = asyncio.Event()
    tracer = trace.get_tracer("python-llm-risk-advisor")

    async def handle_message(message) -> None:  # type: ignore[no-untyped-def]
        with tracer.start_as_current_span("llm_agent.recommend"):
            task = LLMTask.model_validate_json(message.data)
            try:
                recommendation, provider_name = await provider.recommend(task.sku, task.context)
                result = LLMResult(
                    task_id=task.id,
                    trace_id=task.trace_id,
                    success=True,
                    recommendation=recommendation,
                    provider=provider_name,
                )
            except Exception as exc:  # noqa: BLE001 - external LLM failures degrade gracefully.
                LOGGER.exception("llm recommendation failed")
                fallback, provider_name = await OfflineRiskProvider().recommend(task.sku, task.context)
                result = LLMResult(
                    task_id=task.id,
                    trace_id=task.trace_id,
                    success=False,
                    recommendation=fallback,
                    provider=provider_name,
                    error=str(exc),
                )
            await nc.publish("supply.llm.results", result.model_dump_json().encode("utf-8"))
            await nc.flush()

    await nc.subscribe("supply.tasks.llm", queue="llm-risk-advisors", cb=handle_message)
    LOGGER.info("llm agent started")

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()
    await nc.drain()
    await nc.close()
    shutdown_tracing()


if __name__ == "__main__":
    asyncio.run(run())
