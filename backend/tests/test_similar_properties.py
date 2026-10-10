"""Tests for GET /api/properties/similar and similarity scoring."""

from __future__ import annotations

import pytest

from ml.similar_properties import (
    FEATURE_WEIGHTS,
    SimilarPropertiesService,
    get_similar_properties_service,
    reset_similar_properties_service,
)
from models import Prediction
from database import SessionLocal


WHITEFIELD_PARAMS = {
    "area_type": "Super built-up  Area",
    "location": "Whitefield",
    "total_sqft": 1200,
    "bhk": 2,
    "bath": 2,
    "balcony": 1,
    "is_ready_to_move": True,
}


def _similar_get(client, params=None, **extra):
    query = {**(params or WHITEFIELD_PARAMS), **extra}
    return client.get("/api/properties/similar", params=query)


@pytest.fixture(autouse=True)
def _reset_similar_singleton():
    reset_similar_properties_service()
    yield
    reset_similar_properties_service()


def test_whitefield_query_returns_results(client):
    response = _similar_get(client)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "weighted_feature_distance"
    assert data["count"] == len(data["results"])
    assert data["count"] > 0
    assert data["count"] <= 5
    assert "historical listing" in data["disclaimer"].lower() or "dataset" in data[
        "disclaimer"
    ].lower()


def test_same_query_is_deterministic(client):
    first = _similar_get(client).json()["results"]
    second = _similar_get(client).json()["results"]
    assert first == second


def test_result_count_never_exceeds_limit(client):
    data = _similar_get(client, limit=3).json()
    assert data["count"] <= 3
    assert len(data["results"]) <= 3


def test_limit_validation(client):
    assert _similar_get(client, limit=0).status_code == 422
    assert _similar_get(client, limit=11).status_code == 422


def test_min_similarity_validation(client):
    assert _similar_get(client, min_similarity=-0.1).status_code == 422
    assert _similar_get(client, min_similarity=1.1).status_code == 422


def test_results_contain_expected_fields(client):
    data = _similar_get(client).json()
    expected = {
        "rank",
        "similarity",
        "location",
        "area_type",
        "total_sqft",
        "bhk",
        "bath",
        "balcony",
        "is_ready_to_move",
        "listed_price_lakhs",
        "listed_price_per_sqft",
        "match_notes",
        "location_match",
    }
    for item in data["results"]:
        assert expected.issubset(item.keys())
        assert set(item.keys()) == expected


def test_listed_price_is_dataset_price_not_ml_prediction(client):
    similar = _similar_get(client).json()
    predict = client.post("/api/predict", json=WHITEFIELD_PARAMS).json()
    # Similarity results expose listed_price_lakhs; predict uses estimated_price_lakhs.
    assert "estimated_price_lakhs" not in similar
    for item in similar["results"]:
        assert "estimated_price" not in item
        assert item["listed_price_lakhs"] > 0
        # Not required to differ, but field naming must stay listing-oriented.
        assert "listed_price_lakhs" in item
    assert predict["estimated_price_lakhs"] > 0


def test_price_does_not_influence_similarity_ranking():
    service = get_similar_properties_service()
    assert service.loaded
    query = service.normalize_query(WHITEFIELD_PARAMS)
    row = service.frame.iloc[0]
    base = service.weighted_distance(query, row)
    mutated = row.copy()
    mutated["price"] = float(row["price"]) * 50 + 9999
    mutated["price_per_sqft"] = float(row.get("price_per_sqft") or 1) * 50
    assert service.weighted_distance(query, mutated) == base
    assert "price" not in FEATURE_WEIGHTS


def test_exact_location_is_preferred(client):
    data = _similar_get(client, limit=5).json()
    assert data["count"] > 0
    # Whitefield has many listings; top results should match location.
    top = data["results"][0]
    assert top["location_match"] is True
    assert top["location"].lower() == "whitefield"
    assert "same_location" in top["match_notes"]


def test_similar_sqft_preferred_over_wildly_different(client):
    data = _similar_get(client, limit=5, total_sqft=1200).json()
    assert data["count"] > 0
    for item in data["results"]:
        ratio = abs(item["total_sqft"] - 1200) / 1200
        assert ratio <= 0.50 + 1e-9


