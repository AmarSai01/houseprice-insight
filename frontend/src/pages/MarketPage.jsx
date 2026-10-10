import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Menu, X } from "lucide-react";
import {
  DEFAULT_MARKET_AREA_ID,
  MARKET_AREAS,
} from "../constants/marketAreas";
import { PRODUCT_NAV_LINKS } from "../constants/navLinks";
import api from "../services/api";
import { getApiErrorMessage } from "../services/apiErrors";
import {
  computeYoY,
  formatInr,
  formatTrendPct,
  marketPositionLabel,
} from "../services/market";
import { useAuth } from "../contexts/AuthContext";
import "./EstimatePage.css";
import "./MarketPage.css";

const NAV_LINKS = PRODUCT_NAV_LINKS;

const MISSING_MARKET_API_MESSAGE =
  "Market API routes are not loaded on the running backend. Restart the backend so /api/market/overview and /api/market/history become available.";

function getApiDetail(error) {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string" ? detail : "";
}

function isMissingMarketRoute(error) {
  const status = error?.response?.status;
  const detail = getApiDetail(error);
  return status === 404 && (!detail || detail === "Not Found");
}

function marketRequestError(error, fallback) {
  if (isMissingMarketRoute(error)) return MISSING_MARKET_API_MESSAGE;
  return getApiErrorMessage(error, fallback);
}

function formatMonthLabel(isoDate) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString("en-IN", {
    month: "short",
    year: "numeric",
  });
}

function EditorialTrendChart({ series, locality }) {
  const chart = useMemo(() => {
    if (!Array.isArray(series) || series.length === 0) return null;
    const values = series
      .map((row) => Number(row.avg_price_per_sqft))
      .filter((value) => Number.isFinite(value) && value > 0);
    if (values.length === 0) return null;

    const min = Math.min(...values);
    const max = Math.max(...values);
    const width = 720;
    const height = 260;
    const padL = 56;
    const padR = 16;
    const padT = 16;
    const padB = 36;
    const span = max - min || 1;

    const points = series.map((row, index) => {
      const value = Number(row.avg_price_per_sqft);
      const x =
        padL +
        (index / Math.max(series.length - 1, 1)) * (width - padL - padR);
      const y = height - padB - ((value - min) / span) * (height - padT - padB);
      return { x, y, value, date: row.date };
    });

    const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");
    const first = points[0];
    const last = points[points.length - 1];

    return {
      polyline,
      points,
      first,
      last,
      min,
      max,
      width,
      height,
      padL,
      padR,
      padT,
      padB,
      midY: padT + (height - padT - padB) / 2,
      bottomY: height - padB,
    };
  }, [series]);

  if (!chart) {
    return (
      <p className="hpi-mkt-empty">
        No historical points available for this area.
      </p>
    );
  }

  const accessibleSummary = `${locality} recorded average ₹ per sq.ft. from ${formatMonthLabel(
    chart.first.date
  )} to ${formatMonthLabel(chart.last.date)}. Latest ₹${formatInr(
    chart.last.value
  )} per sq.ft. Observed range ₹${formatInr(chart.min)} to ₹${formatInr(
    chart.max
  )} per sq.ft. Historical observations only — not a forecast.`;

  return (
    <div className="hpi-mkt-chart-block">
      <p className="hpi-mkt-chart-metric">₹ / sq.ft.</p>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        className="hpi-mkt-chart"
        role="img"
        aria-label={accessibleSummary}
      >
        <line
          className="hpi-mkt-chart-grid"
          x1={chart.padL}
          y1={chart.padT}
          x2={chart.width - chart.padR}
          y2={chart.padT}
        />
        <line
          className="hpi-mkt-chart-grid"
          x1={chart.padL}
          y1={chart.midY}
          x2={chart.width - chart.padR}
          y2={chart.midY}
        />
        <line
          className="hpi-mkt-chart-axis"
          x1={chart.padL}
          y1={chart.bottomY}
          x2={chart.width - chart.padR}
          y2={chart.bottomY}
        />
        <text
          className="hpi-mkt-chart-tick"
          x={chart.padL - 8}
          y={chart.padT + 4}
          textAnchor="end"
        >
          {formatInr(chart.max)}
        </text>
        <text
          className="hpi-mkt-chart-tick"
          x={chart.padL - 8}
          y={chart.midY + 4}
          textAnchor="end"
        >
          {formatInr((chart.max + chart.min) / 2)}
        </text>
        <text
          className="hpi-mkt-chart-tick"
          x={chart.padL - 8}
          y={chart.bottomY}
          textAnchor="end"
        >
          {formatInr(chart.min)}
        </text>
        <text
          className="hpi-mkt-chart-tick"
          x={chart.padL}
          y={chart.height - 10}
          textAnchor="start"
        >
          {formatMonthLabel(chart.first.date)}
        </text>
        <text
          className="hpi-mkt-chart-tick"
          x={chart.width - chart.padR}
          y={chart.height - 10}
          textAnchor="end"
        >
          {formatMonthLabel(chart.last.date)}
        </text>
        <polyline
          className="hpi-mkt-chart-line"
          fill="none"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={chart.polyline}
        />
        <circle
          className="hpi-mkt-chart-dot"
          cx={chart.last.x}
          cy={chart.last.y}
          r="3.5"
        />
      </svg>
      <p className="hpi-mkt-sr-only">{accessibleSummary}</p>
      <div className="hpi-mkt-chart-meta" aria-hidden="true">
        <span>{formatMonthLabel(chart.first.date)}</span>
        <span>
          Observed range ₹{formatInr(chart.min)} – ₹{formatInr(chart.max)} /
          sq.ft.
        </span>
        <span>{formatMonthLabel(chart.last.date)}</span>
      </div>
    </div>
  );
}

