def test_seasonality_aggregate_response_schema(client):
    response = client.get("/api/v1/analytics/seasonality")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["atc_class"] == "ALL"
    for field in ("day_of_week_effect", "hour_of_day_effect", "weekly_seasonal_strength", "annual_seasonal_strength"):
        assert field in data


def test_seasonality_day_of_week_effect_detected_on_synthetic_pattern(client):
    """The synthetic fixture's units_sold = base + day_of_week is a real,
    deterministic weekday effect — this must be detected as significant,
    not just structurally present."""
    response = client.get("/api/v1/analytics/seasonality")
    dow = response.json()["data"]["day_of_week_effect"]
    assert dow["available"] is True
    assert dow["significant"] is True
    assert dow["mean_units_by_weekday"] is not None
    assert len(dow["mean_units_by_weekday"]) == 7


def test_seasonality_hour_of_day_effect_unavailable_with_single_hour_fixture(client):
    """The synthetic fixture only has one observation hour per day (10:00)
    -- hour-of-day effect genuinely cannot be computed from a single
    group, and that must be reported honestly as unavailable, not
    silently defaulted to some value."""
    response = client.get("/api/v1/analytics/seasonality")
    hod = response.json()["data"]["hour_of_day_effect"]
    assert hod["available"] is False
    assert hod["reason"] == "insufficient_groups"


def test_seasonality_annual_strength_unavailable_with_short_synthetic_history(client):
    """60 days of synthetic history is far short of the 24 months needed
    for annual (period=12, monthly grain) STL decomposition."""
    response = client.get("/api/v1/analytics/seasonality")
    annual = response.json()["data"]["annual_seasonal_strength"]
    assert annual["available"] is False
    assert annual["reason"] == "insufficient_periods"


def test_seasonality_weekly_strength_available_with_60_days(client):
    """60 days >= 2*7, enough for a weekly (period=7) STL fit."""
    response = client.get("/api/v1/analytics/seasonality")
    weekly = response.json()["data"]["weekly_seasonal_strength"]
    assert weekly["available"] is True
    assert weekly["cycle_period"] == 7
    assert 0.0 <= weekly["strength"] <= 1.0


def test_seasonality_filters_by_atc_class(client):
    response = client.get("/api/v1/analytics/seasonality", params={"atc_class": "N02BE"})
    assert response.status_code == 200
    assert response.json()["data"]["atc_class"] == "N02BE"


def test_seasonality_invalid_atc_returns_404(client):
    response = client.get("/api/v1/analytics/seasonality", params={"atc_class": "NOTREAL"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
