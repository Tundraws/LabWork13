from __future__ import annotations

from typing import Any, Protocol

import httpx


class RecommendationProvider(Protocol):
    async def recommend(self, sku: str, context: dict[str, Any]) -> tuple[str, str]: ...


class OfflineRiskProvider:
    """Deterministic fallback used when no local or cloud LLM is configured."""

    async def recommend(self, sku: str, context: dict[str, Any]) -> tuple[str, str]:
        risk_level = str(context.get("risk_level", "unknown"))
        eta_days = context.get("eta_days", "unknown")
        ordered_units = context.get("ordered_units", context.get("reorder_units", "unknown"))
        if risk_level == "high":
            text = (
                f"SKU {sku}: высокий риск. Активировать резервного поставщика, "
                f"увеличить страховой запас и ежедневно сверять ETA={eta_days}; "
                f"объем поставки={ordered_units} требует контроля приоритета."
            )
        elif risk_level == "medium":
            text = (
                f"SKU {sku}: средний риск. Подтвердить слот отгрузки, проверить запас "
                f"на период ETA={eta_days} и подготовить fallback-поставщика."
            )
        else:
            text = f"SKU {sku}: риск низкий. Достаточно стандартного мониторинга поставки и обновления прогноза."
        return text, "offline-rule-provider"


class OllamaProvider:
    """Optional local LLM provider. The project works without Ollama by design."""

    def __init__(self, base_url: str, model: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def recommend(self, sku: str, context: dict[str, Any]) -> tuple[str, str]:
        prompt = (
            "Ты агент управления рисками цепочки поставок. "
            "Дай короткую практическую рекомендацию на русском языке. "
            f"SKU={sku}. Контекст={context}."
        )
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={"model": self._model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("response", "")).strip(), f"ollama:{self._model}"
