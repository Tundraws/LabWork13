from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_orchestrator
from app.models.supply_chain import DemandRequest
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
        form {{ display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 8px; margin: 20px 0; }}
        input, button {{ padding: 9px; border: 1px solid #9ca3af; border-radius: 6px; }}
        button {{ background: #14532d; color: white; cursor: pointer; }}
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
      <form method="get" action="/dashboard/run">
        <input name="sku" value="SKU-25" aria-label="sku">
        <input name="avg_daily_sales" value="18" aria-label="avg_daily_sales">
        <input name="seasonality_index" value="1.3" aria-label="seasonality_index">
        <input name="planning_days" value="14" aria-label="planning_days">
        <input name="current_stock" value="120" aria-label="current_stock">
        <button type="submit">Запустить pipeline</button>
      </form>
      <table>
        <thead><tr><th>Время</th><th>Уровень</th><th>Trace ID</th><th>Событие</th><th>Данные</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </body>
    </html>
    """


@router.get("/dashboard/run")
async def run_from_dashboard(
    sku: str = Query(...),
    avg_daily_sales: float = Query(...),
    seasonality_index: float = Query(...),
    planning_days: int = Query(...),
    current_stock: int = Query(...),
    orchestrator: SupplyChainOrchestrator = Depends(get_orchestrator),
) -> RedirectResponse:
    await orchestrator.run_pipeline(
        DemandRequest(
            sku=sku,
            avg_daily_sales=avg_daily_sales,
            seasonality_index=seasonality_index,
            planning_days=planning_days,
            current_stock=current_stock,
        )
    )
    return RedirectResponse("/", status_code=303)
