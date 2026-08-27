"""The one integration path proving the API can reach the REAL cached
data/model layer (M6 Sec. 30) — not the synthetic fixtures used by
tests/api/. Deliberately placed OUTSIDE tests/api/ so it does NOT inherit
that package's autouse cache-patching fixture (tests/api/conftest.py).

Skipped gracefully if the real raw CSVs or the M4 model registry aren't
present locally (a fresh clone that hasn't run scripts/download_data.py
and scripts/run_m4_backtest.py yet) — matching this project's established
convention (M2-M5) of never requiring real downloaded data for the base
test suite.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.forecasting.registry import REGISTRY_DIR
from app.main import app
from app.services import cache as cache_module

_raw_data_present = (settings.raw_data_dir / "saleshourly.csv").exists()
_registry_present = REGISTRY_DIR.exists() and any(REGISTRY_DIR.glob("*.json"))

pytestmark = pytest.mark.skipif(
    not (_raw_data_present and _registry_present),
    reason="Real raw data / M4 model registry not present locally — run scripts/download_data.py and scripts/run_m4_backtest.py first.",
)


@pytest.fixture
def real_client():
    cache_module.clear_all_caches()
    yield TestClient(app)
    cache_module.clear_all_caches()


def test_kpi_summary_against_real_data(real_client):
    response = real_client.get("/api/v1/kpis/summary")
    assert response.status_code == 200
    data = response.json()["data"]
    # Matches M3's documented finding exactly (docs/business-insights.md).
    assert data["dominant_atc_class"] == "N02BE"
    assert 49.0 < data["dominant_atc_share_pct"] < 50.0


def test_forecast_against_real_registry(real_client):
    response = real_client.get("/api/v1/forecast/N02BE")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["model"] == "moving_average_14"  # M4's actual documented selection
    assert len(data["forecast"]) == 14


def test_aggregate_forecast_against_real_registry(real_client):
    response = real_client.get("/api/v1/forecast/aggregate")
    assert response.status_code == 200
    assert response.json()["data"]["model"] == "ets"  # M4's actual documented selection for ALL


def test_optimization_run_against_real_data_matches_m5_report(real_client):
    response = real_client.post("/api/v1/optimization/run", json={"scenario": "balanced"})
    assert response.status_code == 200
    data = response.json()["data"]
    # docs/optimization-methodology.md documents the balanced-scenario budget as 103.66 units.
    assert 100 < data["capacity_budget"] < 110
    assert 40 < data["improvement_pct"] < 55


def test_data_quality_against_real_data_preserves_monthly_warning(real_client):
    response = real_client.get("/api/v1/data-quality")
    assert response.status_code == 200
    data = response.json()["data"]
    monthly = next(r for r in data["reconciliation"] if r["label"] == "Monthly")
    assert monthly["reconciled"] is False
