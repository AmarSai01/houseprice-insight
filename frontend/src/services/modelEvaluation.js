/**
 * Held-out predicted-vs-actual evaluation helpers.
 * Uses GET /api/model-evaluation/predicted-vs-actual only — never fabricates points.
 */

export const EVALUATION_UNAVAILABLE_MESSAGE =
  "Model evaluation is currently unavailable.";

export const EVALUATION_FALLBACK_ERROR =
  "Model evaluation is currently unavailable.";

/**
 * @param {unknown} data
 */
export function isAvailableEvaluation(data) {
  return Boolean(data && typeof data === "object" && data.available === true);
}

/**
 * @param {unknown} data
 */
export function normalizeEvaluationResponse(data) {
  if (!data || typeof data !== "object") {
    return {
      available: false,
      message: EVALUATION_UNAVAILABLE_MESSAGE,
      points: [],
      metrics: null,
      point_count: 0,
    };
  }

  if (data.available !== true) {
    return {
      available: false,
      message:
        typeof data.message === "string" && data.message.trim()
          ? data.message
          : EVALUATION_UNAVAILABLE_MESSAGE,
      points: [],
      metrics: null,
      point_count: 0,
      model_version: data.model_version ?? null,
    };
  }

  const rawPoints = Array.isArray(data.points) ? data.points : [];
  const points = [];
  for (const item of rawPoints) {
    if (!item || typeof item !== "object") continue;
    const actual = Number(item.actual_price_lakhs);
    const predicted = Number(item.predicted_price_lakhs);
    if (!Number.isFinite(actual) || !Number.isFinite(predicted)) continue;
    points.push({
      actual_price_lakhs: actual,
      predicted_price_lakhs: predicted,
    });
  }

  const metrics =
    data.metrics && typeof data.metrics === "object"
      ? {
          mae: Number.isFinite(Number(data.metrics.mae))
            ? Number(data.metrics.mae)
            : null,
          rmse: Number.isFinite(Number(data.metrics.rmse))
            ? Number(data.metrics.rmse)
            : null,
          r2: Number.isFinite(Number(data.metrics.r2))
            ? Number(data.metrics.r2)
            : null,
        }
      : null;

  const pointCount = Number.isFinite(Number(data.point_count))
    ? Number(data.point_count)
    : points.length;

  return {
    available: true,
    model_name: data.model_name ?? null,
    model_version: data.model_version ?? null,
    evaluation_split: data.evaluation_split ?? "held_out_test",
    random_state: data.random_state ?? null,
    point_count: pointCount,
    units: data.units ?? "INR_lakhs",
    metrics,
    disclaimer:
      typeof data.disclaimer === "string" ? data.disclaimer : null,
    points,
  };
}

/**
 * Shared axis bounds so the identity line y = x is meaningful.
 * @param {Array<{ actual_price_lakhs: number, predicted_price_lakhs: number }>} points
 */
export function computeSharedAxisBounds(points) {
  if (!Array.isArray(points) || points.length === 0) {
    return { min: 0, max: 1 };
  }
  let min = Infinity;
  let max = -Infinity;
  for (const point of points) {
    min = Math.min(min, point.actual_price_lakhs, point.predicted_price_lakhs);
    max = Math.max(max, point.actual_price_lakhs, point.predicted_price_lakhs);
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return { min: 0, max: 1 };
  }
  if (min === max) {
    const pad = Math.max(1, Math.abs(min) * 0.05);
    return { min: min - pad, max: max + pad };
  }
  const pad = (max - min) * 0.04;
  return { min: Math.max(0, min - pad), max: max + pad };
}

/**
 * @param {import('axios').AxiosInstance} apiClient
 */
export async function fetchPredictedVsActual(apiClient) {
  const response = await apiClient.get(
    "/api/model-evaluation/predicted-vs-actual"
  );
  return normalizeEvaluationResponse(response.data);
}
