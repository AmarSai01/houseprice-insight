import assert from "node:assert/strict";
import test from "node:test";
import { getApiErrorMessage } from "../src/services/apiErrors.js";

test("network errors produce a connection message", () => {
  const message = getApiErrorMessage(
    { code: "ERR_NETWORK", message: "Network Error" },
    "fallback"
  );
  assert.match(message, /connect/i);
});

test("422 field errors become readable messages", () => {
  const message = getApiErrorMessage({
    response: {
      status: 422,
      data: {
        detail: "Invalid request.",
        errors: [{ field: "body.total_sqft", message: "Value error, must be > 0" }],
      },
    },
  });
  assert.match(message, /total_sqft/i);
  assert.doesNotMatch(message, /Value error,/i);
});

test("string detail is preferred for 401 login failures", () => {
  const message = getApiErrorMessage({
    response: {
      status: 401,
      data: { detail: "Incorrect email or password" },
    },
  });
  assert.equal(message, "Incorrect email or password");
});

test("500 responses do not expose traceback objects", () => {
  const message = getApiErrorMessage(
    {
      response: {
        status: 500,
        data: { detail: { traceback: "secret" } },
      },
    },
    "Unable to estimate"
  );
  assert.equal(message, "A server error occurred. Please try again.");
});

test("503 uses unavailable wording", () => {
  const message = getApiErrorMessage({
    response: { status: 503, data: {} },
  });
  assert.match(message, /unavailable/i);
});
