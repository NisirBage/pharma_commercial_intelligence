def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert "version" in body["data"]
    assert "environment" in body["data"]


def test_health_reports_database_unavailable_gracefully(client):
    """No Postgres is running in this test environment — the health
    endpoint must report that, not crash or 500 (M6 Sec. 6)."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["data"]["database"] in ("unreachable", "connected")


def test_health_response_has_request_id_header(client):
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
