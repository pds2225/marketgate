const DEFAULT_API_BASE = "";

function normalizeBaseUrl(value) {
  return String(value || "").replace(/\/+$/, "");
}

export const API_BASE =
  normalizeBaseUrl(
    import.meta.env.VITE_VALUEUP_API_BASE_URL ||
      import.meta.env.VITE_API_BASE_URL ||
      DEFAULT_API_BASE
  ) || DEFAULT_API_BASE;

export function buildApiUrl(path, base = API_BASE) {
  const normalizedBase = normalizeBaseUrl(base) || DEFAULT_API_BASE;
  const normalizedPath = String(path || "").startsWith("/")
    ? String(path || "")
    : `/${String(path || "")}`;
  return `${normalizedBase}${normalizedPath}`;
}

/**
 * P1 / legacy FastAPI paths. If VITE_* API base is set, call that origin directly.
 * Otherwise use same-origin `/api/...` (Vite dev proxy strips `/api`; Vercel uses api/[...path].js).
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
};
