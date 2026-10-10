/**
 * Resolve the Axios API base URL for development vs production builds.
 * VITE_API_URL is public frontend config (not a secret) and is baked in at build time.
 */

export const DEFAULT_DEV_API_BASE_URL = "http://127.0.0.1:8001";

export const MISSING_PRODUCTION_API_URL_ERROR =
  "VITE_API_URL must be configured with the production backend API URL for production builds.";

export const LOCALHOST_PRODUCTION_API_URL_ERROR =
  "VITE_API_URL cannot point to a localhost/loopback host for production builds.";

const DISALLOWED_PRODUCTION_HOSTS = new Set([
  "localhost",
  "127.0.0.1",
  "0.0.0.0",
]);

/**
 * @param {unknown} value
 */
export function normalizeApiBaseUrlInput(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * @param {string} value
 */
export function isDisallowedProductionApiHost(value) {
  const raw = normalizeApiBaseUrlInput(value);
  if (!raw) return false;

  try {
    const host = new URL(raw).hostname.toLowerCase();
    return DISALLOWED_PRODUCTION_HOSTS.has(host);
  } catch {
    const lower = raw.toLowerCase();
    return (
      lower.includes("localhost") ||
      lower.includes("127.0.0.1") ||
      lower.includes("0.0.0.0")
    );
  }
}

/**
 * @param {{
 *   viteApiUrl?: unknown,
 *   isProduction?: boolean,
 * }} options
 * @returns {string}
 */
export function resolveApiBaseUrl({
  viteApiUrl,
  isProduction = false,
} = {}) {
  const configured = normalizeApiBaseUrlInput(viteApiUrl);

  if (isProduction) {
    if (!configured) {
      throw new Error(MISSING_PRODUCTION_API_URL_ERROR);
    }
    if (isDisallowedProductionApiHost(configured)) {
      throw new Error(LOCALHOST_PRODUCTION_API_URL_ERROR);
    }
    return configured;
  }

  if (configured) {
    return configured;
  }
  return DEFAULT_DEV_API_BASE_URL;
}

/**
 * Whether this process is a production deployment build
 * (matches backend APP_ENV / ENVIRONMENT convention).
 * @param {Record<string, string | undefined>} [env]
 */
export function isProductionDeployEnv(env = process.env) {
  const value = String(
    env.APP_ENV || env.ENVIRONMENT || env.VITE_APP_ENV || ""
  )
    .toLowerCase()
    .trim();
  return value === "production" || value === "prod";
}

/**
 * Validate API URL for a Vite production build (`vite build`).
 * - Always requires VITE_API_URL (no silent empty bake).
 * - Rejects localhost/loopback when APP_ENV indicates production deploy.
 *
 * @param {{
 *   viteApiUrl?: unknown,
 *   isViteBuild?: boolean,
 *   isProductionDeploy?: boolean,
 * }} options
 * @returns {string}
 */
export function assertViteBuildApiBaseUrl({
  viteApiUrl,
  isViteBuild = false,
  isProductionDeploy = false,
} = {}) {
  if (!isViteBuild) {
    return resolveApiBaseUrl({
      viteApiUrl,
      isProduction: false,
    });
  }

  if (isProductionDeploy) {
    return resolveApiBaseUrl({
      viteApiUrl,
      isProduction: true,
    });
  }

  const configured = normalizeApiBaseUrlInput(viteApiUrl);
  if (!configured) {
    throw new Error(MISSING_PRODUCTION_API_URL_ERROR);
  }
  return configured;
}
