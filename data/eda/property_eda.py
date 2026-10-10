"""EDA for cleaned Bengaluru property dataset."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from svg_charts import save_bar_chart, save_histogram, save_scatter

EDA_DIR = Path(__file__).resolve().parent
ROOT = EDA_DIR.parent
PROCESSED = ROOT / "processed" / "bengaluru_property_clean.csv"
REPORTS = EDA_DIR / "reports"
FIGURES = EDA_DIR / "figures"


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(PROCESSED)
    lines: list[str] = []
    lines.append("# Property Dataset EDA Report")
    lines.append("")
    lines.append(f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Source: `{PROCESSED}`")
    lines.append("")

    # Shape / basics
    lines.append("## Dataset overview")
    lines.append("")
    lines.append(f"- Shape: **{df.shape[0]:,} rows × {df.shape[1]} columns**")
    lines.append(f"- Columns: {', '.join(df.columns)}")
    lines.append(f"- Duplicate rows: **{int(df.duplicated().sum())}**")
    lines.append("")
    lines.append("### Missing values")
    lines.append("")
    missing = df.isna().sum()
    for col in df.columns:
        cnt = int(missing[col])
        pct = cnt / len(df) * 100
        lines.append(f"- `{col}`: {cnt:,} ({pct:.2f}%)")
    lines.append("")

    # Distributions
    num_cols = ["price", "total_sqft", "bhk", "bath", "balcony", "price_per_sqft"]
    lines.append("## Numerical distributions")
    lines.append("")
    for col in num_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        lines.append(
            f"- `{col}`: count={int(s.notna().sum()):,}, min={s.min():.2f}, "
            f"median={s.median():.2f}, mean={s.mean():.2f}, max={s.max():.2f}"
        )
    lines.append("")
    lines.append("Target note: `price` is in **INR lakhs**.")
    lines.append("`price_per_sqft` is analytics-only and must not be used as an ML input feature.")
    lines.append("")

    save_histogram(
        FIGURES / "price_distribution.svg",
        df["price"].dropna(),
        "Price distribution (INR lakhs)",
        xlabel="Price (lakhs)",
    )
    save_histogram(
        FIGURES / "total_sqft_distribution.svg",
        df["total_sqft"].dropna(),
        "Total sqft distribution",
        xlabel="Total sqft",
    )
    save_histogram(
        FIGURES / "price_per_sqft_distribution.svg",
        df["price_per_sqft"].dropna(),
        "Price per sqft distribution (INR)",
        xlabel="INR / sqft",
    )
    bhk_counts = df["bhk"].value_counts().sort_index()
    save_bar_chart(
        FIGURES / "bhk_distribution.svg",
        [str(int(x)) if float(x).is_integer() else str(x) for x in bhk_counts.index],
        bhk_counts.values,
        "BHK distribution",
        xlabel="BHK",
        ylabel="Count",
    )
    bath_counts = df["bath"].round().value_counts().sort_index().head(12)
    save_bar_chart(
        FIGURES / "bathroom_distribution.svg",
        [str(int(x)) for x in bath_counts.index],
        bath_counts.values,
        "Bathroom distribution",
        xlabel="Bathrooms",
        ylabel="Count",
    )

    # Relationships
    lines.append("## Relationships with price")
    lines.append("")
    save_scatter(
        FIGURES / "price_vs_total_sqft.svg",
        df["total_sqft"],
        df["price"],
        "Price vs total_sqft",
        "Total sqft",
        "Price (lakhs)",
    )
    save_scatter(
        FIGURES / "price_vs_bhk.svg",
        df["bhk"],
        df["price"],
        "Price vs BHK",
        "BHK",
        "Price (lakhs)",
    )
    save_scatter(
        FIGURES / "price_vs_bath.svg",
        df["bath"],
        df["price"],
        "Price vs bathrooms",
        "Bathrooms",
        "Price (lakhs)",
    )
    corr = df[["price", "total_sqft", "bhk", "bath", "balcony"]].corr(numeric_only=True)
    lines.append("### Correlations (numerical)")
    lines.append("")
    lines.append("```")
    lines.append(corr.round(3).to_string())
    lines.append("```")
    lines.append("")
    lines.append("Observations:")
    lines.append(
        f"- price ↔ total_sqft correlation: **{corr.loc['price','total_sqft']:.3f}**"
    )
    lines.append(f"- price ↔ bhk correlation: **{corr.loc['price','bhk']:.3f}**")
    lines.append(f"- price ↔ bath correlation: **{corr.loc['price','bath']:.3f}**")
    lines.append(
        "- Size-related features (`total_sqft`, `bhk`, `bath`) are positively associated with price."
    )
    lines.append("")

    # Categorical
    lines.append("## Categorical coverage")
    lines.append("")
    area_counts = df["area_type"].value_counts()
    save_bar_chart(
        FIGURES / "area_type_distribution.svg",
        area_counts.index.astype(str),
        area_counts.values,
        "Area type distribution",
        ylabel="Count",
    )
    lines.append("### Area type counts")
    for k, v in area_counts.items():
        lines.append(f"- {k}: {int(v):,}")
    lines.append("")

    avail = df["availability"].fillna("(missing)")
    ready_share = (avail.astype(str).str.lower() == "ready to move").mean()
    lines.append("### Availability")
    lines.append(f"- Unique availability values: **{avail.nunique()}**")
    lines.append(f"- Share `Ready To Move`: **{ready_share*100:.1f}%**")
    lines.append(
        "- Remaining values are mostly future possession dates, creating high cardinality noise."
    )
    lines.append(
        "- **ML decision:** prefer a binary `is_ready_to_move` flag rather than one-hot encoding all dates."
    )
    lines.append("")

    loc_counts = df["location"].value_counts()
    lines.append("### Location frequency")
    lines.append(f"- Unique locations: **{loc_counts.shape[0]:,}**")
    lines.append(f"- Locations with >= 10 rows: **{int((loc_counts >= 10).sum()):,}**")
    lines.append(f"- Locations with < 10 rows: **{int((loc_counts < 10).sum()):,}**")
    lines.append("")
    lines.append("Top localities by record count:")
    for loc, cnt in loc_counts.head(20).items():
        lines.append(f"- {loc}: {int(cnt)}")
    save_bar_chart(
        FIGURES / "top_locations_by_count.svg",
        loc_counts.head(15).index.astype(str),
        loc_counts.head(15).values,
        "Top 15 localities by record count",
        ylabel="Count",
    )
    lines.append("")
    lines.append(
        "**ML decision:** group rare locations into `Other` using a train-only frequency threshold "
        "(recommended: locations with fewer than 10 training rows)."
    )
    lines.append("")

    # Group stats
    lines.append("## Price statistics by group")
    lines.append("")
    by_area = df.groupby("area_type")["price"].agg(["count", "median", "mean"]).sort_values("median", ascending=False)
    lines.append("### By area_type")
    lines.append("```")
    lines.append(by_area.round(2).to_string())
    lines.append("```")
    lines.append("")
    by_bhk = df.groupby("bhk")["price"].agg(["count", "median", "mean"]).sort_index()
    lines.append("### By BHK")
    lines.append("```")
    lines.append(by_bhk.round(2).to_string())
    lines.append("```")
    lines.append("")

    # Locality price/sqft where enough records
    loc_pps = (
        df.groupby("location")
        .agg(n=("price_per_sqft", "size"), median_pps=("price_per_sqft", "median"))
        .query("n >= 30")
        .sort_values("median_pps", ascending=False)
    )
    lines.append("### Median price/sqft by locality (n ≥ 30, analytics only)")
    lines.append("")
    for loc, row in loc_pps.head(15).iterrows():
        lines.append(f"- {loc}: n={int(row['n'])}, median INR/sqft={row['median_pps']:.0f}")
    if not loc_pps.empty:
        save_bar_chart(
            FIGURES / "top_localities_median_ppsft.svg",
            loc_pps.head(12).index.astype(str),
            loc_pps.head(12)["median_pps"].values,
            "Top localities by median INR/sqft (n>=30)",
            ylabel="Median INR/sqft",
        )
    lines.append("")

    # Suspicious remaining values
    lines.append("## Remaining suspicious values")
    lines.append("")
    suspicious = {
        "price_gt_1000_lakhs": int((df["price"] > 1000).sum()),
        "total_sqft_gt_10000": int((df["total_sqft"] > 10000).sum()),
        "bath_gt_bhk_plus_2": int((df["bath"] > df["bhk"] + 2).sum()),
        "balcony_missing": int(df["balcony"].isna().sum()),
        "society_missing": int(df["society"].isna().sum()) if "society" in df.columns else None,
    }
    for k, v in suspicious.items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append(
        "These are residual edge cases after cleaning. They should not dominate training, "
        "but tree models can tolerate some remaining long-tail values."
    )
    lines.append("")

    # Feature recommendations
    lines.append("## Decisions that affect ML")
    lines.append("")
    lines.append("### Observations")
    lines.append("- `total_sqft` is the strongest continuous driver of `price`.")
    lines.append("- `bhk` and `bath` are useful but correlated with size.")
    lines.append("- `area_type` has low cardinality and clear median-price differences.")
    lines.append("- `location` matters but is high-cardinality and sparse in the long tail.")
    lines.append("- `availability` is mostly binary in practice (`Ready To Move` vs future dates).")
    lines.append("- `society` remains too incomplete for a default feature.")
    lines.append("- `balcony` is useful but has missing values that need imputation inside the train pipeline.")
    lines.append("")
    lines.append("### Limitations")
    lines.append("- Listing-style historical data, not verified sale deeds.")
    lines.append("- No property transaction date in this dataset.")
    lines.append("- Locality names are unevenly represented.")
    lines.append("- Market-history dataset is separate and must not be mixed into property training rows.")
    lines.append("")
    lines.append("### Recommended final feature set")
    lines.append("- `area_type`")
    lines.append("- `location` (rare → `Other`)")
    lines.append("- `total_sqft`")
    lines.append("- `bhk`")
    lines.append("- `bath`")
    lines.append("- `balcony` (median impute in pipeline)")
    lines.append("- `is_ready_to_move` derived from `availability`")
    lines.append("")
    lines.append("### Explicit exclusions")
    lines.append("- `price` (target)")
    lines.append("- `price_per_sqft` (target leakage)")
    lines.append("- `society` (high missingness / weak reliability)")
    lines.append("- raw high-cardinality `availability` date strings")
    lines.append("")
    lines.append("## Figures")
    lines.append("")
    for fig in sorted(FIGURES.glob("*.svg")):
        if fig.name.startswith(("price_", "total_", "bhk_", "bathroom_", "area_", "top_")):
            lines.append(f"- `{fig.relative_to(EDA_DIR).as_posix()}`")
    lines.append("")

    out = REPORTS / "property_eda_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"PROPERTY_EDA_COMPLETE -> {out}")


if __name__ == "__main__":
    main()
