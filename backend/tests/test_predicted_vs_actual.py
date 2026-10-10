"""Tests for predicted-vs-actual evaluation export and API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.export_test_predictions import (
    ALLOWED_POINT_KEYS,
    ARTIFACT_PATH,
    ExportError,
    build_artifact,
    export_predicted_vs_actual,
    sha256_file,
)
from ml.model_evaluation import get_predicted_vs_actual
from ml.model_service import get_model_service
from ml.train_model import METADATA_PATH, PROCESSED_CSV


@pytest.fixture(scope="module")
def artifact():
    # Generate once for the test module against the real production model.
    return export_predicted_vs_actual()


def test_export_produces_exact_test_size(artifact):
    meta = get_model_service().metadata
    assert artifact["point_count"] == 2536
    assert artifact["point_count"] == int(meta["test_size"])
    assert len(artifact["points"]) == 2536


def test_actual_and_predicted_lengths_match(artifact):
    assert len(artifact["points"]) == artifact["point_count"]
    for point in artifact["points"]:
        assert "actual_price_lakhs" in point
        assert "predicted_price_lakhs" in point


def test_artifact_points_only_allowed_fields(artifact):
    for point in artifact["points"]:
        assert set(point.keys()) == ALLOWED_POINT_KEYS


def test_no_identifying_columns(artifact):
    assert "dataset_path" not in artifact
    assert "artifact_paths" not in artifact
    for point in artifact["points"]:
        assert set(point.keys()) == {"actual_price_lakhs", "predicted_price_lakhs"}
    blob = json.dumps(artifact).lower()
    assert "house_price_model.pkl" not in blob
    assert "dataset_path" not in blob
    assert "c:\\users" not in blob


def test_export_fails_closed_on_metric_mismatch():
    meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    with pytest.raises(ExportError, match="do not match model metadata"):
        build_artifact(
            metadata={
                **meta,
                "test_size": 2,
                "final_test_metrics": {"mae": 0.0, "rmse": 0.0, "r2": 0.0},
            },
            y_test=[1.0, 2.0],
            y_pred=__import__("numpy").asarray([1.1, 2.2]),
            dataset_sha256="abc",
            generated_at_utc="2026-01-01T00:00:00+00:00",
        )


def test_metrics_match_metadata(artifact):
    meta = get_model_service().metadata["final_test_metrics"]
    assert artifact["metrics"]["mae"] == pytest.approx(meta["mae"], abs=1e-9)
    assert artifact["metrics"]["rmse"] == pytest.approx(meta["rmse"], abs=1e-9)
    assert artifact["metrics"]["r2"] == pytest.approx(meta["r2"], abs=1e-12)


def test_artifact_model_version_matches_metadata(artifact):
    meta = get_model_service().metadata
    assert artifact["model_version"] == meta["model_version"]
    assert artifact["model_name"] == meta["model_name"]


def test_dataset_sha256_is_correct(artifact):
    assert artifact["dataset_sha256"] == sha256_file(PROCESSED_CSV)


def test_api_available_true(client, artifact):
    response = client.get("/api/model-evaluation/predicted-vs-actual")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["point_count"] == 2536
    assert len(data["points"]) == 2536
    assert data["units"] == "INR_lakhs"
    assert data["evaluation_split"] == "held_out_test"
    assert data["model_version"] == artifact["model_version"]
    assert data["metrics"]["mae"] == pytest.approx(artifact["metrics"]["mae"])
    assert data["disclaimer"]


def test_api_response_public_fields_only(client):
    data = client.get("/api/model-evaluation/predicted-vs-actual").json()
    assert data["available"] is True
    allowed_top = {
        "available",
        "model_name",
        "model_version",
        "evaluation_split",
        "random_state",
        "point_count",
        "units",
        "metrics",
        "disclaimer",
        "points",
        "message",
    }
    assert set(data.keys()) <= allowed_top
    for point in data["points"]:
        assert set(point.keys()) == ALLOWED_POINT_KEYS


def test_api_never_exposes_filesystem_paths(client):
    data = client.get("/api/model-evaluation/predicted-vs-actual").json()
    blob = json.dumps(data).lower()
    assert "dataset_path" not in blob
    assert "house_price_model.pkl" not in blob
    assert "c:\\users" not in blob
    assert "/users/" not in blob
    assert str(ARTIFACT_PATH).lower() not in blob
    assert str(PROCESSED_CSV).lower() not in blob


def test_missing_artifact_unavailable(tmp_path):
    missing = tmp_path / "missing.json"
    payload = get_predicted_vs_actual(artifact_path=missing)
    assert payload["available"] is False
    assert payload["points"] == []
    assert "unavailable" in payload["message"].lower()


def test_dataset_hash_mismatch_unavailable(tmp_path, artifact):
    bad = dict(artifact)
    bad["dataset_sha256"] = "0" * 64
    path = tmp_path / "bad_hash.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    payload = get_predicted_vs_actual(artifact_path=path)
    assert payload["available"] is False
    assert payload["points"] == []


def test_model_version_mismatch_unavailable(tmp_path, artifact):
    bad = dict(artifact)
    bad["model_version"] = "9.9.9"
    path = tmp_path / "bad_version.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    payload = get_predicted_vs_actual(artifact_path=path)
    assert payload["available"] is False
    assert payload["points"] == []


def test_point_count_mismatch_unavailable(tmp_path, artifact):
    bad = dict(artifact)
    bad["point_count"] = 1
    bad["points"] = bad["points"][:1]
    path = tmp_path / "bad_count.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    payload = get_predicted_vs_actual(artifact_path=path)
    assert payload["available"] is False
    assert payload["points"] == []


def test_model_info_and_predict_still_work(client, valid_payload):
    assert client.get("/api/model-info").status_code == 200
    predict = client.post("/api/predict", json=valid_payload)
    assert predict.status_code == 200
    assert predict.json()["estimated_price_lakhs"] > 0
