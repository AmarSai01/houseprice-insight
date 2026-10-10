import assert from "node:assert/strict";
import test from "node:test";
import {
  FALLBACK_MODEL_COMPARISON,
  FALLBACK_SELECTION_RULE,
  getModelComparisonDisplayRows,
  getModelComparisonSelectionRule,
  resolveModelComparison,
} from "../src/services/modelInfo.js";

const liveComparison = {
  scope: "cross_validation_on_training_split",
  selection_rule: "Lowest cross-validated MAE on training folds",
  models: [
    {
      model_name: "RandomForestRegressor",
      selected: true,
      cv_r2_mean: 0.6824115050624149,
    },
    {
      model_name: "HistGradientBoostingRegressor",
      selected: false,
      cv_r2_mean: 0.6751872620426862,
    },
    {
      model_name: "LinearRegression",
      selected: false,
      cv_r2_mean: 0.634203160601488,
    },
  ],
};

test("live model comparison is preferred when available", () => {
  const resolved = resolveModelComparison({
    model_comparison: liveComparison,
  });
  assert.equal(resolved, liveComparison);
  assert.notEqual(resolved, FALLBACK_MODEL_COMPARISON);
});

test("API model names and CV R² are mapped for display", () => {
  const rows = getModelComparisonDisplayRows(liveComparison);
  assert.equal(rows.length, 3);
  assert.equal(rows[0].name, "Random Forest");
  assert.equal(rows[0].cv_r2_mean, 0.6824115050624149);
  assert.equal(rows[0].selected, true);
  assert.equal(rows[1].name, "HistGradientBoosting");
  assert.equal(rows[1].cv_r2_mean, 0.6751872620426862);
  assert.equal(rows[2].name, "Linear Regression");
  assert.equal(rows[2].cv_r2_mean, 0.634203160601488);
});

test("selected model information is handled correctly", () => {
  const rows = getModelComparisonDisplayRows(liveComparison);
  const selected = rows.filter((row) => row.selected);
  assert.equal(selected.length, 1);
  assert.equal(selected[0].model_name, "RandomForestRegressor");
});

test("missing or empty model_comparison falls back safely", () => {
  assert.equal(
    resolveModelComparison({}),
    FALLBACK_MODEL_COMPARISON
  );
  assert.equal(
    resolveModelComparison({ model_comparison: { models: [] } }),
    FALLBACK_MODEL_COMPARISON
  );
  assert.equal(resolveModelComparison(null), FALLBACK_MODEL_COMPARISON);

  const fallbackRows = getModelComparisonDisplayRows(
    resolveModelComparison({ model_comparison: null })
  );
  assert.ok(fallbackRows.length >= 3);
  assert.equal(fallbackRows[0].selected, true);
});

test("API failure path can still render verified fallback rows", () => {
  // Simulate About page: catch → set FALLBACK_MODEL_INFO with comparison.
  const info = {
    model_name: "RandomForestRegressor",
    model_comparison: FALLBACK_MODEL_COMPARISON,
  };
  const rows = getModelComparisonDisplayRows(resolveModelComparison(info));
  assert.ok(rows.length > 0);
  assert.ok(Number.isFinite(rows[0].cv_r2_mean));
});

test("selection_rule comes from API when present", () => {
  assert.equal(
    getModelComparisonSelectionRule(liveComparison, null),
    "Lowest cross-validated MAE on training folds"
  );
  assert.equal(
    getModelComparisonSelectionRule({}, "Custom rule"),
    "Custom rule"
  );
  assert.equal(
    getModelComparisonSelectionRule({}, null),
    FALLBACK_SELECTION_RULE
  );
});

test("display rows never invent CV R² values", () => {
  const rows = getModelComparisonDisplayRows({
    models: [
      { model_name: "X", selected: false, cv_r2_mean: "bad" },
      { model_name: "Y", selected: true },
      { selected: false, cv_r2_mean: 0.5 },
    ],
  });
  assert.equal(rows.length, 0);
});

test("fallback comparison is the only offline source and matches verified metadata shape", () => {
  // Guard against reintroducing a separate rounded MODEL_COMPARISON_CV_R2 source.
  const names = FALLBACK_MODEL_COMPARISON.models.map((m) => m.model_name);
  assert.deepEqual(names, [
    "RandomForestRegressor",
    "HistGradientBoostingRegressor",
    "LinearRegression",
  ]);
  for (const row of FALLBACK_MODEL_COMPARISON.models) {
    assert.ok(Number.isFinite(row.cv_r2_mean));
    assert.ok(row.cv_r2_mean > 0.6 && row.cv_r2_mean < 0.7);
  }
});
