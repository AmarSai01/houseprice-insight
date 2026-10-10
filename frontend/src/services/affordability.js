/**
 * EMI and affordability helpers — standard amortization math only.
 * Not a lender approval or financial advice system.
 */

export const MAX_LOAN_TENURE_YEARS = 40;

export const AFFORDABILITY_DISCLAIMER =
  "Calculator results are estimates based on the inputs provided. Actual loan terms, eligibility, fees, taxes, insurance, and lender policies may differ.";

export const AFFORDABILITY_REFERENCE_NOTE =
  "Reference only — actual affordability depends on lender policies, existing obligations, credit profile, taxes, insurance, and other costs.";

/**
 * @param {number} value
 */
export function roundCurrency(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.round(value);
}

/**
 * @param {number} propertyPrice
 * @param {number} downPayment
 */
export function computeLoanAmount(propertyPrice, downPayment) {
  return propertyPrice - downPayment;
}

/**
 * Annual percentage → decimal monthly rate.
 * @param {number} annualRatePercent
 */
export function computeMonthlyRate(annualRatePercent) {
  return annualRatePercent / 12 / 100;
}

/**
 * Standard EMI: P × r × (1+r)^n / ((1+r)^n − 1)
 * Zero interest: P / n
 *
 * @param {number} principal Loan principal (P)
 * @param {number} annualRatePercent Annual interest rate (%)
 * @param {number} tenureYears Loan tenure in years
 * @returns {number | null}
 */
export function computeEmi(principal, annualRatePercent, tenureYears) {
  if (!Number.isFinite(principal) || principal <= 0) return null;
  if (!Number.isFinite(tenureYears) || tenureYears <= 0) return null;
  if (!Number.isFinite(annualRatePercent) || annualRatePercent < 0) return null;

  const n = tenureYears * 12;
  if (n <= 0) return null;

  if (annualRatePercent === 0) {
    return principal / n;
  }

  const r = computeMonthlyRate(annualRatePercent);
  const compound = (1 + r) ** n;
  return (principal * r * compound) / (compound - 1);
}

/**
 * @param {number} emi
 * @param {number} monthlyIncome
 */
export function computeEmiShareOfIncome(emi, monthlyIncome) {
  if (!Number.isFinite(emi) || emi < 0) return null;
  if (!Number.isFinite(monthlyIncome) || monthlyIncome <= 0) return null;
  return Math.round((emi / monthlyIncome) * 1000) / 10;
}

/**
 * @param {{
 *   propertyPrice: string | number,
 *   downPayment: string | number,
 *   annualRate: string | number,
 *   tenureYears: string | number,
 *   monthlyIncome?: string | number,
 * }} raw
 */
export function validateAffordabilityInputs(raw) {
  const errors = {};

  const propertyPrice = Number(raw.propertyPrice);
  const downPayment =
    raw.downPayment === "" || raw.downPayment === undefined
      ? Number.NaN
      : Number(raw.downPayment);
  const annualRate =
    raw.annualRate === "" || raw.annualRate === undefined
      ? Number.NaN
      : Number(raw.annualRate);
  const tenureYears = Number(raw.tenureYears);
  const hasIncome =
    raw.monthlyIncome !== "" &&
    raw.monthlyIncome !== undefined &&
    raw.monthlyIncome !== null;
  const monthlyIncome = hasIncome ? Number(raw.monthlyIncome) : null;

  if (
    raw.propertyPrice === "" ||
    !Number.isFinite(propertyPrice) ||
    propertyPrice <= 0
  ) {
    errors.propertyPrice = "Enter a property price greater than 0.";
  }

  if (
    raw.downPayment === "" ||
    !Number.isFinite(downPayment) ||
    downPayment < 0
  ) {
    errors.downPayment = "Enter a down payment of 0 or more.";
  } else if (Number.isFinite(propertyPrice) && downPayment >= propertyPrice) {
    errors.downPayment = "Down payment must be less than the property price.";
  }

  if (
    raw.annualRate === "" ||
    raw.annualRate === undefined ||
    !Number.isFinite(annualRate) ||
    annualRate < 0
  ) {
    errors.annualRate = "Enter an annual interest rate of 0% or more.";
  }

  if (
    raw.tenureYears === "" ||
    !Number.isFinite(tenureYears) ||
    tenureYears <= 0
  ) {
    errors.tenureYears = "Enter a loan tenure greater than 0 years.";
  } else if (tenureYears > MAX_LOAN_TENURE_YEARS) {
    errors.tenureYears = `Loan tenure cannot exceed ${MAX_LOAN_TENURE_YEARS} years.`;
  }

  if (
    monthlyIncome !== null &&
    (!Number.isFinite(monthlyIncome) || monthlyIncome <= 0)
  ) {
    errors.monthlyIncome =
      "Enter a monthly income greater than 0, or leave blank.";
  }

  if (Object.keys(errors).length > 0) {
    return { valid: false, errors, result: null };
  }

  const loanAmount = computeLoanAmount(propertyPrice, downPayment);
  if (loanAmount <= 0) {
    errors.downPayment = "Down payment must be less than the property price.";
    return { valid: false, errors, result: null };
  }

  const emiRaw = computeEmi(loanAmount, annualRate, tenureYears);
  if (emiRaw === null) {
    return {
      valid: false,
      errors: { _form: "Unable to calculate EMI with the given inputs." },
      result: null,
    };
  }

  const months = tenureYears * 12;
  const emi = roundCurrency(emiRaw);
  const loanRounded = roundCurrency(loanAmount);
  const totalPayment = roundCurrency(emi * months);
  const totalInterest = totalPayment - loanRounded;

  let emiIncomeSharePercent = null;
  if (monthlyIncome !== null && monthlyIncome > 0) {
    emiIncomeSharePercent = computeEmiShareOfIncome(emi, monthlyIncome);
  }

  return {
    valid: true,
    errors: {},
    result: {
      propertyPrice: roundCurrency(propertyPrice),
      downPayment: roundCurrency(downPayment),
      loanAmount: loanRounded,
      annualRatePercent: annualRate,
      tenureYears,
      tenureMonths: months,
      emi,
      totalPayment,
      totalInterest,
      emiIncomeSharePercent,
    },
  };
}
