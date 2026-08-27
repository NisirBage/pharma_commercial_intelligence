def test_forecast_valid_atc_returns_14_day_horizon(client):
    response = client.get("/api/v1/forecast/N02BE")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["atc_class"] == "N02BE"
    assert data["horizon_days"] == 14
    assert len(data["forecast"]) == 14


def test_forecast_includes_prediction_interval_fields(client):
    response = client.get("/api/v1/forecast/N02BE")
    for point in response.json()["data"]["forecast"]:
        assert set(point.keys()) == {"date", "prediction", "lower", "upper"}
        assert point["lower"] <= point["prediction"] <= point["upper"]


def test_forecast_includes_model_metadata(client):
    response = client.get("/api/v1/forecast/N02BE")
    data = response.json()["data"]
    assert data["model"] in ("ets", "moving_average_14", "naive", "seasonal_naive_7", "linear_regression", "random_forest")
    assert data["uncertainty_method"]
    assert set(data["metrics"].keys()) == {"mae", "rmse", "wape", "mase"}


def test_forecast_invalid_atc_returns_404(client):
    response = client.get("/api/v1/forecast/NOTREAL")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_aggregate_forecast_is_its_own_model_not_a_sum(client):
    """M4 found the direct aggregate model more accurate than summing
    per-class forecasts — the API must serve the direct model (M6 Sec. 12)."""
    response = client.get("/api/v1/forecast/aggregate")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["atc_class"] == "ALL"
    assert len(data["forecast"]) == 14


def test_forecast_diagnostics_valid_atc(client):
    response = client.get("/api/v1/forecast/N02BE/diagnostics")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["atc_class"] == "N02BE"
    assert "residual_diagnostics" in data
    assert "limitations" in data
    assert len(data["limitations"]) > 0


def test_forecast_diagnostics_includes_ljung_box_when_available(client):
    response = client.get("/api/v1/forecast/N02BE/diagnostics")
    data = response.json()["data"]
    rd = data["residual_diagnostics"]
    assert rd["n_residuals"] > 0
    if rd["ljung_box"] is not None:
        assert "autocorrelation_detected" in rd["ljung_box"]


def test_forecast_diagnostics_performance_by_horizon_step(client):
    response = client.get("/api/v1/forecast/N02BE/diagnostics")
    steps = response.json()["data"]["performance_by_horizon_step"]
    assert len(steps) == 14
    assert steps[0]["horizon_step"] == 1


def test_forecast_diagnostics_invalid_atc_returns_404(client):
    response = client.get("/api/v1/forecast/NOTREAL/diagnostics")
    assert response.status_code == 404
