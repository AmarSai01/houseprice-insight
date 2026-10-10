import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import {
  AFFORDABILITY_DISCLAIMER,
  AFFORDABILITY_REFERENCE_NOTE,
  computeLoanAmount,
  roundCurrency,
  validateAffordabilityInputs,
} from "../services/affordability";
import { PRODUCT_NAV_LINKS } from "../constants/navLinks";
import { formatInr } from "../services/market";
import { useAuth } from "../contexts/AuthContext";
import "./EstimatePage.css";
import "./AffordabilityPage.css";

const NAV_LINKS = PRODUCT_NAV_LINKS;

function getInitialAffordabilityState(locationState) {
  const fromEstimate =
    locationState &&
    typeof locationState === "object" &&
    locationState.propertyPriceInr != null &&
    Number.isFinite(Number(locationState.propertyPriceInr)) &&
    Number(locationState.propertyPriceInr) > 0;

  return {
    fromEstimate: Boolean(fromEstimate),
    form: {
      propertyPrice: fromEstimate
        ? String(Math.round(Number(locationState.propertyPriceInr)))
        : "",
      downPayment: "0",
      annualRate: "",
      tenureYears: "",
      monthlyIncome: "",
    },
  };
}

const AffordabilityPage = () => {
  const location = useLocation();
  const { isAuthenticated, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [initial] = useState(() => getInitialAffordabilityState(location.state));
  const [form, setForm] = useState(initial.form);
  const fromEstimate = initial.fromEstimate;

  const closeMobile = () => setMobileOpen(false);

  const evaluation = useMemo(() => validateAffordabilityInputs(form), [form]);
  const result = evaluation.valid ? evaluation.result : null;

  /** Display-only derived loan amount using existing computeLoanAmount. */
  const derivedLoanAmount = useMemo(() => {
    const propertyPrice = Number(form.propertyPrice);
    const downPayment =
      form.downPayment === "" || form.downPayment === undefined
        ? Number.NaN
        : Number(form.downPayment);
    if (!Number.isFinite(propertyPrice) || propertyPrice <= 0) return null;
    if (!Number.isFinite(downPayment) || downPayment < 0) return null;
    if (downPayment >= propertyPrice) return null;
    const loan = computeLoanAmount(propertyPrice, downPayment);
    if (!Number.isFinite(loan) || loan <= 0) return null;
    return roundCurrency(loan);
  }, [form.propertyPrice, form.downPayment]);

  const paymentBreakdown = useMemo(() => {
    if (!result || result.totalPayment <= 0) return null;
    const principalPct = Math.min(
      100,
      Math.max(0, (result.loanAmount / result.totalPayment) * 100)
    );
    const interestPct = Math.min(
      100,
      Math.max(0, (result.totalInterest / result.totalPayment) * 100)
    );
    return {
      principalPct,
      interestPct,
    };
  }, [result]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const inputClass = (name) =>
    `hpi-est-input${evaluation.errors[name] ? " is-invalid" : ""}`;

  const fieldProps = (name) => ({
    "aria-invalid": evaluation.errors[name] ? true : undefined,
    "aria-describedby": evaluation.errors[name] ? `${name}-error` : undefined,
  });

  return (
    <div className="hpi-est hpi-est--product hpi-affordability hpi-ds">
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
                  link.to === "/affordability" ? "is-active" : undefined
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
            aria-controls="afford-mobile-nav"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div id="afford-mobile-nav" className="hpi-est-drawer">
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
          <p className="hpi-est-stage">Property affordability</p>
          <h1 className="hpi-est-title">Could this property fit your budget?</h1>
          <p className="hpi-est-lead">
            Estimate monthly EMI and total borrowing costs from the property
            price, down payment, interest rate, and loan tenure you enter. This
            is planning support — not a bank approval or financial advice.
          </p>
          {fromEstimate && (
            <p className="hpi-aff-context">
              Based on the property value you entered on Estimate — you can edit
              it below.
            </p>
          )}
        </header>

        <div className="hpi-est-afford-workspace">
          <section aria-labelledby="afford-inputs-label">
            <h2 id="afford-inputs-label" className="hpi-est-col-label">
              Loan inputs
            </h2>

            <form
              className="hpi-est-form"
              noValidate
              onSubmit={(e) => e.preventDefault()}
            >
              <div className="hpi-aff-group">
                <p className="hpi-aff-group-label">Property &amp; down payment</p>
                <div className="hpi-est-field">
                  <label htmlFor="propertyPrice" className="hpi-est-label">
                    Property price (₹)
                  </label>
                  <input
                    id="propertyPrice"
                    name="propertyPrice"
                    type="number"
                    min="1"
                    step="1"
                    value={form.propertyPrice}
                    onChange={handleChange}
                    placeholder="e.g. 8500000"
                    className={inputClass("propertyPrice")}
                    {...fieldProps("propertyPrice")}
                  />
                  {evaluation.errors.propertyPrice && (
                    <p
                      id="propertyPrice-error"
                      className="hpi-est-field-error"
                      role="alert"
                    >
                      {evaluation.errors.propertyPrice}
                    </p>
                  )}
                </div>

                <div className="hpi-est-field">
                  <label htmlFor="downPayment" className="hpi-est-label">
                    Down payment (₹)
                  </label>
                  <input
                    id="downPayment"
                    name="downPayment"
                    type="number"
                    min="0"
                    step="1"
                    value={form.downPayment}
                    onChange={handleChange}
                    placeholder="0"
                    className={inputClass("downPayment")}
                    {...fieldProps("downPayment")}
                  />
                  {evaluation.errors.downPayment && (
                    <p
                      id="downPayment-error"
                      className="hpi-est-field-error"
                      role="alert"
                    >
                      {evaluation.errors.downPayment}
                    </p>
                  )}
                </div>

                <div
                  className="hpi-aff-loan-derived"
                  aria-live="polite"
                  aria-atomic="true"
                >
                  <p className="hpi-est-label">Loan amount</p>
                  <p className="hpi-aff-loan-value">
                    {derivedLoanAmount != null
                      ? `₹${formatInr(derivedLoanAmount)}`
                      : "—"}
                  </p>
                  <p className="hpi-aff-loan-hint">
                    Property price minus down payment. A higher down payment
                    reduces the loan amount.
                  </p>
                </div>
              </div>

              <div className="hpi-aff-group">
                <p className="hpi-aff-group-label">Rate &amp; tenure</p>
                <div className="hpi-est-field-row">
                  <div className="hpi-est-field">
                    <label htmlFor="annualRate" className="hpi-est-label">
                      Annual interest rate (%)
                    </label>
                    <input
                      id="annualRate"
                      name="annualRate"
                      type="number"
                      min="0"
                      step="0.01"
                      value={form.annualRate}
                      onChange={handleChange}
                      placeholder="8.5"
                      className={inputClass("annualRate")}
                      {...fieldProps("annualRate")}
                    />
                    {evaluation.errors.annualRate && (
                      <p
                        id="annualRate-error"
                        className="hpi-est-field-error"
                        role="alert"
                      >
                        {evaluation.errors.annualRate}
                      </p>
                    )}
                  </div>

                  <div className="hpi-est-field">
                    <label htmlFor="tenureYears" className="hpi-est-label">
                      Loan tenure (years)
                    </label>
                    <input
                      id="tenureYears"
                      name="tenureYears"
                      type="number"
                      min="1"
                      max="40"
                      step="1"
                      value={form.tenureYears}
                      onChange={handleChange}
                      placeholder="20"
                      className={inputClass("tenureYears")}
                      {...fieldProps("tenureYears")}
                    />
                    {evaluation.errors.tenureYears && (
                      <p
                        id="tenureYears-error"
                        className="hpi-est-field-error"
                        role="alert"
                      >
                        {evaluation.errors.tenureYears}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="hpi-aff-group hpi-aff-group--last">
                <p className="hpi-aff-group-label">Optional</p>
                <div className="hpi-est-field">
                  <label htmlFor="monthlyIncome" className="hpi-est-label">
                    Monthly income (₹/month) — optional
                  </label>
                  <input
                    id="monthlyIncome"
                    name="monthlyIncome"
                    type="number"
                    min="1"
                    step="1"
                    value={form.monthlyIncome}
                    onChange={handleChange}
                    placeholder="Optional"
                    className={inputClass("monthlyIncome")}
                    {...fieldProps("monthlyIncome")}
                  />
                  {evaluation.errors.monthlyIncome && (
                    <p
                      id="monthlyIncome-error"
                      className="hpi-est-field-error"
                      role="alert"
                    >
                      {evaluation.errors.monthlyIncome}
                    </p>
                  )}
                  <p className="hpi-aff-field-hint">
                    Used only to show EMI as a share of monthly income.
                  </p>
                </div>
              </div>
            </form>

            <aside className="hpi-aff-interpret" aria-label="How this works">
              <h3 className="hpi-aff-interpret-h">How these inputs relate</h3>
              <ul className="hpi-aff-interpret-list">
                <li>
                  A higher down payment reduces the loan amount (principal).
                </li>
                <li>
                  Interest rate and tenure affect the total borrowing cost.
                </li>
                <li>
                  EMI is calculated from the entered loan amount, rate, and
                  tenure using standard amortization math.
                </li>
              </ul>
            </aside>
          </section>

          <aside className="hpi-est-afford-results" aria-live="polite">
            <h2 className="hpi-est-col-label">Results</h2>

            {!result ? (
              <div className="hpi-est-afford-empty">
                <p>
                  Enter a valid property price, down payment, interest rate, and
                  tenure to see estimated monthly EMI and loan totals.
                </p>
              </div>
            ) : (
              <div className="hpi-aff-report">
                <section
                  className="hpi-aff-emi-block"
                  aria-labelledby="afford-emi-heading"
                >
                  <p id="afford-emi-heading" className="hpi-est-label">
                    Estimated monthly EMI
                  </p>
                  <p
                    className="hpi-est-afford-emi"
                    aria-label={`Estimated monthly EMI ${formatInr(
                      result.emi
                    )} rupees`}
                  >
                    ₹{formatInr(result.emi)}
                    <small>/month</small>
                  </p>
                </section>

                <dl className="hpi-aff-facts">
                  <div className="hpi-est-afford-row">
                    <dt>Loan amount</dt>
                    <dd>₹{formatInr(result.loanAmount)}</dd>
                  </div>
                  <div className="hpi-est-afford-row">
                    <dt>Interest rate</dt>
                    <dd>{result.annualRatePercent}% p.a.</dd>
                  </div>
                  <div className="hpi-est-afford-row">
                    <dt>Loan tenure</dt>
                    <dd>
                      {result.tenureYears} years ({result.tenureMonths} months)
                    </dd>
                  </div>
                  <div className="hpi-est-afford-row">
                    <dt>Total interest</dt>
                    <dd>₹{formatInr(result.totalInterest)}</dd>
                  </div>
                  <div className="hpi-est-afford-row hpi-est-afford-row--total">
                    <dt>Total payment</dt>
                    <dd>₹{formatInr(result.totalPayment)}</dd>
                  </div>
                </dl>

                {paymentBreakdown && (
                  <section
                    className="hpi-aff-breakdown"
                    aria-labelledby="afford-breakdown-heading"
                  >
                    <h3
                      id="afford-breakdown-heading"
                      className="hpi-aff-section-h"
                    >
                      Payment breakdown
                    </h3>
                    <div
                      className="hpi-aff-bar"
                      role="img"
                      aria-label={`Of total payment, principal is about ${paymentBreakdown.principalPct.toFixed(
                        0
                      )} percent and interest is about ${paymentBreakdown.interestPct.toFixed(
                        0
                      )} percent`}
                    >
                      <span
                        className="hpi-aff-bar-principal"
                        style={{ width: `${paymentBreakdown.principalPct}%` }}
                      />
                      <span
                        className="hpi-aff-bar-interest"
                        style={{ width: `${paymentBreakdown.interestPct}%` }}
                      />
                    </div>
                    <ul className="hpi-aff-bar-legend">
                      <li>
                        <span className="hpi-aff-swatch hpi-aff-swatch--principal" />
                        Principal ₹{formatInr(result.loanAmount)}
                      </li>
                      <li>
                        <span className="hpi-aff-swatch hpi-aff-swatch--interest" />
                        Interest ₹{formatInr(result.totalInterest)}
                      </li>
                    </ul>
                  </section>
                )}

                {result.emiIncomeSharePercent != null && (
                  <section
                    className="hpi-aff-income"
                    aria-labelledby="afford-income-heading"
                  >
                    <h3 id="afford-income-heading" className="hpi-aff-section-h">
                      EMI share of monthly income
                    </h3>
                    <p className="hpi-aff-income-value">
                      {result.emiIncomeSharePercent}%
                    </p>
                    <p className="hpi-est-afford-note">
                      {AFFORDABILITY_REFERENCE_NOTE}
                    </p>
                  </section>
                )}

                <p className="hpi-est-disclaimer">
                  {AFFORDABILITY_DISCLAIMER} This calculator is for planning
                  purposes only and does not constitute financial advice.
                </p>
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
};

export default AffordabilityPage;