def test_bhk_difference_handled(client):
    data = _similar_get(client, limit=5, bhk=2).json()
    assert data["count"] > 0
    for item in data["results"]:
        assert abs(item["bhk"] - 2) <= 2 + 1e-9


def test_missing_balcony_handled_safely():
    service = get_similar_properties_service()
    null_balcony = service.frame[service.frame["balcony"].isna()]
    assert not null_balcony.empty
    query = service.normalize_query({**WHITEFIELD_PARAMS, "balcony": 1})
    row = null_balcony.iloc[0]
    distance = service.weighted_distance(query, row)
    assert distance >= 0
    sim = service.distance_to_similarity(distance)
    assert 0.0 <= sim <= 1.0


def test_unknown_location_empty_or_documented_fallback(client):
    response = _similar_get(
        client,
        location="Completely Unknown Layout XYZ999",
        limit=5,
    )
    assert response.status_code == 200
    data = response.json()
    if data["count"] == 0:
        assert data["results"] == []
        assert "message" in data
        assert "not found" in data["message"].lower() or "similar" in data["message"].lower()
    else:
        # Controlled fallback only — never pretend the query location matched.
        assert all(item["location_match"] is False for item in data["results"])
        assert all("location_fallback" in item["match_notes"] for item in data["results"])


def test_no_duplicate_feature_tuples(client):
    data = _similar_get(client, limit=10).json()
    tuples = [
        (
            item["location"],
            item["area_type"],
            round(item["total_sqft"], 4),
            round(item["bhk"], 4),
            round(item["bath"], 4),
            item["balcony"],
            item["is_ready_to_move"],
        )
        for item in data["results"]
    ]
    assert len(tuples) == len(set(tuples))


def test_guest_access_works(client):
    response = _similar_get(client)
    assert response.status_code == 200
    # No auth headers used above.


def test_endpoint_does_not_write_prediction_history(client):
    db = SessionLocal()
    try:
        before = db.query(Prediction).count()
    finally:
        db.close()

    assert _similar_get(client).status_code == 200

    db = SessionLocal()
    try:
        after = db.query(Prediction).count()
    finally:
        db.close()
    assert after == before


def test_missing_dataset_returns_503(client, tmp_path):
    reset_similar_properties_service()
    missing = tmp_path / "does_not_exist.csv"
    service = SimilarPropertiesService(dataset_path=missing)
    assert service.loaded is False

    # Point singleton at the failed service and hit the API.
    import ml.similar_properties as similar_mod

    similar_mod._service = service
    response = _similar_get(client)
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()
    # Do not leak filesystem paths.
    assert "does_not_exist" not in response.text
    assert str(tmp_path) not in response.text


def test_similarity_scores_within_unit_interval(client):
    data = _similar_get(client, limit=10).json()
    for item in data["results"]:
        assert 0.0 <= item["similarity"] <= 1.0


def test_results_sorted_descending_by_similarity(client):
    data = _similar_get(client, limit=10).json()
    scores = [item["similarity"] for item in data["results"]]
    assert scores == sorted(scores, reverse=True)
    ranks = [item["rank"] for item in data["results"]]
    assert ranks == list(range(1, len(ranks) + 1))


def test_limit_one_and_ten(client):
    one = _similar_get(client, limit=1).json()
    ten = _similar_get(client, limit=10).json()
    assert one["count"] <= 1
    assert len(one["results"]) <= 1
    assert ten["count"] <= 10
    assert len(ten["results"]) <= 10


def test_high_min_similarity_may_return_fewer(client):
    data = _similar_get(client, limit=5, min_similarity=0.99).json()
    assert data["count"] <= 5
    for item in data["results"]:
        assert item["similarity"] >= 0.99


def test_invalid_dimensions_rejected(client):
    assert _similar_get(client, total_sqft=0).status_code == 422
    assert _similar_get(client, bhk=0).status_code == 422
    assert _similar_get(client, bath=0).status_code == 422
    assert _similar_get(client, balcony=-1).status_code == 422


def test_predict_and_model_info_unchanged(client):
    predict = client.post("/api/predict", json=WHITEFIELD_PARAMS)
    assert predict.status_code == 200
    assert "estimated_price_lakhs" in predict.json()

    info = client.get("/api/model-info")
    assert info.status_code == 200
    assert info.json()["model_name"]

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    market = client.get("/api/market/overview")
    assert market.status_code == 200
