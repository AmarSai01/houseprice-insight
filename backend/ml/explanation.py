"""
Global model-level feature influence helpers.

Uses raw-feature permutation importance (MAE scoring). This is NOT local
attribution and must never be presented as per-property rupee contributions.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

FEATURE_LABELS = {
    "total_sqft": "Property size",
    "bath": "Bathrooms",
    "area_type": "Area type",
    "location": "Location",
    "bhk": "Bedrooms",
    "balcony": "Balcony",
    "availability": "Availability",
}

EXPLANATION_TYPE = "global_feature_influence"
EXPLANATION_SCOPE = "model"
EXPLANATION_METHOD = "permutation_importance_mae"
EXPLANATION_NOTE = (
    "Shows which property characteristics generally influence this model "
    "the most. This is not a breakdown of rupees for this specific estimate."
)

# Normalized importance = raw_mae / sum(raw_mae). Relative share of global
# permutation importance only — not probability, price %, or ₹ contribution.
IMPORTANCE_ROUND = 6


def _normalize_shares(raw_scores: Sequence[float]) -> List[float]:
    total = float(sum(raw_scores))
    if total <= 0:
        raise ValueError("Permutation importance totals must be positive.")
    return [round(float(score) / total, IMPORTANCE_ROUND) for score in raw_scores]


def build_global_feature_influence(
    feature_scores: Sequence[Tuple[str, float]],
) -> Dict[str, Any]:
    """
    Build a public explanation payload from (feature, raw_mae_importance) pairs.

    Importance values in the result are normalized shares of the total raw
    permutation importance (MAE). They are not local attributions.
    """
    cleaned: List[Tuple[str, float]] = []
    for feature, score in feature_scores:
        name = str(feature).strip()
        if not name:
            raise ValueError("Feature name must be non-empty.")
        value = float(score)
        if value < 0:
            raise ValueError(f"Negative importance for feature {name!r}.")
        cleaned.append((name, value))

    if not cleaned:
        raise ValueError("No permutation importance rows provided.")

    cleaned.sort(key=lambda item: item[1], reverse=True)
    shares = _normalize_shares([score for _, score in cleaned])

    factors = [
        {
            "feature": name,
            "label": FEATURE_LABELS.get(name, name.replace("_", " ").title()),
            "importance": share,
            "rank": index,
            "raw_importance_mae": round(score, 6),
        }
        for index, ((name, score), share) in enumerate(
            zip(cleaned, shares), start=1
        )
    ]

    return {
        "type": EXPLANATION_TYPE,
        "scope": EXPLANATION_SCOPE,
        "method": EXPLANATION_METHOD,
        "note": EXPLANATION_NOTE,
        "normalization": (
            "Each importance is raw permutation MAE divided by the sum of "
            "raw permutation MAE across features (relative share). Not a "
            "probability, price percentage, or rupee contribution."
        ),
        "factors": factors,
    }


def load_permutation_importance_csv(path: Path) -> Dict[str, Any]:
    """Load and validate permutation_importance_raw_features.csv."""
    if not path.exists():
        raise FileNotFoundError(f"Missing permutation importance CSV: {path}")

    rows: List[Tuple[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Permutation importance CSV has no header.")
        required = {"raw_feature", "permutation_importance_mae"}
        if not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                "Permutation importance CSV missing required columns: "
                f"{sorted(required)}"
            )
        for row in reader:
            feature = (row.get("raw_feature") or "").strip()
            raw = row.get("permutation_importance_mae")
            if not feature or raw is None or str(raw).strip() == "":
                raise ValueError("Malformed permutation importance row.")
            rows.append((feature, float(raw)))

    return build_global_feature_influence(rows)


def public_explanation_payload(
    explanation: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Strip internal-only fields before returning to API clients."""
    if not explanation:
        return None
    factors = []
    for factor in explanation.get("factors") or []:
        factors.append(
            {
                "feature": factor["feature"],
                "label": factor["label"],
                "importance": factor["importance"],
                "rank": factor["rank"],
            }
        )
    if not factors:
        return None
    return {
        "type": explanation.get("type", EXPLANATION_TYPE),
        "scope": explanation.get("scope", EXPLANATION_SCOPE),
        "method": explanation.get("method", EXPLANATION_METHOD),
        "note": explanation.get("note", EXPLANATION_NOTE),
        "factors": factors,
    }


def try_load_explanation(
    csv_path: Path,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Prefer the on-disk permutation CSV; fall back to metadata if present.

    Returns None when neither source is usable (prediction still works).
    """
    try:
        return load_permutation_importance_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not load permutation importance CSV (%s): %s",
            type(exc).__name__,
            exc,
        )

    meta_block = (metadata or {}).get("global_feature_influence")
    if isinstance(meta_block, dict) and meta_block.get("factors"):
        try:
            # Rebuild from stored raw values when available for consistency.
            raw_pairs = []
            for factor in meta_block["factors"]:
                if "raw_importance_mae" in factor:
                    raw_pairs.append(
                        (factor["feature"], float(factor["raw_importance_mae"]))
                    )
            if raw_pairs:
                return build_global_feature_influence(raw_pairs)
            # Accept already-normalized public factors from metadata.
            public = public_explanation_payload(meta_block)
            if public:
                return {
                    **meta_block,
                    "factors": [
                        {
                            **factor,
                            "raw_importance_mae": factor["importance"],
                        }
                        for factor in public["factors"]
                    ],
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not use metadata global_feature_influence (%s): %s",
                type(exc).__name__,
                exc,
            )
    return None
