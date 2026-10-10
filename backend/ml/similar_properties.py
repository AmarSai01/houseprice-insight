"""
Similar-properties search over the clean Bengaluru listing dataset.

Uses weighted hybrid feature distance — explainable and deterministic.
Does NOT use RareLocationGrouper("Other"): that training trick would treat
unrelated rare localities as equivalent. Exact cleaned location is preferred.

Price is NEVER a similarity feature; listed prices are returned only as
historical dataset reference values (INR lakhs), not ML estimates.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ML_DIR.parents[1]
DEFAULT_DATASET_PATH = (
    PROJECT_ROOT / "data" / "processed" / "bengaluru_property_clean.csv"
)

# Relative importance of each feature in the weighted distance.
# Kept as named config — do not scatter magic numbers through call sites.
FEATURE_WEIGHTS: Dict[str, float] = {
    "total_sqft": 0.40,
    "location": 0.25,
    "bhk": 0.15,
    "bath": 0.10,
    "area_type": 0.05,
    "balcony": 0.03,
    "is_ready_to_move": 0.02,
}

MIN_SIMILARITY = 0.40
DEFAULT_LIMIT = 5
MAX_LIMIT = 10

# Size bands: prefer within ~35%; hard reject beyond 50% in primary pool.
PREFERRED_SIZE_RATIO = 0.35
HARD_SIZE_RATIO = 0.50
PREFERRED_BHK_DIFF = 1
FALLBACK_BHK_DIFF = 2

DISCLAIMER = (
    "Listings come from the project Bengaluru property dataset. "
    "Prices are historical listing values in INR lakhs, not this app's ML estimate."
)

EMPTY_MESSAGE = (
    "No sufficiently similar properties were found in the project dataset "
    "for these characteristics."
)

METHOD_NAME = "weighted_feature_distance"

_WHITESPACE_RE = re.compile(r"\s+")


class SimilarPropertiesError(Exception):
    """Raised when the similarity dataset cannot be loaded or used."""


def normalize_location(value: Any) -> str:
    """Match FeatureBuilder location cleaning (strip / collapse whitespace)."""
    text = str(value).strip()
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip(" ,;")


def availability_to_ready(value: Any) -> int:
    """Match FeatureBuilder: Ready To Move → 1, else 0."""
    return int(str(value).strip().lower() == "ready to move")


def _iqr_scale(series: pd.Series, floor: float) -> float:
    """Robust scale: IQR, floored so zero-IQR features still work."""
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return floor
    q75 = float(clean.quantile(0.75))
    q25 = float(clean.quantile(0.25))
    iqr = q75 - q25
    return max(iqr, floor)


def _finite_nonneg(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


@dataclass(frozen=True)
class SimilarityQuery:
    area_type: str
    location: str
    total_sqft: float
    bhk: float
    bath: float
    balcony: float
    is_ready_to_move: bool

    def as_public_dict(self) -> Dict[str, Any]:
        return {
            "area_type": self.area_type,
            "location": self.location,
            "total_sqft": self.total_sqft,
            "bhk": int(self.bhk) if float(self.bhk).is_integer() else self.bhk,
            "bath": self.bath,
            "balcony": self.balcony,
            "is_ready_to_move": bool(self.is_ready_to_move),
        }


class SimilarPropertiesService:
    """Load once, score O(N) with weighted hybrid distance."""

    def __init__(self, dataset_path: Optional[Path] = None) -> None:
        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
        self.frame: Optional[pd.DataFrame] = None
        self.scales: Dict[str, float] = {}
        self.balcony_median: float = 0.0
        self.loaded = False
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        try:
            if not self.dataset_path.exists():
                raise SimilarPropertiesError("Property dataset is unavailable.")

            raw = pd.read_csv(self.dataset_path)
            required = {
                "location",
                "area_type",
                "availability",
                "total_sqft",
                "bhk",
                "bath",
                "balcony",
                "price",
                "price_per_sqft",
            }
            missing = required - set(raw.columns)
            if missing:
                raise SimilarPropertiesError("Property dataset is incomplete.")

            df = raw.copy()
            df["location_norm"] = df["location"].map(normalize_location)
            df["area_type_norm"] = df["area_type"].astype(str).str.strip()
            df["is_ready_to_move"] = df["availability"].map(availability_to_ready)
            df["total_sqft"] = pd.to_numeric(df["total_sqft"], errors="coerce")
            df["bhk"] = pd.to_numeric(df["bhk"], errors="coerce")
            df["bath"] = pd.to_numeric(df["bath"], errors="coerce")
            df["balcony"] = pd.to_numeric(df["balcony"], errors="coerce")
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["price_per_sqft"] = pd.to_numeric(df["price_per_sqft"], errors="coerce")

            df = df.dropna(
                subset=[
                    "location_norm",
                    "area_type_norm",
                    "total_sqft",
                    "bhk",
                    "bath",
                    "price",
                ]
            )
            df = df[df["total_sqft"] > 0]
            df = df[df["bhk"] >= 1]
            df = df[df["bath"] >= 1]
            df = df[df["price"] > 0]

            if df.empty:
                raise SimilarPropertiesError("Property dataset has no usable rows.")

            self.balcony_median = float(df["balcony"].median(skipna=True))
            if not math.isfinite(self.balcony_median):
                self.balcony_median = 0.0

            # Explicit missing-balcony policy: median imputed for distance only.
            df["balcony_for_distance"] = df["balcony"].fillna(self.balcony_median)

            self.scales = {
                "total_sqft": _iqr_scale(df["total_sqft"], floor=100.0),
                "bhk": _iqr_scale(df["bhk"], floor=1.0),
                "bath": _iqr_scale(df["bath"], floor=1.0),
                "balcony": _iqr_scale(df["balcony_for_distance"], floor=1.0),
            }

            # Stable row order for deterministic ties.
            df = df.reset_index(drop=True)
            df["_row_id"] = np.arange(len(df), dtype=int)
            self.frame = df
            self.loaded = True
            self.load_error = None
            logger.info(
                "Loaded similar-properties dataset (%s rows)",
                len(df),
            )
        except SimilarPropertiesError as exc:
            self.frame = None
            self.loaded = False
            self.load_error = str(exc)
            logger.warning("Similar-properties load failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            self.frame = None
            self.loaded = False
            self.load_error = "Property dataset failed to load."
            logger.exception("Similar-properties load error: %s", type(exc).__name__)

    def ensure_loaded(self) -> None:
        if not self.loaded or self.frame is None:
            raise SimilarPropertiesError(
                self.load_error or "Property dataset is unavailable."
            )

    def normalize_query(self, features: Dict[str, Any]) -> SimilarityQuery:
        location = normalize_location(features["location"])
        area_type = str(features["area_type"]).strip()
        total_sqft = _finite_nonneg("total_sqft", float(features["total_sqft"]))
        bhk = _finite_nonneg("bhk", float(features["bhk"]))
        bath = _finite_nonneg("bath", float(features["bath"]))
        balcony = _finite_nonneg("balcony", float(features["balcony"]))
        if total_sqft <= 0 or bhk < 1 or bath < 1 or balcony < 0:
            raise ValueError("Invalid property dimensions")
        ready = features["is_ready_to_move"]
        if isinstance(ready, bool):
            ready_flag = ready
        else:
            ready_flag = int(ready) == 1
        return SimilarityQuery(
            area_type=area_type,
            location=location,
            total_sqft=total_sqft,
            bhk=bhk,
            bath=bath,
            balcony=balcony,
            is_ready_to_move=bool(ready_flag),
        )

    def _component_distances(
        self, query: SimilarityQuery, row: pd.Series
    ) -> Dict[str, float]:
        """
        Per-feature distances in roughly [0, 1].

        Numeric: min(1, |Δ| / IQR_scale).
        Categorical / binary: 0 exact match, else 1.
        """
        sqft_d = min(
            1.0,
            abs(float(row["total_sqft"]) - query.total_sqft)
            / self.scales["total_sqft"],
        )
        bhk_d = min(
            1.0,
            abs(float(row["bhk"]) - query.bhk) / self.scales["bhk"],
        )
        bath_d = min(
            1.0,
            abs(float(row["bath"]) - query.bath) / self.scales["bath"],
        )
        bal_d = min(
            1.0,
            abs(float(row["balcony_for_distance"]) - query.balcony)
            / self.scales["balcony"],
        )
        return {
            "total_sqft": sqft_d,
            "location": 0.0
            if str(row["location_norm"]) == query.location
            else 1.0,
            "bhk": bhk_d,
            "bath": bath_d,
            "area_type": 0.0
            if str(row["area_type_norm"]) == query.area_type
            else 1.0,
            "balcony": bal_d,
            "is_ready_to_move": 0.0
            if int(row["is_ready_to_move"]) == int(query.is_ready_to_move)
            else 1.0,
        }

    def weighted_distance(
        self, query: SimilarityQuery, row: pd.Series
    ) -> float:
        parts = self._component_distances(query, row)
        return float(
            sum(FEATURE_WEIGHTS[name] * parts[name] for name in FEATURE_WEIGHTS)
        )

    @staticmethod
    def distance_to_similarity(distance: float) -> float:
        """
        Map non-negative weighted distance → similarity in [0, 1].

        similarity = 1 / (1 + distance)

        This is a ranking convenience, NOT a probability or confidence
        interval. Distance 0 → 1.0; larger distance → approaches 0.
        """
        if distance < 0:
            distance = 0.0
        return float(1.0 / (1.0 + distance))

    def _size_ratio(self, query: SimilarityQuery, row: pd.Series) -> float:
        return abs(float(row["total_sqft"]) - query.total_sqft) / query.total_sqft

    def _bhk_diff(self, query: SimilarityQuery, row: pd.Series) -> float:
        return abs(float(row["bhk"]) - query.bhk)

    def _build_candidate_mask(
        self, query: SimilarityQuery, limit: int
    ) -> Tuple[np.ndarray, bool]:
        """
        Prefer exact-location candidates with sensible size/BHK filters.
        Controlled fallback expands the pool without inventing localities.
        """
        assert self.frame is not None
        df = self.frame
        exact = df["location_norm"] == query.location
        size_hard = self._size_series(query) <= HARD_SIZE_RATIO
        size_pref = self._size_series(query) <= PREFERRED_SIZE_RATIO
        bhk_pref = self._bhk_series(query) <= PREFERRED_BHK_DIFF
        bhk_loose = self._bhk_series(query) <= FALLBACK_BHK_DIFF

        primary = exact & size_hard & bhk_pref
        used_fallback = False
        mask = primary.to_numpy()

        if int(primary.sum()) < limit:
            widened = exact & size_hard & bhk_loose
            mask = widened.to_numpy()

        if int(mask.sum()) < limit:
            # Controlled fallback: similar size/BHK anywhere; location mismatch
            # is penalized in the distance (weight 0.25), never treated as equal.
            used_fallback = True
            fallback = size_pref & bhk_pref
            mask = (exact & size_hard & bhk_loose) | fallback
            mask = mask.to_numpy()

        return mask, used_fallback

    def _size_series(self, query: SimilarityQuery) -> pd.Series:
        assert self.frame is not None
        return (self.frame["total_sqft"] - query.total_sqft).abs() / query.total_sqft

    def _bhk_series(self, query: SimilarityQuery) -> pd.Series:
        assert self.frame is not None
        return (self.frame["bhk"] - query.bhk).abs()

    def _feature_tuple(self, row: pd.Series) -> Tuple[Any, ...]:
        bal = row["balcony"]
        bal_val = None if pd.isna(bal) else float(bal)
        return (
            str(row["location_norm"]),
            str(row["area_type_norm"]),
            round(float(row["total_sqft"]), 4),
            round(float(row["bhk"]), 4),
            round(float(row["bath"]), 4),
            bal_val,
            int(row["is_ready_to_move"]),
        )

    def _match_notes(
        self, query: SimilarityQuery, row: pd.Series, location_match: bool
    ) -> List[str]:
        notes: List[str] = []
        if location_match:
            notes.append("same_location")
        else:
            notes.append("location_fallback")
        if self._size_ratio(query, row) <= PREFERRED_SIZE_RATIO:
            notes.append("similar_size")
        if abs(float(row["bhk"]) - query.bhk) < 1e-9:
            notes.append("same_bhk")
        elif abs(float(row["bhk"]) - query.bhk) <= PREFERRED_BHK_DIFF:
            notes.append("nearby_bhk")
        if str(row["area_type_norm"]) == query.area_type:
            notes.append("same_area_type")
        if int(row["is_ready_to_move"]) == int(query.is_ready_to_move):
            notes.append("same_ready_status")
        return notes

    def find_similar(
        self,
        features: Dict[str, Any],
        *,
        limit: int = DEFAULT_LIMIT,
        min_similarity: float = MIN_SIMILARITY,
    ) -> Dict[str, Any]:
        self.ensure_loaded()
        assert self.frame is not None

        if not isinstance(limit, int) or limit < 1 or limit > MAX_LIMIT:
            raise ValueError(f"limit must be an integer from 1 to {MAX_LIMIT}")
        if not math.isfinite(float(min_similarity)):
            raise ValueError("min_similarity must be finite")
        min_similarity = float(min_similarity)
        if min_similarity < 0.0 or min_similarity > 1.0:
            raise ValueError("min_similarity must be between 0 and 1")

        query = self.normalize_query(features)
        mask, _used_fallback = self._build_candidate_mask(query, limit)
        candidates = self.frame.loc[mask]

        scored: List[Dict[str, Any]] = []
        for _, row in candidates.iterrows():
            distance = self.weighted_distance(query, row)
            similarity = self.distance_to_similarity(distance)
            if similarity < min_similarity:
                continue
            location_match = str(row["location_norm"]) == query.location
            balcony_raw = row["balcony"]
            balcony_out = (
                None
                if pd.isna(balcony_raw)
                else float(balcony_raw)
            )
            scored.append(
                {
                    "similarity": round(similarity, 6),
                    "distance": distance,
                    "row_id": int(row["_row_id"]),
                    "feature_tuple": self._feature_tuple(row),
                    "location": str(row["location_norm"]),
                    "area_type": str(row["area_type_norm"]),
                    "total_sqft": float(row["total_sqft"]),
                    "bhk": float(row["bhk"]),
                    "bath": float(row["bath"]),
                    "balcony": balcony_out,
                    "is_ready_to_move": bool(int(row["is_ready_to_move"])),
                    # Reference only — excluded from distance above.
                    "listed_price_lakhs": float(row["price"]),
                    "listed_price_per_sqft": float(row["price_per_sqft"])
                    if pd.notna(row["price_per_sqft"])
                    else None,
                    "location_match": location_match,
                    "match_notes": self._match_notes(query, row, location_match),
                }
            )

        # Deterministic order: higher similarity first; tie-break by row_id.
        scored.sort(key=lambda item: (-item["similarity"], item["row_id"]))

        results: List[Dict[str, Any]] = []
        seen_tuples = set()
        for item in scored:
            tup = item["feature_tuple"]
            if tup in seen_tuples:
                continue
            seen_tuples.add(tup)
            results.append(item)
            if len(results) >= limit:
                break

        public_results = []
        for rank, item in enumerate(results, start=1):
            public_results.append(
                {
                    "rank": rank,
                    "similarity": item["similarity"],
                    "location": item["location"],
                    "area_type": item["area_type"],
                    "total_sqft": item["total_sqft"],
                    "bhk": item["bhk"],
                    "bath": item["bath"],
                    "balcony": item["balcony"],
                    "is_ready_to_move": item["is_ready_to_move"],
                    "listed_price_lakhs": round(item["listed_price_lakhs"], 2),
                    "listed_price_per_sqft": (
                        None
                        if item["listed_price_per_sqft"] is None
                        else round(float(item["listed_price_per_sqft"]), 2)
                    ),
                    "match_notes": item["match_notes"],
                    "location_match": item["location_match"],
                }
            )

        payload: Dict[str, Any] = {
            "query": query.as_public_dict(),
            "count": len(public_results),
            "method": METHOD_NAME,
            "disclaimer": DISCLAIMER,
            "results": public_results,
        }
        if not public_results:
            payload["message"] = EMPTY_MESSAGE
        return payload


_service: Optional[SimilarPropertiesService] = None


def get_similar_properties_service(
    dataset_path: Optional[Path] = None,
    *,
    force_reload: bool = False,
) -> SimilarPropertiesService:
    """Process-wide cached service (CSV loaded once)."""
    global _service
    if force_reload or _service is None:
        _service = SimilarPropertiesService(dataset_path=dataset_path)
    elif dataset_path is not None and Path(dataset_path) != _service.dataset_path:
        _service = SimilarPropertiesService(dataset_path=dataset_path)
    return _service


def reset_similar_properties_service() -> None:
    """Test helper to clear the singleton."""
    global _service
    _service = None
