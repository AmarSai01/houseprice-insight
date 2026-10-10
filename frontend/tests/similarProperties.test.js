import assert from "node:assert/strict";
import test from "node:test";
import {
  DEFAULT_MIN_SIMILARITY,
  DEFAULT_SIMILAR_LIMIT,
  buildSimilarQueryParams,
  fetchSimilarProperties,
  formatMatchNote,
  formatSimilarityPercent,
  isValidSimilarResponse,
  similarPayloadKey,
} from "../src/services/similarProperties.js";

const samplePayload = {
  area_type: "Super built-up  Area",
  location: "Whitefield",
  total_sqft: 1200,
  bhk: 2,
  bath: 2,
  balcony: 1,
  is_ready_to_move: true,
};

test("buildSimilarQueryParams maps all seven fields", () => {
  const params = buildSimilarQueryParams(samplePayload);
  assert.equal(params.area_type, samplePayload.area_type);
  assert.equal(params.location, samplePayload.location);
  assert.equal(params.total_sqft, 1200);
  assert.equal(params.bhk, 2);
  assert.equal(params.bath, 2);
  assert.equal(params.balcony, 1);
  assert.equal(params.is_ready_to_move, true);
});

test("limit defaults to 5", () => {
  assert.equal(buildSimilarQueryParams(samplePayload).limit, DEFAULT_SIMILAR_LIMIT);
  assert.equal(DEFAULT_SIMILAR_LIMIT, 5);
});

test("min_similarity defaults to 0.40", () => {
  assert.equal(
    buildSimilarQueryParams(samplePayload).min_similarity,
    DEFAULT_MIN_SIMILARITY
  );
  assert.equal(DEFAULT_MIN_SIMILARITY, 0.4);
});

test("boolean is_ready_to_move is preserved correctly", () => {
  assert.equal(
    buildSimilarQueryParams({ ...samplePayload, is_ready_to_move: false })
      .is_ready_to_move,
    false
  );
  assert.equal(
    buildSimilarQueryParams({ ...samplePayload, is_ready_to_move: 1 })
      .is_ready_to_move,
    true
  );
});

test("no price field is sent to the similarity API", () => {
  const params = buildSimilarQueryParams({
    ...samplePayload,
    estimated_price_lakhs: 99,
    estimated_price_inr: 9_900_000,
    listed_price_lakhs: 70,
  });
  assert.equal("estimated_price_lakhs" in params, false);
  assert.equal("estimated_price_inr" in params, false);
  assert.equal("listed_price_lakhs" in params, false);
  assert.equal("price" in params, false);
});

test("fetchSimilarProperties calls the correct endpoint", async () => {
  let calledPath = "";
  let calledConfig = null;
  const api = {
    get: async (path, config) => {
      calledPath = path;
      calledConfig = config;
      return {
        data: {
          query: samplePayload,
          count: 1,
          method: "weighted_feature_distance",
          disclaimer: "Historical dataset listing values.",
          results: [
            {
              rank: 1,
              similarity: 0.91,
              location: "Whitefield",
              area_type: "Super built-up  Area",
              total_sqft: 1180,
              bhk: 2,
              bath: 2,
              balcony: 1,
              is_ready_to_move: true,
              listed_price_lakhs: 72,
              listed_price_per_sqft: 6101.69,
              match_notes: ["same_location"],
              location_match: true,
            },
          ],
        },
      };
    },
  };

  const data = await fetchSimilarProperties(api, samplePayload);
  assert.equal(calledPath, "/api/properties/similar");
  assert.deepEqual(calledConfig.params, buildSimilarQueryParams(samplePayload));
  assert.equal(data.count, 1);
});

test("response validation accepts a valid backend response", () => {
  assert.equal(
    isValidSimilarResponse({
      query: samplePayload,
      count: 0,
      method: "weighted_feature_distance",
      disclaimer: "Historical dataset listing values.",
      results: [],
      message: "No sufficiently similar properties were found.",
    }),
    true
  );
});

test("malformed response is rejected", () => {
  assert.equal(isValidSimilarResponse(null), false);
  assert.equal(isValidSimilarResponse({ count: 1, results: [] }), false);
  assert.equal(
    isValidSimilarResponse({
      count: 1,
      method: "weighted_feature_distance",
      disclaimer: "x",
      results: [
        {
          similarity: 1.5,
          location: "Whitefield",
          listed_price_lakhs: 10,
        },
      ],
    }),
    false
  );
  assert.equal(
    isValidSimilarResponse({
      count: 1,
      method: "weighted_feature_distance",
      disclaimer: "x",
      results: [
        {
          similarity: 0.9,
          location: "Whitefield",
          listed_price_lakhs: 10,
          estimated_price_lakhs: 99,
        },
      ],
    }),
    false
  );
});

test("listed_price_lakhs remains distinct from prediction price", () => {
  const params = buildSimilarQueryParams(samplePayload);
  assert.equal("estimated_price_lakhs" in params, false);
  const valid = isValidSimilarResponse({
    count: 1,
    method: "weighted_feature_distance",
    disclaimer: "Historical dataset listing values.",
    results: [
      {
        similarity: 0.9,
        location: "Whitefield",
        listed_price_lakhs: 72,
      },
    ],
  });
  assert.equal(valid, true);
});

test("cache key is deterministic", () => {
  const a = similarPayloadKey(samplePayload);
  const b = similarPayloadKey({ ...samplePayload });
  assert.equal(a, b);
  assert.notEqual(
    a,
    similarPayloadKey({ ...samplePayload, total_sqft: 1300 })
  );
});

test("match note and similarity formatting stay user-facing", () => {
  assert.equal(formatMatchNote("same_location"), "Same location");
  assert.equal(formatMatchNote("unknown_note"), null);
  assert.equal(formatSimilarityPercent(0.962), "96.2%");
});
