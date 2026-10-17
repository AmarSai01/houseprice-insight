import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Menu, Save, X } from "lucide-react";
import api from "../services/api";
import { getApiErrorMessage } from "../services/apiErrors";
import {
  getGlobalExplanationView,
  importanceToBarPercent,
} from "../services/explanation";
import { formatInr } from "../services/market";
import {
  buildPredictPayload,
  createInitialPropertyForm,
  validatePropertyForm,
  AREA_TYPE_OPTIONS,
} from "../services/propertyForm";
import {
  SESSION_EXPIRED_SAVE_MESSAGE,
  reconcileUnauthenticatedSave,
} from "../services/reconcileEstimateSave";
import {
  SIMILAR_EMPTY_MESSAGE,
  SIMILAR_FALLBACK_ERROR,
  fetchSimilarProperties,
  formatMatchNote,
  formatSimilarityPercent,
  similarPayloadKey,
} from "../services/similarProperties";
import LocalityDatalist, {
  LOCALITY_DATALIST_ID,
  getLocalityHint,
} from "../components/LocalityDatalist";
import { PRODUCT_NAV_LINKS } from "../constants/navLinks";
import { useAuth } from "../contexts/AuthContext";
import "./EstimatePage.css";

const FALLBACK_DISCLAIMER =
  "This is an ML-based estimate, not a professional property valuation.";

const formatAreaTypeLabel = (option) =>
  String(option || "")
    .replace(/\s+/g, " ")
    .trim();

