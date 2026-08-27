def test_sales_trends_valid_atc(client):
    response = client.get("/api/v1/sales/trends", params={"atc_class": "N02BE", "grain": "daily"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["atc_class"] == "N02BE"
    assert data["grain"] == "daily"
    assert len(data["points"]) == 60  # 60 synthetic days


def test_sales_trends_aggregate_when_no_atc_given(client):
    response = client.get("/api/v1/sales/trends")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["atc_class"] is None
    assert len(data["points"]) == 60


def test_sales_trends_invalid_atc_returns_404(client):
    response = client.get("/api/v1/sales/trends", params={"atc_class": "ZZZZZ"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_sales_trends_invalid_date_format_returns_400(client):
    response = client.get("/api/v1/sales/trends", params={"start_date": "not-a-date"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_sales_trends_start_after_end_returns_400(client):
    response = client.get("/api/v1/sales/trends", params={"start_date": "2020-02-01", "end_date": "2020-01-01"})
    assert response.status_code == 400


def test_sales_trends_empty_result_for_out_of_range_dates(client):
    response = client.get("/api/v1/sales/trends", params={"start_date": "2099-01-01", "end_date": "2099-01-31"})
    assert response.status_code == 200
    assert response.json()["data"]["points"] == []


def test_sales_trends_weekly_grain(client):
    response = client.get("/api/v1/sales/trends", params={"grain": "weekly"})
    assert response.status_code == 200
    assert response.json()["data"]["grain"] == "weekly"


def test_sales_trends_invalid_grain_returns_422(client):
    response = client.get("/api/v1/sales/trends", params={"grain": "yearly"})
    assert response.status_code == 422
