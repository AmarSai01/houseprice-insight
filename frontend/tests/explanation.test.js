import assert from "node:assert/strict";
import test from "node:test";
import {
  getGlobalExplanationView,
  importanceToBarPercent,
} from "../src/services/explanation.js";

test("renders top global factors when explanation is present", () => {
  const view = getGlobalExplanationView(
    {
      type: "global_feature_influence",
      scope: "model",
      method: "permutation_importance_mae",
      note: "Model-level factors only.",
      factors: [
        { feature: "total_sqft", label: "Property size", importance: 0.55, rank: 1 },
        { feature: "bath", label: "Bathrooms", importance: 0.14, rank: 2 },
        { feature: "location", label: "Location", importance: 0.09, rank: 3 },
      ],
    },
    { max: 2 }
  );

  assert.ok(view);
  assert.equal(view.factors.length, 2);
  assert.equal(view.factors[0].label, "Property size");
  assert.equal(view.note, "Model-level factors only.");
});

test("hides explanation section when payload is absent", () => {
  assert.equal(getGlobalExplanationView(undefined), null);
  assert.equal(getGlobalExplanationView(null), null);
  assert.equal(getGlobalExplanationView({}), null);
  assert.equal(
    getGlobalExplanationView({ type: "global_feature_influence", factors: [] }),
    null
  );
});

test("bar percent is display-only share, not currency", () => {
  assert.equal(importanceToBarPercent(0.549397), 54.9);
  assert.equal(importanceToBarPercent(-1), 0);
  assert.equal(importanceToBarPercent("x"), 0);
});
