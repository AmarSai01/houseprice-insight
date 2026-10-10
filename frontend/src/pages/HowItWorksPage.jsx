import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Menu, X } from "lucide-react";
import PredictedVsActualChart from "../components/PredictedVsActualChart";
import api from "../services/api";
import { getApiErrorMessage } from "../services/apiErrors";
import {
  getGlobalExplanationView,
  importanceToBarPercent,
} from "../services/explanation";
import {
  EVALUATION_FALLBACK_ERROR,
  EVALUATION_UNAVAILABLE_MESSAGE,
  fetchPredictedVsActual,
} from "../services/modelEvaluation";
import {
  FALLBACK_MODEL_COMPARISON,
  FALLBACK_SELECTION_RULE,
  getModelComparisonDisplayRows,
  getModelComparisonSelectionRule,
  resolveModelComparison,
} from "../services/modelInfo";
import { PRODUCT_NAV_LINKS } from "../constants/navLinks";
import { useAuth } from "../contexts/AuthContext";
import "./EstimatePage.css";
import "./AboutPage.css";

const NAV_LINKS = PRODUCT_NAV_LINKS;

const FEATURE_LABELS = [
  "Area type",
  "Location",
  "Total sq.ft.",
  "BHK",
  "Bathrooms",
  "Balcony",
  "Ready to move",
];

const PROCESS_STEPS = [
  {
    n: "01",
    title: "Property details",
    body: "You provide location, area type, size, bedrooms, bathrooms, balcony count, and readiness — the characteristics the production model was trained on.",
  },
  {
    n: "02",
    title: "Feature processing",
    body: "The application prepares those supplied property characteristics so they match the trained model’s expected inputs.",
  },
  {
    n: "03",
    title: "Model",
    body: "The production estimate is produced by the selected Random Forest model, chosen from cross-validated comparison on the training split.",
  },
  {
    n: "04",
    title: "Estimate",
    body: "The model returns an estimated market value plus an estimated range based on historical out-of-fold residuals — not a confidence interval or guarantee.",
  },
  {
    n: "05",
    title: "Understand",
    body: "You can review model-wide feature influence, similar recorded properties, market history for supported localities, and held-out model evaluation.",
  },
];

const FALLBACK_MODEL_INFO = {
  model_name: "RandomForestRegressor",
  model_version: "1.0.0",
  dataset_name: "bengaluru_property_clean.csv",
  dataset_row_count: 12679,
  train_size: 10143,
  test_size: 2536,
  features: [
    "area_type",
    "location",
    "total_sqft",
    "bhk",
    "bath",
    "balcony",
    "is_ready_to_move",
  ],
  test_r2: 0.6885026261968055,
  test_mae: 30.824051491492362,
  test_rmse: 71.12139031318152,
  selection_rule: FALLBACK_SELECTION_RULE,
  model_comparison: FALLBACK_MODEL_COMPARISON,
  prediction_range: {
    description:
      "Estimated price range based on model prediction error using 10th/90th percentiles of out-of-fold residuals on the training set. This is not a statistical confidence interval.",
    supported: true,
  },
  limitations: [
    "Predictions are model estimates from historical listing-style data, not professional valuations.",
    "Target unit is INR lakhs.",
    "price_per_sqft is excluded to prevent target leakage.",
    "Market-history dataset is not used in training.",
    "Rare localities are grouped as Other; estimates for sparse areas are less reliable.",
    "No property transaction date was available for time-aware validation.",
    "Estimated price range is residual-based and is not a confidence interval.",
  ],
  disclaimer:
    "This is an ML-based estimate, not a professional property valuation.",
};

function formatLakhsMetric(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `₹${Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} L`;
}

function formatR2(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return Number(value).toFixed(3);
}

function friendlyModelName(name) {
  if (!name) return "Random Forest";
  if (name === "RandomForestRegressor") return "Random Forest";
  return name;
}

