def test_atc_performance_returns_all_8_classes(client):
    response = client.get("/api/v1/analytics/atc")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["classes"]) == 8
    assert len(data["dominant_classes"]) == 3
    assert "hhi" in data["concentration"]


def test_atc_performance_each_class_has_required_fields(client):
    response = client.get("/api/v1/analytics/atc")
    data = response.json()["data"]
    for entry in data["classes"]:
        for field in ("atc_class", "total_demand", "trend_classification", "volatility_cv"):
            assert field in entry


def test_anomalies_valid_response_schema(client):
    response = client.get("/api/v1/analytics/anomalies")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "anomalies" in data
    assert data["total_count"] == len(data["anomalies"])


def test_anomalies_filter_by_atc(client):
    response = client.get("/api/v1/analytics/anomalies", params={"atc_class": "N05C"})
    assert response.status_code == 200
    for a in response.json()["data"]["anomalies"]:
        assert a["atc_class"] == "N05C"


def test_anomalies_invalid_atc_returns_404(client):
    response = client.get("/api/v1/analytics/anomalies", params={"atc_class": "NOPE"})
    assert response.status_code == 404


def test_anomalies_invalid_severity_returns_400(client):
    response = client.get("/api/v1/analytics/anomalies", params={"severity": "catastrophic"})
    assert response.status_code == 400


def test_anomalies_invalid_method_returns_422(client):
    response = client.get("/api/v1/analytics/anomalies", params={"method": "neural_net"})
    assert response.status_code == 422


def test_anomalies_iqr_method(client):
    response = client.get("/api/v1/analytics/anomalies", params={"method": "iqr"})
    assert response.status_code == 200
    assert response.json()["data"]["method"] == "iqr"
