"""EDA for cleaned Bengaluru market-history dataset (insights only, not ML training)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from svg_charts import save_bar_chart, save_line_chart

EDA_DIR = Path(__file__).resolve().parent
ROOT = EDA_DIR.parent
PROCESSED = ROOT / "processed" / "bengaluru_market_history_clean.csv"
REPORTS = EDA_DIR / "reports"
FIGURES = EDA_DIR / "figures"


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(PROCESSED)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    lines: list[str] = []
    lines.append("# Market Dataset EDA Report")
    lines.append("")
    lines.append(f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Source: `{PROCESSED}`")
    lines.append("")
    lines.append(
        "This dataset is for **Market Insights only**. "
        "It must not be used to train the property-level price model."
    )
    lines.append("")

    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Rows: **{len(df):,}**")
    lines.append(f"- Columns: {', '.join(df.columns)}")
    lines.append(f"- Areas: **{', '.join(sorted(df['area'].dropna().unique()))}**")
    lines.append(f"- Date range: **{df['date'].min().date()} → {df['date'].max().date()}**")
    lines.append(f"- Unique months: **{df['date'].dt.to_period('M').nunique()}**")
    lines.append(f"- Duplicate rows: **{int(df.duplicated().sum())}**")
    lines.append("")

    lines.append("### Missing values")
    for col in df.columns:
        cnt = int(df[col].isna().sum())
        lines.append(f"- `{col}`: {cnt:,} ({cnt/len(df)*100:.2f}%)")
    lines.append("")
    lines.append(
        "Missing `yoy_pct` / `avg_price_prev_year` are expected in the first year of each series."
    )
    lines.append("")

    # Completeness
    lines.append("## Completeness by area")
    lines.append("")
    start = df["date"].min().to_period("M")
    end = df["date"].max().to_period("M")
    full = pd.period_range(start, end, freq="M")
    for area, group in df.groupby("area"):
        observed = set(group["date"].dt.to_period("M"))
        missing = [str(p) for p in full if p not in observed]
        lines.append(
            f"- **{area}**: rows={len(group)}, observed_months={len(observed)}, "
            f"missing_months={len(missing)}, "
            f"range={group['date'].min().date()} → {group['date'].max().date()}"
        )
    lines.append("")

    # Trends
    lines.append("## Price trends")
    lines.append("")
    series = {}
    for area, group in df.groupby("area"):
        g = group.sort_values("date")
        series[area] = [
            (d.strftime("%Y-%m"), float(v))
            for d, v in zip(g["date"], g["avg_price_per_sqft"])
        ]
    save_line_chart(
        FIGURES / "market_avg_price_per_sqft_over_time.svg",
        series,
        "Average price/sqft over time by area",
        xlabel="Month",
        ylabel="INR / sqft",
    )

    yearly = (
        df.groupby(["area", "year"], as_index=False)["avg_price_per_sqft"]
        .mean()
        .sort_values(["area", "year"])
    )
    lines.append("### Yearly mean avg_price_per_sqft")
    lines.append("```")
    lines.append(
        yearly.pivot(index="year", columns="area", values="avg_price_per_sqft")
        .round(1)
        .to_string()
    )
    lines.append("```")
    lines.append("")

    # YoY
    lines.append("## YoY growth")
    lines.append("")
    yoy = df.dropna(subset=["yoy_pct"])
    yoy_stats = yoy.groupby("area")["yoy_pct"].agg(["count", "mean", "median", "min", "max"])
    lines.append("```")
    lines.append(yoy_stats.round(2).to_string())
    lines.append("```")
    lines.append("")
    latest_year = int(df["year"].max())
    latest = (
        df[df["year"] == latest_year]
        .groupby("area")["avg_price_per_sqft"]
        .mean()
        .sort_values(ascending=False)
    )
    save_bar_chart(
        FIGURES / "market_latest_year_avg_ppsft.svg",
        latest.index.astype(str),
        latest.values,
        f"Mean avg price/sqft by area ({latest_year})",
        ylabel="INR / sqft",
    )

    # Area comparison overall
    overall = df.groupby("area")["avg_price_per_sqft"].agg(["mean", "median", "min", "max"])
    lines.append("## Area comparisons (all months)")
    lines.append("```")
    lines.append(overall.round(2).to_string())
    lines.append("```")
    lines.append("")

    lines.append("## Decisions that affect product features")
    lines.append("")
    lines.append("### Observations")
    lines.append("- Four areas have complete monthly history from 2015-01 through 2025-12.")
    lines.append("- Indiranagar is consistently among the higher INR/sqft markets.")
    lines.append("- Devanahalli is comparatively lower on a price/sqft basis.")
    lines.append("- YoY can be negative in some periods; zero-filling would be misleading.")
    lines.append("")
    lines.append("### Limitations")
    lines.append("- Area-level index/history, not property-level transactions.")
    lines.append("- Only 4 Bengaluru areas are covered.")
    lines.append("- Cannot provide Market Insights for most property localities.")
    lines.append("")
    lines.append("### Product implication")
    lines.append(
        "- Market Insights UI should be enabled only for localities mapped to these four areas."
    )
    lines.append(
        "- Do **not** join this dataset into property-model training rows in the current phase."
    )
    lines.append("")
    lines.append("## Figures")
    lines.append("")
    lines.append("- `figures/market_avg_price_per_sqft_over_time.svg`")
    lines.append("- `figures/market_latest_year_avg_ppsft.svg`")
    lines.append("")

    out = REPORTS / "market_eda_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"MARKET_EDA_COMPLETE -> {out}")


if __name__ == "__main__":
    main()
