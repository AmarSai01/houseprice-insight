"""
Property listing similarity routes (guest-capable, read-only).

Uses the clean Bengaluru property CSV — not the ML model and not market history.
Does not persist results to prediction history.
"""

from __future__ import annotations

import math
from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ml.similar_properties import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_SIMILARITY,
    SimilarPropertiesError,
    get_similar_properties_service,
)

router = APIRouter(tags=["properties"])


class SimilarQueryEcho(BaseModel):
    area_type: str
    location: str
    total_sqft: float
    bhk: Union[int, float]
    bath: float
    balcony: float
    is_ready_to_move: bool


class SimilarPropertyItem(BaseModel):
    rank: int
    similarity: float
    location: str
    area_type: str
    total_sqft: float
    bhk: float
    bath: float
    balcony: Optional[float] = None
    is_ready_to_move: bool
    listed_price_lakhs: float = Field(
        ...,
        description="Historical dataset listing value in INR lakhs (not an ML estimate).",
    )
    listed_price_per_sqft: Optional[float] = Field(
        None,
        description="Historical dataset listing price per sq.ft. (reference only).",
    )
    match_notes: List[str]
    location_match: bool


class SimilarPropertiesResponse(BaseModel):
    query: SimilarQueryEcho
    count: int
    method: str
    disclaimer: str
    results: List[SimilarPropertyItem]
    message: Optional[str] = None


@router.get(
    "/api/properties/similar",
    response_model=SimilarPropertiesResponse,
    summary="Find similar Bengaluru property listings from the project dataset",
)
async def get_similar_properties(
    area_type: str = Query(..., min_length=1),
    location: str = Query(..., min_length=1),
    total_sqft: float = Query(..., gt=0),
    bhk: int = Query(..., ge=1),
    bath: float = Query(..., ge=1),
    balcony: float = Query(..., ge=0),
    is_ready_to_move: bool = Query(...),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    min_similarity: float = Query(MIN_SIMILARITY, ge=0.0, le=1.0),
):
    """
    Guest-accessible similarity search.

    Returns historical dataset listings only. Does not call the ML model,
    does not use market-history data, and does not write prediction history.
    """
    if (
        not math.isfinite(total_sqft)
        or not math.isfinite(bath)
        or not math.isfinite(balcony)
        or not math.isfinite(min_similarity)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request.",
        )

    features = {
        "area_type": area_type.strip(),
        "location": location.strip(),
        "total_sqft": float(total_sqft),
        "bhk": int(bhk),
        "bath": float(bath),
        "balcony": float(balcony),
        "is_ready_to_move": bool(is_ready_to_move),
    }
    if not features["area_type"] or not features["location"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request.",
        )

    service = get_similar_properties_service()
    try:
        return service.find_similar(
            features,
            limit=limit,
            min_similarity=float(min_similarity),
        )
    except SimilarPropertiesError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Similar properties data is currently unavailable.",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to search similar properties.",
        )
