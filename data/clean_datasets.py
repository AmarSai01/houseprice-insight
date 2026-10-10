"""
HousePrice Insight — reproducible data cleaning.

Reads ONLY from data/raw/
Writes ONLY to data/processed/ and data/reports/cleaning_report.md

Does not modify raw files, train models, or touch application code.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
PROCESSED_DIR = ROOT / "processed"
REPORTS_DIR = ROOT / "reports"

PROPERTY_RAW = RAW_DIR / "bengaluru_house_data_raw.csv"
MARKET_RAW = RAW_DIR / "bengaluru_market_history_raw.csv"
PROPERTY_CLEAN = PROCESSED_DIR / "bengaluru_property_clean.csv"
MARKET_CLEAN = PROCESSED_DIR / "bengaluru_market_history_clean.csv"
CLEANING_REPORT = REPORTS_DIR / "cleaning_report.md"

KNOWN_MARKET_AREAS = ["Devanahalli", "Indiranagar", "Whitefield", "Yelahanka"]

# Standard area conversions to square feet
SQFT_PER_SQ_METER = 10.76391041671
SQFT_PER_SQ_YARD = 9.0
SQFT_PER_PERCH = 272.25  # 16.5 ft x 16.5 ft
SQFT_PER_ACRE = 43560.0
SQFT_PER_CENT = 435.6  # 1/100 acre

RANGE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$")
UNIT_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(sq\.?\s*meters?|sq\.?\s*meter|sq\.?\s*yards?|sq\.?\s*yard|"
    r"perch|acres?|cents?|sq\.?\s*ft|sqft|sq\.\s*feet)?\s*$",
    re.IGNORECASE,
)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_snake_case(name: str) -> str:
    text = str(name).strip()
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^0-9a-zA-Z_]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").lower()
    return text


def normalize_locality_safe(value) -> str | None:
    """Safe locality normalization for processed data and mapping analysis."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" ,;")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_locality_key(value) -> str | None:
    """Analysis-only key for market mapping (does not rewrite raw locality identity)."""
    base = normalize_locality_safe(value)
    if base is None:
        return None
    key = base.lower()
    key = re.sub(r"[^\w\s]", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    key = key.replace("bangalore", "bengaluru")
    # Strip a trailing generic 'road' only for mapping key comparisons
    key = re.sub(r"\s+road$", "", key).strip()
    return key or None


def parse_bhk(size_value) -> float:
    if pd.isna(size_value):
        return np.nan
    text = str(size_value).strip()
    if not text:
        return np.nan
    # "1 RK" treated as 1 bedroom-equivalent for modeling readiness
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return np.nan
    return float(match.group(1))


def parse_total_sqft(value) -> tuple[float, str]:
    """
    Returns (numeric_sqft, status)
    status in: numeric, range_midpoint, unit_converted, invalid, missing
    """
    if pd.isna(value):
        return np.nan, "missing"
    text = str(value).strip()
    if not text:
        return np.nan, "missing"

    # Plain numeric (allow commas)
    plain = text.replace(",", "")
    try:
        number = float(plain)
        if number > 0:
            return number, "numeric"
    except ValueError:
        pass

    range_match = RANGE_RE.match(text.replace(",", ""))
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        if low > 0 and high > 0:
            return (low + high) / 2.0, "range_midpoint"
        return np.nan, "invalid"

    unit_match = UNIT_RE.match(text.replace(",", ""))
    if unit_match:
        amount = float(unit_match.group(1))
        unit = (unit_match.group(2) or "").lower().replace(" ", "")
        unit = unit.replace(".", "")
        if amount <= 0:
            return np.nan, "invalid"
        if unit in {"sqmeter", "sqmeters", "sqm"}:
            return amount * SQFT_PER_SQ_METER, "unit_converted"
        if unit in {"sqyard", "sqyards", "sqy"}:
            return amount * SQFT_PER_SQ_YARD, "unit_converted"
        if unit == "perch":
            return amount * SQFT_PER_PERCH, "unit_converted"
        if unit in {"acre", "acres"}:
            return amount * SQFT_PER_ACRE, "unit_converted"
        if unit in {"cent", "cents"}:
            return amount * SQFT_PER_CENT, "unit_converted"
        if unit in {"sqft", "sqfeet", ""}:
            return amount, "numeric" if unit else "invalid"

    # Fallback patterns like "34.46Sq. Meter"
    lowered = text.lower().replace(",", "")
    num_match = re.search(r"(\d+(?:\.\d+)?)", lowered)
    if not num_match:
        return np.nan, "invalid"
    amount = float(num_match.group(1))
    if "sq. meter" in lowered or "sq meter" in lowered or "sq.meter" in lowered:
        return amount * SQFT_PER_SQ_METER, "unit_converted"
    if "sq. yard" in lowered or "sq yard" in lowered or "sq.yard" in lowered:
        return amount * SQFT_PER_SQ_YARD, "unit_converted"
    if "perch" in lowered:
        return amount * SQFT_PER_PERCH, "unit_converted"
    if "acre" in lowered:
        return amount * SQFT_PER_ACRE, "unit_converted"
    if "cent" in lowered:
        return amount * SQFT_PER_CENT, "unit_converted"
    return np.nan, "invalid"


def clean_property(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats: dict = {
        "raw_rows": int(len(df_raw)),
        "raw_columns": list(df_raw.columns),
    }

    df = df_raw.copy()
    df.columns = [to_snake_case(c) for c in df.columns]
    stats["columns_after_snake_case"] = list(df.columns)

    # Exact duplicates
    dup_count = int(df.duplicated().sum())
    stats["duplicate_rows_before_removal"] = dup_count
    df = df.drop_duplicates().reset_index(drop=True)
    stats["rows_after_dedup"] = int(len(df))

    # Location normalization
    df["location"] = df["location"].map(normalize_locality_safe)
    # Documented safe mappings for punctuation-only variants
    safe_location_map = {
        "Whitefield,": "Whitefield",
    }
    mapped = df["location"].isin(safe_location_map.keys()).sum()
    df["location"] = df["location"].replace(safe_location_map)
    stats["safe_location_mappings_applied"] = int(mapped)
    stats["safe_location_mapping"] = safe_location_map

    # Keep original size for traceability, parse bhk
    df["size_raw"] = df["size"]
    df["bhk"] = df["size"].map(parse_bhk)
    stats["bhk_parsed_non_null"] = int(df["bhk"].notna().sum())
    stats["bhk_parse_failed"] = int(df["bhk"].isna().sum())

    # total_sqft parsing
    parsed = df["total_sqft"].map(parse_total_sqft)
    df["total_sqft"] = [p[0] for p in parsed]
    df["total_sqft_parse_status"] = [p[1] for p in parsed]
    status_counts = df["total_sqft_parse_status"].value_counts().to_dict()
    stats["sqft_parse_status_counts"] = {str(k): int(v) for k, v in status_counts.items()}
    stats["range_sqft_conversions"] = int(status_counts.get("range_midpoint", 0))
    stats["unit_sqft_conversions"] = int(status_counts.get("unit_converted", 0))
    stats["invalid_unusable_sqft"] = int(status_counts.get("invalid", 0))

    # Numeric conversions
    for col in ["bath", "balcony", "price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Missing-value treatment before validity filters
    missing_before = {
        "location": int(df["location"].isna().sum()),
        "total_sqft": int(df["total_sqft"].isna().sum()),
        "bhk": int(df["bhk"].isna().sum()),
        "price": int(df["price"].isna().sum()),
        "bath": int(df["bath"].isna().sum()),
        "balcony": int(df["balcony"].isna().sum()),
        "society": int(df["society"].isna().sum()) if "society" in df.columns else None,
    }
    stats["missing_before_row_filters"] = missing_before

    # Required fields: drop only when unrecovered
    required_mask = (
        df["location"].notna()
        & df["total_sqft"].notna()
        & df["bhk"].notna()
        & df["price"].notna()
    )
    stats["rows_dropped_missing_required"] = int((~required_mask).sum())
    df = df.loc[required_mask].copy()

    # bath imputation: median bath within same bhk, else global median
    bath_missing_before = int(df["bath"].isna().sum())
    bhk_medians = df.groupby("bhk")["bath"].median()
    global_bath_median = float(df["bath"].median()) if df["bath"].notna().any() else np.nan

    def impute_bath(row):
        if pd.notna(row["bath"]):
            return row["bath"]
        bhk_val = row["bhk"]
        if pd.notna(bhk_val) and bhk_val in bhk_medians.index and pd.notna(bhk_medians.loc[bhk_val]):
            return float(bhk_medians.loc[bhk_val])
        return global_bath_median

    df["bath"] = df.apply(impute_bath, axis=1)
    stats["bath_missing_before_imputation"] = bath_missing_before
    stats["bath_imputed_count"] = bath_missing_before - int(df["bath"].isna().sum())
    stats["bath_imputation_strategy"] = (
        "median bath within same bhk; fallback to global median bath"
    )

    # balcony: preserve missingness (do not fill with 0)
    stats["balcony_missing_preserved"] = int(df["balcony"].isna().sum())
    stats["balcony_strategy"] = "preserve NaN; do not impute with zero"

    # society: keep column, do not drop rows for missing society
    if "society" in df.columns:
        stats["society_missing_after_required_filter"] = int(df["society"].isna().sum())
        stats["society_strategy"] = (
            "retain column for traceability/EDA; high missingness (~41% raw) "
            "so it is NOT recommended as an ML feature yet"
        )

    # price_per_sqft in INR/sqft (price is in lakhs in this dataset)
    df["price_per_sqft"] = (df["price"] * 100000.0) / df["total_sqft"]
    stats["price_unit_note"] = (
        "Raw `price` is treated as INR lakhs (dataset convention). "
        "`price_per_sqft` is derived as (price * 100000) / total_sqft in INR per sqft "
        "for analytics only. It must NOT be used as an ML input feature for predicting price."
    )

    # Invalid / impossible observation filters
    invalid_rules = []
    before = len(df)

    mask_invalid = (
        (df["total_sqft"] <= 0)
        | (df["price"] <= 0)
        | (df["bhk"] <= 0)
        | (df["bath"] <= 0)
    )
    invalid_rules.append(("non_positive_core_fields", int(mask_invalid.sum())))
    df = df.loc[~mask_invalid].copy()

    # Conservative outlier / error filters (documented)
    # These target clear data errors, not merely expensive properties.
    outlier_masks = {
        "total_sqft_lt_100": df["total_sqft"] < 100,
        "total_sqft_gt_20000": df["total_sqft"] > 20000,
        "bhk_gt_9": df["bhk"] > 9,
        "bath_gt_9": df["bath"] > 9,
        "bath_gt_bhk_plus_3": df["bath"] > (df["bhk"] + 3),
        "price_per_sqft_lt_1000": df["price_per_sqft"] < 1000,
        "price_per_sqft_gt_50000": df["price_per_sqft"] > 50000,
        "unrealistic_tiny_multibhk": (df["bhk"] >= 3) & (df["total_sqft"] < 400),
    }
    outlier_counts = {name: int(mask.sum()) for name, mask in outlier_masks.items()}
    combined_outlier = np.zeros(len(df), dtype=bool)
    for mask in outlier_masks.values():
        combined_outlier |= mask.to_numpy()
    stats["outlier_rule_counts"] = outlier_counts
    stats["outlier_rows_removed"] = int(combined_outlier.sum())
    stats["outlier_rules"] = {
        "total_sqft_lt_100": "Residential listings under 100 sqft after conversion are treated as errors.",
        "total_sqft_gt_20000": "Values above 20,000 sqft are treated as land/misparsed errors for this housing model scope.",
        "bhk_gt_9": "BHK > 9 is treated as a recording error for this dataset's residential scope.",
        "bath_gt_9": "Bath > 9 is treated as a recording error for this dataset's residential scope.",
        "bath_gt_bhk_plus_3": "Bathrooms exceeding BHK+3 are treated as inconsistent records.",
        "price_per_sqft_lt_1000": "INR/sqft below 1,000 is treated as an error given Bengaluru market ranges.",
        "price_per_sqft_gt_50000": "INR/sqft above 50,000 is treated as an error/outlier beyond plausible listing quality.",
        "unrealistic_tiny_multibhk": "3+ BHK with under 400 sqft is treated as inconsistent.",
        "note": "High absolute price alone is NOT removed if size and price/sqft are plausible.",
    }
    df = df.loc[~combined_outlier].copy()
    stats["rows_after_outlier_filters"] = int(len(df))
    stats["rows_removed_total_from_deduped"] = int(stats["rows_after_dedup"] - len(df))

    # Final column selection
    keep_cols = [
        "location",
        "area_type",
        "availability",
        "bhk",
        "total_sqft",
        "bath",
        "balcony",
        "price",
        "price_per_sqft",
        "society",
        "size_raw",
        "total_sqft_parse_status",
    ]
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].reset_index(drop=True)

    # dtypes
    df["bhk"] = df["bhk"].astype(float)
    df["total_sqft"] = df["total_sqft"].astype(float)
    df["bath"] = df["bath"].astype(float)
    df["price"] = df["price"].astype(float)
    df["price_per_sqft"] = df["price_per_sqft"].astype(float)

    # Second-pass dedup: normalization/parsing can make previously distinct rows identical
    post_dedup = int(df.duplicated().sum())
    stats["duplicate_rows_after_transforms"] = post_dedup
    if post_dedup:
        df = df.drop_duplicates().reset_index(drop=True)
    stats["duplicate_rows_removed_total"] = (
        int(stats["duplicate_rows_before_removal"]) + post_dedup
    )

    stats["clean_rows"] = int(len(df))
    stats["rows_removed_from_raw"] = int(stats["raw_rows"] - stats["clean_rows"])
    stats["unique_locations"] = int(df["location"].nunique())
    loc_counts = df["location"].value_counts()
    stats["locations_ge_10"] = int((loc_counts >= 10).sum())
    stats["locations_lt_10"] = int((loc_counts < 10).sum())
    stats["final_columns"] = list(df.columns)
    stats["duplicate_rows_in_clean"] = int(df.duplicated().sum())
    stats["invalid_price_or_sqft_remaining"] = int(
        ((df["price"] <= 0) | (df["total_sqft"] <= 0)).sum()
    )

    # Locality statistics for report (not deleting sparse localities)
    loc_stats = (
        df.groupby("location", as_index=False)
        .agg(
            record_count=("price", "size"),
            median_price_per_sqft=("price_per_sqft", "median"),
            median_price_lakhs=("price", "median"),
        )
        .sort_values("record_count", ascending=False)
    )
    stats["locality_stats_top30"] = loc_stats.head(30).to_dict(orient="records")
    stats["sparse_locality_stats_sample"] = (
        loc_stats[loc_stats["record_count"] < 10].head(30).to_dict(orient="records")
    )
    stats["locality_stats_path_note"] = (
        "Sparse localities (<10 records) are retained in the cleaned dataset."
    )

    # Market mapping coverage (analysis only)
    market_keys = {normalize_locality_key(a): a for a in KNOWN_MARKET_AREAS}
    df["_map_key"] = df["location"].map(normalize_locality_key)
    key_to_market = {}
    for key, market_area in market_keys.items():
        key_to_market[key] = market_area
    # Also allow keys that normalize to these markets (e.g., Devanahalli Road -> devanahalli)
    df["market_area"] = df["_map_key"].map(key_to_market)
    # Expand: if key equals a known key after stripping road already in normalize_locality_key
    covered_mask = df["market_area"].notna()
    stats["market_coverage"] = {
        "supported_market_areas": KNOWN_MARKET_AREAS,
        "property_records_mapped": int(covered_mask.sum()),
        "property_records_not_mapped": int((~covered_mask).sum()),
        "mapped_location_names": sorted(df.loc[covered_mask, "location"].dropna().unique().tolist()),
        "mapping_pairs": sorted(
            {
                (loc, mkt)
                for loc, mkt in zip(
                    df.loc[covered_mask, "location"], df.loc[covered_mask, "market_area"]
                )
            }
        ),
    }
    # Keep market_area in clean file as optional linkage helper (not a leakage feature)
    df = df.drop(columns=["_map_key"])
    stats["final_columns"] = list(df.columns)

    return df, stats


def clean_market(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats: dict = {
        "raw_rows": int(len(df_raw)),
        "raw_columns": list(df_raw.columns),
    }
    df = df_raw.copy()
    df.columns = [to_snake_case(c) for c in df.columns]

    dup_count = int(df.duplicated().sum())
    stats["duplicate_rows_before_removal"] = dup_count
    df = df.drop_duplicates().reset_index(drop=True)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
    df["area"] = df["area"].map(normalize_locality_safe)

    for col in ["avg_price_per_sqft", "base_price", "index_100", "avg_price_prev_year", "yoy_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Date vs year/month consistency
    consistent = (
        df["date"].notna()
        & df["year"].notna()
        & df["month"].notna()
        & (df["date"].dt.year == df["year"])
        & (df["date"].dt.month == df["month"])
    )
    stats["date_year_month_inconsistencies"] = int((~consistent).sum())
    if int((~consistent).sum()) > 0:
        # Prefer parsed date fields when inconsistent
        df.loc[~consistent, "year"] = df.loc[~consistent, "date"].dt.year.astype("Int64")
        df.loc[~consistent, "month"] = df.loc[~consistent, "date"].dt.month.astype("Int64")

    # Validate known areas only (do not invent areas)
    stats["areas_found"] = sorted(df["area"].dropna().unique().tolist())
    unexpected_areas = sorted(set(stats["areas_found"]) - set(KNOWN_MARKET_AREAS))
    missing_expected = sorted(set(KNOWN_MARKET_AREAS) - set(stats["areas_found"]))
    stats["unexpected_areas"] = unexpected_areas
    stats["missing_expected_areas"] = missing_expected
    if unexpected_areas:
        df = df[df["area"].isin(KNOWN_MARKET_AREAS)].copy()

    # Date range checks
    stats["min_date"] = str(df["date"].min().date()) if df["date"].notna().any() else None
    stats["max_date"] = str(df["date"].max().date()) if df["date"].notna().any() else None
    stats["expected_min_date"] = "2015-01-01"
    stats["expected_max_date"] = "2025-12-01"

    # Monthly continuity / duplicates per area
    continuity = {}
    for area, group in df.groupby("area"):
        periods = group["date"].dt.to_period("M")
        dup_months = int(periods.duplicated().sum())
        observed = set(periods.dropna().unique())
        if observed:
            full = pd.period_range(min(observed), max(observed), freq="M")
            missing = [str(p) for p in full if p not in observed]
        else:
            missing = []
        continuity[str(area)] = {
            "rows": int(len(group)),
            "duplicate_months": dup_months,
            "missing_months_count": len(missing),
            "missing_months": missing,
            "min_date": str(group["date"].min().date()),
            "max_date": str(group["date"].max().date()),
        }
    stats["monthly_continuity"] = continuity

    # Keep YoY gaps as NaN (do not fill with 0)
    stats["yoy_pct_missing"] = int(df["yoy_pct"].isna().sum())
    stats["avg_price_prev_year_missing"] = int(df["avg_price_prev_year"].isna().sum())
    stats["yoy_strategy"] = (
        "Preserve NaN for first-year baseline gaps; do not impute with zero."
    )

    # Validate avg_price_per_sqft
    invalid_pps = df["avg_price_per_sqft"].isna() | (df["avg_price_per_sqft"] <= 0)
    stats["invalid_avg_price_per_sqft_rows"] = int(invalid_pps.sum())
    # Flag extremes for report but do not remove valid high markets blindly
    stats["avg_price_per_sqft_stats"] = {
        "min": float(df["avg_price_per_sqft"].min()),
        "max": float(df["avg_price_per_sqft"].max()),
        "median": float(df["avg_price_per_sqft"].median()),
    }
    stats["extreme_flags"] = {
        "avg_price_per_sqft_gt_30000": int((df["avg_price_per_sqft"] > 30000).sum()),
        "avg_price_per_sqft_lt_1000": int((df["avg_price_per_sqft"] < 1000).sum()),
    }
    # Only remove non-positive/missing price rows if any
    df = df.loc[~invalid_pps].copy()

    # Sort for usability
    df = df.sort_values(["area", "date"]).reset_index(drop=True)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    final_cols = [
        "date",
        "year",
        "month",
        "area",
        "avg_price_per_sqft",
        "base_price",
        "index_100",
        "avg_price_prev_year",
        "yoy_pct",
    ]
    df = df[final_cols]
    stats["clean_rows"] = int(len(df))
    stats["rows_removed_from_raw"] = int(stats["raw_rows"] - stats["clean_rows"])
    stats["unique_areas"] = int(df["area"].nunique())
    stats["final_columns"] = list(df.columns)
    stats["duplicate_rows_in_clean"] = int(df.duplicated().sum())
    return df, stats


def render_report(
    prop_stats: dict,
    market_stats: dict,
    prop_raw_hash: str,
    market_raw_hash: str,
    validation: dict,
) -> str:
    lines: list[str] = []
    lines.append("# HousePrice Insight — Data Cleaning Report")
    lines.append("")
    lines.append(f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("Raw files were read only. Processed outputs were written to `data/processed/`.")
    lines.append("")
    lines.append("## Property Dataset")
    lines.append("")
    lines.append(f"- **Raw rows:** {prop_stats['raw_rows']:,}")
    lines.append(f"- **Clean rows:** {prop_stats['clean_rows']:,}")
    lines.append(f"- **Rows removed (raw → clean):** {prop_stats['rows_removed_from_raw']:,}")
    lines.append(
        f"- **Duplicate rows removed:** "
        f"{prop_stats.get('duplicate_rows_removed_total', prop_stats['duplicate_rows_before_removal']):,} "
        f"(exact raw duplicates: {prop_stats['duplicate_rows_before_removal']:,}; "
        f"post-transform duplicates: {prop_stats.get('duplicate_rows_after_transforms', 0):,})"
    )
    lines.append(f"- **Range sqft conversions:** {prop_stats['range_sqft_conversions']:,}")
    lines.append(f"- **Unit conversions:** {prop_stats['unit_sqft_conversions']:,}")
    lines.append(f"- **Invalid/unusable sqft values:** {prop_stats['invalid_unusable_sqft']:,}")
    lines.append(
        f"- **Rows dropped for missing required fields "
        f"(location/total_sqft/bhk/price):** {prop_stats['rows_dropped_missing_required']:,}"
    )
    lines.append(f"- **Outlier/error rows removed:** {prop_stats['outlier_rows_removed']:,}")
    lines.append(f"- **Number of locations:** {prop_stats['unique_locations']:,}")
    lines.append(f"- **Locations with >= 10 records:** {prop_stats['locations_ge_10']:,}")
    lines.append(f"- **Sparse locations (<10 records, retained):** {prop_stats['locations_lt_10']:,}")
    lines.append(f"- **Final columns:** {', '.join(prop_stats['final_columns'])}")
    lines.append("")
    lines.append("### Missing-value treatment")
    lines.append("")
    lines.append(f"- Missing before required-field filter: `{prop_stats['missing_before_row_filters']}`")
    lines.append(
        f"- Bath imputation: {prop_stats['bath_imputation_strategy']} "
        f"(imputed {prop_stats['bath_imputed_count']} values)."
    )
    lines.append(f"- Balcony: {prop_stats['balcony_strategy']}")
    lines.append(f"- Society: {prop_stats.get('society_strategy')}")
    lines.append("")
    lines.append("### Sqft parse status counts")
    lines.append("")
    for k, v in prop_stats["sqft_parse_status_counts"].items():
        lines.append(f"- `{k}`: {v:,}")
    lines.append("")
    lines.append("### Outlier rules")
    lines.append("")
    for rule, desc in prop_stats["outlier_rules"].items():
        count = prop_stats["outlier_rule_counts"].get(rule, "n/a")
        lines.append(f"- `{rule}` (removed/count contribution {count}): {desc}")
    lines.append("")
    lines.append("### Safe location mapping")
    lines.append("")
    lines.append(f"- Mapping applied: `{prop_stats['safe_location_mapping']}`")
    lines.append(f"- Rows affected: {prop_stats['safe_location_mappings_applied']}")
    lines.append("")
    lines.append("### Sparse-location statistics (sample)")
    lines.append("")
    lines.append("Sparse localities were **kept**. Sample of sparse localities:")
    lines.append("")
    for row in prop_stats["sparse_locality_stats_sample"][:15]:
        lines.append(
            f"- {row['location']}: count={row['record_count']}, "
            f"median_price_per_sqft={row['median_price_per_sqft']:.2f}"
        )
    lines.append("")
    lines.append("### Top localities by record count")
    lines.append("")
    for row in prop_stats["locality_stats_top30"][:15]:
        lines.append(
            f"- {row['location']}: count={row['record_count']}, "
            f"median_price_per_sqft={row['median_price_per_sqft']:.2f}"
        )
    lines.append("")

    lines.append("## Market Dataset")
    lines.append("")
    lines.append(f"- **Raw rows:** {market_stats['raw_rows']:,}")
    lines.append(f"- **Clean rows:** {market_stats['clean_rows']:,}")
    lines.append(
        f"- **Duplicates removed:** {market_stats['duplicate_rows_before_removal']:,}"
    )
    lines.append(f"- **Date range:** {market_stats['min_date']} → {market_stats['max_date']}")
    lines.append(f"- **Number of areas:** {market_stats['unique_areas']}")
    lines.append(f"- **Areas:** {', '.join(market_stats['areas_found'])}")
    lines.append(
        f"- **Date/year/month inconsistencies repaired from date:** "
        f"{market_stats['date_year_month_inconsistencies']}"
    )
    lines.append(f"- **Missing YoY values preserved as NaN:** {market_stats['yoy_pct_missing']}")
    lines.append(
        f"- **Missing avg_price_prev_year preserved as NaN:** "
        f"{market_stats['avg_price_prev_year_missing']}"
    )
    lines.append(
        f"- **Invalid avg_price_per_sqft rows removed:** "
        f"{market_stats['invalid_avg_price_per_sqft_rows']}"
    )
    lines.append(f"- **Final columns:** {', '.join(market_stats['final_columns'])}")
    lines.append("")
    lines.append("### Monthly continuity")
    lines.append("")
    for area, info in market_stats["monthly_continuity"].items():
        lines.append(
            f"- **{area}:** rows={info['rows']}, duplicate_months={info['duplicate_months']}, "
            f"missing_months={info['missing_months_count']}, "
            f"range={info['min_date']} → {info['max_date']}"
        )
        if info["missing_months"]:
            lines.append(f"  - missing: {', '.join(info['missing_months'][:12])}")
    lines.append("")

    cov = prop_stats["market_coverage"]
    lines.append("## Market Coverage")
    lines.append("")
    lines.append("### Market Insight Coverage")
    lines.append("")
    lines.append(
        "Historical Market Insights can be linked only to property localities that safely "
        "map to one of the four market areas."
    )
    lines.append("")
    lines.append(f"- **Supported market areas:** {', '.join(cov['supported_market_areas'])}")
    lines.append(f"- **Property records mapped:** {cov['property_records_mapped']:,}")
    lines.append(f"- **Property records not mapped:** {cov['property_records_not_mapped']:,}")
    lines.append(f"- **Mapped property locality names:** {', '.join(cov['mapped_location_names'])}")
    lines.append("- **Mapping pairs (property location → market area):**")
    for loc, mkt in cov["mapping_pairs"]:
        lines.append(f"  - `{loc}` → `{mkt}`")
    lines.append("")
    lines.append(
        "All other Bengaluru property localities remain valid for ML price estimation but "
        "will not show locality-specific historical Market Insights with the current market dataset."
    )
    lines.append("")

    lines.append("## Data Quality Decisions")
    lines.append("")
    lines.append("1. Exact duplicate property rows were removed.")
    lines.append("2. Location cleanup was limited to trim/collapse whitespace and trailing punctuation.")
    lines.append("3. `Whitefield,` was mapped to `Whitefield` as a punctuation-only safe fix.")
    lines.append("4. BHK was parsed from `size` (including Bedroom / RK patterns); `size_raw` retained.")
    lines.append("5. Range sqft values used midpoint; unit-bearing values were converted to sqft.")
    lines.append("6. Required fields for a usable supervised row: location, total_sqft, bhk, price.")
    lines.append("7. Society missingness did **not** cause row deletion.")
    lines.append("8. Bath missing values were imputed by BHK-group median (fallback global median).")
    lines.append("9. Balcony missing values were preserved as NaN.")
    lines.append(
        "10. `price_per_sqft` uses INR/sqft via `(price_lakhs * 100000) / total_sqft` and is analytics-only."
    )
    lines.append(
        "11. Outlier removal targeted impossible/error configurations, not merely expensive homes."
    )
    lines.append("12. Sparse localities were retained for later encoding decisions.")
    lines.append("13. Market YoY baseline gaps remain NaN (not zero-filled).")
    lines.append("14. Market data stays monthly; no yearly aggregation was performed.")
    lines.append("")

    lines.append("## Future ML Considerations")
    lines.append("")
    lines.append("- **Target:** `price` (INR lakhs).")
    lines.append(
        "- **Do not use `price_per_sqft` as a model input** for predicting `price` "
        "(target leakage: it is derived from price and sqft)."
    )
    lines.append(
        "- Candidate input features later: `location` (encoded), `area_type`, `availability`, "
        "`bhk`, `total_sqft`, `bath`, `balcony` (with missingness handling), optionally mapped `market_area`."
    )
    lines.append(
        "- Locality encoding strategy still to decide (frequency threshold / Other bucket / target encoding with care)."
    )
    lines.append(
        "- Market history features should be joined carefully by mapped area and time; "
        "avoid leaking future market values into training rows if dates become available later."
    )
    lines.append("")

    lines.append("## Validation Summary")
    lines.append("")
    for key, value in validation.items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("### Raw file integrity hashes (SHA-256)")
    lines.append("")
    lines.append(f"- property raw: `{prop_raw_hash}`")
    lines.append(f"- market raw: `{market_raw_hash}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def validate(
    prop_clean: pd.DataFrame,
    market_clean: pd.DataFrame,
    prop_raw_hash_before: str,
    market_raw_hash_before: str,
) -> dict:
    prop_raw_hash_after = file_sha256(PROPERTY_RAW)
    market_raw_hash_after = file_sha256(MARKET_RAW)
    house_data = ROOT / "house_data.csv"

    results = {
        "no_nonpositive_property_price": bool((prop_clean["price"] > 0).all()),
        "no_nonpositive_property_sqft": bool((prop_clean["total_sqft"] > 0).all()),
        "property_numeric_ok": bool(
            all(
                pd.api.types.is_numeric_dtype(prop_clean[c])
                for c in ["bhk", "total_sqft", "bath", "price", "price_per_sqft"]
            )
        ),
        "property_no_duplicate_rows": bool(int(prop_clean.duplicated().sum()) == 0),
        "market_dates_parseable": bool(
            pd.to_datetime(market_clean["date"], errors="coerce").notna().all()
        ),
        "market_areas_valid": bool(
            set(market_clean["area"].unique()).issubset(set(KNOWN_MARKET_AREAS))
        ),
        "market_no_duplicate_rows": bool(int(market_clean.duplicated().sum()) == 0),
        "market_numeric_ok": bool(
            all(
                pd.api.types.is_numeric_dtype(market_clean[c])
                for c in ["avg_price_per_sqft", "base_price", "index_100"]
            )
        ),
        "raw_property_hash_unchanged": bool(prop_raw_hash_before == prop_raw_hash_after),
        "raw_market_hash_unchanged": bool(market_raw_hash_before == market_raw_hash_after),
        "house_data_csv_exists": bool(house_data.exists()),
        "house_data_csv_bytes": int(house_data.stat().st_size) if house_data.exists() else None,
    }
    return results


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not PROPERTY_RAW.exists() or not MARKET_RAW.exists():
        raise FileNotFoundError("Raw datasets not found under data/raw/")

    prop_raw_hash = file_sha256(PROPERTY_RAW)
    market_raw_hash = file_sha256(MARKET_RAW)

    prop_raw = pd.read_csv(PROPERTY_RAW)
    market_raw = pd.read_csv(MARKET_RAW)

    prop_clean, prop_stats = clean_property(prop_raw)
    market_clean, market_stats = clean_market(market_raw)

    prop_clean.to_csv(PROPERTY_CLEAN, index=False)
    market_clean.to_csv(MARKET_CLEAN, index=False)

    validation = validate(prop_clean, market_clean, prop_raw_hash, market_raw_hash)
    report = render_report(prop_stats, market_stats, prop_raw_hash, market_raw_hash, validation)
    CLEANING_REPORT.write_text(report, encoding="utf-8")

    # machine-readable side summary for convenience
    summary = {
        "property": {
            "raw_rows": prop_stats["raw_rows"],
            "clean_rows": prop_stats["clean_rows"],
            "duplicates_removed": prop_stats.get(
                "duplicate_rows_removed_total",
                prop_stats["duplicate_rows_before_removal"],
            ),
            "duplicates_removed_raw_exact": prop_stats["duplicate_rows_before_removal"],
            "duplicates_removed_post_transform": prop_stats.get(
                "duplicate_rows_after_transforms", 0
            ),
            "range_sqft_conversions": prop_stats["range_sqft_conversions"],
            "unit_sqft_conversions": prop_stats["unit_sqft_conversions"],
            "outlier_rows_removed": prop_stats["outlier_rows_removed"],
            "unique_locations": prop_stats["unique_locations"],
            "market_records_mapped": prop_stats["market_coverage"]["property_records_mapped"],
            "market_records_not_mapped": prop_stats["market_coverage"]["property_records_not_mapped"],
            "mapped_locations": prop_stats["market_coverage"]["mapped_location_names"],
        },
        "market": {
            "raw_rows": market_stats["raw_rows"],
            "clean_rows": market_stats["clean_rows"],
            "unique_areas": market_stats["unique_areas"],
            "min_date": market_stats["min_date"],
            "max_date": market_stats["max_date"],
            "yoy_missing": market_stats["yoy_pct_missing"],
        },
        "validation": validation,
    }
    (REPORTS_DIR / "cleaning_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("CLEANING_COMPLETE")
    print(f"PROPERTY_RAW_ROWS={prop_stats['raw_rows']}")
    print(f"PROPERTY_CLEAN_ROWS={prop_stats['clean_rows']}")
    print(f"PROPERTY_DUPES_REMOVED={prop_stats['duplicate_rows_before_removal']}")
    print(f"RANGE_SQFT={prop_stats['range_sqft_conversions']}")
    print(f"UNIT_SQFT={prop_stats['unit_sqft_conversions']}")
    print(f"OUTLIERS_REMOVED={prop_stats['outlier_rows_removed']}")
    print(f"UNIQUE_LOCATIONS={prop_stats['unique_locations']}")
    print(f"MARKET_RAW_ROWS={market_stats['raw_rows']}")
    print(f"MARKET_CLEAN_ROWS={market_stats['clean_rows']}")
    print(f"MARKET_AREAS={market_stats['unique_areas']}")
    print(f"MAPPED_PROPERTY_ROWS={prop_stats['market_coverage']['property_records_mapped']}")
    print(f"UNMAPPED_PROPERTY_ROWS={prop_stats['market_coverage']['property_records_not_mapped']}")
    print(f"VALIDATION_ALL_PASSED={all(bool(v) for k,v in validation.items() if k != 'house_data_csv_bytes')}")
    for k, v in validation.items():
        print(f"VALIDATE_{k}={v}")


if __name__ == "__main__":
    main()
