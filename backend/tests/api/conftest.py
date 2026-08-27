"""API test fixtures. Every test in this package runs against small,
synthetic, in-memory data — never the real CSVs or the real M4 model
registry (M6 Sec. 30, test isolation). This is possible because the
service layer accesses `app.services.cache` module-qualified
(`cache.get_x()`, not `from ... import get_x`), so monkeypatching the
cache module's functions here correctly reaches every consumer.

See tests/api/test_integration_real_data.py for the one path that DOES
exercise the real cached data layer (skipped gracefully if the real data/
registry aren't present locally — M6 Sec. 30's "at least one integration
path" requirement).
"""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.forecasting.predictions import ForecastOutput
from app.main import app
from app.services import cache as cache_module
from tests.unit.analytics.helpers import make_frame
from tests.unit.optimization.helpers import make_demand_input

ATC_CLASSES = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]


def _synthetic_fold_results() -> list[dict]:
    return [
        {"residuals": [1.0, -1.0, 2.0, -2.0, 0.5, -0.5, 1.5, 1.0, -1.0, 2.0, -2.0, 0.5, -0.5, 1.5]},
        {"residuals": [0.5, -0.5, 1.0, -1.0, 0.2, -0.2, 0.8, 0.5, -0.5, 1.0, -1.0, 0.2, -0.2, 0.8]},
    ]


def build_synthetic_canonical_frame() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=60, freq="D")
    rows = []
    for i, atc in enumerate(ATC_CLASSES):
        base = 10.0 + i * 5
        for d in dates:
            rows.append(
                {"atc_code": atc, "observation_ts": d + pd.Timedelta(hours=10), "units_sold": base + d.dayofweek}
            )
    return make_frame(rows)


def _synthetic_forecast_output(atc: str, model: str, base: float) -> ForecastOutput:
    dates = pd.date_range("2020-03-01", periods=14, freq="D")
    predictions = [
        {"date": str(d.date()), "point_forecast": base, "lower_bound": base * 0.7, "upper_bound": base * 1.3}
        for d in dates
    ]
    return ForecastOutput(
        atc_class=atc,
        forecast_grain="daily",
        horizon=14,
        model=model,
        predictions=predictions,
        uncertainty_method="residual_based_backtest_quantile",
        evaluation={"mae": 1.0, "rmse": 1.5, "wape": 25.0, "mase": 0.7},
    )


def build_synthetic_demand_inputs() -> dict:
    inputs = {}
    for i, atc in enumerate(ATC_CLASSES):
        base = 10.0 + i * 5
        model = "ets" if i % 2 == 0 else "moving_average_14"
        di = make_demand_input(atc, model=model, point_forecast=[base] * 14, residual_std=base * 0.2, wape=25.0 + i)
        di.fold_results = _synthetic_fold_results()
        di.forecast_output = _synthetic_forecast_output(atc, model, base)
        inputs[atc] = di

    aggregate = make_demand_input("ALL", model="ets", point_forecast=[100.0] * 14, residual_std=15.0, wape=16.27)
    aggregate.fold_results = _synthetic_fold_results()
    aggregate.forecast_output = _synthetic_forecast_output("ALL", "ets", 100.0)
    inputs["ALL"] = aggregate
    return inputs


def build_synthetic_quality_report() -> dict:
    return {
        "overall_status": "warn",
        "file_summaries": [
            {"file_name": "saleshourly.csv", "total_records": 100, "valid_records": 100, "rejected_records": 0},
            {"file_name": "salesdaily.csv", "total_records": 10, "valid_records": 10, "rejected_records": 0},
            {"file_name": "salesweekly.csv", "total_records": 2, "valid_records": 2, "rejected_records": 0},
            {"file_name": "salesmonthly.csv", "total_records": 1, "valid_records": 1, "rejected_records": 0},
        ],
    }


def build_synthetic_reconciliation_report() -> dict:
    return {
        "summary": {
            "Daily": {"reconciled": True, "status": "pass", "details": {}},
            "Weekly": {"reconciled": True, "status": "pass", "details": {}},
            "Monthly": {"reconciled": False, "status": "warn", "details": {"n_cell_mismatches": 1}},
        },
        "human_readable": "Daily:\nReconciled ✓\n\nWeekly:\nReconciled ✓\n\nMonthly:\nSource inconsistency detected ⚠",
        "all_reconciled_except_known_monthly_issue": True,
    }


@pytest.fixture
def synthetic_frame() -> pd.DataFrame:
    return build_synthetic_canonical_frame()


@pytest.fixture
def synthetic_demand_inputs() -> dict:
    return build_synthetic_demand_inputs()


@pytest.fixture(autouse=True)
def patched_cache(monkeypatch, synthetic_frame, synthetic_demand_inputs):
    monkeypatch.setattr(cache_module, "get_canonical_frame", lambda: synthetic_frame)
    monkeypatch.setattr(cache_module, "get_demand_inputs", lambda: synthetic_demand_inputs)
    monkeypatch.setattr(cache_module, "get_contributions", lambda: {atc: 100 / len(ATC_CLASSES) for atc in ATC_CLASSES})
    monkeypatch.setattr(cache_module, "get_quality_report", build_synthetic_quality_report)
    monkeypatch.setattr(cache_module, "get_reconciliation_report", build_synthetic_reconciliation_report)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
