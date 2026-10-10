import assert from "node:assert/strict";
import test from "node:test";
import {
  compareTwoProperties,
  computeComparisonSummary,
  isValidPredictionResponse,
  runPropertyPrediction,
  shouldBlockCompareSubmit,
} from "../src/services/compareProperties.js";

const samplePrediction = (lakhs, ppsft) => ({
  estimated_price_lakhs: lakhs,
  estimated_low_lakhs: lakhs - 10,
  estimated_high_lakhs: lakhs + 10,
  price_per_sqft: ppsft,
  estimated_price_inr: Math.round(lakhs * 100_000),
});

test("computeComparisonSummary calculates absolute and percent difference", () => {
  const summary = computeComparisonSummary(
    samplePrediction(100, 5000),
    samplePrediction(120, 5500)
  );
  assert.ok(summary);
  assert.equal(summary.absoluteDiffLakhs, 20);
  assert.equal(summary.percentDiff, 20);
  assert.equal(summary.higherProperty, "B");
  assert.match(summary.higherSummaryText, /Property B has the higher/);
});

test("computeComparisonSummary calculates price per sq.ft difference", () => {
  const summary = computeComparisonSummary(
    samplePrediction(90, 6000),
    samplePrediction(85, 5500)
  );
  assert.equal(summary.ppsftDiff, 500);
  assert.equal(summary.higherProperty, "A");
});

test("computeComparisonSummary handles tie", () => {
  const summary = computeComparisonSummary(
    samplePrediction(100, 5000),
    samplePrediction(100, 5000)
  );
  assert.equal(summary.higherProperty, "tie");
  assert.match(summary.higherSummaryText, /same estimated value/i);
});

test("isValidPredictionResponse rejects malformed payloads", () => {
  assert.equal(isValidPredictionResponse(null), false);
  assert.equal(isValidPredictionResponse({ estimated_price_lakhs: 0 }), false);
  assert.equal(
    isValidPredictionResponse(samplePrediction(100, 5000)),
    true
  );
});

test("compareTwoProperties succeeds with parallel predictions", async () => {
  const calls = [];
  const predictFn = async (payload) => {
    calls.push(payload.location);
    return samplePrediction(payload.location === "A-side" ? 100 : 110, 5000);
  };
  const result = await compareTwoProperties({
    predictFn,
    payloadA: { location: "A-side" },
    payloadB: { location: "B-side" },
  });
  assert.equal(result.propertyA.status, "success");
  assert.equal(result.propertyB.status, "success");
  assert.ok(result.summary);
  assert.equal(calls.length, 2);
});

test("compareTwoProperties preserves one-sided failure", async () => {
  const predictFn = async (payload) => {
    if (payload.location === "fail") {
      throw new Error("network");
    }
    return samplePrediction(100, 5000);
  };
  const result = await compareTwoProperties({
    predictFn,
    payloadA: { location: "ok" },
    payloadB: { location: "fail" },
  });
  assert.equal(result.propertyA.status, "success");
  assert.equal(result.propertyB.status, "error");
  assert.equal(result.summary, null);
  assert.match(result.propertyB.message, /estimate/i);
});

test("runPropertyPrediction rejects incomplete API data", async () => {
  const outcome = await runPropertyPrediction(async () => ({ foo: 1 }), {});
  assert.equal(outcome.status, "error");
  assert.match(outcome.message, /incomplete/i);
});

test("shouldBlockCompareSubmit prevents duplicate submissions while loading", () => {
  assert.equal(shouldBlockCompareSubmit(true), true);
  assert.equal(shouldBlockCompareSubmit(false), false);
});
