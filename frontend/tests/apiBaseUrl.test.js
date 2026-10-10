import assert from "node:assert/strict";
import test from "node:test";
import {
  DEFAULT_DEV_API_BASE_URL,
  LOCALHOST_PRODUCTION_API_URL_ERROR,
  MISSING_PRODUCTION_API_URL_ERROR,
  assertViteBuildApiBaseUrl,
  isDisallowedProductionApiHost,
  isProductionDeployEnv,
  resolveApiBaseUrl,
} from "../src/services/apiBaseUrl.js";

test("development with VITE_API_URL configured uses that URL", () => {
  assert.equal(
    resolveApiBaseUrl({
      viteApiUrl: "http://127.0.0.1:8001",
      isProduction: false,
    }),
    "http://127.0.0.1:8001"
  );
});

test("development without VITE_API_URL uses existing localhost backend", () => {
  assert.equal(
    resolveApiBaseUrl({ viteApiUrl: undefined, isProduction: false }),
    DEFAULT_DEV_API_BASE_URL
  );
  assert.equal(
    resolveApiBaseUrl({ viteApiUrl: "  ", isProduction: false }),
    DEFAULT_DEV_API_BASE_URL
  );
  assert.equal(DEFAULT_DEV_API_BASE_URL, "http://127.0.0.1:8001");
});

test("production with VITE_API_URL configured uses that URL", () => {
  assert.equal(
    resolveApiBaseUrl({
      viteApiUrl: "https://api.example.com",
      isProduction: true,
    }),
    "https://api.example.com"
  );
});

test("production without VITE_API_URL fails clearly", () => {
  assert.throws(
    () => resolveApiBaseUrl({ viteApiUrl: "", isProduction: true }),
    (error) => {
      assert.equal(error.message, MISSING_PRODUCTION_API_URL_ERROR);
      return true;
    }
  );
});

test("production localhost URL is rejected", () => {
  assert.throws(
    () =>
      resolveApiBaseUrl({
        viteApiUrl: "http://localhost:8001",
        isProduction: true,
      }),
    (error) => {
      assert.equal(error.message, LOCALHOST_PRODUCTION_API_URL_ERROR);
      return true;
    }
  );
});

test("production 127.0.0.1 URL is rejected", () => {
  assert.throws(
    () =>
      resolveApiBaseUrl({
        viteApiUrl: "http://127.0.0.1:8001",
        isProduction: true,
      }),
    (error) => {
      assert.equal(error.message, LOCALHOST_PRODUCTION_API_URL_ERROR);
      return true;
    }
  );
  assert.equal(isDisallowedProductionApiHost("http://0.0.0.0:8001"), true);
});

test("normal production URL is accepted", () => {
  assert.equal(
    resolveApiBaseUrl({
      viteApiUrl: "https://api.example.com",
      isProduction: true,
    }),
    "https://api.example.com"
  );
  assert.equal(isDisallowedProductionApiHost("https://api.example.com"), false);
});

test("vite build without VITE_API_URL fails even in local deploy mode", () => {
  assert.throws(
    () =>
      assertViteBuildApiBaseUrl({
        viteApiUrl: "",
        isViteBuild: true,
        isProductionDeploy: false,
      }),
    (error) => error.message === MISSING_PRODUCTION_API_URL_ERROR
  );
});

test("local vite build may use loopback API URL", () => {
  assert.equal(
    assertViteBuildApiBaseUrl({
      viteApiUrl: "http://127.0.0.1:8001",
      isViteBuild: true,
      isProductionDeploy: false,
    }),
    "http://127.0.0.1:8001"
  );
});

test("production deploy vite build rejects loopback API URL", () => {
  assert.throws(
    () =>
      assertViteBuildApiBaseUrl({
        viteApiUrl: "http://127.0.0.1:8001",
        isViteBuild: true,
        isProductionDeploy: true,
      }),
    (error) => error.message === LOCALHOST_PRODUCTION_API_URL_ERROR
  );
});

test("isProductionDeployEnv matches backend APP_ENV convention", () => {
  assert.equal(isProductionDeployEnv({ APP_ENV: "production" }), true);
  assert.equal(isProductionDeployEnv({ ENVIRONMENT: "prod" }), true);
  assert.equal(isProductionDeployEnv({ VITE_APP_ENV: "production" }), true);
  assert.equal(isProductionDeployEnv({ APP_ENV: "development" }), false);
  assert.equal(isProductionDeployEnv({}), false);
});
