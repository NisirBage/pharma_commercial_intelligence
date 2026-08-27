def test_data_quality_response_schema(client):
    response = client.get("/api/v1/data-quality")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["kaggle_dataset_id"] == "milanzdravkovic/pharma-sales-data"
    assert len(data["file_summaries"]) == 4
    assert len(data["reconciliation"]) == 3


def test_data_quality_preserves_monthly_inconsistency_warning(client):
    """The documented salesmonthly.csv defect must never be hidden for
    presentation purposes (M6 Sec. 19)."""
    response = client.get("/api/v1/data-quality")
    data = response.json()["data"]
    monthly = next(r for r in data["reconciliation"] if r["label"] == "Monthly")
    assert monthly["reconciled"] is False
    assert monthly["status"] == "warn"
    assert "does not reconcile" in data["monthly_inconsistency_warning"].lower()
    assert "salesmonthly.csv" in data["monthly_inconsistency_warning"]


def test_data_quality_daily_and_weekly_reconciled(client):
    response = client.get("/api/v1/data-quality")
    data = response.json()["data"]
    daily = next(r for r in data["reconciliation"] if r["label"] == "Daily")
    weekly = next(r for r in data["reconciliation"] if r["label"] == "Weekly")
    assert daily["reconciled"] is True
    assert weekly["reconciled"] is True


def test_data_quality_overall_status_reflects_warn(client):
    response = client.get("/api/v1/data-quality")
    assert response.json()["data"]["overall_status"] == "warn"
