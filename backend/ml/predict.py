"""
Backward-compatible prediction helpers wrapping the production ModelService.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ml.model_service import ModelServiceError, get_model_service


class HousePricePredictor:
    """Thin adapter used by older admin routes."""

    def __init__(self) -> None:
        self._service = get_model_service()

    def predict(self, input_data: Dict[str, Any]) -> float:
        """
        Predict price in INR lakhs.

        Accepts either Phase 5 feature names or a minimal mapped subset.
        """
        features = self._normalize_features(input_data)
        result = self._service.predict(features)
        return float(result["estimated_price_lakhs"])

    def get_metrics(self) -> Dict[str, float]:
        """Return model metrics derived from model_metadata.json."""
        try:
            return self._service.get_admin_metrics()
        except ModelServiceError:
            return {}

    @staticmethod
    def _normalize_features(input_data: Dict[str, Any]) -> Dict[str, Any]:
        if all(
            key in input_data
            for key in (
                "area_type",
                "location",
                "total_sqft",
                "bhk",
                "bath",
                "balcony",
                "is_ready_to_move",
            )
        ):
            return {
                "area_type": input_data["area_type"],
                "location": input_data["location"],
                "total_sqft": input_data["total_sqft"],
                "bhk": input_data["bhk"],
                "bath": input_data["bath"],
                "balcony": input_data["balcony"],
                "is_ready_to_move": input_data["is_ready_to_move"],
            }

        # Legacy admin/dashboard field names (best-effort mapping).
        return {
            "area_type": input_data.get("area_type", "Super built-up  Area"),
            "location": input_data.get("location", "Other"),
            "total_sqft": float(
                input_data.get("total_sqft", input_data.get("square_feet", 0))
            ),
            "bhk": int(
                input_data.get("bhk", input_data.get("number_of_bedrooms", 1))
            ),
            "bath": float(
                input_data.get("bath", input_data.get("number_of_bathrooms", 1))
            ),
            "balcony": float(input_data.get("balcony", 0)),
            "is_ready_to_move": bool(
                input_data.get("is_ready_to_move", True)
            ),
        }


_predictor_instance: Optional[HousePricePredictor] = None


def get_predictor() -> HousePricePredictor:
    """Get or create the global predictor adapter."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = HousePricePredictor()
    return _predictor_instance
