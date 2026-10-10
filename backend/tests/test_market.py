"""Tests for the market-history insights API."""

from __future__ import annotations


SUPPORTED = {"Devanahalli", "Indiranagar", "Whitefield", "Yelahanka"}


def test_market_overview(client):
    response = client.get("/api/market/overview")
    assert response.status_code == 200
    data = response.json()
    assert set(data["supported_areas"]) == SUPPORTED
    assert data["total_observations"] > 0
    assert data["metric"] == "avg_price_per_sqft"
    assert len(data["comparisons"]) == 4
    assert "disclaimer" in data
    for row in data["comparisons"]:
        assert row["area"] in SUPPORTED
        assert row["latest_avg_price_per_sqft"] > 0
        assert row["observations"] > 0


def test_market_history_supported_area(client):
    response = client.get("/api/market/history", params={"area": "Whitefield"})
    assert response.status_code == 200
    data = response.json()
    assert data["supported"] is True
    assert data["area"] == "Whitefield"
    assert len(data["series"]) > 0
    first = data["series"][0]
    assert "date" in first
    assert first["avg_price_per_sqft"] > 0


def test_market_history_unsupported_area(client):
    response = client.get(
        "/api/market/history",
        params={"area": "Koramangala"},
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "not currently available" in detail.lower()
