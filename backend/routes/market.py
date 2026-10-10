"""
Market Insights routes: read-only access to cleaned Bengaluru market-history data.

This dataset is separate from property-level ML prediction and must not be mixed
into the prediction model.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/api/market", tags=["market"])

SUPPORTED_AREAS = ("Devanahalli", "Indiranagar", "Whitefield", "Yelahanka")
MARKET_CSV = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "bengaluru_market_history_clean.csv"
)
DISCLAIMER = (
    "This page shows historical market data from the project's market dataset. "
    "It is separate from the machine-learning property estimate."
)


@lru_cache(maxsize=1)
def _load_market_frame() -> pd.DataFrame:
    if not MARKET_CSV.exists():
        raise FileNotFoundError("Market history dataset is unavailable.")

    df = pd.read_csv(MARKET_CSV)
    required = {"date", "area", "avg_price_per_sqft"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Market dataset missing columns: {sorted(missing)}")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "area", "avg_price_per_sqft"])
    df["area"] = df["area"].astype(str).str.strip()
    df = df[df["area"].isin(SUPPORTED_AREAS)]
    df = df.sort_values(["area", "date"]).reset_index(drop=True)
    return df


def _safe_float(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _area_summary(frame: pd.DataFrame, area: str) -> Dict[str, Any]:
    subset = frame[frame["area"] == area]
    if subset.empty:
        raise KeyError(area)

    latest = subset.iloc[-1]
    earliest = subset.iloc[0]
    return {
        "area": area,
        "observations": int(len(subset)),
        "date_start": earliest["date"].date().isoformat(),
        "date_end": latest["date"].date().isoformat(),
        "earliest_avg_price_per_sqft": _safe_float(earliest["avg_price_per_sqft"]),
        "latest_avg_price_per_sqft": _safe_float(latest["avg_price_per_sqft"]),
        "mean_avg_price_per_sqft": _safe_float(subset["avg_price_per_sqft"].mean()),
        "min_avg_price_per_sqft": _safe_float(subset["avg_price_per_sqft"].min()),
        "max_avg_price_per_sqft": _safe_float(subset["avg_price_per_sqft"].max()),
        "latest_yoy_pct": _safe_float(latest.get("yoy_pct")),
    }


@router.get("/overview")
async def get_market_overview() -> Dict[str, Any]:
    """Return coverage metadata and area comparison stats from the cleaned CSV."""
    try:
        frame = _load_market_frame()
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market history data is currently unavailable.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load market history data.",
        )

    comparisons = [_area_summary(frame, area) for area in SUPPORTED_AREAS]
    return {
        "supported_areas": list(SUPPORTED_AREAS),
        "metric": "avg_price_per_sqft",
        "metric_label": "Average price per sq ft (INR)",
        "date_start": frame["date"].min().date().isoformat(),
        "date_end": frame["date"].max().date().isoformat(),
        "total_observations": int(len(frame)),
        "unique_months": int(frame["date"].dt.to_period("M").nunique()),
        "comparisons": comparisons,
        "disclaimer": DISCLAIMER,
    }


@router.get("/history")
async def get_market_history(
    area: str = Query(..., min_length=1, description="Supported market-history area"),
) -> Dict[str, Any]:
    """Return the monthly historical series for one supported area."""
    requested = area.strip()
    if requested not in SUPPORTED_AREAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Historical market data is not currently available for this location."
            ),
        )

    try:
        frame = _load_market_frame()
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market history data is currently unavailable.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load market history data.",
        )

    subset = frame[frame["area"] == requested]
    if subset.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Historical market data is not currently available for this location."
            ),
        )

    series: List[Dict[str, Any]] = []
    for _, row in subset.iterrows():
        point = {
            "date": row["date"].date().isoformat(),
            "year": int(row["year"]) if "year" in subset.columns and pd.notna(row.get("year")) else None,
            "month": int(row["month"]) if "month" in subset.columns and pd.notna(row.get("month")) else None,
            "avg_price_per_sqft": _safe_float(row["avg_price_per_sqft"]),
        }
        if "index_100" in subset.columns:
            point["index_100"] = _safe_float(row.get("index_100"))
        if "yoy_pct" in subset.columns:
            point["yoy_pct"] = _safe_float(row.get("yoy_pct"))
        series.append(point)

    summary = _area_summary(frame, requested)
    return {
        "area": requested,
        "metric": "avg_price_per_sqft",
        "metric_label": "Average price per sq ft (INR)",
        "supported": True,
        "summary": summary,
        "series": series,
        "disclaimer": DISCLAIMER,
    }
