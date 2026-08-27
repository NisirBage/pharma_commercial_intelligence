"""Contract tests (M6 Sec. 31): Pydantic schemas must match actual
service outputs, response serialization must not silently drop fields,
dates must serialize as strings, and NaN/Infinity/numpy scalar types must
never leak into a JSON response.
"""

import json

from app.schemas.common import _sanitize_float


def test_sanitize_float_converts_nan_and_inf_to_none():
    assert _sanitize_float(float("nan")) is None
    assert _sanitize_float(float("inf")) is None
    assert _sanitize_float(float("-inf")) is None
    assert _sanitize_float(3.14) == 3.14
    assert _sanitize_float(None) is None


def test_all_endpoints_produce_valid_strict_json(client):
    endpoints = [
        ("GET", "/health"),
        ("GET", "/api/v1/kpis/summary"),
        ("GET", "/api/v1/sales/trends"),
        ("GET", "/api/v1/analytics/atc"),
        ("GET", "/api/v1/analytics/anomalies"),
        ("GET", "/api/v1/analytics/seasonality"),
        ("GET", "/api/v1/forecast/N02BE"),
        ("GET", "/api/v1/forecast/aggregate"),
        ("GET", "/api/v1/forecast/N02BE/diagnostics"),
        ("GET", "/api/v1/optimization/scenarios"),
        ("GET", "/api/v1/recommendations"),
        ("GET", "/api/v1/data-quality"),
    ]
    for method, path in endpoints:
        response = client.request(method, path)
        assert response.status_code == 200, f"{method} {path} -> {response.status_code}: {response.text[:200]}"
        assert "NaN" not in response.text, f"{path} leaked a NaN token"
        assert "Infinity" not in response.text, f"{path} leaked an Infinity token"
        json.loads(response.text)  # must not raise


def test_optimization_run_produces_valid_strict_json(client):
    response = client.post("/api/v1/optimization/run", json={"scenario": "balanced"})
    assert response.status_code == 200
    assert "NaN" not in response.text
    assert "Infinity" not in response.text
    json.loads(response.text)


def test_forecast_dates_serialize_as_iso_date_strings(client):
    response = client.get("/api/v1/forecast/N02BE")
    for point in response.json()["data"]["forecast"]:
        assert isinstance(point["date"], str)
        year, month, day = point["date"].split("-")
        assert len(year) == 4
        assert len(month) == 2
        assert len(day) == 2


def test_numpy_and_pandas_scalars_coerce_to_native_json_numbers(client):
    """app.analytics/app.forecasting/app.optimization return plenty of
    numpy float64/int64 values internally — this proves they reach the
    client as plain JSON numbers, not unserializable/opaque objects."""
    response = client.get("/api/v1/analytics/atc")
    data = response.json()["data"]
    assert len(data["classes"]) > 0
    for entry in data["classes"]:
        assert isinstance(entry["total_demand"], (int, float))
        assert entry["volatility_cv"] is None or isinstance(entry["volatility_cv"], (int, float))


def test_anomaly_deviation_pct_infinity_case_sanitized(client):
    """app.analytics.anomalies explicitly returns float('inf') for
    deviation_pct when the baseline mean is exactly 0 — this must never
    reach the client as a raw Infinity token."""
    response = client.get("/api/v1/analytics/anomalies", params={"method": "rolling_zscore"})
    assert response.status_code == 200
    assert "Infinity" not in response.text
    for a in response.json()["data"]["anomalies"]:
        assert a["deviation_pct"] is None or isinstance(a["deviation_pct"], (int, float))