const MarketPage = () => {
  const { isAuthenticated, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [overview, setOverview] = useState(null);
  const [selectedArea, setSelectedArea] = useState(DEFAULT_MARKET_AREA_ID);
  const [history, setHistory] = useState(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [overviewError, setOverviewError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [unsupportedMessage, setUnsupportedMessage] = useState("");
  const [overviewRetryKey, setOverviewRetryKey] = useState(0);
  const [historyRetryKey, setHistoryRetryKey] = useState(0);

  const closeMobile = () => setMobileOpen(false);

  const areas = useMemo(() => {
    const fromApi = overview?.supported_areas;
    if (Array.isArray(fromApi) && fromApi.length) {
      return MARKET_AREAS.filter((area) => fromApi.includes(area.id));
    }
    return MARKET_AREAS;
  }, [overview]);

  useEffect(() => {
    let active = true;
    const loadOverview = async () => {
      setLoadingOverview(true);
      setOverviewError("");
      try {
        const response = await api.get("/api/market/overview");
        if (!active) return;
        setOverview(response.data);
        if (
          response.data.supported_areas?.length &&
          !response.data.supported_areas.includes(selectedArea)
        ) {
          setSelectedArea(response.data.supported_areas[0]);
        }
      } catch (error) {
        if (!active) return;
        setOverviewError(
          marketRequestError(error, "Unable to load market coverage right now.")
        );
      } finally {
        if (active) setLoadingOverview(false);
      }
    };
    loadOverview();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overviewRetryKey]);

  useEffect(() => {
    let active = true;
    const loadHistory = async () => {
      setLoadingHistory(true);
      setHistoryError("");
      setUnsupportedMessage("");
      setHistory(null);
      try {
        const response = await api.get("/api/market/history", {
          params: { area: selectedArea },
        });
        if (!active) return;
        setHistory(response.data);
      } catch (error) {
        if (!active) return;
        const status = error?.response?.status;
        const detail = getApiDetail(error);
        if (isMissingMarketRoute(error)) {
          setHistoryError(MISSING_MARKET_API_MESSAGE);
        } else if (status === 404) {
          setUnsupportedMessage(
            detail ||
              "Historical market data is not currently available for this location."
          );
        } else {
          setHistoryError(
            marketRequestError(
              error,
              "Unable to load historical market data right now."
            )
          );
        }
      } finally {
        if (active) setLoadingHistory(false);
      }
    };
    loadHistory();
    return () => {
      active = false;
    };
  }, [selectedArea, historyRetryKey]);

  const series = history?.series || [];
  const yoyPct = computeYoY(series, history?.summary?.latest_yoy_pct);
  const yoyLabel = formatTrendPct(yoyPct);
  const position = marketPositionLabel(
    selectedArea,
    overview?.comparisons || []
  );
  const latestPpsft = history?.summary?.latest_avg_price_per_sqft;
  const comparisons = overview?.comparisons || [];

  const maxLatestPrice = useMemo(() => {
    const values = comparisons
      .map((row) => Number(row.latest_avg_price_per_sqft))
      .filter((value) => Number.isFinite(value) && value > 0);
    return values.length ? Math.max(...values) : 0;
  }, [comparisons]);

  return (
    <div className="hpi-est hpi-est--product hpi-mkt hpi-ds">
      <header className="hpi-est-nav">
        <div className="hpi-est-nav-inner">
          <Link to="/" className="hpi-est-brand" onClick={closeMobile}>
            <span className="hpi-est-brand-mark">HousePrice</span>
            <span className="hpi-est-brand-sub">Insight</span>
          </Link>

          <nav className="hpi-est-links" aria-label="Primary">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={link.to === "/market" ? "is-active" : undefined}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="hpi-est-nav-actions">
            {isAuthenticated ? (
              <button
                type="button"
                className="hpi-est-nav-auth"
                onClick={logout}
              >
                Sign out
              </button>
            ) : (
              <Link to="/login" className="hpi-est-nav-auth">
                Sign in
              </Link>
            )}
            <Link to="/estimate" className="hpi-est-nav-cta">
              Get estimate
            </Link>
          </div>

          <button
            type="button"
            className="hpi-est-menu"
            aria-expanded={mobileOpen}
            aria-controls="market-mobile-nav"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div id="market-mobile-nav" className="hpi-est-drawer">
            {NAV_LINKS.map((link) => (
              <Link key={link.to} to={link.to} onClick={closeMobile}>
                {link.label}
              </Link>
            ))}
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => {
                  logout();
                  closeMobile();
                }}
              >
                Sign out
              </button>
            ) : (
              <Link to="/login" onClick={closeMobile}>
                Sign in
              </Link>
            )}
            <Link
              to="/estimate"
              className="hpi-est-drawer-cta"
              onClick={closeMobile}
            >
              Get estimate
            </Link>
          </div>
        )}
      </header>

      <main className="hpi-est-main">
        <header className="hpi-est-intro">
          <p className="hpi-est-stage">Bengaluru market</p>
          <h1 className="hpi-est-title">Where is the market moving?</h1>
          <p className="hpi-est-lead">
            Historical average ₹ / sq.ft. for the four Bengaluru localities in
            this platform&apos;s market-history dataset — Devanahalli,
            Indiranagar, Whitefield, and Yelahanka. This is not a live listing
            feed and does not cover all Bengaluru properties.
          </p>
        </header>

        {/* Overview comparison */}
        <section
          className="hpi-mkt-section"
          aria-labelledby="mkt-overview-heading"
        >
          <div className="hpi-mkt-section-head">
            <div>
              <p className="hpi-mkt-label">Market overview</p>
              <h2 id="mkt-overview-heading" className="hpi-mkt-section-title">
                Supported localities
              </h2>
            </div>
            <p className="hpi-mkt-section-note">Current ₹ / sq.ft.</p>
          </div>

          {loadingOverview ? (
            <div className="hpi-mkt-status hpi-mkt-status-compact" role="status">
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              Loading market overview…
            </div>
          ) : overviewError ? (
            <div className="hpi-mkt-error" role="alert">
              <p>{overviewError}</p>
              <button
                type="button"
                className="hpi-mkt-retry"
                onClick={() => setOverviewRetryKey((k) => k + 1)}
              >
                Retry →
              </button>
            </div>
          ) : (
            <ul className="hpi-mkt-overview">
              {comparisons.map((row) => {
                const price = Number(row.latest_avg_price_per_sqft);
                const relativePct =
                  maxLatestPrice > 0 && Number.isFinite(price)
                    ? Math.min(100, Math.max(0, (price / maxLatestPrice) * 100))
                    : 0;
                const rowYoy = formatTrendPct(row.latest_yoy_pct);
                const isSelected = row.area === selectedArea;
                return (
                  <li key={row.area}>
                    <button
                      type="button"
                      className={`hpi-mkt-overview-row${
                        isSelected ? " is-active" : ""
                      }`}
                      onClick={() => setSelectedArea(row.area)}
                      aria-pressed={isSelected}
                    >
                      <span className="hpi-mkt-overview-name">{row.area}</span>
                      <span className="hpi-mkt-overview-price">
                        ₹{formatInr(price)}
                        <small>/ sq.ft.</small>
                      </span>
                      <span className="hpi-mkt-overview-yoy">
                        {rowYoy != null ? (
                          <>
                            <span className="hpi-mkt-overview-yoy-label">
                              Year-on-year change
                            </span>
                            <strong
                              className={
                                Number(row.latest_yoy_pct) < 0
                                  ? "is-down"
                                  : "is-up"
                              }
                            >
                              {rowYoy}
                            </strong>
                          </>
                        ) : (
                          <span className="hpi-mkt-overview-yoy-label">
                            Year-on-year change unavailable
                          </span>
                        )}
                      </span>
                      <span
                        className="hpi-mkt-relative"
                        aria-hidden="true"
                        title="Relative to highest current ₹/sq.ft. among supported localities"
                      >
                        <span
                          className="hpi-mkt-relative-fill"
                          style={{ width: `${relativePct}%` }}
                        />
                      </span>
                    </button>
                  </li>
                );
              })}
              {!comparisons.length && (
                <li>
                  <p className="hpi-mkt-empty">No comparison rows available.</p>
                </li>
              )}
            </ul>
          )}
        </section>

        {/* Locality selection + selected metrics */}
        <section
          className="hpi-mkt-section"
          aria-labelledby="mkt-locality-heading"
        >
          <div className="hpi-mkt-section-head">
            <div>
              <p className="hpi-mkt-label">Selected locality</p>
              <h2 id="mkt-locality-heading" className="hpi-mkt-section-title">
                {selectedArea}
              </h2>
            </div>
          </div>

          <div
            className="hpi-mkt-chips"
            role="tablist"
            aria-label="Choose locality"
          >
            {(areas.length ? areas : MARKET_AREAS).map((area) => {
              const id = area.id || area;
              const label = area.label || area;
              return (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={id === selectedArea}
                  className={`hpi-mkt-chip${
                    id === selectedArea ? " is-active" : ""
                  }`}
                  onClick={() => setSelectedArea(id)}
                >
                  {label}
                </button>
              );
            })}
          </div>

          <div className="hpi-mkt-metrics" aria-label="Selected locality metrics">
            <div className="hpi-mkt-metric">
              <p className="hpi-mkt-label">Current ₹ / sq.ft.</p>
              <p className="hpi-mkt-metric-value hpi-mkt-serif">
                {loadingHistory
                  ? "…"
                  : latestPpsft != null
                    ? `₹${formatInr(latestPpsft)}`
                    : "—"}
              </p>
              <p className="hpi-mkt-metric-sub">
                Latest recorded average price per square foot
              </p>
            </div>

            <div className="hpi-mkt-metric">
              <p className="hpi-mkt-label">Year-on-year change</p>
              <p
                className={`hpi-mkt-metric-value${
                  yoyPct !== null && yoyPct < 0 ? " is-down" : " is-accent"
                }`}
              >
                {loadingHistory ? "…" : yoyLabel || "—"}
              </p>
              <p className="hpi-mkt-metric-sub">
                Recorded market movement — not a forecast
              </p>
            </div>

            <div className="hpi-mkt-metric">
              <p className="hpi-mkt-label">Among supported localities</p>
              <p className="hpi-mkt-metric-text">
                {loadingOverview ? "…" : position}
              </p>
              <p className="hpi-mkt-metric-sub">
                Relative to the four tracked localities only
              </p>
            </div>
          </div>
        </section>

        {/* Historical trend */}
        <section
          className="hpi-mkt-section"
          aria-labelledby="mkt-history-heading"
        >
          <div className="hpi-mkt-section-head">
            <div>
              <p className="hpi-mkt-label">Historical trend</p>
              <h2 id="mkt-history-heading" className="hpi-mkt-section-title">
                {selectedArea} · ₹ / sq.ft.
              </h2>
            </div>
            <p className="hpi-mkt-section-note">
              Monthly observations · not a forecast
            </p>
          </div>

          <div className="hpi-mkt-chart-wrap">
            {loadingHistory ? (
              <div className="hpi-mkt-status" role="status">
                <Loader2
                  size={16}
                  className="animate-spin"
                  aria-hidden="true"
                />
                Loading market history…
              </div>
            ) : unsupportedMessage ? (
              <div className="hpi-mkt-error" role="alert">
                {unsupportedMessage}
              </div>
            ) : historyError ? (
              <div className="hpi-mkt-error" role="alert">
                <p>{historyError}</p>
                <button
                  type="button"
                  className="hpi-mkt-retry"
                  onClick={() => setHistoryRetryKey((k) => k + 1)}
                >
                  Retry →
                </button>
              </div>
            ) : history ? (
              series.length > 0 ? (
                <EditorialTrendChart
                  series={series}
                  locality={selectedArea}
                />
              ) : (
                <p className="hpi-mkt-empty">
                  No historical observations are available for this locality.
                </p>
              )
            ) : (
              <p className="hpi-mkt-empty">
                Select a supported locality to view historical trends.
              </p>
            )}
          </div>
        </section>

        {/* Data transparency */}
        <section
          className="hpi-mkt-section"
          aria-labelledby="mkt-coverage-heading"
        >
          <div className="hpi-mkt-section-head">
            <div>
              <p className="hpi-mkt-label">Data transparency</p>
              <h2 id="mkt-coverage-heading" className="hpi-mkt-section-title">
                Market-history dataset
              </h2>
            </div>
          </div>

          {loadingOverview ? (
            <div className="hpi-mkt-status hpi-mkt-status-compact" role="status">
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              Loading coverage…
            </div>
          ) : overviewError ? (
            <div className="hpi-mkt-error" role="alert">
              {overviewError}
            </div>
          ) : overview ? (
            <div className="hpi-mkt-coverage">
              <div className="hpi-mkt-coverage-stats">
                <div className="hpi-mkt-coverage-stat">
                  <span className="hpi-mkt-label">Unique months</span>
                  <strong>
                    {overview.unique_months?.toLocaleString("en-IN") || "—"}
                  </strong>
                </div>
                <div className="hpi-mkt-coverage-stat">
                  <span className="hpi-mkt-label">Observations</span>
                  <strong>
                    {overview.total_observations.toLocaleString("en-IN")}
                  </strong>
                </div>
                <div className="hpi-mkt-coverage-stat">
                  <span className="hpi-mkt-label">Dataset period</span>
                  <strong className="hpi-mkt-coverage-period">
                    {overview.date_start} → {overview.date_end}
                  </strong>
                </div>
              </div>
              <p className="hpi-mkt-coverage-copy">
                This section uses the platform&apos;s market-history dataset for
                supported localities only ({overview.supported_areas.join(", ")}
                ). Values are historical averages of ₹ / sq.ft. — not live
                listings, live market prices, or a forecast of future movement.
                The market view is independent from the machine-learning
                property estimate.
              </p>
            </div>
          ) : null}
        </section>

        <p className="hpi-mkt-disclaimer">
          {overview?.disclaimer ||
            history?.disclaimer ||
            "This page shows historical market data from the project's market dataset. It is separate from the machine-learning property estimate."}
        </p>
      </main>
    </div>
  );
};

export default MarketPage;