const EstimatePage = () => {
  const { isAuthenticated, logout, clearSession } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [form, setForm] = useState(createInitialPropertyForm);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [sessionNotice, setSessionNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [lastPayload, setLastPayload] = useState(null);
  const [similarOpen, setSimilarOpen] = useState(false);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState("");
  const [similarData, setSimilarData] = useState(null);
  const [similarPayloadKeyState, setSimilarPayloadKeyState] = useState("");
  const similarRequestKeyRef = useRef("");

  const validate = () => {
    const { valid, errors: next } = validatePropertyForm(form);
    setErrors(next);
    return valid;
  };

  const clearFieldError = (name) => {
    setErrors((prev) => {
      if (!prev[name]) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
    setApiError("");
  };

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    clearFieldError(name);
  };

  const setAreaType = (value) => {
    setForm((prev) => ({ ...prev, area_type: value }));
    clearFieldError("area_type");
  };

  const setReadyToMove = (value) => {
    setForm((prev) => ({ ...prev, is_ready_to_move: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (loading) return;

    setApiError("");
    setSessionNotice("");
    // Keep the previous successful result visible until a new success replaces it.

    if (!validate()) return;

    const payload = buildPredictPayload(form);
    const wasAuthenticated = isAuthenticated;
    setLoading(true);
    try {
      const response = await api.post("/api/predict", payload);
      const data = response.data;
      setResult(data);
      setLastPayload(payload);
      // Invalidate any previous similar-properties cache for the prior estimate.
      similarRequestKeyRef.current = "";
      setSimilarOpen(false);
      setSimilarLoading(false);
      setSimilarError("");
      setSimilarData(null);
      setSimilarPayloadKeyState("");

      const reconciliation = await reconcileUnauthenticatedSave({
        wasAuthenticated,
        saved: Boolean(data?.saved),
        verifySession: () => api.get("/api/auth/me"),
        clearSession,
      });

      if (reconciliation.status === "session_expired") {
        setSessionNotice(SESSION_EXPIRED_SAVE_MESSAGE);
      }
    } catch (error) {
      setApiError(
        getApiErrorMessage(
          error,
          "Unable to estimate this property right now. Please try again."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const loadSimilarProperties = async () => {
    if (!lastPayload || similarLoading) return;

    const requestKey = similarPayloadKey(lastPayload);
    if (!requestKey) return;

    // Cache hit for the same successful estimate payload.
    if (similarData && similarPayloadKeyState === requestKey) {
      setSimilarOpen(true);
      setSimilarError("");
      return;
    }

    setSimilarOpen(true);
    setSimilarLoading(true);
    setSimilarError("");
    similarRequestKeyRef.current = requestKey;

    try {
      const data = await fetchSimilarProperties(api, lastPayload);
      if (similarRequestKeyRef.current !== requestKey) return;
      setSimilarData(data);
      setSimilarPayloadKeyState(requestKey);
    } catch (error) {
      if (similarRequestKeyRef.current !== requestKey) return;
      setSimilarData(null);
      setSimilarPayloadKeyState("");
      setSimilarError(getApiErrorMessage(error, SIMILAR_FALLBACK_ERROR));
    } finally {
      if (similarRequestKeyRef.current === requestKey) {
        setSimilarLoading(false);
      }
    }
  };

  const resultSummary = useMemo(() => {
    if (!result) return null;

    const estimate = Number(result.estimated_price_lakhs);
    const low = Number(result.estimated_low_lakhs);
    const high = Number(result.estimated_high_lakhs);
    const span = high - low;
    const rangePositionPct =
      Number.isFinite(estimate) &&
      Number.isFinite(low) &&
      Number.isFinite(high) &&
      span > 0
        ? Math.min(100, Math.max(0, ((estimate - low) / span) * 100))
        : 50;

    const compactLakhs = (value) =>
      Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      });

    return {
      mainLakhs: compactLakhs(estimate),
      inr: formatInr(result.estimated_price_inr),
      lowCompact: compactLakhs(low),
      highCompact: compactLakhs(high),
      rangePositionPct,
      ppsft: formatInr(result.price_per_sqft),
      disclaimer: result.disclaimer || FALLBACK_DISCLAIMER,
      rangeNote: result.range_note || "",
      explanation: getGlobalExplanationView(result.explanation, { max: 5 }),
    };
  }, [result]);

  const propertySummary = useMemo(() => {
    if (!lastPayload) return null;
    return {
      location: lastPayload.location,
      bhk: lastPayload.bhk,
      sqft: Number(lastPayload.total_sqft).toLocaleString("en-IN"),
      bath: lastPayload.bath,
      balcony: lastPayload.balcony,
      areaType: formatAreaTypeLabel(lastPayload.area_type),
      ready: Boolean(lastPayload.is_ready_to_move),
    };
  }, [lastPayload]);

  const inputClass = (name) =>
    `hpi-est-input${errors[name] ? " is-invalid" : ""}`;

  const fieldProps = (name) => ({
    "aria-invalid": errors[name] ? true : undefined,
    "aria-describedby": errors[name] ? `${name}-error` : undefined,
  });

  const closeMobile = () => setMobileOpen(false);

  return (
    <div className="hpi-est hpi-est--product hpi-est--estimate hpi-ds">
      <header className="hpi-est-nav">
        <div className="hpi-est-nav-inner">
          <Link to="/" className="hpi-est-brand" onClick={closeMobile}>
            <span className="hpi-est-brand-mark">HousePrice</span>
            <span className="hpi-est-brand-sub">Insight</span>
          </Link>

          <nav className="hpi-est-links" aria-label="Primary">
            {PRODUCT_NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={link.to === "/estimate" ? "is-active" : undefined}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="hpi-est-nav-actions">
            {isAuthenticated ? (
              <button type="button" className="hpi-est-nav-auth" onClick={logout}>
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
            aria-controls="estimate-mobile-nav"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div id="estimate-mobile-nav" className="hpi-est-drawer">
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
            <Link to="/estimate" className="hpi-est-drawer-cta" onClick={closeMobile}>
              Get estimate
            </Link>
          </div>
        )}
      </header>

      <main className="hpi-est-main">
        <div className="hpi-est-workspace">
          <div className="hpi-est-input-col">
            <header className="hpi-est-intro">
              <p className="hpi-est-stage">Property estimate</p>
              <h1 className="hpi-est-title">What is your property worth?</h1>
              <p className="hpi-est-lead">
                Tell us a few details about the property and we&apos;ll estimate
                its value using Bengaluru housing data.
              </p>
            </header>

            <form
              onSubmit={handleSubmit}
              className="hpi-est-form"
              noValidate
              aria-labelledby="estimate-form-title"
            >
              <h2 id="estimate-form-title" className="hpi-est-sr">
                Property details
              </h2>

              {/* 01 Location */}
              <section className="hpi-est-section" aria-labelledby="est-sec-01">
                <div className="hpi-est-section-head">
                  <span className="hpi-est-section-n" aria-hidden="true">
                    01
                  </span>
                  <h3 id="est-sec-01" className="hpi-est-section-title">
                    Where is the property?
                  </h3>
                </div>
                <div className="hpi-est-field">
                  <label htmlFor="location" className="hpi-est-label">
                    Location
                  </label>
                  <input
                    id="location"
                    name="location"
                    type="text"
                    value={form.location}
                    onChange={handleChange}
                    placeholder="e.g. Whitefield"
                    className={inputClass("location")}
                    autoComplete="off"
                    list={LOCALITY_DATALIST_ID}
                    aria-invalid={errors.location ? true : undefined}
                    aria-describedby={
                      errors.location
                        ? "location-error"
                        : "location-hint"
                    }
                  />
                  <LocalityDatalist />
                  <p id="location-hint" className="hpi-est-hint" aria-live="polite">
                    {getLocalityHint(form.location)}
                  </p>
                  {errors.location && (
                    <p
                      id="location-error"
                      className="hpi-est-field-error"
                      role="alert"
                    >
                      {errors.location}
                    </p>
                  )}
                </div>
              </section>

              {/* 02 Area type */}
              <section className="hpi-est-section" aria-labelledby="est-sec-02">
                <div className="hpi-est-section-head">
                  <span className="hpi-est-section-n" aria-hidden="true">
                    02
                  </span>
                  <h3 id="est-sec-02" className="hpi-est-section-title">
                    What kind of property is it?
                  </h3>
                </div>
                <fieldset className="hpi-est-fieldset">
                  <legend className="hpi-est-label">Area type</legend>
                  <div
                    className={`hpi-est-choice-grid${
                      errors.area_type ? " is-invalid" : ""
                    }`}
                    role="radiogroup"
                    aria-label="Area type"
                    aria-invalid={errors.area_type ? true : undefined}
                    aria-describedby={
                      errors.area_type ? "area_type-error" : undefined
                    }
                  >
                    {AREA_TYPE_OPTIONS.map((option) => {
                      const selected = form.area_type === option;
                      return (
                        <button
                          key={option}
                          type="button"
                          role="radio"
                          aria-checked={selected}
                          className={`hpi-est-choice${
                            selected ? " is-selected" : ""
                          }`}
                          onClick={() => setAreaType(option)}
                        >
                          {formatAreaTypeLabel(option)}
                        </button>
                      );
                    })}
                  </div>
                  {errors.area_type && (
                    <p
                      id="area_type-error"
                      className="hpi-est-field-error"
                      role="alert"
                    >
                      {errors.area_type}
                    </p>
                  )}
                </fieldset>
              </section>

              {/* 03 Size */}
              <section className="hpi-est-section" aria-labelledby="est-sec-03">
                <div className="hpi-est-section-head">
                  <span className="hpi-est-section-n" aria-hidden="true">
                    03
                  </span>
                  <h3 id="est-sec-03" className="hpi-est-section-title">
                    How large is it?
                  </h3>
                </div>
                <div className="hpi-est-field">
                  <label htmlFor="total_sqft" className="hpi-est-label">
                    Total sq.ft.
                  </label>
                  <div className="hpi-est-unit">
                    <input
                      id="total_sqft"
                      name="total_sqft"
                      type="number"
                      min="1"
                      step="1"
                      inputMode="numeric"
                      value={form.total_sqft}
                      onChange={handleChange}
                      placeholder="1,200"
                      className={inputClass("total_sqft")}
                      {...fieldProps("total_sqft")}
                    />
                    <span className="hpi-est-unit-tag">sq.ft.</span>
                  </div>
                  {errors.total_sqft && (
                    <p
                      id="total_sqft-error"
                      className="hpi-est-field-error"
                      role="alert"
                    >
                      {errors.total_sqft}
                    </p>
                  )}
                </div>
              </section>

              {/* 04 Rooms */}
              <section className="hpi-est-section" aria-labelledby="est-sec-04">
                <div className="hpi-est-section-head">
                  <span className="hpi-est-section-n" aria-hidden="true">
                    04
                  </span>
                  <h3 id="est-sec-04" className="hpi-est-section-title">
                    How many rooms?
                  </h3>
                </div>
                <div className="hpi-est-field-row">
                  <div className="hpi-est-field">
                    <label htmlFor="bhk" className="hpi-est-label">
                      BHK
                    </label>
                    <input
                      id="bhk"
                      name="bhk"
                      type="number"
                      min="1"
                      step="1"
                      inputMode="numeric"
                      value={form.bhk}
                      onChange={handleChange}
                      placeholder="2"
                      className={inputClass("bhk")}
                      {...fieldProps("bhk")}
                    />
                    {errors.bhk && (
                      <p id="bhk-error" className="hpi-est-field-error" role="alert">
                        {errors.bhk}
                      </p>
                    )}
                  </div>
                  <div className="hpi-est-field">
                    <label htmlFor="bath" className="hpi-est-label">
                      Bathrooms
                    </label>
                    <input
                      id="bath"
                      name="bath"
                      type="number"
                      min="1"
                      step="1"
                      inputMode="numeric"
                      value={form.bath}
                      onChange={handleChange}
                      placeholder="2"
                      className={inputClass("bath")}
                      {...fieldProps("bath")}
                    />
                    {errors.bath && (
                      <p
                        id="bath-error"
                        className="hpi-est-field-error"
                        role="alert"
                      >
                        {errors.bath}
                      </p>
                    )}
                  </div>
                </div>
              </section>

              {/* 05 Details */}
              <section className="hpi-est-section" aria-labelledby="est-sec-05">
                <div className="hpi-est-section-head">
                  <span className="hpi-est-section-n" aria-hidden="true">
                    05
                  </span>
                  <h3 id="est-sec-05" className="hpi-est-section-title">
                    Property details
                  </h3>
                </div>
                <div className="hpi-est-field-row">
                  <div className="hpi-est-field">
                    <label htmlFor="balcony" className="hpi-est-label">
                      Balcony
                    </label>
                    <input
                      id="balcony"
                      name="balcony"
                      type="number"
                      min="0"
                      step="1"
                      inputMode="numeric"
                      value={form.balcony}
                      onChange={handleChange}
                      placeholder="1"
                      className={inputClass("balcony")}
                      {...fieldProps("balcony")}
                    />
                    {errors.balcony && (
                      <p
                        id="balcony-error"
                        className="hpi-est-field-error"
                        role="alert"
                      >
                        {errors.balcony}
                      </p>
                    )}
                  </div>
                  <div className="hpi-est-field">
                    <fieldset className="hpi-est-fieldset">
                      <legend className="hpi-est-label">Ready to move</legend>
                      <div
                        className="hpi-est-segment"
                        role="radiogroup"
                        aria-label="Ready to move"
                      >
                        <button
                          type="button"
                          role="radio"
                          aria-checked={form.is_ready_to_move === true}
                          className={`hpi-est-segment-btn${
                            form.is_ready_to_move ? " is-selected" : ""
                          }`}
                          onClick={() => setReadyToMove(true)}
                        >
                          Yes
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={form.is_ready_to_move === false}
                          className={`hpi-est-segment-btn${
                            !form.is_ready_to_move ? " is-selected" : ""
                          }`}
                          onClick={() => setReadyToMove(false)}
                        >
                          No
                        </button>
                      </div>
                    </fieldset>
                  </div>
                </div>
              </section>

              {apiError && (
                <div className="hpi-est-error" role="alert">
                  {apiError}
                </div>
              )}

              <div className="hpi-est-submit-block">
                <button
                  type="submit"
                  disabled={loading}
                  aria-busy={loading}
                  className="hpi-est-submit"
                >
                  {loading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                      Estimating…
                    </>
                  ) : (
                    "Get my estimate →"
                  )}
                </button>
                <p className="hpi-est-reassure">
                  Uses Bengaluru housing data · No property listing is created
                </p>
              </div>
            </form>
          </div>

          <aside
            className="hpi-est-result"
            aria-live="polite"
            aria-busy={loading}
          >
            <h2 className="hpi-est-col-label">Valuation report</h2>

            {loading && !resultSummary && (
              <div className="hpi-est-result-empty" role="status">
                <p className="hpi-est-calculating">Calculating your estimate…</p>
              </div>
            )}

            {!loading && !resultSummary && (
              <div className="hpi-est-result-empty">
                <ol className="hpi-est-flow" aria-label="Estimate workflow">
                  <li>Property details</li>
                  <li>Property profile</li>
                  <li>Model estimate</li>
                  <li>Evidence</li>
                  <li>Next decision</li>
                </ol>
                <p>
                  Complete the property details and select Get my estimate to
                  see the valuation here.
                </p>
              </div>
            )}

            {resultSummary && (
              <article
                className="hpi-est-report"
                key={`${result.estimated_price_lakhs}-${result.model_version}-${lastPayload?.location || ""}`}
              >
                {loading && (
                  <p className="hpi-est-calculating" role="status">
                    Calculating your estimate…
                  </p>
                )}

                {/* 01 Property summary */}
                {propertySummary && (
                  <header className="hpi-est-report-property">
                    <p className="hpi-est-label">Your property</p>
                    <p className="hpi-est-report-location">
                      {propertySummary.location}
                    </p>
                    <p className="hpi-est-report-meta">
                      {propertySummary.bhk} BHK · {propertySummary.sqft} sq.ft.
                      · {propertySummary.bath} bathroom
                      {Number(propertySummary.bath) === 1 ? "" : "s"}
                    </p>
                    <p className="hpi-est-report-meta">
                      {propertySummary.areaType}
                      {" · "}
                      {propertySummary.ready ? "Ready to move" : "Not ready"}
                      {propertySummary.balcony != null
                        ? ` · ${propertySummary.balcony} balcony`
                        : ""}
                    </p>
                  </header>
                )}

                {/* 02 Primary valuation */}
                <section
                  className="hpi-est-report-value"
                  aria-labelledby="est-value-heading"
                >
                  <p id="est-value-heading" className="hpi-est-label">
                    Estimated market value
                  </p>
                  <p
                    className="hpi-est-price"
                    aria-label={`Estimated market value ${resultSummary.mainLakhs} lakh rupees`}
                  >
                    ₹{resultSummary.mainLakhs}
                    <small>L</small>
                  </p>
                  <p className="hpi-est-ppsft">
                    ₹{resultSummary.ppsft} / sq.ft.
                  </p>
                  <p className="hpi-est-inr">≈ ₹{resultSummary.inr}</p>
                </section>

                {/* 03 Estimated range */}
                <section
                  className="hpi-est-report-range"
                  aria-labelledby="est-range-heading"
                >
                  <p id="est-range-heading" className="hpi-est-label">
                    Estimated range
                  </p>
                  <div
                    className="hpi-est-range-scale"
                    role="img"
                    aria-label={`Estimated range from ${resultSummary.lowCompact} lakh to ${resultSummary.highCompact} lakh rupees`}
                  >
                    <div className="hpi-est-range-ends">
                      <span>
                        <strong>₹{resultSummary.lowCompact} L</strong>
                        Lower
                      </span>
                      <span>
                        <strong>₹{resultSummary.highCompact} L</strong>
                        Upper
                      </span>
                    </div>
                    <div className="hpi-est-range-track" aria-hidden="true">
                      <span
                        className="hpi-est-range-dot"
                        style={{ left: `${resultSummary.rangePositionPct}%` }}
                      />
                    </div>
                  </div>
                  <p className="hpi-est-range-note">
                    Based on the model&apos;s historical out-of-fold residuals.
                    This is not a statistical confidence interval.
                    {resultSummary.rangeNote
                      ? ` ${resultSummary.rangeNote}`
                      : ""}
                  </p>
                </section>

                {/* 04 Context */}
                <section
                  className="hpi-est-report-context"
                  aria-labelledby="est-context-heading"
                >
                  <h3 id="est-context-heading" className="hpi-est-report-h">
                    What this estimate tells you
                  </h3>
                  <p>
                    The estimate reflects how properties with similar recorded
                    characteristics have been valued by the model trained on
                    Bengaluru housing data. It is decision support — not a
                    formal professional valuation.
                  </p>
                </section>

                {/* 05 What influences the estimate */}
                {resultSummary.explanation && (
                  <section
                    className="hpi-est-report-factors"
                    aria-labelledby="est-factors-heading"
                  >
                    <h3 id="est-factors-heading" className="hpi-est-report-h">
                      What this model relies on most
                    </h3>
                    <p className="hpi-est-why-note">
                      These are the features that have the strongest overall
                      influence on the trained model. They are not a
                      property-specific breakdown of the estimate.
                    </p>
                    <ul className="hpi-est-why-list">
                      {resultSummary.explanation.factors.map((factor) => (
                        <li key={factor.feature} className="hpi-est-why-item">
                          <div className="hpi-est-why-row">
                            <span>{factor.label}</span>
                            <span className="hpi-est-why-share">
                              {importanceToBarPercent(factor.importance)}%
                            </span>
                          </div>
                          <div className="hpi-est-why-track" aria-hidden="true">
                            <span
                              className="hpi-est-why-fill"
                              style={{
                                width: `${importanceToBarPercent(
                                  factor.importance
                                )}%`,
                              }}
                            />
                          </div>
                        </li>
                      ))}
                    </ul>
                    {resultSummary.explanation.note && (
                      <p className="hpi-est-why-note">
                        {resultSummary.explanation.note}
                      </p>
                    )}
                  </section>
                )}

                {/* 06 Similar properties */}
                <section
                  className="hpi-est-report-similar"
                  aria-labelledby="est-similar-heading"
                >
                  <h3 id="est-similar-heading" className="hpi-est-report-h">
                    Similar recorded properties
                  </h3>
                  <p className="hpi-est-why-note">
                    Records from the available Bengaluru property dataset.
                    Similarity is a match score — not confidence or valuation
                    accuracy.
                  </p>
                  <button
                    type="button"
                    className="hpi-est-submit hpi-est-submit--secondary"
                    onClick={loadSimilarProperties}
                    disabled={similarLoading || !lastPayload}
                    aria-expanded={similarOpen}
                    aria-busy={similarLoading}
                  >
                    {similarLoading ? (
                      <>
                        <Loader2
                          size={16}
                          className="animate-spin"
                          aria-hidden="true"
                        />
                        Finding similar properties…
                      </>
                    ) : (
                      "View similar properties →"
                    )}
                  </button>

                  {similarOpen && (
                    <div className="hpi-est-similar-panel" aria-live="polite">
                      {similarError && (
                        <div className="hpi-est-error" role="alert">
                          <p>{similarError}</p>
                          <button
                            type="button"
                            className="hpi-est-submit hpi-est-submit--secondary"
                            onClick={loadSimilarProperties}
                            disabled={similarLoading}
                          >
                            Retry
                          </button>
                        </div>
                      )}

                      {!similarLoading &&
                        !similarError &&
                        similarData &&
                        similarData.count === 0 && (
                          <p className="hpi-est-why-note">
                            {similarData.message || SIMILAR_EMPTY_MESSAGE}
                          </p>
                        )}

                      {!similarLoading &&
                        !similarError &&
                        similarData &&
                        similarData.count > 0 && (
                          <ul className="hpi-est-similar-list">
                            {similarData.results.map((item) => {
                              const similarityLabel = formatSimilarityPercent(
                                item.similarity
                              );
                              const noteLabels = (item.match_notes || [])
                                .map(formatMatchNote)
                                .filter(Boolean);
                              return (
                                <li
                                  key={`${item.rank}-${item.location}-${item.total_sqft}-${item.bhk}`}
                                  className="hpi-est-similar-item"
                                >
                                  <div className="hpi-est-similar-top">
                                    <p className="hpi-est-similar-place">
                                      {item.location}
                                    </p>
                                    {similarityLabel && (
                                      <p className="hpi-est-similar-match">
                                        Match {similarityLabel}
                                      </p>
                                    )}
                                  </div>
                                  <p className="hpi-est-report-meta">
                                    {item.bhk} BHK ·{" "}
                                    {Number(item.total_sqft).toLocaleString(
                                      "en-IN"
                                    )}{" "}
                                    sq.ft.
                                    {item.bath != null
                                      ? ` · ${item.bath} bath`
                                      : ""}
                                  </p>
                                  <p className="hpi-est-similar-price">
                                    Historical recorded value: ₹
                                    {Number(
                                      item.listed_price_lakhs
                                    ).toLocaleString("en-IN", {
                                      minimumFractionDigits: 1,
                                      maximumFractionDigits: 1,
                                    })}
                                    L
                                    {item.listed_price_per_sqft != null
                                      ? ` · ₹${formatInr(
                                          item.listed_price_per_sqft
                                        )} / sq.ft.`
                                      : ""}
                                  </p>
                                  {item.location_match === false && (
                                    <p className="hpi-est-why-note">
                                      Different location — shown because closely
                                      matching properties were limited.
                                    </p>
                                  )}
                                  {noteLabels.length > 0 && (
                                    <p className="hpi-est-why-note">
                                      {noteLabels.join(" · ")}
                                    </p>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        )}

                      {!similarLoading &&
                        !similarError &&
                        similarData?.disclaimer && (
                          <p className="hpi-est-why-note">
                            {similarData.disclaimer}
                          </p>
                        )}
                    </div>
                  )}
                </section>

                {/* 07 Next decisions */}
                <section
                  className="hpi-est-report-actions"
                  aria-labelledby="est-actions-heading"
                >
                  <h3 id="est-actions-heading" className="hpi-est-report-h">
                    Next decisions
                  </h3>
                  <ul className="hpi-est-action-list">
                    <li>
                      <Link to="/compare" className="hpi-est-action-link">
                        <span className="hpi-est-action-copy">
                          <span className="hpi-est-action-title">
                            Compare properties
                          </span>
                          <span className="hpi-est-action-desc">
                            Place this estimate beside another property profile.
                          </span>
                        </span>
                        <span className="hpi-est-action-arrow" aria-hidden="true">
                          →
                        </span>
                      </Link>
                    </li>
                    <li>
                      <Link
                        to="/affordability"
                        state={{
                          propertyPriceInr: result.estimated_price_inr,
                        }}
                        className="hpi-est-action-link"
                      >
                        <span className="hpi-est-action-copy">
                          <span className="hpi-est-action-title">
                            Calculate affordability
                          </span>
                          <span className="hpi-est-action-desc">
                            Check EMI and budget fit against this estimate.
                          </span>
                        </span>
                        <span className="hpi-est-action-arrow" aria-hidden="true">
                          →
                        </span>
                      </Link>
                    </li>
                    <li>
                      <button
                        type="button"
                        className="hpi-est-action-link"
                        onClick={loadSimilarProperties}
                        disabled={similarLoading || !lastPayload}
                      >
                        <span className="hpi-est-action-copy">
                          <span className="hpi-est-action-title">
                            View similar properties
                          </span>
                          <span className="hpi-est-action-desc">
                            Review recorded dataset matches for this profile.
                          </span>
                        </span>
                        <span className="hpi-est-action-arrow" aria-hidden="true">
                          →
                        </span>
                      </button>
                    </li>
                  </ul>
                </section>

                {/* 08 Save / history */}
                <section className="hpi-est-report-save" aria-label="Save status">
                  {sessionNotice ? (
                    <p>
                      {sessionNotice}{" "}
                      <Link to="/login">Sign in</Link>
                    </p>
                  ) : isAuthenticated ? (
                    result.saved ? (
                      <p className="hpi-est-saved">
                        <Save size={13} aria-hidden="true" />
                        Saved to your history
                        {result.prediction_id
                          ? ` (#${result.prediction_id})`
                          : ""}
                        .
                      </p>
                    ) : (
                      <p>
                        Estimate ready. History save was unavailable for this
                        request.
                      </p>
                    )
                  ) : (
                    <p>
                      <Link to="/login">Sign in</Link> before estimating to save
                      results to history.
                    </p>
                  )}
                </section>

                {/* 09 Disclaimer */}
                <footer className="hpi-est-report-foot">
                  <p className="hpi-est-disclaimer">{resultSummary.disclaimer}</p>
                  {(result.model || result.model_version) && (
                    <p className="hpi-est-model">
                      {result.model || "Model"}
                      {result.model_version
                        ? ` · v${result.model_version}`
                        : ""}
                    </p>
                  )}
                </footer>
              </article>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
};

export default EstimatePage;
