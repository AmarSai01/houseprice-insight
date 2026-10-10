/**
 * Similar-properties helpers for GET /api/properties/similar.
 * Uses lastPayload from a successful estimate — never ML price fields.
 */

export const DEFAULT_SIMILAR_LIMIT = 5;
export const DEFAULT_MIN_SIMILARITY = 0.4;

export const SIMILAR_FALLBACK_ERROR =
  "Similar properties data is currently unavailable.";

export const SIMILAR_EMPTY_MESSAGE =
  "No sufficiently similar properties were found in the project dataset.";

const MATCH_NOTE_LABELS = {
  same_location: "Same location",
  location_fallback: "Different location (limited exact matches)",
  similar_size: "Similar size",
  same_bhk: "Same BHK",
  nearby_bhk: "Nearby BHK",
  same_area_type: "Same area type",
  same_ready_status: "Same ready-to-move status",
};

/**
 * Deterministic fingerprint for cache / stale-request guards.
 * @param {unknown} payload
 */
export function similarPayloadKey(payload) {
  if (!payload || typeof payload !== "object") return "";
  return JSON.stringify({
    area_type: payload.area_type,
    location: payload.location,
    total_sqft: payload.total_sqft,
    bhk: payload.bhk,
    bath: payload.bath,
    balcony: payload.balcony,
    is_ready_to_move: Boolean(payload.is_ready_to_move),
  });
}

/**
 * Build GET query params from a successful estimate lastPayload.
 * Never includes estimated_price_* fields.
 *
 * @param {Record<string, unknown>} payload
 */
export function buildSimilarQueryParams(payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Similar properties payload is required.");
  }

  return {
    area_type: String(payload.area_type),
    location: String(payload.location),
    total_sqft: Number(payload.total_sqft),
    bhk: Number.parseInt(String(payload.bhk), 10),
    bath: Number(payload.bath),
    balcony: Number(payload.balcony),
    is_ready_to_move: Boolean(payload.is_ready_to_move),
    limit: DEFAULT_SIMILAR_LIMIT,
    min_similarity: DEFAULT_MIN_SIMILARITY,
  };
}

/**
 * @param {unknown} data
 */
export function isValidSimilarResponse(data) {
  if (!data || typeof data !== "object") return false;
  if (!Array.isArray(data.results)) return false;
  if (!Number.isFinite(Number(data.count))) return false;
  if (Number(data.count) !== data.results.length) return false;
  if (typeof data.method !== "string" || !data.method) return false;
  if (typeof data.disclaimer !== "string") return false;

  for (const item of data.results) {
    if (!item || typeof item !== "object") return false;
    if (!Number.isFinite(Number(item.similarity))) return false;
    const sim = Number(item.similarity);
    if (sim < 0 || sim > 1) return false;
    if (typeof item.location !== "string") return false;
    if (!Number.isFinite(Number(item.listed_price_lakhs))) return false;
    if ("estimated_price_lakhs" in item) return false;
  }
  return true;
}

/**
 * @param {import('axios').AxiosInstance} api
 * @param {Record<string, unknown>} payload
 * @param {{ signal?: AbortSignal }} [options]
 */
export async function fetchSimilarProperties(api, payload, options = {}) {
  const params = buildSimilarQueryParams(payload);
  const response = await api.get("/api/properties/similar", {
    params,
    signal: options.signal,
  });
  const data = response.data;
  if (!isValidSimilarResponse(data)) {
    throw new Error("Incomplete similar-properties response.");
  }
  return data;
}

/**
 * @param {string} note
 */
export function formatMatchNote(note) {
  if (typeof note !== "string" || !note) return null;
  return MATCH_NOTE_LABELS[note] || null;
}

/**
 * @param {number} similarity
 */
export function formatSimilarityPercent(similarity) {
  const value = Number(similarity);
  if (!Number.isFinite(value)) return null;
  return `${(Math.round(value * 1000) / 10).toFixed(1)}%`;
}
