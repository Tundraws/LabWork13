from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_orchestrator
from app.services.orchestrator import SupplyChainOrchestrator

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(orchestrator: SupplyChainOrchestrator = Depends(get_orchestrator)) -> str:
    events = orchestrator.recent_events(30)
    rows = "\n".join(
        f"<tr><td>{event.created_at.isoformat()}</td><td>{event.level}</td>"
        f"<td>{event.trace_id}</td><td>{event.message}</td><td><code>{event.payload}</code></td></tr>"
        for event in events
    )
    return f"""
    <!doctype html>
    <html lang="ru">
    <head>
      <meta charset="utf-8">
      <title>Supply Chain MAS</title>
      <style>
        body {{ font-family: Inter, Arial, sans-serif; margin: 32px; color: #1f2937; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border-bottom: 1px solid #d1d5db; padding: 10px; text-align: left; }}
        code {{ white-space: pre-wrap; }}
        .actions {{ margin-bottom: 18px; }}
      </style>
    </head>
    <body>
      <h1>Мониторинг мультиагентной системы поставок</h1>
      <div class="actions">
        <a href="/docs">OpenAPI</a> · <a href="/api/v1/events">JSON события</a>
      </div>
      <table>
        <thead><tr><th>Время</th><th>Уровень</th><th>Trace ID</th><th>Событие</th><th>Данные</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </body>
    </html>
    """
