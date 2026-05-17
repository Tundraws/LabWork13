from __future__ import annotations

from typing import Any


class RiskAdvisor:
    """LLM-ready advisor with deterministic fallback for offline checks."""

    def build_recommendation(self, pipeline_output: dict[str, Any]) -> str:
        risk_level = str(pipeline_output.get("risk_level", "unknown"))
        eta_days = pipeline_output.get("eta_days", "unknown")
        if risk_level == "high":
            return (
                "Высокий риск поставки: активировать резервного поставщика, "
                f"увеличить страховой запас и ежедневно контролировать ETA={eta_days}."
            )
        if risk_level == "medium":
            return (
                "Средний риск поставки: подтвердить слот отгрузки у поставщика "
                f"и держать резервный сценарий при ETA={eta_days}."
            )
        return "Риск низкий: продолжать стандартный мониторинг поставки и обновлять прогноз спроса."
