/**
 * Helpers for /api/model-info model comparison (CV on training split).
 * Live API is preferred; fallback uses verified project metadata only.
 */

export const FALLBACK_SELECTION_RULE =
  "Lowest cross-validated MAE on training folds";

/**
 * Verified CV comparison from model_metadata.json (not invented UI values).
 * Used only when live model_comparison is missing or empty.
 */
export const FALLBACK_MODEL_COMPARISON = {
  scope: "cross_validation_on_training_split",
  selection_rule: FALLBACK_SELECTION_RULE,
  unit_note:
    "Cross-validated MAE and RMSE are in INR lakhs. Cross-validated R² is unitless. These CV metrics are for model selection comparison; they are not the held-out test metrics.",
  models: [
    {
      model_name: "RandomForestRegressor",
      selected: true,
      cv_mae_mean: 33.06882982563963,
      cv_mae_std: 1.3312035909700124,
      cv_rmse_mean: 81.72430842057975,
      cv_rmse_std: 6.537522575490865,
      cv_r2_mean: 0.6824115050624149,
      cv_r2_std: 0.03520695170875633,
    },
    {
      model_name: "HistGradientBoostingRegressor",
      selected: false,
      cv_mae_mean: 33.71146534779317,
      cv_mae_std: 1.1156999207840683,
      cv_rmse_mean: 82.72529109918993,
      cv_rmse_std: 4.278912938201808,
      cv_r2_mean: 0.6751872620426862,
      cv_r2_std: 0.011303791862599648,
    },
    {
      model_name: "LinearRegression",
      selected: false,
      cv_mae_mean: 41.01956299586056,
      cv_mae_std: 1.424498426189466,
      cv_rmse_mean: 87.76131395104538,
      cv_rmse_std: 5.554328636978344,
      cv_r2_mean: 0.634203160601488,
      cv_r2_std: 0.026773932112375415,
    },
  ],
};

/**
 * Prefer live API model_comparison; otherwise verified fallback.
 * @param {unknown} info
 * @param {typeof FALLBACK_MODEL_COMPARISON} [fallback]
 */
export function resolveModelComparison(
  info,
  fallback = FALLBACK_MODEL_COMPARISON
) {
  const comparison =
    info && typeof info === "object" ? info.model_comparison : null;

  if (
    comparison &&
    typeof comparison === "object" &&
    Array.isArray(comparison.models) &&
    comparison.models.length > 0
  ) {
    return comparison;
  }

  return fallback;
}

/**
 * @param {string | null | undefined} name
 */
export function friendlyComparisonModelName(name) {
  if (!name) return "Model";
  if (name === "RandomForestRegressor") return "Random Forest";
  if (name === "HistGradientBoostingRegressor") return "HistGradientBoosting";
  if (name === "LinearRegression") return "Linear Regression";
  return name;
}

/**
 * Map API comparison models to display rows (name + CV R² + selected).
 * Does not invent metrics — invalid rows are skipped.
 * @param {unknown} comparison
 */
export function getModelComparisonDisplayRows(comparison) {
  const models =
    comparison &&
    typeof comparison === "object" &&
    Array.isArray(comparison.models)
      ? comparison.models
      : [];

  const rows = [];
  for (const row of models) {
    if (!row || typeof row !== "object") continue;
    const cvR2 = Number(row.cv_r2_mean);
    if (!Number.isFinite(cvR2)) continue;
    const modelName =
      typeof row.model_name === "string" ? row.model_name : null;
    if (!modelName) continue;
    rows.push({
      model_name: modelName,
      name: friendlyComparisonModelName(modelName),
      cv_r2_mean: cvR2,
      selected: Boolean(row.selected),
    });
  }
  return rows;
}

/**
 * @param {unknown} comparison
 * @param {string | null | undefined} topLevelSelectionRule
 */
export function getModelComparisonSelectionRule(
  comparison,
  topLevelSelectionRule
) {
  if (
    comparison &&
    typeof comparison === "object" &&
    typeof comparison.selection_rule === "string" &&
    comparison.selection_rule.trim()
  ) {
    return comparison.selection_rule.trim();
  }
  if (
    typeof topLevelSelectionRule === "string" &&
    topLevelSelectionRule.trim()
  ) {
    return topLevelSelectionRule.trim();
  }
  return FALLBACK_SELECTION_RULE;
}
