"""Tests for prediction and model-info API endpoints."""

from __future__ import annotations


REQUIRED_PREDICTION_FIELDS = {
    "estimated_price_lakhs",
    "estimated_price_inr",
    "estimated_low_lakhs",
    "estimated_high_lakhs",
    "estimated_low_inr",
    "estimated_high_inr",
    "price_per_sqft",
    "model",
    "model_version",
    "disclaimer",
    "range_note",
    "prediction_id",
    "saved",
}


def test_valid_prediction(client, valid_payload):
    response = client.post("/api/predict", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    assert "estimated_price_lakhs" in data
    assert "estimated_price_inr" in data
    assert data["model"]
    assert data["model_version"]
    assert "disclaimer" in data


def test_prediction_returns_positive_price(client, valid_payload):
    data = client.post("/api/predict", json=valid_payload).json()
    assert data["estimated_price_lakhs"] > 0
    assert data["estimated_price_inr"] > 0


def test_prediction_inr_conversion(client, valid_payload):
    data = client.post("/api/predict", json=valid_payload).json()
    expected_inr = int(round(data["estimated_price_lakhs"] * 100_000))
    assert data["estimated_price_inr"] == expected_inr


def test_range_is_ordered(client, valid_payload):
    data = client.post("/api/predict", json=valid_payload).json()
    assert (
        data["estimated_low_lakhs"]
        <= data["estimated_price_lakhs"]
        <= data["estimated_high_lakhs"]
    )
    assert (
        data["estimated_low_inr"]
        <= data["estimated_price_inr"]
        <= data["estimated_high_inr"]
    )


def test_unseen_location_does_not_crash(client, valid_payload):
    payload = {**valid_payload, "location": "Completely Fake Layout ZZ99"}
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["estimated_price_lakhs"] > 0


def test_invalid_square_footage_rejected(client, valid_payload):
    payload = {**valid_payload, "total_sqft": 0}
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_invalid_bhk_rejected(client, valid_payload):
    payload = {**valid_payload, "bhk": 0}
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_model_info_endpoint(client):
    response = client.get("/api/model-info")
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"]
    assert data["model_version"]
    assert data["target_name"] == "price"
    assert data["target_unit"] == "INR_lakhs"
    assert isinstance(data["features"], list)
    assert "test_mae" in data
    assert "limitations" in data
    # Do not leak filesystem paths
    assert "dataset_path" not in data
    assert "artifact_paths" not in data
    blob = str(data).lower()
    assert "house_price_model.pkl" not in blob
    assert "permutation_importance_raw_features.csv" not in blob
    assert "c:\\users" not in blob
    assert "/users/" not in blob


def test_model_info_evaluation_metadata(client):
    data = client.get("/api/model-info").json()

    # Existing fields remain present
    for key in (
        "model_name",
        "model_version",
        "features",
        "test_mae",
        "test_rmse",
        "test_r2",
        "cv_mae",
        "cv_mae_std",
        "train_size",
        "test_size",
        "prediction_range",
        "disclaimer",
    ):
        assert key in data

    assert data["selection_rule"]
    assert "mae" in data["selection_rule"].lower()

    assert data["has_property_date"] is False

    units = data["metric_units"]
    assert units["mae"] == "INR_lakhs"
    assert units["rmse"] == "INR_lakhs"
    assert units["r2"] == "unitless"

    held = data["held_out_test_metrics"]
    assert held["scope"] == "held_out_test_split"
    assert held["mae"] == data["test_mae"]
    assert held["rmse"] == data["test_rmse"]
    assert held["r2"] == data["test_r2"]
    assert "inr lakhs" in held["unit_note"].lower()

    comparison = data["model_comparison"]
    assert comparison["scope"] == "cross_validation_on_training_split"
    assert comparison["selection_rule"] == data["selection_rule"]
    assert "cross-validated" in comparison["unit_note"].lower()
    models = comparison["models"]
    assert isinstance(models, list)
    assert len(models) >= 3
    names = {row["model_name"] for row in models}
    assert "RandomForestRegressor" in names
    assert "HistGradientBoostingRegressor" in names
    assert "LinearRegression" in names
    selected = [row for row in models if row.get("selected")]
    assert len(selected) == 1
    assert selected[0]["model_name"] == data["model_name"]
    for row in models:
        assert "cv_mae_mean" in row
        assert "cv_r2_mean" in row

    # Comparison metrics must match stored metadata (not invented UI constants).
    from ml.model_service import get_model_service

    meta = get_model_service().metadata
    for row in models:
        stored = meta["cv_metrics"][row["model_name"]]
        assert row["cv_mae_mean"] == stored["cv_mae_mean"]
        assert row["cv_r2_mean"] == stored["cv_r2_mean"]

    pr = data["prediction_range"]
    assert pr["method"] == "out_of_fold_residual_percentiles"
    assert pr["supported"] is True
    assert "confidence interval" in pr["description"].lower()
    assert "not a statistical confidence interval" in pr["description"].lower()
    assert "residual_p10_lakhs" in pr
    assert "residual_p90_lakhs" in pr
    assert pr["residual_p10_lakhs"] == meta["prediction_range"]["residual_p10_lakhs"]
    assert pr["residual_p90_lakhs"] == meta["prediction_range"]["residual_p90_lakhs"]
    # Do not claim formal prediction/probability intervals in description.
    assert "probability interval" not in pr["description"].lower()
    assert "formal prediction interval" not in pr["description"].lower()


def test_model_info_includes_global_explanation(client):
    data = client.get("/api/model-info").json()
    explanation = data["explanation"]
    assert explanation["type"] == "global_feature_influence"
    assert explanation["scope"] == "model"
    assert explanation["method"] == "permutation_importance_mae"
    assert explanation["factors"]
    assert "not a breakdown of rupees" in explanation["note"].lower()


def test_guest_prediction_is_not_saved(client, valid_payload):
    response = client.post("/api/predict", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is False
    assert data["prediction_id"] is None
    assert data["estimated_price_lakhs"] > 0


def test_invalid_bearer_token_treated_as_guest(client, valid_payload):
    response = client.post(
        "/api/predict",
        json=valid_payload,
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is False
    assert data["prediction_id"] is None
    assert data["estimated_price_lakhs"] > 0


def test_authenticated_prediction_is_saved(client, valid_payload):
    email = "predict_save_user@example.com"
    password = "TestPass123"
    client.post(
        "/api/auth/register",
        json={"name": "Predict Save", "email": email, "password": password},
    )
    login = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.post(
        "/api/predict",
        json=valid_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["prediction_id"] is not None
    assert data["estimated_price_lakhs"] > 0
    assert "explanation" in data


def test_prediction_keeps_existing_fields_and_adds_explanation(client, valid_payload):
    data = client.post("/api/predict", json=valid_payload).json()
    missing = REQUIRED_PREDICTION_FIELDS - set(data)
    assert not missing, f"Missing prediction fields: {missing}"

    explanation = data["explanation"]
    assert explanation["type"] == "global_feature_influence"
    assert explanation["scope"] == "model"
    assert explanation["method"] == "permutation_importance_mae"
    assert "not a breakdown of rupees" in explanation["note"].lower()

    factors = explanation["factors"]
    assert len(factors) >= 3
    ranks = [factor["rank"] for factor in factors]
    assert ranks == sorted(ranks)
    assert ranks[0] == 1

    importances = [factor["importance"] for factor in factors]
    assert all(isinstance(value, (int, float)) for value in importances)
    assert all(value > 0 for value in importances)
    assert abs(sum(importances) - 1.0) < 1e-5
    assert factors[0]["feature"] == "total_sqft"

    blob = str(explanation).lower()
    assert "₹" not in str(explanation)
    assert "added" not in blob
    assert "contributed" not in blob
    assert "inputs_highlighted" not in explanation


def test_authenticated_history_still_returns_saved_estimate(client, valid_payload):
    email = "predict_history_explain@example.com"
    password = "TestPass123"
    client.post(
        "/api/auth/register",
        json={"name": "History Explain", "email": email, "password": password},
    )
    token = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    predict = client.post("/api/predict", json=valid_payload, headers=headers)
    assert predict.status_code == 200
    prediction_id = predict.json()["prediction_id"]

    history = client.get("/api/predict/history", headers=headers)
    assert history.status_code == 200
    items = history.json()
    assert any(item["id"] == prediction_id for item in items)
