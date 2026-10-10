/**
 * Compare two properties via independent POST /api/predict calls.
 * Summary math uses API-returned values only.
 */

import { getApiErrorMessage } from "./apiErrors.js";

const PREDICTION_REQUIRED_NUMERIC = [
  "estimated_price_lakhs",
  "estimated_low_lakhs",
  "estimated_high_lakhs",
  "price_per_sqft",
];

/**
 * @param {unknown} data
 */
export function isValidPredictionResponse(data) {
  if (!data || typeof data !== "object") return false;
  for (const key of PREDICTION_REQUIRED_NUMERIC) {
    const value = Number(data[key]);
    if (!Number.isFinite(value)) return false;
  }
  if (Number(data.estimated_price_lakhs) <= 0) return false;
  return true;
}

/**
 * @param {number} value
 */
export function formatCompactLakhs(value) {
  return Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

/**
 * @param {Record<string, unknown>} predictionA
 * @param {Record<string, unknown>} predictionB
 */
export function computeComparisonSummary(predictionA, predictionB) {
  if (!isValidPredictionResponse(predictionA) || !isValidPredictionResponse(predictionB)) {
    return null;
  }

  const priceA = Number(predictionA.estimated_price_lakhs);
  const priceB = Number(predictionB.estimated_price_lakhs);
  const ppsftA = Number(predictionA.price_per_sqft);
  const ppsftB = Number(predictionB.price_per_sqft);

  const absoluteDiffLakhs = Math.abs(priceA - priceB);
  const lower = Math.min(priceA, priceB);
  const higher = Math.max(priceA, priceB);
  const percentDiff =
    lower > 0 ? Math.round(((higher - lower) / lower) * 1000) / 10 : 0;
  const ppsftDiff = Math.round((ppsftA - ppsftB) * 100) / 100;

  let higherProperty = "tie";
  if (priceA > priceB) higherProperty = "A";
  else if (priceB > priceA) higherProperty = "B";

  let higherSummaryText =
    "Both properties have the same estimated value.";
  if (higherProperty === "A") {
    higherSummaryText = "Property A has the higher estimated value.";
  } else if (higherProperty === "B") {
    higherSummaryText = "Property B has the higher estimated value.";
  }

  return {
    absoluteDiffLakhs: Math.round(absoluteDiffLakhs * 100) / 100,
    percentDiff,
    ppsftDiff,
    higherProperty,
    higherSummaryText,
  };
}

/**
 * @param {(payload: object) => Promise<unknown>} predictFn
 * @param {object} payload
 * @param {string} [fallbackMessage]
 */
export async function runPropertyPrediction(
  predictFn,
  payload,
  fallbackMessage = "Unable to estimate this property right now. Please try again."
) {
  try {
    const data = await predictFn(payload);
    if (!isValidPredictionResponse(data)) {
      return {
        status: "error",
        message: "The prediction service returned an incomplete response.",
      };
    }
    return { status: "success", data, payload };
  } catch (error) {
    return {
      status: "error",
      message: getApiErrorMessage(error, fallbackMessage),
      error,
    };
  }
}

/**
 * Run two predictions in parallel (independent API calls).
 *
 * @param {{
 *   predictFn: (payload: object) => Promise<unknown>,
 *   payloadA: object,
 *   payloadB: object,
 * }} options
 */
export async function compareTwoProperties({ predictFn, payloadA, payloadB }) {
  const [propertyA, propertyB] = await Promise.all([
    runPropertyPrediction(predictFn, payloadA),
    runPropertyPrediction(
      predictFn,
      payloadB,
      "Unable to estimate Property B right now. Please try again."
    ),
  ]);

  const summary =
    propertyA.status === "success" && propertyB.status === "success"
      ? computeComparisonSummary(propertyA.data, propertyB.data)
      : null;

  return { propertyA, propertyB, summary };
}

/**
 * @param {boolean} loading
 */
export function shouldBlockCompareSubmit(loading) {
  return Boolean(loading);
}
