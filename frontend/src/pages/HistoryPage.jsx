import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Menu, X } from "lucide-react";
import { PRODUCT_NAV_LINKS } from "../constants/navLinks";
import api from "../services/api";
import { getApiErrorMessage } from "../services/apiErrors";
import { useAuth } from "../contexts/AuthContext";
import "./EstimatePage.css";
import "./HistoryPage.css";

const NAV_LINKS = PRODUCT_NAV_LINKS;

function formatLakhs(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `₹${Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} L`;
}

/** Returns a formatted date only when the API timestamp is trustworthy. */
function formatSavedDate(iso) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function readFeature(features, keys, fallback = null) {
  if (!features || typeof features !== "object") return fallback;
  for (const key of keys) {
    const value = features[key];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return fallback;
}

function formatSqft(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return `${n.toLocaleString("en-IN")} sq.ft.`;
}

function formatBath(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (Number.isNaN(n)) return `${value} bath`;
  return `${n} bathroom${n === 1 ? "" : "s"}`;
}

function formatBalcony(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  if (n === 1) return "1 balcony";
  return `${n} balconies`;
}

function formatReady(value) {
  if (value === undefined || value === null || value === "") return null;
  if (value === true || value === 1 || value === "1" || value === "true") {
    return "Ready to move";
  }
  if (value === false || value === 0 || value === "0" || value === "false") {
    return "Not ready";
  }
  return String(value);
}

function formatAreaType(value) {
  if (value == null || value === "") return null;
  return String(value).replace(/\s+/g, " ").trim();
}

const HistoryPage = () => {
  const { isAuthenticated, loading: authLoading, user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");
  const [retryKey, setRetryKey] = useState(0);

  const closeMobile = () => setMobileOpen(false);

  useEffect(() => {
    let active = true;

    const run = async () => {
      if (authLoading) return;

      if (!isAuthenticated) {
        if (!active) return;
        setHistory([]);
        setHistoryLoading(false);
        setError("");
        return;
      }

      setHistoryLoading(true);
      setError("");
      try {
        const response = await api.get("/api/predict/history");
        if (!active) return;
        setHistory(Array.isArray(response.data) ? response.data : []);
      } catch (err) {
        if (!active) return;
        setHistory([]);
        setError(
          getApiErrorMessage(
            err,
            "Unable to load your saved estimates right now. Please try again."
          )
        );
      } finally {
        if (active) setHistoryLoading(false);
      }
    };

    run();
    return () => {
      active = false;
    };
  }, [authLoading, isAuthenticated, retryKey]);

  const handleRetry = () => {
    setRetryKey((k) => k + 1);
  };

  return (
    <div className="hpi-est hpi-est--product hpi-hist hpi-ds">
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
                className={link.to === "/history" ? "is-active" : undefined}
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
            aria-controls="history-mobile-nav"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div id="history-mobile-nav" className="hpi-est-drawer">
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
          <p className="hpi-est-stage">Estimate history</p>
          <h1 className="hpi-est-title">Your property estimates.</h1>
          <p className="hpi-est-lead">
            {isAuthenticated
              ? "Estimates saved to your account while signed in. These are model estimates — not live property listings."
              : "Sign in to view estimates saved to your account. History is personal and is not available to guests."}
          </p>
          {isAuthenticated && !authLoading && (
            <p className="hpi-hist-signed">
              Signed in as{" "}
              <strong>{user?.name || user?.email || "member"}</strong>
            </p>
          )}
        </header>

        <div aria-live="polite">
          {authLoading ? (
            <p className="hpi-hist-status" role="status">
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              Checking your session…
            </p>
          ) : !isAuthenticated ? (
            <section className="hpi-hist-gate" aria-labelledby="hist-gate-title">
              <h2 id="hist-gate-title" className="hpi-hist-empty-title">
                Sign in to view your estimate history.
              </h2>
              <p className="hpi-hist-empty-copy">
                Saved estimates are available after signing in. Guests cannot
                see account history.
              </p>
              <div className="hpi-hist-empty-actions">
                <Link to="/login" className="hpi-est-submit hpi-hist-cta-btn">
                  Sign in →
                </Link>
                <Link to="/estimate" className="hpi-hist-link">
                  Create an estimate →
                </Link>
              </div>
            </section>
          ) : historyLoading ? (
            <p className="hpi-hist-status" role="status">
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              Loading saved estimates…
            </p>
          ) : error ? (
            <div className="hpi-hist-error" role="alert">
              <p>{error}</p>
              <button
                type="button"
                className="hpi-hist-retry"
                onClick={handleRetry}
              >
                Retry →
              </button>
            </div>
          ) : history.length === 0 ? (
            <section
              className="hpi-hist-empty"
              aria-labelledby="hist-empty-title"
            >
              <h2 id="hist-empty-title" className="hpi-hist-empty-title">
                No saved estimates yet.
              </h2>
              <p className="hpi-hist-empty-copy">
                Estimates can be saved by signing in before you request an
                estimate. Create one to start your history.
              </p>
              <div className="hpi-hist-empty-actions">
                <Link to="/estimate" className="hpi-est-submit hpi-hist-cta-btn">
                  Create an estimate →
                </Link>
              </div>
            </section>
          ) : (
            <>
              <h2 className="hpi-hist-list-label">
                Saved estimates
                <span>
                  {history.length.toLocaleString("en-IN")}{" "}
                  {history.length === 1 ? "record" : "records"}
                </span>
              </h2>

              <ul className="hpi-hist-archive">
                {history.map((item) => {
                  const features = item.input_features || {};
                  const location =
                    readFeature(features, ["location"]) || "Location unavailable";
                  const areaType = formatAreaType(
                    readFeature(features, ["area_type"])
                  );
                  const bhk = readFeature(features, [
                    "bhk",
                    "number_of_bedrooms",
                  ]);
                  const sqft = formatSqft(
                    readFeature(features, ["total_sqft", "square_feet"])
                  );
                  const bath = formatBath(
                    readFeature(features, ["bath", "number_of_bathrooms"])
                  );
                  const balcony = formatBalcony(
                    readFeature(features, ["balcony"])
                  );
                  const ready = formatReady(
                    readFeature(features, ["is_ready_to_move"])
                  );
                  const savedDate = formatSavedDate(item.timestamp);
                  const detailParts = [
                    bhk != null ? `${bhk} BHK` : null,
                    sqft,
                    bath,
                    areaType,
                    balcony,
                    ready,
                  ].filter(Boolean);

                  return (
                    <li key={item.id} className="hpi-hist-row">
                      <div className="hpi-hist-property">
                        <p className="hpi-hist-eyebrow">Your property</p>
                        <h3 className="hpi-hist-location">{location}</h3>
                        {detailParts.length > 0 && (
                          <p className="hpi-hist-meta">
                            {detailParts.join(" · ")}
                          </p>
                        )}
                        {savedDate && (
                          <p className="hpi-hist-saved">
                            Saved {savedDate}
                            {item.id != null ? ` · #${item.id}` : ""}
                          </p>
                        )}
                        {!savedDate && item.id != null && (
                          <p className="hpi-hist-saved">#{item.id}</p>
                        )}
                      </div>

                      <div className="hpi-hist-value-block">
                        <p className="hpi-hist-value-label">
                          Estimated market value
                        </p>
                        <p
                          className="hpi-hist-value"
                          aria-label={`Estimated market value ${formatLakhs(
                            item.predicted_value
                          )}`}
                        >
                          {formatLakhs(item.predicted_value)}
                        </p>
                      </div>
                    </li>
                  );
                })}
              </ul>

              <div className="hpi-hist-footer">
                <Link to="/estimate" className="hpi-hist-link">
                  New estimate →
                </Link>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default HistoryPage;
