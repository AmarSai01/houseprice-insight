"""
Public model-evaluation helpers (predicted vs actual).

Fail closed on missing/stale artifacts. Never expose filesystem paths or
property-identifying fields.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ml.export_test_predictions import ALLOWED_POINT_KEYS, ARTIFACT_PATH, DISCLAIMER
from ml.train_model import METADATA_PATH, PROCESSED_CSV

logger = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = (
    "Model evaluation is temporarily unavailable because the evaluation "
    "artifact does not match the current model or dataset."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unavailable(
    *,
    model_version: Optional[str] = None,
    message: str = UNAVAILABLE_MESSAGE,
) -> Dict[str, Any]:
    return {
        "available": False,
        "model_version": model_version,
        "evaluation_split": "held_out_test",
        "message": message,
        "points": [],
    }


def _sanitize_points(raw_points: Any) -> Optional[List[Dict[str, float]]]:
    if not isinstance(raw_points, list):
        return None
    cleaned: List[Dict[str, float]] = []
    for item in raw_points:
        if not isinstance(item, dict):
            return None
        if set(item.keys()) != ALLOWED_POINT_KEYS:
            return None
        try:
            actual = float(item["actual_price_lakhs"])
            predicted = float(item["predicted_price_lakhs"])
        except (TypeError, ValueError, KeyError):
            return None
        cleaned.append(
            {
                "actual_price_lakhs": actual,
                "predicted_price_lakhs": predicted,
            }
        )
    return cleaned


def load_metadata(metadata_path: Path = METADATA_PATH) -> Dict[str, Any]:
    if not metadata_path.exists():
        return {}
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        logger.exception("Failed to read model metadata for evaluation checks")
        return {}


def get_predicted_vs_actual(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    metadata_path: Path = METADATA_PATH,
    dataset_path: Path = PROCESSED_CSV,
) -> Dict[str, Any]:
    """
    Return a public-safe predicted-vs-actual payload.

    Validates model_version, dataset_sha256, and point_count against current
    production metadata/dataset. Fail closed on any mismatch.
    """
    metadata = load_metadata(metadata_path)
    current_version = metadata.get("model_version")

    if not artifact_path.exists():
        return _unavailable(model_version=current_version)

    try:
        raw = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        logger.exception("Failed to parse predicted-vs-actual artifact")
        return _unavailable(model_version=current_version)

    if not isinstance(raw, dict):
        return _unavailable(model_version=current_version)

    artifact_version = raw.get("model_version")
    if not current_version or artifact_version != current_version:
        return _unavailable(model_version=current_version)

    expected_test_size = metadata.get("test_size")
    point_count = raw.get("point_count")
    points = _sanitize_points(raw.get("points"))
    if points is None:
        return _unavailable(model_version=current_version)
    if expected_test_size is None or int(point_count or -1) != int(expected_test_size):
        return _unavailable(model_version=current_version)
    if len(points) != int(expected_test_size):
        return _unavailable(model_version=current_version)

    if not dataset_path.exists():
        return _unavailable(model_version=current_version)
    try:
        current_hash = sha256_file(dataset_path)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to hash clean dataset for evaluation checks")
        return _unavailable(model_version=current_version)

    if raw.get("dataset_sha256") != current_hash:
        return _unavailable(model_version=current_version)

    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    return {
        "available": True,
        "model_name": raw.get("model_name") or metadata.get("model_name"),
        "model_version": artifact_version,
        "evaluation_split": "held_out_test",
        "random_state": raw.get("random_state", metadata.get("random_state")),
        "point_count": len(points),
        "units": "INR_lakhs",
        "metrics": {
            "mae": metrics.get("mae"),
            "rmse": metrics.get("rmse"),
            "r2": metrics.get("r2"),
        },
        "disclaimer": raw.get("disclaimer") or DISCLAIMER,
        "points": points,
    }
