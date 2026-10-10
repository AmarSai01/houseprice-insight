import assert from "node:assert/strict";
import test from "node:test";
import {
  EVALUATION_UNAVAILABLE_MESSAGE,
  computeSharedAxisBounds,
  fetchPredictedVsActual,
  isAvailableEvaluation,
  normalizeEvaluationResponse,
} from "../src/services/modelEvaluation.js";

const samplePoint = {
  actual_price_lakhs: 150,
  predicted_price_lakhs: 135.27,
};

test("normalizeEvaluationResponse maps API points and metrics", () => {
  const data = normalizeEvaluationResponse({
    available: true,
    model_version: "1.0.0",
    point_count: 2,
    units: "INR_lakhs",
    metrics: { mae: 30.82, rmse: 71.12, r2: 0.6885 },
    disclaimer: "Held-out test predictions.",
    points: [
      samplePoint,
      { actual_price_lakhs: 80, predicted_price_lakhs: 75 },
      { actual_price_lakhs: "bad", predicted_price_lakhs: 1 },
    ],
  });

  assert.equal(data.available, true);
  assert.equal(data.point_count, 2);
  assert.equal(data.points.length, 2);
  assert.deepEqual(data.points[0], samplePoint);
  assert.equal(data.metrics.mae, 30.82);
  assert.equal(data.metrics.r2, 0.6885);
  assert.equal(data.disclaimer, "Held-out test predictions.");
});

test("available=false does not fabricate points", () => {
  const data = normalizeEvaluationResponse({
    available: false,
    message: "Artifact mismatch.",
    points: [{ actual_price_lakhs: 1, predicted_price_lakhs: 1 }],
  });
  assert.equal(data.available, false);
  assert.equal(data.points.length, 0);
  assert.equal(data.message, "Artifact mismatch.");
  assert.equal(isAvailableEvaluation(data), false);
});

test("metrics and point count come from API response", () => {
  const data = normalizeEvaluationResponse({
    available: true,
    point_count: 2536,
    metrics: { mae: 11.1, rmse: 22.2, r2: 0.5 },
    points: [samplePoint],
  });
  assert.equal(data.point_count, 2536);
  assert.equal(data.metrics.mae, 11.1);
  assert.equal(data.metrics.rmse, 22.2);
  assert.equal(data.metrics.r2, 0.5);
});

test("malformed payload becomes unavailable without invented points", () => {
  const data = normalizeEvaluationResponse(null);
  assert.equal(data.available, false);
  assert.equal(data.points.length, 0);
  assert.equal(data.message, EVALUATION_UNAVAILABLE_MESSAGE);
});

test("shared axis bounds include full range", () => {
  const bounds = computeSharedAxisBounds([
    { actual_price_lakhs: 10, predicted_price_lakhs: 12 },
    { actual_price_lakhs: 100, predicted_price_lakhs: 90 },
  ]);
  assert.ok(bounds.min <= 10);
  assert.ok(bounds.max >= 100);
});

test("fetchPredictedVsActual calls the evaluation endpoint", async () => {
  let called = "";
  const api = {
    get: async (path) => {
      called = path;
      return {
        data: {
          available: true,
          point_count: 1,
          metrics: { mae: 1, rmse: 2, r2: 0.1 },
          points: [samplePoint],
          disclaimer: "x",
        },
      };
    },
  };
  const data = await fetchPredictedVsActual(api);
  assert.equal(called, "/api/model-evaluation/predicted-vs-actual");
  assert.equal(data.available, true);
  assert.equal(data.points.length, 1);
});
