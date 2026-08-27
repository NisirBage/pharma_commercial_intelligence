def test_recommendations_response_schema(client):
    response = client.get("/api/v1/recommendations")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["scenario"] == "balanced"
    assert len(data["recommendations"]) == 8


def test_recommendations_have_evidence_and_assumptions(client):
    response = client.get("/api/v1/recommendations")
    for rec in response.json()["data"]["recommendations"]:
        assert len(rec["evidence"]) > 0
        assert len(rec["assumptions"]) > 0
        assert rec["confidence"] in ("low", "medium", "medium-high")


def test_recommendations_have_limitations(client):
    response = client.get("/api/v1/recommendations")
    for rec in response.json()["data"]["recommendations"]:
        assert len(rec["limitations"]) > 0
        assert any("Kaggle" in lim for lim in rec["limitations"])


def test_recommendations_n02be_mentions_exposure_not_risk(client):
    response = client.get("/api/v1/recommendations")
    recs = {r["atc_class"]: r for r in response.json()["data"]["recommendations"]}
    assert "PLANNING EXPOSURE" in recs["N02BE"]["recommendation"] or "planning exposure" in recs["N02BE"]["recommendation"].lower()


def test_recommendations_respects_scenario_query_param(client):
    response = client.get("/api/v1/recommendations", params={"scenario": "lean"})
    assert response.status_code == 200
    assert response.json()["data"]["scenario"] == "lean"


def test_recommendations_invalid_scenario_returns_422(client):
    response = client.get("/api/v1/recommendations", params={"scenario": "extreme"})
    assert response.status_code == 422
