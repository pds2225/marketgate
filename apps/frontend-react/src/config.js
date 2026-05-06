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

export const ENDPOINTS = {
  health: buildApiUrl("/api/v1/health"),
  predict: buildApiUrl("/v1/predict"),
  legacyPredict: buildApiUrl("/api/predict"),
  snapshot: buildApiUrl("/api/v1/snapshot"),
};
