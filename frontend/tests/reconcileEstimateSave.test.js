import assert from "node:assert/strict";
import test from "node:test";
import { reconcileUnauthenticatedSave } from "../src/services/reconcileEstimateSave.js";

test("guest prediction path never verifies session", async () => {
  let verified = false;
  let cleared = false;
  const result = await reconcileUnauthenticatedSave({
    wasAuthenticated: false,
    saved: false,
    verifySession: async () => {
      verified = true;
    },
    clearSession: () => {
      cleared = true;
    },
  });
  assert.equal(result.status, "ok");
  assert.equal(verified, false);
  assert.equal(cleared, false);
});

test("saved=true keeps session without revalidation", async () => {
  let verified = false;
  const result = await reconcileUnauthenticatedSave({
    wasAuthenticated: true,
    saved: true,
    verifySession: async () => {
      verified = true;
    },
    clearSession: () => {},
  });
  assert.equal(result.status, "ok");
  assert.equal(verified, false);
});

test("authenticated saved=false with valid session stays logged in", async () => {
  let cleared = false;
  const result = await reconcileUnauthenticatedSave({
    wasAuthenticated: true,
    saved: false,
    verifySession: async () => ({ data: { id: 1 } }),
    clearSession: () => {
      cleared = true;
    },
  });
  assert.equal(result.status, "save_failed");
  assert.equal(cleared, false);
});

test("authenticated saved=false with 401 clears session", async () => {
  let cleared = false;
  const result = await reconcileUnauthenticatedSave({
    wasAuthenticated: true,
    saved: false,
    verifySession: async () => {
      const error = new Error("Unauthorized");
      error.response = { status: 401 };
      throw error;
    },
    clearSession: () => {
      cleared = true;
    },
  });
  assert.equal(result.status, "session_expired");
  assert.equal(cleared, true);
});

test("authenticated saved=false with network error does not force logout", async () => {
  let cleared = false;
  const result = await reconcileUnauthenticatedSave({
    wasAuthenticated: true,
    saved: false,
    verifySession: async () => {
      throw new Error("Network Error");
    },
    clearSession: () => {
      cleared = true;
    },
  });
  assert.equal(result.status, "save_failed");
  assert.equal(cleared, false);
});