const HowItWorksPage = () => {
  const { isAuthenticated, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [evaluationLoading, setEvaluationLoading] = useState(true);
  const [evaluationError, setEvaluationError] = useState("");
  const [evaluationData, setEvaluationData] = useState(null);

  const closeMobile = () => setMobileOpen(false);

  useEffect(() => {
    let live = true;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const response = await api.get("/api/model-info");
        if (!live) return;
        setModelInfo(response.data);
      } catch {
        if (!live) return;
        setModelInfo(FALLBACK_MODEL_INFO);
        setError(
          "Live model information is temporarily unavailable. Showing documented project metrics."
        );
      } finally {
        if (live) setLoading(false);
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  const loadEvaluation = useCallback(async () => {
    setEvaluationLoading(true);
    setEvaluationError("");
    try {
      const data = await fetchPredictedVsActual(api);
      setEvaluationData(data);
      if (!data.available) {
        setEvaluationError(data.message || EVALUATION_UNAVAILABLE_MESSAGE);
      }
    } catch (err) {
      setEvaluationData(null);
      setEvaluationError(getApiErrorMessage(err, EVALUATION_FALLBACK_ERROR));
    } finally {
      setEvaluationLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEvaluation();
  }, [loadEvaluation]);

  const info = modelInfo || FALLBACK_MODEL_INFO;

  const featureLabels = useMemo(() => {
    if (!Array.isArray(info.features) || !info.features.length) {
      return FEATURE_LABELS;
    }
    const map = {
      area_type: "Area type",
      location: "Location",
      total_sqft: "Total sq.ft.",
      bhk: "BHK",
      bath: "Bathrooms",
      balcony: "Balcony",
      is_ready_to_move: "Ready to move",
    };
    return info.features.map((f) => map[f] || f);
  }, [info.features]);

  const rangeNote =
    info.prediction_range?.description ||
    FALLBACK_MODEL_INFO.prediction_range.description;

  const limitations =
    Array.isArray(info.limitations) && info.limitations.length
      ? info.limitations
      : FALLBACK_MODEL_INFO.limitations;

  const modelComparison = useMemo(
    () => resolveModelComparison(info, FALLBACK_MODEL_COMPARISON),
    [info]
  );
  const comparisonRows = useMemo(
    () => getModelComparisonDisplayRows(modelComparison),
    [modelComparison]
  );
  const comparisonSelectionRule = useMemo(
    () =>
      getModelComparisonSelectionRule(modelComparison, info.selection_rule),
    [modelComparison, info.selection_rule]
  );

  const explanationView = useMemo(
    () => getGlobalExplanationView(info.explanation, { max: 7 }),
    [info.explanation]
  );

  return (
    <div className="hpi-est hpi-est--product hpi-about hpi-ds">
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
                className={
                  link.to === "/how-it-works" ? "is-active" : undefined
                }
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
            aria-controls="about-mobile-nav"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div id="about-mobile-nav" className="hpi-est-drawer">
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
        {/* 1. Hero */}
        <header className="hpi-est-intro">
          <p className="hpi-est-stage">How it works</p>
          <h1 className="hpi-est-title">
            From property details to a data-backed estimate.
          </h1>
          <p className="hpi-est-lead">
            HousePrice Insight uses Bengaluru housing data and a machine-learning
            model to estimate property value for decision support. It is not a
            formal professional property valuation.
          </p>
          {loading && (
            <p className="hpi-about-status" role="status">
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
              Loading model information…
            </p>
          )}
          {error && (
            <p className="hpi-about-error" role="status">
              {error}
            </p>
          )}
        </header>

        {/* 2. The process */}
        <section
          className="hpi-about-section"
          aria-labelledby="about-process-heading"
        >
          <div className="hpi-about-section-head">
            <p className="hpi-about-index">Process</p>
            <h2 id="about-process-heading" className="hpi-about-heading">
              Property data → estimate
            </h2>
          </div>
          <ol className="hpi-about-process">
            {PROCESS_STEPS.map((step) => (
              <li key={step.n} className="hpi-about-process-item">
                <span className="hpi-about-process-n" aria-hidden="true">
                  {step.n}
                </span>
                <div>
                  <h3 className="hpi-about-process-title">{step.title}</h3>
                  <p className="hpi-about-copy">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* 3. Dataset */}
        <section
          className="hpi-about-section"
          aria-labelledby="about-data-heading"
        >
          <div className="hpi-about-section-grid">
            <div>
              <p className="hpi-about-index">Dataset</p>
              <h2 id="about-data-heading" className="hpi-about-heading">
                Property training data
              </h2>
            </div>
            <div>
              <p className="hpi-about-copy">
                The prediction model was trained on cleaned Bengaluru property
                records from{" "}
                <strong>
                  {info.dataset_name || "bengaluru_property_clean.csv"}
                </strong>
                . The market-history dataset used on the Market page is separate
                and is not used as training features for the property estimate.
              </p>
              <p className="hpi-about-copy">
                No property transaction date was available for time-aware
                validation in this project. Do not treat estimates as live listing
                prices.
              </p>
              <div className="hpi-about-meta">
                <div className="hpi-about-meta-item">
                  <span>Usable records</span>
                  <strong>
                    {Number(info.dataset_row_count || 0).toLocaleString("en-IN")}
                  </strong>
                </div>
                <div className="hpi-about-meta-item">
                  <span>Train / test</span>
                  <strong>
                    {Number(info.train_size || 0).toLocaleString("en-IN")} /{" "}
                    {Number(info.test_size || 0).toLocaleString("en-IN")}
                  </strong>
                </div>
                <div className="hpi-about-meta-item">
                  <span>Target</span>
                  <strong>
                    {info.target_name || "price"}
                    {info.target_unit ? ` (${info.target_unit})` : ""}
                  </strong>
                </div>
              </div>
              <p className="hpi-about-copy hpi-about-features-lead">
                Features used by the model:
              </p>
              <ul className="hpi-about-features">
                {featureLabels.map((label) => (
                  <li key={label} className="hpi-about-feature">
                    {label}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* 4. Model */}
        <section
          className="hpi-about-section"
          aria-labelledby="about-model-heading"
        >
          <div className="hpi-about-section-grid">
            <div>
              <p className="hpi-about-index">Model</p>
              <h2 id="about-model-heading" className="hpi-about-heading">
                Selected production model
              </h2>
            </div>
            <div>
              <p className="hpi-about-copy">
                Production estimates are generated by{" "}
                <strong>{friendlyModelName(info.model_name)}</strong>
                {info.model_version ? ` (v${info.model_version})` : ""}. The
                model learns relationships between the supplied property
                characteristics and historical Bengaluru housing prices. It is a
                statistical estimate — not a professional appraisal.
              </p>

              <div className="hpi-about-meta">
                <div className="hpi-about-meta-item">
                  <span>Selected model</span>
                  <strong>{friendlyModelName(info.model_name)}</strong>
                </div>
                <div className="hpi-about-meta-item">
                  <span>Version</span>
                  <strong>{info.model_version || "—"}</strong>
                </div>
                <div className="hpi-about-meta-item">
                  <span>Selection rule</span>
                  <strong className="hpi-about-meta-rule">
                    {comparisonSelectionRule}
                  </strong>
                </div>
              </div>

              <p className="hpi-about-copy hpi-about-metrics-lead">
                Held-out test metrics for the selected production model. Lower
                MAE and RMSE indicate smaller average prediction error in INR
                lakhs; higher R² indicates stronger explained variance — not
                “accuracy.”
              </p>

              <div className="hpi-about-metrics" aria-label="Held-out test metrics">
                <div className="hpi-about-metric">
                  <span>R²</span>
                  <strong>{formatR2(info.test_r2)}</strong>
                  <em>Test set · explained variance</em>
                </div>
                <div className="hpi-about-metric">
                  <span>MAE</span>
                  <strong>{formatLakhsMetric(info.test_mae)}</strong>
                  <em>Mean absolute error</em>
                </div>
                <div className="hpi-about-metric">
                  <span>RMSE</span>
                  <strong>{formatLakhsMetric(info.test_rmse)}</strong>
                  <em>Root mean squared error</em>
                </div>
              </div>

              <div className="hpi-about-compare">
                <h3 className="hpi-about-subheading">Model comparison</h3>
                <p className="hpi-about-compare-label">
                  Cross-validated R² on the training split
                </p>
                {comparisonRows.map((row) => (
                  <div
                    key={row.model_name}
                    className={`hpi-about-compare-row${
                      row.selected ? " is-selected" : ""
                    }`}
                  >
                    <span className="hpi-about-compare-name">
                      {row.name}
                      {row.selected ? " · Selected" : ""}
                    </span>
                    <span className="hpi-about-compare-value">
                      {formatR2(row.cv_r2_mean)}
                    </span>
                  </div>
                ))}
                <p className="hpi-about-compare-note">
                  Models compared using 5-fold cross-validation on the training
                  split. {comparisonSelectionRule}. Values shown are CV R² for
                  model selection — not held-out test R². Test-set metrics above
                  are for the production model only.
                  {modelComparison?.unit_note
                    ? ` ${modelComparison.unit_note}`
                    : ""}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 5. Model evaluation */}
        <section
          className="hpi-about-section"
          aria-labelledby="about-eval-heading"
        >
          <div className="hpi-about-section-grid">
            <div>
              <p className="hpi-about-index">Evaluation</p>
              <h2 id="about-eval-heading" className="hpi-about-heading">
                Predicted vs actual
              </h2>
            </div>
            <div>
              <p className="hpi-about-copy">
                This visualization shows how the production model&apos;s
                predictions compare with actual prices on the held-out test set.
              </p>

              <div className="hpi-about-evaluation" aria-live="polite">
                {evaluationLoading && (
                  <p className="hpi-about-status" role="status">
                    <Loader2
                      size={14}
                      className="animate-spin"
                      aria-hidden="true"
                    />
                    Loading model evaluation…
                  </p>
                )}

                {!evaluationLoading && evaluationError && (
                  <div className="hpi-about-evaluation-fallback">
                    <p className="hpi-about-error" role="alert">
                      {evaluationData?.available === false
                        ? EVALUATION_UNAVAILABLE_MESSAGE
                        : evaluationError}
                    </p>
                    {(!evaluationData ||
                      evaluationData.available !== false) && (
                      <button
                        type="button"
                        className="hpi-about-retry"
                        onClick={loadEvaluation}
                      >
                        Retry →
                      </button>
                    )}
                  </div>
                )}

                {!evaluationLoading &&
                  !evaluationError &&
                  evaluationData?.available &&
                  evaluationData.points.length > 0 && (
                    <>
                      <p className="hpi-about-copy hpi-about-evaluation-meta">
                        Held-out test set ·{" "}
                        {Number(evaluationData.point_count).toLocaleString(
                          "en-IN"
                        )}{" "}
                        properties
                      </p>

                      <div
                        className="hpi-about-evaluation-metrics"
                        aria-label="Evaluation metrics"
                      >
                        <div className="hpi-about-metric">
                          <span>R²</span>
                          <strong>
                            {formatR2(evaluationData.metrics?.r2)}
                          </strong>
                        </div>
                        <div className="hpi-about-metric">
                          <span>MAE (₹ lakhs)</span>
                          <strong>
                            {formatLakhsMetric(evaluationData.metrics?.mae)}
                          </strong>
                        </div>
                        <div className="hpi-about-metric">
                          <span>RMSE (₹ lakhs)</span>
                          <strong>
                            {formatLakhsMetric(evaluationData.metrics?.rmse)}
                          </strong>
                        </div>
                      </div>

                      <div className="hpi-about-scatter-wrap">
                        <PredictedVsActualChart
                          points={evaluationData.points}
                        />
                      </div>

                      {evaluationData.disclaimer && (
                        <p className="hpi-about-copy hpi-about-evaluation-disclaimer">
                          {evaluationData.disclaimer}
                        </p>
                      )}
                    </>
                  )}

                {!evaluationLoading &&
                  !evaluationError &&
                  evaluationData?.available &&
                  evaluationData.points.length === 0 && (
                    <p className="hpi-about-error" role="status">
                      {EVALUATION_UNAVAILABLE_MESSAGE}
                    </p>
                  )}
              </div>
            </div>
          </div>
        </section>

        {/* 6. Prediction range */}
        <section
          className="hpi-about-section"
          aria-labelledby="about-range-heading"
        >
          <div className="hpi-about-section-grid">
            <div>
              <p className="hpi-about-index">Range</p>
              <h2 id="about-range-heading" className="hpi-about-heading">
                What the estimated range means
              </h2>
            </div>
            <div>
              <p className="hpi-about-copy">{rangeNote}</p>
              <p className="hpi-about-copy">
                The low/high band around an estimate reflects historical
                out-of-fold residual prediction error. It is{" "}
                <strong>not</strong> a confidence interval,{" "}
                <strong>not</strong> a formal statistical prediction interval,
                and <strong>not</strong> a guaranteed transaction price.
              </p>
              {info.disclaimer && (
                <p className="hpi-about-copy">{info.disclaimer}</p>
              )}
            </div>
          </div>
        </section>

        {/* 7. Model influence */}
        {explanationView && (
          <section
            className="hpi-about-section"
            aria-labelledby="about-influence-heading"
          >
            <div className="hpi-about-section-grid">
              <div>
                <p className="hpi-about-index">Influence</p>
                <h2 id="about-influence-heading" className="hpi-about-heading">
                  Which characteristics influence the model most
                </h2>
              </div>
              <div>
                <p className="hpi-about-copy">
                  These are the features with the strongest overall influence on
                  the trained model. They are model-wide influences — not a
                  property-specific rupee attribution, and not SHAP values.
                </p>
                <ul className="hpi-about-why-list">
                  {explanationView.factors.map((factor) => (
                    <li key={factor.feature} className="hpi-about-why-item">
                      <div className="hpi-about-why-row">
                        <span>{factor.label}</span>
                        <span className="hpi-about-why-share">
                          {importanceToBarPercent(factor.importance)}%
                        </span>
                      </div>
                      <div className="hpi-about-why-track" aria-hidden="true">
                        <span
                          className="hpi-about-why-fill"
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
                {explanationView.note && (
                  <p className="hpi-about-why-note">{explanationView.note}</p>
                )}
              </div>
            </div>
          </section>
        )}

        {/* 8. Limitations */}
        <section
          className="hpi-about-section"
          aria-labelledby="about-limits-heading"
        >
          <div className="hpi-about-section-grid">
            <div>
              <p className="hpi-about-index">Limitations</p>
              <h2 id="about-limits-heading" className="hpi-about-heading">
                What this product does not claim
              </h2>
            </div>
            <div>
              <ul className="hpi-about-limits">
                {limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
                <li>
                  Market-history views do not represent live listings or live
                  market prices.
                </li>
                <li>
                  Global feature influence is not a property-specific explanation
                  of an individual estimate.
                </li>
                <li>
                  Similar properties come from the available historical Bengaluru
                  property dataset — not live inventory.
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* 9. CTA */}
        <div className="hpi-about-cta">
          <p className="hpi-about-cta-lead">Start with your property.</p>
          <Link to="/estimate" className="hpi-est-submit hpi-about-cta-btn">
            Get my estimate →
          </Link>
        </div>
      </main>
    </div>
  );
};

export default HowItWorksPage;
