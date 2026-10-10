"""
Prediction routes: guest-capable estimate, optional history save, model info.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from auth import get_current_user, get_optional_current_user
from database import get_db
from ml.model_service import ModelServiceError, get_model_service
from models import Prediction, User

router = APIRouter(tags=["predict"])


class PredictionRequest(BaseModel):
    """Request body for POST /api/predict."""

    area_type: str = Field(..., min_length=1, description="Property area type")
    location: str = Field(..., min_length=1, description="Bengaluru locality")
    total_sqft: float = Field(..., gt=0, description="Total area in square feet")
    bhk: int = Field(..., ge=1, description="Number of bedrooms (BHK)")
    bath: float = Field(..., ge=1, description="Number of bathrooms")
    balcony: float = Field(..., ge=0, description="Number of balconies")
    is_ready_to_move: bool = Field(
        ..., description="True if the property is ready to move"
    )

    @field_validator("area_type", "location")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class ExplanationFactor(BaseModel):
    """One global model-level influence factor (not a local ₹ attribution)."""

    feature: str
    label: str
    importance: float
    rank: int


class PredictionExplanation(BaseModel):
    """Global feature influence for the loaded model."""

    type: str
    scope: str
    method: str
    note: str
    factors: List[ExplanationFactor]


class PredictionResponse(BaseModel):
    """Structured estimate response."""

    estimated_price_lakhs: float
    estimated_price_inr: int
    estimated_low_lakhs: float
    estimated_high_lakhs: float
    estimated_low_inr: int
    estimated_high_inr: int
    price_per_sqft: float
    model: str
    model_version: str
    disclaimer: str
    range_note: str
    prediction_id: Optional[int] = None
    saved: bool = False
    explanation: Optional[PredictionExplanation] = None


class HistoryItem(BaseModel):
    id: int
    input_features: Dict[str, Any]
    predicted_value: float
    timestamp: str


@router.post(
    "/api/predict",
    response_model=PredictionResponse,
    summary="Estimate Bengaluru house price",
)
async def predict_house_price(
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Generate a model-based price estimate.

    Authentication is optional. Guests receive an estimate without persistence.
    Authenticated users also get the estimate saved to prediction history.
    """
    service = get_model_service()
    features = payload.model_dump()

    try:
        result = service.predict(features)
    except ModelServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service is unavailable. Please try again later.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed due to an unexpected error.",
        )

    prediction_id = None
    saved = False
    if current_user is not None:
        try:
            record = Prediction(
                user_id=current_user.id,
                input_features=features,
                predicted_value=result["estimated_price_lakhs"],
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            prediction_id = record.id
            saved = True
        except Exception:
            db.rollback()
            # Estimate succeeded; history save is best-effort.
            prediction_id = None
            saved = False

    return {
        **result,
        "prediction_id": prediction_id,
        "saved": saved,
    }


@router.get(
    "/api/predict/history",
    response_model=List[HistoryItem],
    summary="Get authenticated user's prediction history",
)
async def get_prediction_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return prediction history for the signed-in user."""
    predictions = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.timestamp.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "input_features": p.input_features,
            "predicted_value": p.predicted_value,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
        }
        for p in predictions
    ]


@router.get(
    "/api/model-info",
    summary="Model transparency information",
)
async def get_model_info():
    """Return selected metrics and limitations from model_metadata.json."""
    service = get_model_service()
    try:
        return service.get_public_model_info()
    except ModelServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model information is currently unavailable.",
        )
