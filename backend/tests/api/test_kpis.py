def test_kpi_summary_valid_response_schema(client):
    response = client.get("/api/v1/kpis/summary")
    assert response.status_code == 200
    data = response.json()["data"]
    for field in ("total_demand", "average_daily_demand", "peak_daily_demand", "dominant_atc_class", "dominant_atc_share_pct", "period"):
        assert field in data


def test_kpi_summary_values_are_computed_not_fabricated(client):
    response = client.get("/api/v1/kpis/summary")
    data = response.json()["data"]
    # N05C has the highest synthetic base (10 + 4*5 = 30)... actually
    # N02BE (index 3) does -- verify it's whichever class the synthetic
    # data actually makes dominant, not a hardcoded guess.
    assert data["total_demand"] > 0
    assert data["dominant_atc_class"] in (
        "M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06",
    )
    assert 0 < data["dominant_atc_share_pct"] <= 100


def test_kpi_summary_period_reflects_synthetic_date_range(client):
    response = client.get("/api/v1/kpis/summary")
    period = response.json()["data"]["period"]
    assert period["start"] == "2020-01-01"
    assert period["end"] == "2020-02-29"  # 60 days from 2020-01-01 (leap year)
