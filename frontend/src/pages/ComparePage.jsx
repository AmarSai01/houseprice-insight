import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Menu, X } from "lucide-react";
import PropertyFormFields from "../components/PropertyFormFields";
import api from "../services/api";
import { getApiErrorMessage } from "../services/apiErrors";
import {
  compareTwoProperties,
  computeComparisonSummary,
  formatCompactLakhs,
  runPropertyPrediction,
  shouldBlockCompareSubmit,
} from "../services/compareProperties";
import { formatInr } from "../services/market";
import {
  buildPredictPayload,
  createInitialPropertyForm,
  validatePropertyForm,
} from "../services/propertyForm";
import {
  SESSION_EXPIRED_SAVE_MESSAGE,
  reconcileUnauthenticatedSave,
} from "../services/reconcileEstimateSave";
import { PRODUCT_NAV_LINKS } from "../constants/navLinks";
import { useAuth } from "../contexts/AuthContext";
import "./EstimatePage.css";
import "./ComparePage.css";

const NAV_LINKS = PRODUCT_NAV_LINKS;

const FALLBACK_DISCLAIMER =
  "This is an ML-based estimate, not a professional property valuation.";

const predictFn = (payload) =>
  api.post("/api/predict", payload).then((response) => response.data);

const ComparePage = () => {
  const { isAuthenticated, logout, clearSession } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [formA, setFormA] = useState(createInitialPropertyForm);
  const [formB, setFormB] = useState(createInitialPropertyForm);
  const [errorsA, setErrorsA] = useState({});
  const [errorsB, setErrorsB] = useState({});
  const [loading, setLoading] = useState(false);
  const [sessionNotice, setSessionNotice] = useState("");
  const [formError, setFormError] = useState("");
  const [propertyA, setPropertyA] = useState(null);
  const [propertyB, setPropertyB] = useState(null);
  const [summary, setSummary] = useState(null);

  const closeMobile = () => setMobileOpen(false);

  const makeChangeHandler = (setter, errorSetter) => (event) => {
    const { name, value, type, checked } = event.target;
    setter((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    errorSetter((prev) => {
      if (!prev[name]) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
    setFormError("");
  };

  const handleChangeA = makeChangeHandler(setFormA, setErrorsA);
  const handleChangeB = makeChangeHandler(setFormB, setErrorsB);

  const inputClass = (errors, name) =>
    `hpi-est-input${errors[name] ? " is-invalid" : ""}`;

  const fieldProps = (errors, name) => ({
    "aria-invalid": errors[name] ? true : undefined,
  });

  const validateBoth = () => {
    const resultA = validatePropertyForm(formA);
    const resultB = validatePropertyForm(formB);
    setErrorsA(resultA.errors);
    setErrorsB(resultB.errors);
    return resultA.valid && resultB.valid;
  };

  const maybeReconcileSession = async (wasAuthenticated, outcomes) => {
    if (!wasAuthenticated) return;
    const needsCheck = outcomes.some(
      (outcome) => outcome?.status === "success" && outcome.data?.saved === false
    );
    if (!needsCheck) return;

    const reconciliation = await reconcileUnauthenticatedSave({
      wasAuthenticated,
      saved: false,
      verifySession: () => api.get("/api/auth/me"),
      clearSession,
    });
    if (reconciliation.status === "session_expired") {
      setSessionNotice(SESSION_EXPIRED_SAVE_MESSAGE);
    }
  };

  const applyComparisonResult = (result) => {
    setPropertyA(result.propertyA);
    setPropertyB(result.propertyB);
    setSummary(result.summary);
  };

  const handleCompare = async (event) => {
    event.preventDefault();
    if (shouldBlockCompareSubmit(loading)) return;

    setFormError("");
    setSessionNotice("");
    if (!validateBoth()) {
      setFormError("Fix the highlighted fields for both properties.");
      return;
    }

    const payloadA = buildPredictPayload(formA);
    const payloadB = buildPredictPayload(formB);
    const wasAuthenticated = isAuthenticated;

    setLoading(true);
    try {
      const result = await compareTwoProperties({
        predictFn,
        payloadA,
        payloadB,
      });
      applyComparisonResult(result);
      await maybeReconcileSession(wasAuthenticated, [
        result.propertyA,
        result.propertyB,
      ]);

      if (
        result.propertyA.status === "error" &&
        result.propertyB.status === "error"
      ) {
        setFormError(
          result.propertyA.message ||
            "Unable to compare properties right now. Please try again."
        );
      }
    } catch (error) {
      setFormError(
        getApiErrorMessage(
          error,
          "Unable to compare properties right now. Please try again."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async (side) => {
    if (shouldBlockCompareSubmit(loading)) return;

    const isA = side === "A";
    const form = isA ? formA : formB;
    const validation = validatePropertyForm(form);
    if (isA) setErrorsA(validation.errors);
    else setErrorsB(validation.errors);
    if (!validation.valid) return;

    const payload = buildPredictPayload(form);
    const wasAuthenticated = isAuthenticated;
    setLoading(true);
    setFormError("");
    try {
      const outcome = await runPropertyPrediction(predictFn, payload);
      const other = isA ? propertyB : propertyA;
      const nextA = isA ? outcome : propertyA;
      const nextB = isA ? propertyB : outcome;

      if (isA) setPropertyA(outcome);
      else setPropertyB(outcome);

      if (outcome.status === "success" && other?.status === "success") {
        setSummary(
          computeComparisonSummary(
            isA ? outcome.data : other.data,
            isA ? other.data : outcome.data
          )
        );
      } else {
        setSummary(null);
      }

      await maybeReconcileSession(wasAuthenticated, [
        isA ? outcome : nextA,
        isA ? nextB : outcome,
      ]);
    } catch (error) {
      const message = getApiErrorMessage(
        error,
        `Unable to estimate Property ${side} right now. Please try again.`
      );
      if (isA) setPropertyA({ status: "error", message });
      else setPropertyB({ status: "error", message });
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  const hasAnyResult = propertyA !== null || propertyB !== null;
  const hasSuccessfulResult =
    propertyA?.status === "success" || propertyB?.status === "success";

  const resultDisclaimer =
    (propertyA?.status === "success" && propertyA.data?.disclaimer) ||
    (propertyB?.status === "success" && propertyB.data?.disclaimer) ||
    FALLBACK_DISCLAIMER;

  const renderResultPanel = (side, label, form, outcome) => {
    if (!outcome) return null;
    if (outcome.status === "error") {
      return (
        <article
          className="hpi-cmp-result"
          aria-labelledby={`compare-result-${side}`}
        >
          <p id={`compare-result-${side}`} className="hpi-est-label">
            {label}
          </p>
          <div className="hpi-est-error" role="alert">
            {outcome.message}
          </div>
          <button
            type="button"
            className="hpi-est-compare-retry"
            onClick={() => handleRetry(side)}
            disabled={loading}
            aria-busy={loading}
          >
            {loading ? "Retrying…" : `Retry ${label} →`}
          </button>
        </article>
      );
    }

    const data = outcome.data;
    const input = outcome.payload || buildPredictPayload(form);
    if (!data || !input) return null;

    const isHigher =
      summary &&
      ((summary.higherProperty === "A" && side === "A") ||
        (summary.higherProperty === "B" && side === "B"));

    return (
      <article
        className={`hpi-cmp-result${isHigher ? " is-higher" : ""}`}
        aria-labelledby={`compare-result-${side}`}
      >
        <p id={`compare-result-${side}`} className="hpi-est-label">
          {label}
          {isHigher ? " · Higher estimated value" : ""}
        </p>
        <p className="hpi-cmp-result-place">{input.location}</p>
        <p className="hpi-cmp-result-meta">
          {input.bhk} BHK · {Number(input.total_sqft).toLocaleString("en-IN")}{" "}
          sq.ft. · {input.bath} bath
          {input.balcony != null ? ` · ${input.balcony} balcony` : ""}
          {" · "}
          {input.is_ready_to_move ? "Ready to move" : "Not ready"}
        </p>
        <p className="hpi-est-label">Estimated market value</p>
        <p
          className="hpi-est-price"
          aria-label={`Estimated market value ${formatCompactLakhs(
            data.estimated_price_lakhs
          )} lakh rupees`}
        >
          ₹{formatCompactLakhs(data.estimated_price_lakhs)}
          <small>L</small>
        </p>
        <p className="hpi-cmp-ppsft">
          ₹{formatInr(data.price_per_sqft)} / sq.ft.
        </p>
        <p className="hpi-est-inr">≈ ₹{formatInr(data.estimated_price_inr)}</p>
        <div className="hpi-cmp-range">
          <p className="hpi-est-label">Estimated range</p>
          <p className="hpi-est-range">
            ₹{formatCompactLakhs(data.estimated_low_lakhs)}L — ₹
            {formatCompactLakhs(data.estimated_high_lakhs)}L
          </p>
        </div>
        {isAuthenticated && data.saved && (
          <p className="hpi-est-compare-meta">
            Saved to history
            {data.prediction_id ? ` (#${data.prediction_id})` : ""}.
          </p>
        )}
      </article>
    );
  };

  return (
    <div className="hpi-est hpi-est--product hpi-cmp hpi-ds">
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
                className={link.to === "/compare" ? "is-active" : undefined}
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
            aria-controls="compare-mobile-nav"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div id="compare-mobile-nav" className="hpi-est-drawer">
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
          <p className="hpi-est-stage">Property comparison</p>
          <h1 className="hpi-est-title">Compare two properties.</h1>
          <p className="hpi-est-lead">
            Enter two Bengaluru property configurations and compare their model
            estimates side by side — same production model as Estimate, run as
            independent predictions.
          </p>
        </header>

        <form onSubmit={handleCompare} noValidate>
          <div className="hpi-est-compare-grid">
            <section
              className="hpi-est-compare-panel"
              aria-labelledby="compare-a"
            >
              <h2 id="compare-a" className="hpi-est-compare-tag">
                Property A
              </h2>
              <div className="hpi-est-form">
                <PropertyFormFields
                  idPrefix="compare-a"
                  form={formA}
                  errors={errorsA}
                  onChange={handleChangeA}
                  onToggleReady={() =>
                    setFormA((prev) => ({
                      ...prev,
                      is_ready_to_move: !prev.is_ready_to_move,
                    }))
                  }
                  inputClass={(name) => inputClass(errorsA, name)}
                  fieldProps={(name) => fieldProps(errorsA, name)}
                />
              </div>
            </section>

            <section
              className="hpi-est-compare-panel"
              aria-labelledby="compare-b"
            >
              <h2 id="compare-b" className="hpi-est-compare-tag">
                Property B
              </h2>
              <div className="hpi-est-form">
                <PropertyFormFields
                  idPrefix="compare-b"
                  form={formB}
                  errors={errorsB}
                  onChange={handleChangeB}
                  onToggleReady={() =>
                    setFormB((prev) => ({
                      ...prev,
                      is_ready_to_move: !prev.is_ready_to_move,
                    }))
                  }
                  inputClass={(name) => inputClass(errorsB, name)}
                  fieldProps={(name) => fieldProps(errorsB, name)}
                />
              </div>
            </section>
          </div>

          {formError && (
            <div className="hpi-est-error hpi-est-compare-actions" role="alert">
              {formError}
            </div>
          )}

          <div className="hpi-est-compare-actions">
            <button
              type="submit"
              disabled={loading}
              aria-busy={loading}
              className="hpi-est-submit"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                  Comparing…
                </>
              ) : (
                "Compare properties →"
              )}
            </button>
          </div>
        </form>

        {sessionNotice && (
          <p className="hpi-est-compare-partial" role="status">
            {sessionNotice} <Link to="/login">Sign in</Link>
          </p>
        )}

        {hasAnyResult && (
          <section
            className="hpi-est-compare-results"
            aria-live="polite"
            aria-labelledby="compare-results-heading"
          >
            <h2 id="compare-results-heading" className="hpi-est-col-label">
              Comparison results
            </h2>

            <div className="hpi-est-compare-cards">
              {renderResultPanel("A", "Property A", formA, propertyA)}
              {renderResultPanel("B", "Property B", formB, propertyB)}
            </div>

            {summary && (
              <div
                className="hpi-est-compare-summary"
                aria-labelledby="compare-summary-heading"
              >
                <h3 id="compare-summary-heading" className="hpi-cmp-summary-h">
                  Difference at a glance
                </h3>
                <p className="hpi-cmp-summary-lead">
                  {summary.higherSummaryText}
                </p>
                <dl className="hpi-cmp-diff-list">
                  <div className="hpi-cmp-diff-row">
                    <dt>Estimated price difference</dt>
                    <dd>
                      ₹{formatCompactLakhs(summary.absoluteDiffLakhs)}L
                      <span className="hpi-cmp-diff-note">
                        {summary.percentDiff}% relative to the lower estimate
                      </span>
                    </dd>
                  </div>
                  <div className="hpi-cmp-diff-row">
                    <dt>Price per sq.ft. difference (A − B)</dt>
                    <dd>
                      ₹{formatInr(Math.abs(summary.ppsftDiff))}
                      <span className="hpi-cmp-diff-note">
                        {summary.ppsftDiff > 0
                          ? "Property A is higher"
                          : summary.ppsftDiff < 0
                            ? "Property B is higher"
                            : "Same"}
                      </span>
                    </dd>
                  </div>
                </dl>
                <p className="hpi-cmp-summary-note">
                  A higher estimated value does not mean the property is
                  objectively better — only that the model produced a higher
                  estimate for the characteristics entered.
                </p>
              </div>
            )}

            {!summary && hasSuccessfulResult && (
              <p className="hpi-est-compare-partial">
                Complete both predictions to see the comparison summary.
              </p>
            )}

            <p className="hpi-est-disclaimer">{resultDisclaimer}</p>
          </section>
        )}
      </main>
    </div>
  );
};

export default ComparePage;
