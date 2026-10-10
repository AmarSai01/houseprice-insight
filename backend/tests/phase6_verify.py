"""Phase 6 end-to-end API verification against the running backend."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001"
ROOT = Path(__file__).resolve().parents[2]
META_PATH = ROOT / "backend" / "ml" / "model_metadata.json"


def main() -> int:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    client = httpx.Client(base_url=BASE, timeout=30.0)

    print("=== 1. HEALTH ===")
    r = client.get("/health")
    print(r.status_code, r.json())
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"
    assert r.json().get("model_loaded") is True

    print("=== 2. MODEL INFO ===")
    r = client.get("/api/model-info")
    info = r.json()
    print(r.status_code)
    assert r.status_code == 200
    checks = {
        "model_name": meta["model_name"],
        "model_version": meta["model_version"],
        "training_date": meta["training_date_utc"],
        "dataset_row_count": meta["dataset_row_count_model_usable"],
        "target_name": meta["target_name"],
        "target_unit": meta["target_unit"],
        "features": meta["feature_names_model"],
        "cv_mae": meta["selected_model_cv_metrics"]["cv_mae_mean"],
        "test_mae": meta["final_test_metrics"]["mae"],
        "test_rmse": meta["final_test_metrics"]["rmse"],
        "test_r2": meta["final_test_metrics"]["r2"],
        "limitations": meta["limitations"],
    }
    for key, expected in checks.items():
        actual = info.get(key)
        ok = actual == expected
        print(f"  {key}: match={ok}")
        assert ok, (key, actual, expected)
    assert "dataset_path" not in info
    assert "house_price_model.pkl" not in str(info)

    print("=== 3. PREDICTIONS ===")
    samples = [
        {
            "area_type": "Super built-up  Area",
            "location": "Whitefield",
            "total_sqft": 1200,
            "bhk": 2,
            "bath": 2,
            "balcony": 1,
            "is_ready_to_move": True,
        },
        {
            "area_type": "Built-up  Area",
            "location": "Koramangala",
            "total_sqft": 1600,
            "bhk": 3,
            "bath": 2,
            "balcony": 2,
            "is_ready_to_move": True,
        },
        {
            "area_type": "Plot  Area",
            "location": "Yelahanka",
            "total_sqft": 2200,
            "bhk": 4,
            "bath": 3,
            "balcony": 1,
            "is_ready_to_move": False,
        },
    ]
    examples = []
    for sample in samples:
        r = client.post("/api/predict", json=sample)
        data = r.json()
        assert r.status_code == 200
        assert data["estimated_price_lakhs"] > 0
        assert data["estimated_price_inr"] > 0
        assert data["estimated_price_inr"] == int(
            round(data["estimated_price_lakhs"] * 100000)
        )
        assert (
            data["estimated_low_lakhs"]
            <= data["estimated_price_lakhs"]
            <= data["estimated_high_lakhs"]
        )
        assert data["estimated_low_inr"] == int(
            round(data["estimated_low_lakhs"] * 100000)
        )
        assert data["estimated_high_inr"] == int(
            round(data["estimated_high_lakhs"] * 100000)
        )
        assert data["price_per_sqft"] > 0
        assert data["model"] and data["model_version"]
        assert data["disclaimer"]
        assert "not a statistical confidence" in data["range_note"].lower()
        examples.append(
            {
                "location": sample["location"],
                **{
                    k: data[k]
                    for k in [
                        "estimated_price_lakhs",
                        "estimated_low_lakhs",
                        "estimated_high_lakhs",
                        "estimated_price_inr",
                        "price_per_sqft",
                        "model",
                        "model_version",
                    ]
                },
            }
        )
        print(
            "  OK",
            sample["location"],
            data["estimated_price_lakhs"],
            data["estimated_low_lakhs"],
            data["estimated_high_lakhs"],
        )

    print("=== 4. LOCATION HANDLING ===")
    known = client.post("/api/predict", json=samples[0])
    unseen = client.post(
        "/api/predict",
        json={**samples[0], "location": "Test Locality Bengaluru"},
    )
    assert known.status_code == 200 and unseen.status_code == 200
    assert unseen.json()["estimated_price_lakhs"] > 0
    print(
        "  known",
        known.json()["estimated_price_lakhs"],
        "unseen",
        unseen.json()["estimated_price_lakhs"],
    )

    print("=== 5. INVALID INPUTS ===")
    invalid_cases = [
        ("sqft_0", {**samples[0], "total_sqft": 0}),
        ("sqft_neg", {**samples[0], "total_sqft": -10}),
        ("bhk_0", {**samples[0], "bhk": 0}),
        ("bath_0", {**samples[0], "bath": 0}),
        (
            "missing_location",
            {k: v for k, v in samples[0].items() if k != "location"},
        ),
    ]
    for name, body in invalid_cases:
        r = client.post("/api/predict", json=body)
        text = r.text.lower()
        assert r.status_code == 422, (name, r.status_code, r.text)
        assert "traceback" not in text
        assert 'file "' not in text
        print(f"  {name}: {r.status_code}")
    r = client.post(
        "/api/predict",
        content="{not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code in (400, 422)
    assert "traceback" not in r.text.lower()
    print("  malformed_json:", r.status_code)

    print("=== 6. RANGE METHODOLOGY ===")
    rng = meta["prediction_range"]
    assert rng["method"] == "out_of_fold_residual_percentiles"
    assert rng["supported"] is True
    assert "not a statistical confidence interval" in rng["description"].lower()
    print(
        "  method",
        rng["method"],
        "p10",
        rng["residual_p10_lakhs"],
        "p90",
        rng["residual_p90_lakhs"],
    )

    print("=== 8. AUTH ===")
    email = "phase6_verify@example.com"
    reg = client.post(
        "/api/auth/register",
        json={"name": "Phase6", "email": email, "password": "testpass123"},
    )
    print("  register", reg.status_code)
    login = client.post(
        "/api/auth/login",
        data={"username": email, "password": "testpass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    print("  login/me OK", me.json()["email"])
    pred = client.post(
        "/api/predict",
        json=samples[0],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pred.status_code == 200
    assert pred.json().get("saved") is True
    hist = client.get(
        "/api/predict/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert hist.status_code == 200 and len(hist.json()) >= 1
    print("  history OK", len(hist.json()))

    print("=== ARTIFACT INTEGRITY ===")
    for rel in [
        "data/raw/bengaluru_house_data_raw.csv",
        "data/raw/bengaluru_market_history_raw.csv",
        "backend/ml/house_price_model.pkl",
        "backend/ml/model_metadata.json",
    ]:
        path = ROOT / rel
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        print(f"  {rel}: {digest} size={path.stat().st_size}")

    print("EXAMPLES_JSON")
    print(json.dumps(examples, indent=2))
    print("MODEL_INFO_SUMMARY")
    print(
        json.dumps(
            {
                k: info[k]
                for k in [
                    "model_name",
                    "model_version",
                    "training_date",
                    "dataset_row_count",
                    "target_name",
                    "target_unit",
                    "features",
                    "cv_mae",
                    "test_mae",
                    "test_rmse",
                    "test_r2",
                ]
            },
            indent=2,
        )
    )
    print("PHASE6_API_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print("PHASE6_API_FAIL", type(exc).__name__, exc)
        raise
