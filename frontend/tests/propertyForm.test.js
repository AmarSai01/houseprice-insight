import assert from "node:assert/strict";
import test from "node:test";
import {
  buildPredictPayload,
  createInitialPropertyForm,
  matchModelLocality,
} from "../src/services/propertyForm.js";

test("matchModelLocality maps case and spacing variants to the model spelling", () => {
  assert.equal(matchModelLocality("whitefield"), "Whitefield");
  assert.equal(matchModelLocality("  ELECTRONIC   city "), "Electronic City");
  assert.equal(matchModelLocality("1st phase jp nagar"), "1st Phase JP Nagar");
});

test("matchModelLocality returns null for localities the model does not know", () => {
  assert.equal(matchModelLocality("Atlantis"), null);
  assert.equal(matchModelLocality(""), null);
  assert.equal(matchModelLocality(undefined), null);
});

test("buildPredictPayload sends the canonical locality when one matches", () => {
  const form = { ...createInitialPropertyForm(), location: "whitefield", total_sqft: "1200", bhk: "2", bath: "2" };
  assert.equal(buildPredictPayload(form).location, "Whitefield");
});

test("buildPredictPayload keeps unknown localities as typed (trimmed)", () => {
  const form = { ...createInitialPropertyForm(), location: "  Atlantis ", total_sqft: "1200", bhk: "2", bath: "2" };
  assert.equal(buildPredictPayload(form).location, "Atlantis");
});
