/**
 * Safe helpers for the global "Why this price?" explanation payload.
 * This is model-level influence only — never treat importance as ₹ attribution.
 */

/**
 * @param {unknown} explanation
 * @param {{ max?: number }} [options]
 * @returns {null | { note: string, factors: Array<{ feature: string, label: string, importance: number, rank: number }> }}
 */
export function getGlobalExplanationView(explanation, options = {}) {
  const max = Number.isFinite(options.max) ? options.max : 5;
  if (!explanation || typeof explanation !== "object") return null;
  if (explanation.type !== "global_feature_influence") return null;
  if (!Array.isArray(explanation.factors) || explanation.factors.length === 0) {
    return null;
  }

  const factors = explanation.factors
    .filter(
      (factor) =>
        factor &&
        typeof factor.label === "string" &&
        typeof factor.feature === "string" &&
        Number.isFinite(Number(factor.importance))
    )
    .slice(0, Math.max(1, max))
    .map((factor) => ({
      feature: factor.feature,
      label: factor.label,
      importance: Number(factor.importance),
      rank: Number(factor.rank) || 0,
    }));

  if (factors.length === 0) return null;

  return {
    note:
      typeof explanation.note === "string" && explanation.note.trim()
        ? explanation.note
        : "These are model-level factors that generally influence estimates. They are not a rupee-by-rupee breakdown of this property.",
    factors,
  };
}

/**
 * Convert a normalized importance share (0–1) to a bar width percentage.
 * Caps at 100 for display safety; not a price percentage.
 */
export function importanceToBarPercent(importance) {
  const value = Number(importance);
  if (!Number.isFinite(value) || value <= 0) return 0;
  return Math.min(100, Math.round(value * 1000) / 10);
}
