"""
Public model-evaluation routes (guest-capable, read-only).
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ml.model_evaluation import get_predicted_vs_actual

router = APIRouter(tags=["model-evaluation"])


class PredictedActualPoint(BaseModel):
    actual_price_lakhs: float
    predicted_price_lakhs: float


class PredictedVsActualMetrics(BaseModel):
    mae: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None


class PredictedVsActualResponse(BaseModel):
    available: bool
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    evaluation_split: str = "held_out_test"
    random_state: Optional[int] = None
    point_count: Optional[int] = None
    units: Optional[str] = None
    metrics: Optional[PredictedVsActualMetrics] = None
    disclaimer: Optional[str] = None
    points: List[PredictedActualPoint] = Field(default_factory=list)
    message: Optional[str] = None


@router.get(
    "/api/model-evaluation/predicted-vs-actual",
    response_model=PredictedVsActualResponse,
    summary="Held-out predicted vs actual evaluation points",
)
async def predicted_vs_actual() -> PredictedVsActualResponse:
    """
    Return public-safe held-out evaluation points for the production model.

    Guests allowed. No database access. Fail closed on stale/missing artifacts.
    """
    payload = get_predicted_vs_actual()
    if not payload.get("available"):
        return PredictedVsActualResponse(
            available=False,
            model_version=payload.get("model_version"),
            evaluation_split="held_out_test",
            message=payload.get("message"),
            points=[],
        )

    return PredictedVsActualResponse(
        available=True,
        model_name=payload.get("model_name"),
        model_version=payload.get("model_version"),
        evaluation_split="held_out_test",
        random_state=payload.get("random_state"),
        point_count=payload.get("point_count"),
        units=payload.get("units"),
        metrics=PredictedVsActualMetrics(**(payload.get("metrics") or {})),
        disclaimer=payload.get("disclaimer"),
        points=[
            PredictedActualPoint(**point) for point in payload.get("points") or []
        ],
    )
