import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import heroProperty from "../assets/hero-property.jpg";
import { MARKET_AREAS } from "../constants/marketAreas";
import { PRODUCT_NAV_LINKS } from "../constants/navLinks";
import api from "../services/api";
import { formatInr, formatTrendPct } from "../services/market";
import { useAuth } from "../contexts/AuthContext";
import "./LandingPage.css";

const THINK_STEPS = [
  {
    n: "01",
    title: "Property",
    text: "Size, layout, bathrooms, balcony and readiness.",
  },
  {
    n: "02",
    title: "Location",
    text: "Bengaluru locality and area type as model inputs.",
  },
  {
    n: "03",
    title: "Market",
    text: "Historical ₹/sq.ft. context for tracked localities.",
  },
  {
    n: "04",
    title: "Prediction",
    text: "A selected Random Forest estimate with residual-based range.",
  },
  {
    n: "05",
    title: "Insight",
    text: "Model factors, similar records and evaluation transparency.",
  },
];

function formatR2(value) {
  if (value == null || Number.isNaN(Number(value))) return null;
  return Number(value).toFixed(3);
}

function formatMaeLakhs(value) {
  if (value == null || Number.isNaN(Number(value))) return null;
  return `₹${Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} L`;
}

function friendlyModelName(name) {
  if (!name) return null;
  if (name === "RandomForestRegressor") return "Random Forest";
  return name;
}

function TrendBar({ value, max }) {
  const width =
    max > 0 && value != null
      ? `${Math.max(8, Math.round((Number(value) / max) * 100))}%`
      : "0%";
  return (
    <div className="ai-bar" aria-hidden="true">
      <span className="ai-bar-fill" style={{ width }} />
    </div>
  );
}

