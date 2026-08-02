const DEFAULT_API_BASE = "";

function normalizeBaseUrl(value) {
  return String(value || "").replace(/\/+$/, "");
}

const CONFIGURED_API_BASE =
  import.meta.env.VITE_VALUEUP_API_BASE_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  DEFAULT_API_BASE;

// Deployed Vercel clients always use the same-origin `/api` proxy. Direct API
// origins are only useful for local Vite development and otherwise trigger CORS.
export const API_BASE = import.meta.env.DEV
  ? normalizeBaseUrl(CONFIGURED_API_BASE) || DEFAULT_API_BASE
  : DEFAULT_API_BASE;

export function buildApiUrl(path, base = API_BASE) {
  const normalizedBase = normalizeBaseUrl(base) || DEFAULT_API_BASE;
  const normalizedPath = String(path || "").startsWith("/")
    ? String(path || "")
    : `/${String(path || "")}`;
  return `${normalizedBase}${normalizedPath}`;
}

/**
 * P1 / legacy FastAPI paths. Local Vite development can call a configured API
 * origin directly; deployments use `/api/...` through api/[...path].js.
 */
export function buildP1Url(path) {
  const normalizedPath = String(path || "").startsWith("/")
    ? String(path || "")
    : `/${String(path || "")}`;
  let base = normalizeBaseUrl(API_BASE);
  // If VITE_* points at the same host as the SPA (common misconfig on Vercel),
  // absolute URLs like https://marketgate.vercel.app/v1/predict hit the static app, not FastAPI.
  if (base && typeof window !== "undefined") {
    try {
      if (new URL(base).origin === window.location.origin) {
        base = "";
      }
    } catch {
      /* ignore invalid base */
    }
  }
  if (base) {
    return `${base}${normalizedPath}`;
  }
  return `/api${normalizedPath}`;
}

export const ENDPOINTS = {
  health: buildP1Url("/v1/health"),
  predict: buildP1Url("/v1/predict"),
  legacyPredict: buildP1Url("/predict"),
  snapshot: buildP1Url("/v1/snapshot"),
  demoSnapshot: buildP1Url("/v1/demo/snapshot"),
};
