import { useMemo, useState } from "react";
import { MARKET_AREAS } from "../constants/marketAreas";
import { formatInr } from "../services/market";

function LocTrend({ values }) {
  const path = useMemo(() => {
    if (!values.length) return "";
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const w = 180;
    const h = 26;
    return values
      .map((v, i) => {
        const x = (i / Math.max(values.length - 1, 1)) * w;
        const y = h - ((v - min) / span) * (h - 3) - 1.5;
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [values]);

  if (!values.length) {
    return <div className="hpi-ed-loc-trend is-empty" aria-hidden="true" />;
  }

  return (
    <svg
      className="hpi-ed-loc-trend"
      viewBox="0 0 180 26"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

/**
 * Editorial locality + market intelligence.
 * Controlled by Home: location / market / onSelect.
 */
const LocationIntelligence = ({ location, market, onSelect, loading, error }) => {
  const [hoverId, setHoverId] = useState(null);

  const selectedId = location?.id;
  const selectedLoc = location;
  const yoy = market?.yoyPct ?? null;
  const trendLabel = market?.yoyLabel ?? null;
  const currentValue = market?.averagePricePerSqft;
  const position = market?.marketPosition;
  const trendValues = market?.trendSeries || [];

  return (
    <section className="hpi-ed-loc" aria-label="Location intelligence">
      <div className="hpi-ed-loc-rule" aria-hidden="true" />

      <div className="hpi-ed-loc-head">
        <p className="hpi-ed-loc-stage">02 · Location</p>
        <p className="hpi-ed-meta-label">Location intelligence</p>
        <h2 className="hpi-ed-loc-title hpi-ed-serif">
          {location?.label || selectedId}
          <span> · {location?.city || "Bengaluru"}</span>
        </h2>
      </div>

      <div className="hpi-ed-loc-body">
        <div className="hpi-ed-loc-stats">
          <div className="hpi-ed-loc-stat">
            <span className="hpi-ed-meta-label">Avg. market value</span>
            <span className="hpi-ed-loc-stat-value">
              {loading ? "…" : currentValue ? `₹${formatInr(currentValue)}` : "—"}
              <small>/ sq.ft</small>
            </span>
          </div>
          <div className="hpi-ed-loc-stat">
            <span className="hpi-ed-meta-label">12-month trend</span>
            <span
              className={`hpi-ed-loc-stat-value${
                yoy !== null && yoy < 0 ? " is-down" : " is-accent"
              }`}
            >
              {loading ? "…" : trendLabel || "—"}
            </span>
          </div>
          <div className="hpi-ed-loc-stat">
            <span className="hpi-ed-meta-label">Market position</span>
            <span className="hpi-ed-loc-stat-text">
              {loading ? "…" : position}
            </span>
          </div>
          <div className="hpi-ed-loc-stat hpi-ed-loc-stat-trend">
            <div className="hpi-ed-loc-chart-head">
              <span>Trend</span>
              <span>12 months</span>
            </div>
            <LocTrend values={trendValues} />
            {error && <p className="hpi-ed-loc-error">{error}</p>}
          </div>
        </div>

        <div className="hpi-ed-loc-viz">
          <div className="hpi-ed-loc-map">
            <svg
              viewBox="34 10 50 48"
              className="hpi-ed-loc-svg"
              role="img"
              aria-label="Bengaluru market localities"
            >
              <path
                className="hpi-ed-loc-city"
                d="M26 32 C34 16, 64 12, 74 24 C86 38, 88 60, 74 74 C60 88, 34 86, 24 70 C14 54, 16 42, 26 32 Z"
              />
              {selectedLoc?.x != null && (
                <circle
                  cx={selectedLoc.x}
                  cy={selectedLoc.y}
                  r="5.5"
                  className="hpi-ed-loc-halo"
                />
              )}
              {MARKET_AREAS.map((loc) => {
                const isSelected = loc.id === selectedId;
                const isHover = loc.id === hoverId;
                return (
                  <g
                    key={loc.id}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isSelected}
                    aria-label={`Select ${loc.label}`}
                    className={`hpi-ed-loc-pin${isSelected ? " is-active" : ""}${
                      isHover ? " is-hover" : ""
                    }`}
                    onClick={() => onSelect(loc.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(loc.id);
                      }
                    }}
                    onMouseEnter={() => setHoverId(loc.id)}
                    onMouseLeave={() => setHoverId(null)}
                  >
                    <circle cx={loc.x} cy={loc.y} r="4" fill="transparent" stroke="none" />
                    <circle
                      cx={loc.x}
                      cy={loc.y}
                      r={isSelected || isHover ? 1.35 : 0.95}
                    />
                    <text
                      x={loc.x + 2.2}
                      y={loc.y - 1.4}
                      className={isSelected ? "is-active-label" : undefined}
                    >
                      {loc.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="hpi-ed-loc-nav" role="tablist" aria-label="Select locality">
            {MARKET_AREAS.map((loc) => (
              <button
                key={loc.id}
                type="button"
                role="tab"
                aria-selected={loc.id === selectedId}
                className={`hpi-ed-loc-chip${loc.id === selectedId ? " is-active" : ""}`}
                onClick={() => onSelect(loc.id)}
              >
                {loc.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default LocationIntelligence;