const LandingPage = () => {
  const { isAuthenticated, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [comparisons, setComparisons] = useState([]);
  const [marketMeta, setMarketMeta] = useState(null);
  const [marketLoading, setMarketLoading] = useState(true);
  const [marketError, setMarketError] = useState("");
  const [modelError, setModelError] = useState("");

  useEffect(() => {
    const t = window.setTimeout(() => setReady(true), 30);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const res = await api.get("/api/model-info");
        if (!live) return;
        setModelInfo(res.data || null);
        setModelError("");
      } catch {
        if (!live) return;
        setModelInfo(null);
        setModelError("Model information is temporarily unavailable.");
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    let live = true;
    setMarketLoading(true);
    setMarketError("");
    (async () => {
      try {
        const res = await api.get("/api/market/overview");
        if (!live) return;
        setComparisons(res.data?.comparisons || []);
        setMarketMeta({
          supported: res.data?.supported_areas || [],
          dateStart: res.data?.date_start || null,
          dateEnd: res.data?.date_end || null,
          observations: res.data?.total_observations ?? null,
        });
        setMarketLoading(false);
      } catch {
        if (!live) return;
        setComparisons([]);
        setMarketMeta(null);
        setMarketLoading(false);
        setMarketError("Market overview is temporarily unavailable.");
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  const marketRows = useMemo(() => {
    if (!comparisons.length) {
      return MARKET_AREAS.map((area) => ({
        area: area.label,
        ppsft: null,
        yoy: null,
      }));
    }
    return comparisons.map((row) => ({
      area: row.area,
      ppsft: row.latest_avg_price_per_sqft ?? null,
      yoy: row.latest_yoy_pct ?? null,
    }));
  }, [comparisons]);

  const maxPpsft = useMemo(() => {
    const values = marketRows
      .map((row) => Number(row.ppsft))
      .filter((v) => Number.isFinite(v) && v > 0);
    return values.length ? Math.max(...values) : 0;
  }, [marketRows]);

  const signalLocalities =
    marketMeta?.supported?.length > 0
      ? marketMeta.supported.length
      : MARKET_AREAS.length;

  const datasetCount = Number(modelInfo?.dataset_row_count);
  const modelName = friendlyModelName(modelInfo?.model_name);
  const modelVersion = modelInfo?.model_version
    ? String(modelInfo.model_version)
    : null;
  const testR2 = formatR2(modelInfo?.test_r2);
  const testMae = formatMaeLakhs(modelInfo?.test_mae);

  const featuredMarket = useMemo(() => {
    if (!marketRows.length) return null;
    const withPrice = marketRows.find((row) => row.ppsft != null);
    return withPrice || marketRows[0];
  }, [marketRows]);

  const closeMobile = () => setMobileOpen(false);

  return (
    <div className={`ai-home hpi-ds${ready ? " is-ready" : ""}`}>
      <a href="#main" className="ai-skip">
        Skip to content
      </a>

      {/* NAV */}
      <header className="ai-nav">
        <div className="ai-shell ai-nav-inner">
          <Link to="/" className="ai-brand" onClick={closeMobile}>
            <span className="ai-brand-top">HousePrice</span>
            <span className="ai-brand-bot">/ Insight</span>
          </Link>

          <nav className="ai-nav-links" aria-label="Primary">
            {PRODUCT_NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={link.to === "/" ? "is-active" : undefined}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="ai-nav-actions">
            {isAuthenticated ? (
              <button type="button" className="ai-nav-ghost" onClick={logout}>
                Sign out
              </button>
            ) : (
              <Link to="/login" className="ai-nav-ghost">
                Sign in
              </Link>
            )}
            <Link to="/estimate" className="ai-btn ai-btn--solid">
              Get estimate
            </Link>
          </div>

          <button
            type="button"
            className="ai-menu"
            aria-expanded={mobileOpen}
            aria-controls="ai-mobile-nav"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div id="ai-mobile-nav" className="ai-drawer">
            {PRODUCT_NAV_LINKS.map((link) => (
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
              className="ai-drawer-cta"
              onClick={closeMobile}
            >
              Get estimate
            </Link>
          </div>
        )}
      </header>

      <main id="main">
        {/* 01 HERO */}
        <section className="ai-hero" aria-labelledby="ai-hero-title">
          <div className="ai-shell ai-hero-grid">
            <div className="ai-hero-copy">
              <h1 id="ai-hero-title" className="ai-hero-title">
                Know what
                <br />
                your property
                <br />
                is worth.
              </h1>
              <p className="ai-hero-lead">
                Bengaluru property intelligence for estimation, market context
                and better property decisions.
              </p>
              <div className="ai-hero-actions">
                <Link to="/estimate" className="ai-btn ai-btn--solid">
                  Estimate your property →
                </Link>
                <Link to="/market" className="ai-btn ai-btn--ghost">
                  Explore the market →
                </Link>
              </div>
            </div>

            <div className="ai-hero-visual">
              <figure className="ai-hero-figure">
                <div className="ai-hero-media">
                  <img
                    src={heroProperty}
                    alt="Residential architecture used as editorial context for Bengaluru property intelligence"
                    width={960}
                    height={1200}
                    decoding="async"
                  />
                </div>
                {featuredMarket && (
                  <aside
                    className="ai-hero-meta"
                    aria-label="Sample locality market signal"
                  >
                    <div>
                      <p className="ai-meta-label">Locality</p>
                      <p className="ai-meta-value">
                        {featuredMarket.area || "—"}
                      </p>
                    </div>
                    <div>
                      <p className="ai-meta-label">Current ₹/sq.ft.</p>
                      <p className="ai-meta-value ai-meta-value--num">
                        {marketLoading
                          ? "…"
                          : featuredMarket.ppsft != null
                            ? `₹${formatInr(featuredMarket.ppsft)}`
                            : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="ai-meta-label">YoY change</p>
                      <p className="ai-meta-value ai-meta-value--num">
                        {marketLoading
                          ? "…"
                          : formatTrendPct(featuredMarket.yoy) || "—"}
                      </p>
                    </div>
                  </aside>
                )}
              </figure>
            </div>
          </div>
        </section>

        {/* 02 DATA SIGNAL */}
        <section
          className="ai-signal"
          aria-labelledby="ai-signal-heading"
        >
          <div className="ai-shell">
            <h2 id="ai-signal-heading" className="ai-sr">
              Live product data signal
            </h2>
            <ul className="ai-signal-band">
              <li>
                <p className="ai-signal-num">
                  {Number.isFinite(datasetCount) && datasetCount > 0
                    ? datasetCount.toLocaleString("en-IN")
                    : "—"}
                </p>
                <p className="ai-signal-label">Properties</p>
              </li>
              <li>
                <p className="ai-signal-num">{signalLocalities}</p>
                <p className="ai-signal-label">Localities</p>
              </li>
              <li>
                <p className="ai-signal-num">{testR2 || "—"}</p>
                <p className="ai-signal-label">Model R²</p>
              </li>
              <li>
                <p className="ai-signal-num ai-signal-num--text">
                  {modelVersion ? `v${modelVersion}` : "—"}
                </p>
                <p className="ai-signal-label">Model version</p>
              </li>
            </ul>
            {(modelError || marketError) && (
              <p className="ai-note" role="status">
                {[modelError, marketError].filter(Boolean).join(" ")}
              </p>
            )}
          </div>
        </section>

        {/* 03 MARKET */}
        <section className="ai-market" aria-labelledby="ai-market-heading">
          <div className="ai-shell ai-market-grid">
            <div className="ai-market-intro">
              <p className="ai-kicker">Market intelligence</p>
              <h2 id="ai-market-heading" className="ai-display">
                Bengaluru
                <br />
                market
              </h2>
              <p className="ai-lead">
                Where is the market moving? Latest average ₹/sq.ft. and
                year-on-year change for tracked localities from the platform
                market-history dataset
                {marketMeta?.dateStart && marketMeta?.dateEnd
                  ? ` (${marketMeta.dateStart} → ${marketMeta.dateEnd})`
                  : ""}
                . Not live listings.
              </p>
              <Link to="/market" className="ai-btn ai-btn--solid">
                Explore the market →
              </Link>
            </div>

            <div className="ai-market-panel">
              {marketError ? (
                <p className="ai-note" role="status">
                  {marketError}
                </p>
              ) : null}
              <div className="ai-market-table" role="list">
                <div className="ai-market-head" aria-hidden="true">
                  <span>Locality</span>
                  <span>₹ / sq.ft.</span>
                  <span>YoY</span>
                </div>
                {marketRows.map((row) => {
                  const yoyLabel = formatTrendPct(row.yoy);
                  const yoyDown = row.yoy != null && Number(row.yoy) < 0;
                  return (
                    <div
                      key={row.area}
                      className="ai-market-row"
                      role="listitem"
                    >
                      <div className="ai-market-main">
                        <p className="ai-market-area">{row.area}</p>
                        <TrendBar value={row.ppsft} max={maxPpsft} />
                      </div>
                      <p className="ai-market-ppsft">
                        {marketLoading
                          ? "…"
                          : row.ppsft != null
                            ? `₹${formatInr(row.ppsft)}`
                            : "—"}
                      </p>
                      <p
                        className={`ai-market-yoy${
                          yoyDown ? " is-down" : yoyLabel ? " is-up" : ""
                        }`}
                      >
                        {marketLoading ? "…" : yoyLabel || "—"}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* 04 THINK FLOW */}
        <section className="ai-think" aria-labelledby="ai-think-heading">
          <div className="ai-shell">
            <p className="ai-kicker">Process</p>
            <h2 id="ai-think-heading" className="ai-display ai-display--wide">
              How the model
              <br />
              thinks
            </h2>
            <ol className="ai-think-flow">
              {THINK_STEPS.map((step, index) => (
                <li key={step.n} className="ai-think-step">
                  <span className="ai-think-n" aria-hidden="true">
                    {step.n}
                  </span>
                  <h3 className="ai-think-title">{step.title}</h3>
                  <p className="ai-think-text">{step.text}</p>
                  {index < THINK_STEPS.length - 1 && (
                    <span className="ai-think-arrow" aria-hidden="true">
                      ↓
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* 05 ESTIMATE MOMENT — no invented valuation */}
        <section className="ai-moment" aria-labelledby="ai-moment-heading">
          <div className="ai-shell ai-moment-grid">
            <div className="ai-moment-media">
              <img
                src={heroProperty}
                alt=""
                width={800}
                height={600}
                decoding="async"
                aria-hidden="true"
              />
            </div>
            <div className="ai-moment-copy">
              <p className="ai-kicker">Estimate moment</p>
              <h2 id="ai-moment-heading" className="ai-display">
                Start with the
                <br />
                property itself.
              </h2>
              <p className="ai-lead">
                Enter Bengaluru locality, size and layout. The model returns an
                estimated market value, ₹/sq.ft., and a residual-based range —
                with global feature influence and similar recorded properties.
              </p>
              <dl className="ai-spec">
                <div>
                  <dt>Location</dt>
                  <dd>Bengaluru locality</dd>
                </div>
                <div>
                  <dt>Area</dt>
                  <dd>Total sq.ft.</dd>
                </div>
                <div>
                  <dt>Bedrooms</dt>
                  <dd>BHK</dd>
                </div>
                <div>
                  <dt>Bathrooms</dt>
                  <dd>Count</dd>
                </div>
                <div>
                  <dt>Property type</dt>
                  <dd>Area type · readiness</dd>
                </div>
              </dl>
              <Link to="/estimate" className="ai-btn ai-btn--solid">
                Estimate this property →
              </Link>
            </div>
          </div>
        </section>

        {/* 06 MODEL INTELLIGENCE — dark */}
        <section className="ai-model" aria-labelledby="ai-model-heading">
          <div className="ai-shell ai-model-grid">
            <div className="ai-model-intro">
              <p className="ai-kicker ai-kicker--on-dark">Model intelligence</p>
              <h2 id="ai-model-heading" className="ai-display ai-display--on-dark">
                Built on
                <br />
                real data.
              </h2>
              <p className="ai-lead ai-lead--on-dark">
                Held-out test metrics for the selected production model. R² is
                explained variance — not “accuracy.” Estimates remain decision
                support, not a professional valuation.
              </p>
              <Link to="/how-it-works" className="ai-btn ai-btn--on-dark">
                About the model →
              </Link>
            </div>
            <dl className="ai-model-metrics">
              <div>
                <dt>Model</dt>
                <dd>{modelName || "—"}</dd>
              </div>
              <div>
                <dt>Dataset</dt>
                <dd>
                  {Number.isFinite(datasetCount) && datasetCount > 0
                    ? `${datasetCount.toLocaleString("en-IN")} properties`
                    : "—"}
                </dd>
              </div>
              <div>
                <dt>Test R²</dt>
                <dd>{testR2 || "—"}</dd>
              </div>
              <div>
                <dt>MAE</dt>
                <dd>{testMae || "—"}</dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>{modelVersion ? `v${modelVersion}` : "—"}</dd>
              </div>
            </dl>
          </div>
        </section>

        {/* 07 FINAL CTA */}
        <section className="ai-final" aria-labelledby="ai-final-heading">
          <div className="ai-shell ai-final-inner">
            <h2 id="ai-final-heading" className="ai-final-title">
              Your next
              <br />
              property decision
              <br />
              starts here.
            </h2>
            <Link to="/estimate" className="ai-btn ai-btn--final">
              Estimate a property →
            </Link>
          </div>
        </section>
      </main>

      <footer className="ai-footer">
        <div className="ai-shell ai-footer-inner">
          <p>HousePrice Insight</p>
          <p>Bengaluru property valuation and market intelligence.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
