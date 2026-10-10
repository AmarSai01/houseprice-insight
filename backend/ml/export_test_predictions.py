"""
Export held-out predicted-vs-actual evaluation points.

Replays the production train/test split through the EXISTING trained pipeline.
Does NOT call fit() and does NOT retrain.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from ml.train_model import (
    METADATA_PATH,
    MODEL_PATH,
    PROCESSED_CSV,
    RANDOM_STATE,
    build_xy,
    load_dataset,
)

ML_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ML_DIR.parents[1]
DATA_ML_DIR = PROJECT_ROOT / "data" / "ml"
ARTIFACT_PATH = DATA_ML_DIR / "predicted_vs_actual.json"

DISCLAIMER = (
    "Held-out test predictions from the production model on the project dataset. "
    "Prices are INR lakhs. This is model evaluation, not live listings."
)

METRIC_ABS_TOL = 1e-9
METRIC_REL_TOL = 1e-12
ALLOWED_POINT_KEYS = frozenset({"actual_price_lakhs", "predicted_price_lakhs"})


class ExportError(Exception):
    """Raised when the evaluation artifact cannot be generated safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metrics_match(actual: float, expected: float) -> bool:
    return math.isclose(
        float(actual),
        float(expected),
        rel_tol=METRIC_REL_TOL,
        abs_tol=METRIC_ABS_TOL,
    )


def rebuild_held_out_split() -> Tuple[Any, Any, Any, Any]:
    """Reproduce training build_xy + train_test_split(random_state=42)."""
    df = load_dataset()
    X, y, _features = build_xy(df)
    return train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
    )


def compute_metrics(y_true: Any, y_pred: Any) -> Dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def build_artifact(
    *,
    metadata: Dict[str, Any],
    y_test: Any,
    y_pred: np.ndarray,
    dataset_sha256: str,
    generated_at_utc: str | None = None,
) -> Dict[str, Any]:
    metrics = compute_metrics(y_test, y_pred)
    expected = metadata.get("final_test_metrics") or {}
    for key in ("mae", "rmse", "r2"):
        if key not in expected:
            raise ExportError(f"Metadata missing final_test_metrics.{key}")
        if not _metrics_match(metrics[key], expected[key]):
            raise ExportError(
                "Regenerated held-out metrics do not match model metadata. "
                "Artifact was not written."
            )

    expected_test_size = int(metadata.get("test_size", -1))
    if len(y_pred) != expected_test_size:
        raise ExportError(
            f"Test prediction count {len(y_pred)} does not match "
            f"metadata test_size {expected_test_size}."
        )

    y_true_arr = np.asarray(y_test, dtype=float)
    points: List[Dict[str, float]] = [
        {
            "actual_price_lakhs": float(y_true_arr[i]),
            "predicted_price_lakhs": float(y_pred[i]),
        }
        for i in range(len(y_pred))
    ]
    for point in points:
        if set(point.keys()) != ALLOWED_POINT_KEYS:
            raise ExportError("Point schema must contain only allowed fields.")

    return {
        "model_name": metadata.get("model_name"),
        "model_version": metadata.get("model_version"),
        "dataset_name": metadata.get("dataset_name", "bengaluru_property_clean.csv"),
        "dataset_row_count": int(
            metadata.get("dataset_row_count_model_usable")
            or metadata.get("dataset_row_count_total_clean")
            or 0
        ),
        "train_size": int(metadata.get("train_size", 0)),
        "test_size": expected_test_size,
        "evaluation_split": "held_out_test",
        "test_size_fraction": 0.2,
        "random_state": int(metadata.get("random_state", RANDOM_STATE)),
        "point_count": len(points),
        "generated_at_utc": generated_at_utc
        or datetime.now(timezone.utc).isoformat(),
        "model_training_date_utc": metadata.get("training_date_utc"),
        "dataset_sha256": dataset_sha256,
        "units": "INR_lakhs",
        "metrics": metrics,
        "disclaimer": DISCLAIMER,
        "points": points,
    }


def export_predicted_vs_actual(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    model_path: Path = MODEL_PATH,
    metadata_path: Path = METADATA_PATH,
    dataset_path: Path = PROCESSED_CSV,
) -> Dict[str, Any]:
    if not dataset_path.exists():
        raise ExportError("Clean property dataset is unavailable.")
    if not model_path.exists():
        raise ExportError("Production model artifact is unavailable.")
    if not metadata_path.exists():
        raise ExportError("Model metadata artifact is unavailable.")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    dataset_sha256 = sha256_file(dataset_path)

    _X_train, X_test, _y_train, y_test = rebuild_held_out_split()
    model = joblib.load(model_path)
    # Predict only — never fit.
    y_pred = np.asarray(model.predict(X_test), dtype=float)

    artifact = build_artifact(
        metadata=metadata,
        y_test=y_test,
        y_pred=y_pred,
        dataset_sha256=dataset_sha256,
    )

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    # Write only after validation succeeded.
    artifact_path.write_text(
        json.dumps(artifact, indent=2),
        encoding="utf-8",
    )
    return artifact


def main() -> None:
    artifact = export_predicted_vs_actual()
    print("EXPORT_COMPLETE")
    print(f"ARTIFACT={ARTIFACT_PATH}")
    print(f"POINT_COUNT={artifact['point_count']}")
    print(f"MAE={artifact['metrics']['mae']}")
    print(f"RMSE={artifact['metrics']['rmse']}")
    print(f"R2={artifact['metrics']['r2']}")
    print(f"DATASET_SHA256={artifact['dataset_sha256']}")


if __name__ == "__main__":
    main()
