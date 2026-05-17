from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.supply_chain import DemandRequest


def test_demand_request_accepts_valid_payload() -> None:
    request = DemandRequest(
        sku="SKU-42",
        avg_daily_sales=10,
        seasonality_index=1.2,
        planning_days=14,
        current_stock=20,
    )

    assert request.sku == "SKU-42"
    assert request.avg_daily_sales == 10


@pytest.mark.parametrize(
    "payload",
    [
        {"sku": "A", "avg_daily_sales": 10, "current_stock": 1},
        {"sku": "SKU-42", "avg_daily_sales": 0, "current_stock": 1},
        {"sku": "SKU-42", "avg_daily_sales": 10, "current_stock": -1},
    ],
)
def test_demand_request_rejects_invalid_payload(payload: dict) -> None:
    with pytest.raises(ValidationError):
        DemandRequest(**payload)
