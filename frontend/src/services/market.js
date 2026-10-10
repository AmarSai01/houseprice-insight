/**
 * Pure helpers for market-history data from GET /api/market/*.
 * No fetching — call sites own API requests via services/api.js.
 */

export const formatInr = (value) =>
  Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 });

export const formatTrendPct = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return null;
  }
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
};

export const sampleSeries = (series) => {
  if (!Array.isArray(series) || series.length === 0) return [];
  const step = Math.max(1, Math.floor(series.length / 10));
  const vals = [];
  for (let i = 0; i < series.length; i += step) {
    const v = Number(series[i].avg_price_per_sqft);
    if (Number.isFinite(v) && v > 0) vals.push(v);
  }
  const last = Number(series[series.length - 1].avg_price_per_sqft);
  if (Number.isFinite(last) && vals[vals.length - 1] !== last) {
    vals.push(last);
  }
  return vals.slice(-10);
};

export const computeYoY = (series, summaryYoY) => {
  if (
    summaryYoY !== null &&
    summaryYoY !== undefined &&
    Number.isFinite(Number(summaryYoY))
  ) {
    return Number(summaryYoY);
  }
  if (!Array.isArray(series) || series.length < 2) return null;
  const latest = Number(series[series.length - 1]?.avg_price_per_sqft);
  const yearAgoIndex = Math.max(0, series.length - 13);
  const prior = Number(series[yearAgoIndex]?.avg_price_per_sqft);
  if (!Number.isFinite(latest) || !Number.isFinite(prior) || prior <= 0) {
    return null;
  }
  return ((latest - prior) / prior) * 100;
};

export const marketPositionLabel = (area, comparisons) => {
  if (!comparisons?.length) return "Market data loading…";
  const ranked = [...comparisons].sort(
    (a, b) =>
      Number(b.latest_avg_price_per_sqft) - Number(a.latest_avg_price_per_sqft)
  );
  const index = ranked.findIndex((row) => row.area === area);
  if (index < 0) return "Position unavailable";
  if (index === 0) return "Highest among tracked localities";
  if (index === 1) return "Upper range among tracked localities";
  if (index === ranked.length - 1) return "Lowest among tracked localities";
  return "Mid-range among tracked localities";
};
