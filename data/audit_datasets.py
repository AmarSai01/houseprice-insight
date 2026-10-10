"""
Dataset audit for HousePrice Insight.

Inspects RAW property and market CSVs only.
Does not modify raw files. Writes reports under data/reports/.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
REPORTS_DIR = ROOT / "reports"

PROPERTY_PATH = RAW_DIR / "bengaluru_house_data_raw.csv"
MARKET_PATH = RAW_DIR / "bengaluru_market_history_raw.csv"
MD_PATH = REPORTS_DIR / "dataset_audit.md"
JSON_PATH = REPORTS_DIR / "dataset_summary.json"

RANGE_SQFT_RE = re.compile(
    r"^\s*\d+(\.\d+)?\s*-\s*\d+(\.\d+)?\s*$"
)


def normalize_locality(value) -> str | None:
    """Normalize locality names for overlap analysis only (does not alter raw files)."""
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Common Bengaluru spelling variants for comparison only
    replacements = {
        "bangalore": "bengaluru",
        "bengalore": "bengaluru",
        " layout": " ",
        " road": " ",
        " nagar": " nagar",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_sqft_numeric(value):
    """Best-effort numeric parse for audit stats only."""
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if not text:
        return np.nan
    if RANGE_SQFT_RE.match(text):
        parts = re.split(r"\s*-\s*", text)
        try:
            return (float(parts[0]) + float(parts[1])) / 2.0
        except ValueError:
            return np.nan
    # Strip unit-like suffixes for audit classification
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned) if cleaned else np.nan
    except ValueError:
        return np.nan


def is_range_sqft(value) -> bool:
    if pd.isna(value):
        return False
    return bool(RANGE_SQFT_RE.match(str(value).strip()))


def is_unusual_sqft(value) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip()
    if not text:
        return False
    if is_range_sqft(text):
        return False
    try:
        float(text.replace(",", ""))
        return False
    except ValueError:
        return True


def file_size_bytes(path: Path) -> int:
    return path.stat().st_size


def missing_report(df: pd.DataFrame) -> dict:
    missing = df.isna().sum()
    return {
        col: {"count": int(missing[col]), "pct": round(float(missing[col] / len(df) * 100), 2)}
        for col in df.columns
    }


def series_stats(series: pd.Series) -> dict:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"count": 0}
    return {
        "count": int(clean.shape[0]),
        "min": float(clean.min()),
        "max": float(clean.max()),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "std": float(clean.std(ddof=1)) if clean.shape[0] > 1 else 0.0,
        "p01": float(clean.quantile(0.01)),
        "p05": float(clean.quantile(0.05)),
        "p95": float(clean.quantile(0.95)),
        "p99": float(clean.quantile(0.99)),
    }


def audit_property(df: pd.DataFrame, path: Path) -> dict:
    n_rows, n_cols = df.shape
    dtypes = {c: str(t) for c, t in df.dtypes.items()}
    missing = missing_report(df)
    duplicate_rows = int(df.duplicated().sum())

    location_col = "location" if "location" in df.columns else None
    unique_locations = int(df[location_col].nunique(dropna=True)) if location_col else 0
    loc_counts = (
        df[location_col].fillna("(missing)").astype(str).value_counts()
        if location_col
        else pd.Series(dtype=int)
    )
    top30 = loc_counts.head(30).to_dict()
    records_per_location = {str(k): int(v) for k, v in loc_counts.items()}
    locs_ge_10 = int((loc_counts >= 10).sum())
    locs_lt_10 = int((loc_counts < 10).sum())

    size_counts = (
        df["size"].fillna("(missing)").astype(str).value_counts().head(40).to_dict()
        if "size" in df.columns
        else {}
    )

    sqft_raw = df["total_sqft"] if "total_sqft" in df.columns else pd.Series(dtype=object)
    range_sqft_mask = sqft_raw.map(is_range_sqft)
    unusual_sqft_mask = sqft_raw.map(is_unusual_sqft)
    sqft_num = sqft_raw.map(parse_sqft_numeric)
    price = pd.to_numeric(df["price"], errors="coerce") if "price" in df.columns else pd.Series(dtype=float)
    bath = pd.to_numeric(df["bath"], errors="coerce") if "bath" in df.columns else pd.Series(dtype=float)
    balcony = (
        pd.to_numeric(df["balcony"], errors="coerce") if "balcony" in df.columns else pd.Series(dtype=float)
    )

    price_per_sqft = price * 100000.0 / sqft_num  # dataset prices are typically in lakhs

    # BHK extraction from size like "2 BHK"
    bhk = pd.Series(np.nan, index=df.index, dtype=float)
    if "size" in df.columns:
        bhk = df["size"].astype(str).str.extract(r"(\d+)", expand=False)
        bhk = pd.to_numeric(bhk, errors="coerce")

    suspicious = {
        "missing_location": int(df[location_col].isna().sum()) if location_col else 0,
        "missing_total_sqft": int(sqft_raw.isna().sum()) if len(sqft_raw) else 0,
        "missing_price": int(price.isna().sum()) if len(price) else 0,
        "range_total_sqft_rows": int(range_sqft_mask.sum()),
        "unusual_non_numeric_total_sqft_rows": int(unusual_sqft_mask.sum()),
        "price_non_positive": int((price <= 0).sum()) if len(price) else 0,
        "sqft_non_positive": int((sqft_num <= 0).sum()),
        "bath_gt_bhk_plus_2": int(((bath > (bhk + 2)) & bath.notna() & bhk.notna()).sum()),
        "bhk_ge_10": int((bhk >= 10).sum()),
        "bath_ge_10": int((bath >= 10).sum()),
        "sqft_lt_100": int((sqft_num < 100).sum()),
        "sqft_gt_20000": int((sqft_num > 20000).sum()),
        "price_lakhs_gt_2000": int((price > 2000).sum()) if len(price) else 0,
        "price_per_sqft_lt_1000": int((price_per_sqft < 1000).sum()),
        "price_per_sqft_gt_50000": int((price_per_sqft > 50000).sum()),
        "unrealistic_tiny_home": int(((bhk >= 3) & (sqft_num < 400)).sum()),
    }

    # Outlier heuristic using IQR on parsed price/sqft
    def iqr_outlier_count(s: pd.Series) -> int:
        clean = s.dropna()
        if clean.shape[0] < 20:
            return 0
        q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return 0
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return int(((clean < lower) | (clean > upper)).sum())

    outliers = {
        "price_iqr_outliers": iqr_outlier_count(price),
        "sqft_iqr_outliers": iqr_outlier_count(sqft_num),
        "price_per_sqft_iqr_outliers": iqr_outlier_count(price_per_sqft),
    }

    return {
        "path": str(path),
        "file_size_bytes": file_size_bytes(path),
        "rows": int(n_rows),
        "columns": int(n_cols),
        "column_names": list(df.columns),
        "dtypes": dtypes,
        "missing_values": missing,
        "duplicate_rows": duplicate_rows,
        "unique_locations": unique_locations,
        "top_30_locations": {str(k): int(v) for k, v in top30.items()},
        "records_per_location_count": len(records_per_location),
        "locations_with_lt_10_records": locs_lt_10,
        "locations_with_ge_10_records": locs_ge_10,
        "size_value_counts_top40": {str(k): int(v) for k, v in size_counts.items()},
        "total_sqft_stats": series_stats(sqft_num),
        "price_stats_lakhs": series_stats(price),
        "price_per_sqft_stats_inr": series_stats(price_per_sqft),
        "bathroom_stats": series_stats(bath),
        "balcony_stats": series_stats(balcony),
        "bhk_stats": series_stats(bhk),
        "range_total_sqft_rows": int(range_sqft_mask.sum()),
        "unusual_non_numeric_total_sqft_rows": int(unusual_sqft_mask.sum()),
        "sample_range_total_sqft": sqft_raw[range_sqft_mask].astype(str).head(15).tolist(),
        "sample_unusual_total_sqft": sqft_raw[unusual_sqft_mask].astype(str).head(15).tolist(),
        "suspicious_values": suspicious,
        "potential_outliers": outliers,
        "availability_top": (
            df["availability"].fillna("(missing)").astype(str).value_counts().head(20).to_dict()
            if "availability" in df.columns
            else {}
        ),
        "area_type_counts": (
            df["area_type"].fillna("(missing)").astype(str).value_counts().to_dict()
            if "area_type" in df.columns
            else {}
        ),
        "date_available": False,
        "notes": [
            "price values in this dataset are commonly expressed in INR lakhs.",
            "price_per_sqft computed as (price_lakhs * 100000) / total_sqft for audit only.",
        ],
    }


def audit_market(df: pd.DataFrame, path: Path) -> dict:
    n_rows, n_cols = df.shape
    dtypes = {c: str(t) for c, t in df.dtypes.items()}
    missing = missing_report(df)
    duplicate_rows = int(df.duplicated().sum())

    area_col = "area" if "area" in df.columns else None
    unique_areas = int(df[area_col].nunique(dropna=True)) if area_col else 0
    area_counts = (
        df[area_col].fillna("(missing)").astype(str).value_counts()
        if area_col
        else pd.Series(dtype=int)
    )

    dates = pd.to_datetime(df["date"], errors="coerce") if "date" in df.columns else pd.Series(dtype="datetime64[ns]")
    years = sorted(df["year"].dropna().unique().tolist()) if "year" in df.columns else []
    months = (
        df[["year", "month"]].dropna().drop_duplicates().shape[0]
        if {"year", "month"}.issubset(df.columns)
        else int(dates.dt.to_period("M").nunique())
    )

    pps = (
        pd.to_numeric(df["avg_price_per_sqft"], errors="coerce")
        if "avg_price_per_sqft" in df.columns
        else pd.Series(dtype=float)
    )
    yoy = pd.to_numeric(df["yoy_pct"], errors="coerce") if "yoy_pct" in df.columns else pd.Series(dtype=float)

    # Missing months by area: compare observed year-month pairs vs full span per area
    missing_months_by_area = {}
    complete_areas = []
    near_complete_areas = []
    insufficient_areas = []

    if area_col and "date" in df.columns:
        tmp = df.copy()
        tmp["_date"] = pd.to_datetime(tmp["date"], errors="coerce")
        tmp = tmp.dropna(subset=["_date", area_col])
        if not tmp.empty:
            global_start = tmp["_date"].min().to_period("M")
            global_end = tmp["_date"].max().to_period("M")
            full_span = pd.period_range(global_start, global_end, freq="M")
            expected_months = len(full_span)

            for area, group in tmp.groupby(area_col):
                observed = set(group["_date"].dt.to_period("M").unique())
                missing_month_list = [str(p) for p in full_span if p not in observed]
                missing_months_by_area[str(area)] = {
                    "observed_months": len(observed),
                    "expected_months_global_span": expected_months,
                    "missing_months_count": len(missing_month_list),
                    "missing_months_sample": missing_month_list[:12],
                }
                coverage = len(observed) / expected_months if expected_months else 0
                if coverage >= 0.98:
                    complete_areas.append(str(area))
                elif coverage >= 0.80:
                    near_complete_areas.append(str(area))
                else:
                    insufficient_areas.append(str(area))

    return {
        "path": str(path),
        "file_size_bytes": file_size_bytes(path),
        "rows": int(n_rows),
        "columns": int(n_cols),
        "column_names": list(df.columns),
        "dtypes": dtypes,
        "missing_values": missing,
        "duplicate_rows": duplicate_rows,
        "unique_areas": unique_areas,
        "records_per_area": {str(k): int(v) for k, v in area_counts.items()},
        "min_date": str(dates.min().date()) if dates.notna().any() else None,
        "max_date": str(dates.max().date()) if dates.notna().any() else None,
        "months_represented": int(months),
        "years_represented": [int(y) if not isinstance(y, str) else y for y in years]
        if years
        else sorted({int(d.year) for d in dates.dropna()}),
        "avg_price_per_sqft_stats": series_stats(pps),
        "yoy_pct_stats": series_stats(yoy),
        "missing_months_by_area": missing_months_by_area,
        "areas_complete_coverage": sorted(complete_areas),
        "areas_near_complete_coverage": sorted(near_complete_areas),
        "areas_insufficient_coverage": sorted(insufficient_areas),
    }


def locality_overlap(property_df: pd.DataFrame, market_df: pd.DataFrame) -> dict:
    prop_raw = (
        property_df["location"].dropna().astype(str).str.strip()
        if "location" in property_df.columns
        else pd.Series(dtype=str)
    )
    mkt_raw = (
        market_df["area"].dropna().astype(str).str.strip()
        if "area" in market_df.columns
        else pd.Series(dtype=str)
    )

    prop_raw_set = set(prop_raw.unique())
    mkt_raw_set = set(mkt_raw.unique())
    exact = sorted(prop_raw_set & mkt_raw_set)

    prop_norm_map = {}
    for loc in prop_raw_set:
        norm = normalize_locality(loc)
        if norm:
            prop_norm_map.setdefault(norm, set()).add(loc)

    mkt_norm_map = {}
    for area in mkt_raw_set:
        norm = normalize_locality(area)
        if norm:
            mkt_norm_map.setdefault(norm, set()).add(area)

    shared_norms = sorted(set(prop_norm_map) & set(mkt_norm_map))
    normalized_match_pairs = []
    for norm in shared_norms:
        for p in sorted(prop_norm_map[norm]):
            for m in sorted(mkt_norm_map[norm]):
                normalized_match_pairs.append({"property_location": p, "market_area": m, "normalized": norm})

    prop_only_norms = sorted(set(prop_norm_map) - set(mkt_norm_map))
    mkt_only_norms = sorted(set(mkt_norm_map) - set(prop_norm_map))

    property_without_market = sorted(
        {loc for norm in prop_only_norms for loc in prop_norm_map[norm]}
    )
    market_without_property = sorted(
        {area for norm in mkt_only_norms for area in mkt_norm_map[norm]}
    )

    # Count property rows covered by normalized market overlap
    prop_norm_series = prop_raw.map(normalize_locality)
    covered_rows = int(prop_norm_series.isin(shared_norms).sum())

    return {
        "exact_matches": exact,
        "exact_match_count": len(exact),
        "normalized_match_pairs": normalized_match_pairs,
        "normalized_match_count": len(shared_norms),
        "property_locations_without_market": property_without_market,
        "property_locations_without_market_count": len(property_without_market),
        "market_areas_without_property": market_without_property,
        "market_areas_without_property_count": len(market_without_property),
        "property_rows_with_normalized_market_overlap": covered_rows,
        "property_rows_total_non_null_location": int(prop_raw.shape[0]),
    }


def render_markdown(prop: dict, market: dict, overlap: dict) -> str:
    lines = []
    lines.append("# HousePrice Insight Dataset Audit")
    lines.append("")
    lines.append(f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("Raw files were inspected only. No cleaning was applied.")
    lines.append("")

    lines.append("## 1. Property Dataset")
    lines.append("")
    lines.append(f"- **File:** `{prop['path']}`")
    lines.append(f"- **File size:** {prop['file_size_bytes']:,} bytes")
    lines.append(f"- **Rows:** {prop['rows']:,}")
    lines.append(f"- **Columns:** {prop['columns']}")
    lines.append(f"- **Column names:** {', '.join(prop['column_names'])}")
    lines.append(f"- **Date column available:** {prop['date_available']}")
    lines.append(f"- **Unique locations:** {prop['unique_locations']:,}")
    lines.append(
        f"- **Locations with >= 10 records:** {prop['locations_with_ge_10_records']:,}"
    )
    lines.append(
        f"- **Locations with < 10 records:** {prop['locations_with_lt_10_records']:,}"
    )
    lines.append(f"- **Duplicate rows:** {prop['duplicate_rows']:,}")
    lines.append("")
    lines.append("### Important fields")
    lines.append("")
    lines.append("- `location`: Bengaluru locality for property listings")
    lines.append("- `size`: BHK / bedroom style label (e.g. `2 BHK`)")
    lines.append("- `total_sqft`: area; sometimes ranges or unit-suffixed strings")
    lines.append("- `bath`, `balcony`: numeric-like amenities")
    lines.append("- `price`: typically in INR lakhs in this dataset")
    lines.append("- `area_type`, `availability`, `society`: categorical listing metadata")
    lines.append("")
    lines.append("### Missing values")
    lines.append("")
    for col, info in prop["missing_values"].items():
        lines.append(f"- `{col}`: {info['count']:,} ({info['pct']}%)")
    lines.append("")
    lines.append("### Price / size statistics")
    lines.append("")
    lines.append(f"- Price (lakhs): `{prop['price_stats_lakhs']}`")
    lines.append(f"- Total sqft (parsed): `{prop['total_sqft_stats']}`")
    lines.append(f"- Price/sqft INR (derived): `{prop['price_per_sqft_stats_inr']}`")
    lines.append(f"- Bathrooms: `{prop['bathroom_stats']}`")
    lines.append(f"- BHK (parsed from size): `{prop['bhk_stats']}`")
    lines.append("")
    lines.append("### Top 30 locations by record count")
    lines.append("")
    for loc, count in prop["top_30_locations"].items():
        lines.append(f"- {loc}: {count}")
    lines.append("")
    lines.append("### Data-quality problems")
    lines.append("")
    lines.append(f"- Range `total_sqft` rows: {prop['range_total_sqft_rows']:,}")
    lines.append(
        f"- Unusual/non-numeric `total_sqft` rows: {prop['unusual_non_numeric_total_sqft_rows']:,}"
    )
    lines.append(f"- Suspicious value counts: `{prop['suspicious_values']}`")
    lines.append(f"- Potential IQR outliers: `{prop['potential_outliers']}`")
    if prop["sample_range_total_sqft"]:
        lines.append(f"- Sample range sqft values: {prop['sample_range_total_sqft']}")
    if prop["sample_unusual_total_sqft"]:
        lines.append(f"- Sample unusual sqft values: {prop['sample_unusual_total_sqft']}")
    lines.append("")
    for note in prop.get("notes", []):
        lines.append(f"- Note: {note}")
    lines.append("")

    lines.append("## 2. Historical Market Dataset")
    lines.append("")
    lines.append(f"- **File:** `{market['path']}`")
    lines.append(f"- **File size:** {market['file_size_bytes']:,} bytes")
    lines.append(f"- **Rows:** {market['rows']:,}")
    lines.append(f"- **Columns:** {market['columns']}")
    lines.append(f"- **Column names:** {', '.join(market['column_names'])}")
    lines.append(f"- **Unique areas:** {market['unique_areas']:,}")
    lines.append(f"- **Min date:** {market['min_date']}")
    lines.append(f"- **Max date:** {market['max_date']}")
    lines.append(f"- **Months represented:** {market['months_represented']}")
    lines.append(f"- **Years represented:** {market['years_represented']}")
    lines.append(f"- **Duplicate rows:** {market['duplicate_rows']:,}")
    lines.append("")
    lines.append("### Missing values")
    lines.append("")
    for col, info in market["missing_values"].items():
        lines.append(f"- `{col}`: {info['count']:,} ({info['pct']}%)")
    lines.append("")
    lines.append("### Price statistics")
    lines.append("")
    lines.append(f"- avg_price_per_sqft: `{market['avg_price_per_sqft_stats']}`")
    lines.append(f"- yoy_pct: `{market['yoy_pct_stats']}`")
    lines.append("")
    lines.append("### Historical completeness")
    lines.append("")
    lines.append(
        f"- Areas with complete coverage (>=98% of global month span): {len(market['areas_complete_coverage'])}"
    )
    lines.append(
        f"- Areas with near-complete coverage (>=80%): {len(market['areas_near_complete_coverage'])}"
    )
    lines.append(
        f"- Areas with insufficient coverage (<80%): {len(market['areas_insufficient_coverage'])}"
    )
    if market["areas_complete_coverage"]:
        lines.append(f"- Complete areas: {', '.join(market['areas_complete_coverage'])}")
    if market["areas_near_complete_coverage"]:
        lines.append(
            f"- Near-complete areas: {', '.join(market['areas_near_complete_coverage'])}"
        )
    if market["areas_insufficient_coverage"]:
        lines.append(
            f"- Insufficient areas: {', '.join(market['areas_insufficient_coverage'])}"
        )
    lines.append("")
    lines.append("### Records per area")
    lines.append("")
    for area, count in market["records_per_area"].items():
        miss = market["missing_months_by_area"].get(area, {})
        lines.append(
            f"- {area}: {count} rows; observed_months={miss.get('observed_months')}, "
            f"missing_months={miss.get('missing_months_count')}"
        )
    lines.append("")
    lines.append("### Data-quality problems")
    lines.append("")
    lines.append("- Sparse area set compared with property localities (market file is area-index style).")
    lines.append("- Early YoY values may be missing until a prior-year baseline exists.")
    lines.append("- This is area-level historical price index data, not property-level transactions.")
    lines.append("")

    lines.append("## 3. Locality Overlap")
    lines.append("")
    lines.append(
        "Normalization was used for analysis only (lowercase, punctuation strip, "
        "basic Bangalore/Bengaluru and layout/road cleanup). Raw files were not modified."
    )
    lines.append("")
    lines.append(f"- **Exact matches:** {overlap['exact_match_count']}")
    if overlap["exact_matches"]:
        lines.append(f"  - {', '.join(overlap['exact_matches'])}")
    lines.append(f"- **Normalized match groups:** {overlap['normalized_match_count']}")
    if overlap["normalized_match_pairs"]:
        lines.append("- Example normalized pairs:")
        for pair in overlap["normalized_match_pairs"][:40]:
            lines.append(
                f"  - property `{pair['property_location']}` ↔ market `{pair['market_area']}` "
                f"(norm: `{pair['normalized']}`)"
            )
    lines.append(
        f"- **Property locations with no market history (normalized):** "
        f"{overlap['property_locations_without_market_count']:,}"
    )
    lines.append(
        f"- **Market areas with no property records (normalized):** "
        f"{overlap['market_areas_without_property_count']:,}"
    )
    lines.append(
        f"- **Property rows whose locality has market overlap:** "
        f"{overlap['property_rows_with_normalized_market_overlap']:,} / "
        f"{overlap['property_rows_total_non_null_location']:,}"
    )
    if overlap["market_areas_without_property"]:
        lines.append(
            f"- Market-only areas: {', '.join(overlap['market_areas_without_property'])}"
        )
    lines.append("")
    lines.append("### Important implication for UI")
    lines.append("")
    lines.append(
        "Market Insights should only be offered for localities that map to market areas "
        "after normalization. Most property localities will not have dedicated historical "
        "market series in the current market file."
    )
    lines.append("")

    lines.append("## 4. Recommended Cleaning")
    lines.append("")
    lines.append("Do **not** apply these now. Recommended later:")
    lines.append("")
    lines.append("1. Drop or impute rows with missing critical fields (`location`, `total_sqft`, `price`).")
    lines.append("2. Parse `total_sqft` ranges to midpoint; handle unit-suffixed values separately.")
    lines.append("3. Extract numeric BHK from `size`; standardize bedroom labels.")
    lines.append("4. Convert `price` to a clear INR unit and compute `price_per_sqft`.")
    lines.append("5. Remove impossible combinations (e.g., baths >> BHK, tiny sqft with high BHK).")
    lines.append("6. Cap or filter extreme price/sqft outliers using transparent rules.")
    lines.append("7. Deduplicate exact duplicate rows.")
    lines.append("8. Create a locality mapping table between property `location` and market `area`.")
    lines.append("9. Keep sparse localities labeled; optionally group rare localities as `Other`.")
    lines.append("10. Leave market raw history intact; fill analysis gaps only in processed outputs.")
    lines.append("")

    lines.append("## 5. ML Readiness")
    lines.append("")
    lines.append(
        "The property dataset is **suitable for ML after cleaning**. It has enough rows "
        f"({prop['rows']:,}) and useful features (location, size/BHK, sqft, bath, balcony, area_type). "
        "However, raw quality issues (range sqft strings, missing society/balcony, sparse localities, "
        "and likely listing-era rather than verified transaction prices) mean a cleaned processed "
        "dataset is required before training."
    )
    lines.append("")

    lines.append("## 6. Market Insights Readiness")
    lines.append("")
    lines.append("Safe historical market features we can build from the market dataset:")
    lines.append("")
    lines.append("- Average price per sqft over time by area")
    lines.append("- Year/month trend charts for areas with sufficient coverage")
    lines.append("- YoY % change where `yoy_pct` / prior-year baseline exists")
    lines.append("- Index-style comparison using `index_100` / `base_price`")
    lines.append("- Area selector limited to market areas (and property localities that map to them)")
    lines.append("")
    lines.append("Not safe yet:")
    lines.append("")
    lines.append("- City-wide Market Insights for every property locality")
    lines.append("- Claiming transaction-level truth from listing/index history")
    lines.append("- Fine-grained street-level trends")
    lines.append("")

    lines.append("## 7. Limitations")
    lines.append("")
    lines.append("- Property data appears to be historical listing-style data, not confirmed sale deeds.")
    lines.append("- Property dataset has no listing/sale date column in the raw file.")
    lines.append(
        f"- Market history covers {market['min_date']} to {market['max_date']} across "
        f"{market['unique_areas']} areas only."
    )
    lines.append(
        "- Locality naming is inconsistent between sources; overlap is limited without a mapping layer."
    )
    lines.append("- `total_sqft` is dirty (ranges / non-numeric forms), affecting price-per-sqft quality.")
    lines.append("- High missingness in `society` (and some balcony values) limits those features.")
    lines.append("- Sparse localities (<10 rows) will be unreliable for locality-specific learning.")
    lines.append("- Existing app sample file `data/house_data.csv` was left untouched and unused here.")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not PROPERTY_PATH.exists():
        raise FileNotFoundError(PROPERTY_PATH)
    if not MARKET_PATH.exists():
        raise FileNotFoundError(MARKET_PATH)

    property_df = pd.read_csv(PROPERTY_PATH)
    market_df = pd.read_csv(MARKET_PATH)

    prop_audit = audit_property(property_df, PROPERTY_PATH)
    market_audit = audit_market(market_df, MARKET_PATH)
    overlap = locality_overlap(property_df, market_df)

    md = render_markdown(prop_audit, market_audit, overlap)
    MD_PATH.write_text(md, encoding="utf-8")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "property_dataset": {
            "path": prop_audit["path"],
            "file_size_bytes": prop_audit["file_size_bytes"],
            "rows": prop_audit["rows"],
            "columns": prop_audit["columns"],
            "column_names": prop_audit["column_names"],
            "unique_locations": prop_audit["unique_locations"],
            "duplicate_rows": prop_audit["duplicate_rows"],
            "locations_with_ge_10_records": prop_audit["locations_with_ge_10_records"],
            "locations_with_lt_10_records": prop_audit["locations_with_lt_10_records"],
            "range_total_sqft_rows": prop_audit["range_total_sqft_rows"],
            "unusual_non_numeric_total_sqft_rows": prop_audit[
                "unusual_non_numeric_total_sqft_rows"
            ],
            "date_available": False,
            "missing_values": prop_audit["missing_values"],
            "price_stats_lakhs": prop_audit["price_stats_lakhs"],
            "total_sqft_stats": prop_audit["total_sqft_stats"],
            "price_per_sqft_stats_inr": prop_audit["price_per_sqft_stats_inr"],
            "suspicious_values": prop_audit["suspicious_values"],
            "potential_outliers": prop_audit["potential_outliers"],
        },
        "market_dataset": {
            "path": market_audit["path"],
            "file_size_bytes": market_audit["file_size_bytes"],
            "rows": market_audit["rows"],
            "columns": market_audit["columns"],
            "column_names": market_audit["column_names"],
            "unique_areas": market_audit["unique_areas"],
            "min_date": market_audit["min_date"],
            "max_date": market_audit["max_date"],
            "months_represented": market_audit["months_represented"],
            "years_represented": market_audit["years_represented"],
            "duplicate_rows": market_audit["duplicate_rows"],
            "missing_values": market_audit["missing_values"],
            "avg_price_per_sqft_stats": market_audit["avg_price_per_sqft_stats"],
            "yoy_pct_stats": market_audit["yoy_pct_stats"],
            "areas_complete_coverage": market_audit["areas_complete_coverage"],
            "areas_near_complete_coverage": market_audit["areas_near_complete_coverage"],
            "areas_insufficient_coverage": market_audit["areas_insufficient_coverage"],
            "records_per_area": market_audit["records_per_area"],
        },
        "locality_overlap": {
            "exact_matches": overlap["exact_match_count"],
            "exact_match_names": overlap["exact_matches"],
            "normalized_matches": overlap["normalized_match_count"],
            "normalized_match_pairs_sample": overlap["normalized_match_pairs"][:50],
            "property_locations_without_market": overlap[
                "property_locations_without_market_count"
            ],
            "market_areas_without_property": overlap["market_areas_without_property_count"],
            "market_areas_without_property_names": overlap["market_areas_without_property"],
            "property_rows_with_normalized_market_overlap": overlap[
                "property_rows_with_normalized_market_overlap"
            ],
            "property_rows_total_non_null_location": overlap[
                "property_rows_total_non_null_location"
            ],
        },
    }

    JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("AUDIT_COMPLETE")
    print(f"PROPERTY_ROWS={prop_audit['rows']}")
    print(f"PROPERTY_COLS={prop_audit['columns']}")
    print(f"PROPERTY_UNIQUE_LOCATIONS={prop_audit['unique_locations']}")
    print(f"MARKET_ROWS={market_audit['rows']}")
    print(f"MARKET_COLS={market_audit['columns']}")
    print(f"MARKET_UNIQUE_AREAS={market_audit['unique_areas']}")
    print(f"MARKET_MIN_DATE={market_audit['min_date']}")
    print(f"MARKET_MAX_DATE={market_audit['max_date']}")
    print(f"EXACT_MATCHES={overlap['exact_match_count']}")
    print(f"NORMALIZED_MATCHES={overlap['normalized_match_count']}")
    print(f"MD_REPORT={MD_PATH}")
    print(f"JSON_SUMMARY={JSON_PATH}")


if __name__ == "__main__":
    main()
