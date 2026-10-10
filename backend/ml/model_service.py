"""
Production model service: load Phase 4 artifacts once and serve predictions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd

from ml.explanation import public_explanation_payload, try_load_explanation

logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).resolve().parent
REPO_ROOT = ML_DIR.parents[1]
MODEL_PATH = ML_DIR / "house_price_model.pkl"
METADATA_PATH = ML_DIR / "model_metadata.json"
PERMUTATION_IMPORTANCE_CSV = (
    REPO_ROOT / "data" / "ml" / "permutation_importance_raw_features.csv"
)

DISCLAIMER = (
    "This is an ML-based estimate, not a professional property valuation."
)

# Columns expected by the trained sklearn Pipeline (FeatureBuilder uses availability).
PIPELINE_INPUT_COLUMNS = [
    "area_type",
    "location",
    "availability",
    "total_sqft",
    "bhk",
    "bath",
    "balcony",
]


class ModelServiceError(Exception):
    """Raised when the model cannot be loaded or a prediction fails."""


class ModelService:
    """Singleton-style service that holds the loaded pipeline and metadata."""

    def __init__(self) -> None:
        self.model = None
        self.metadata: Dict[str, Any] = {}
        self.explanation: Optional[Dict[str, Any]] = None
        self.loaded = False
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        try:
            if not MODEL_PATH.exists():
                raise ModelServiceError("Production model artifact is missing.")
            if not METADATA_PATH.exists():
                raise ModelServiceError("Model metadata artifact is missing.")

            self.model = joblib.load(MODEL_PATH)
            self.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            # Load once at startup — never on each prediction request.
            self.explanation = try_load_explanation(
                PERMUTATION_IMPORTANCE_CSV,
                metadata=self.metadata,
            )
            self.loaded = True
            self.load_error = None
            logger.info(
                "Loaded model %s v%s (explanation=%s)",
                self.metadata.get("model_name"),
                self.metadata.get("model_version"),
                "yes" if self.explanation else "no",
            )
        except Exception as exc:  # noqa: BLE001 - surface clean load status
            self.model = None
            self.metadata = {}
            self.explanation = None
            self.loaded = False
            self.load_error = "Model failed to load."
            logger.exception("Model load failed: %s", type(exc).__name__)

    def ensure_loaded(self) -> None:
        if not self.loaded or self.model is None:
            raise ModelServiceError(self.load_error or "Model is not available.")

    def _to_pipeline_frame(self, features: Dict[str, Any]) -> pd.DataFrame:
        """Map API features to the dataframe columns the trained pipeline expects."""
        is_ready = features.get("is_ready_to_move")
        if isinstance(is_ready, bool):
            ready_flag = is_ready
        else:
            ready_flag = int(is_ready) == 1

        row = {
            "area_type": str(features["area_type"]).strip(),
            "location": str(features["location"]).strip(),
            "availability": "Ready To Move" if ready_flag else "Not Ready",
            "total_sqft": float(features["total_sqft"]),
            "bhk": float(features["bhk"]),
            "bath": float(features["bath"]),
            "balcony": float(features["balcony"]),
        }
        return pd.DataFrame([row], columns=PIPELINE_INPUT_COLUMNS)

    def _estimate_range(self, estimate_lakhs: float) -> tuple[float, float]:
        """
        Apply Phase 4 residual-percentile range methodology.

        residual = actual - predicted (OOF). Adding p10/p90 residuals to the
        point estimate yields an estimated price range based on model prediction
        error. This is not a statistical confidence interval.
        """
        range_meta = self.metadata.get("prediction_range") or {}
        if not range_meta.get("supported", False):
            return estimate_lakhs, estimate_lakhs

        p10 = float(range_meta["residual_p10_lakhs"])
        p90 = float(range_meta["residual_p90_lakhs"])
        low = max(0.0, estimate_lakhs + p10)
        high = max(0.0, estimate_lakhs + p90)
        # Keep ordering: low <= estimate <= high
        low = min(low, estimate_lakhs)
        high = max(high, estimate_lakhs)
        return low, high

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured prediction from validated request features."""
        self.ensure_loaded()

        try:
            frame = self._to_pipeline_frame(features)
            # Never pass price_per_sqft into the model.
            raw_pred = float(self.model.predict(frame)[0])
        except ModelServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Prediction failed: %s", type(exc).__name__)
            raise ModelServiceError("Prediction failed.") from exc

        estimate_lakhs = round(max(0.0, raw_pred), 2)
        low_raw, high_raw = self._estimate_range(estimate_lakhs)
        low_lakhs = round(low_raw, 2)
        high_lakhs = round(high_raw, 2)
        # Keep ordering after rounding.
        low_lakhs = min(low_lakhs, estimate_lakhs)
        high_lakhs = max(high_lakhs, estimate_lakhs)

        total_sqft = float(features["total_sqft"])
        estimate_inr = int(round(estimate_lakhs * 100_000))
        low_inr = int(round(low_lakhs * 100_000))
        high_inr = int(round(high_lakhs * 100_000))
        price_per_sqft = (
            round(estimate_inr / total_sqft, 2) if total_sqft > 0 else 0.0
        )

        payload: Dict[str, Any] = {
            "estimated_price_lakhs": estimate_lakhs,
            "estimated_price_inr": estimate_inr,
            "estimated_low_lakhs": low_lakhs,
            "estimated_high_lakhs": high_lakhs,
            "estimated_low_inr": low_inr,
            "estimated_high_inr": high_inr,
            "price_per_sqft": price_per_sqft,
            "model": self.metadata.get("model_name", "unknown"),
            "model_version": self.metadata.get("model_version", "unknown"),
            "disclaimer": DISCLAIMER,
            "range_note": (
                "Estimated price range based on model prediction error "
                "(not a statistical confidence interval)."
            ),
        }
        explanation = public_explanation_payload(self.explanation)
        if explanation is not None:
            payload["explanation"] = explanation
        return payload

    def get_public_model_info(self) -> Dict[str, Any]:
        """Return transparency fields from metadata without internal paths."""
        self.ensure_loaded()
        cv = self.metadata.get("selected_model_cv_metrics") or {}
        test = self.metadata.get("final_test_metrics") or {}
        range_meta = self.metadata.get("prediction_range") or {}
        selected_name = self.metadata.get("model_name")
        selection_rule = self.metadata.get("selection_rule")

        # Cross-validation comparison from training artifacts (not held-out test).
        comparison_models: list[Dict[str, Any]] = []
        cv_block = self.metadata.get("cv_metrics")
        if isinstance(cv_block, dict):
            for model_name, metrics in cv_block.items():
                if not isinstance(metrics, dict):
                    continue
                comparison_models.append(
                    {
                        "model_name": model_name,
                        "selected": model_name == selected_name,
                        "cv_mae_mean": metrics.get("cv_mae_mean"),
                        "cv_mae_std": metrics.get("cv_mae_std"),
                        "cv_rmse_mean": metrics.get("cv_rmse_mean"),
                        "cv_rmse_std": metrics.get("cv_rmse_std"),
                        "cv_r2_mean": metrics.get("cv_r2_mean"),
                        "cv_r2_std": metrics.get("cv_r2_std"),
                    }
                )
            # Stable ordering: selected first, then by ascending CV MAE when available.
            def _sort_key(row: Dict[str, Any]) -> tuple:
                mae = row.get("cv_mae_mean")
                mae_key = float(mae) if isinstance(mae, (int, float)) else float("inf")
                return (0 if row.get("selected") else 1, mae_key, str(row.get("model_name")))

            comparison_models.sort(key=_sort_key)

        prediction_range: Dict[str, Any] = {
            "method": range_meta.get("method"),
            "description": range_meta.get("description"),
            "supported": range_meta.get("supported", False),
        }
        if "residual_p10_lakhs" in range_meta:
            prediction_range["residual_p10_lakhs"] = range_meta.get(
                "residual_p10_lakhs"
            )
        if "residual_p90_lakhs" in range_meta:
            prediction_range["residual_p90_lakhs"] = range_meta.get(
                "residual_p90_lakhs"
            )
        if "mae_oof_lakhs" in range_meta:
            prediction_range["mae_oof_lakhs"] = range_meta.get("mae_oof_lakhs")

        info: Dict[str, Any] = {
            "model_name": selected_name,
            "model_version": self.metadata.get("model_version"),
            "training_date": self.metadata.get("training_date_utc"),
            "dataset_name": self.metadata.get("dataset_name"),
            "dataset_row_count": self.metadata.get("dataset_row_count_model_usable"),
            "target_name": self.metadata.get("target_name"),
            "target_unit": self.metadata.get("target_unit"),
            "features": self.metadata.get("feature_names_model"),
            "cv_mae": cv.get("cv_mae_mean"),
            "cv_mae_std": cv.get("cv_mae_std"),
            "test_mae": test.get("mae"),
            "test_rmse": test.get("rmse"),
            "test_r2": test.get("r2"),
            "train_size": self.metadata.get("train_size"),
            "test_size": self.metadata.get("test_size"),
            "prediction_range": prediction_range,
            "limitations": self.metadata.get("limitations", []),
            "disclaimer": DISCLAIMER,
            # Explicit units for evaluation metrics (headline = held-out test).
            "metric_units": {
                "mae": "INR_lakhs",
                "rmse": "INR_lakhs",
                "r2": "unitless",
            },
            "held_out_test_metrics": {
                "scope": "held_out_test_split",
                "mae": test.get("mae"),
                "rmse": test.get("rmse"),
                "r2": test.get("r2"),
                "unit_note": (
                    "MAE and RMSE are in INR lakhs. R² is unitless. "
                    "These are the production model's held-out test metrics."
                ),
            },
            "selection_rule": selection_rule,
            "model_comparison": {
                "scope": "cross_validation_on_training_split",
                "selection_rule": selection_rule,
                "unit_note": (
                    "Cross-validated MAE and RMSE are in INR lakhs. "
                    "Cross-validated R² is unitless. "
                    "These CV metrics are for model selection comparison; "
                    "they are not the held-out test metrics."
                ),
                "models": comparison_models,
            },
            # Property listing dataset has no trustworthy transaction/date column.
            "has_property_date": False,
        }
        explanation = public_explanation_payload(self.explanation)
        if explanation is not None:
            info["explanation"] = explanation
        return info

    def get_admin_metrics(self) -> Dict[str, float]:
        """Map metadata metrics into the shape expected by the admin metrics route."""
        self.ensure_loaded()
        cv = self.metadata.get("selected_model_cv_metrics") or {}
        test = self.metadata.get("final_test_metrics") or {}
        return {
            "train_mae": float(cv.get("cv_mae_mean", 0.0)),
            "test_mae": float(test.get("mae", 0.0)),
            "train_rmse": float(cv.get("cv_rmse_mean", 0.0)),
            "test_rmse": float(test.get("rmse", 0.0)),
            "train_r2": float(cv.get("cv_r2_mean", 0.0)),
            "test_r2": float(test.get("r2", 0.0)),
        }


_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """Return the process-wide model service (loaded once)."""
    global _service
    if _service is None:
        _service = ModelService()
    return _service
