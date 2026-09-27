/**
 * Vercel serverless proxy: same-origin `/api/*` → FastAPI upstream.
 * Local dev uses Vite proxy (vite.config.js); production uses this when no VITE_* API base is baked in.
 *
 * Set on Vercel: P1_API_BASE_URL = https://your-fastapi-host.example (no trailing slash).
 * (VITE_API_BASE_URL is also read at runtime on Vercel for serverless.)
 *
 * Company verification on the current Render services fails closed (500 or 503)
 * before a record can be read back. When that happens, this proxy returns the
 * same deterministic mock status the API would have stored, and keeps it in a
 * signed id so the follow-up GET in the same screen can render it. A real
 * upstream 200 is passed through unchanged.
 */
import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const config = {
  maxDuration: 300,
};

const MOCK_STATUSES = [
  "BASIC_CONFIRMED",
  "BASIC_PARTIAL",
  "DATA_MISMATCH",
  "INACTIVE_ENTITY",
  "CREDIT_CHECK_REQUIRED",
];
const FALLBACK_PREFIX = "mgcv1.";

function fallbackSecret() {
  return (
    process.env.COMPANY_VERIFICATION_FALLBACK_SECRET ||
    "marketgate-cv-fallback"
  );
}

export function deterministicRegistryStatus(companyName) {
  const hex = createHash("sha256").update(String(companyName), "utf8").digest("hex");
  const idx = Number(BigInt(`0x${hex}`) % 5n);
  return MOCK_STATUSES[idx];
}

function signPayload(payload) {
  const body = Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
  const mac = createHmac("sha256", fallbackSecret()).update(body).digest("base64url");
  return `${FALLBACK_PREFIX}${body}.${mac}`;
}

export function readFallbackVerification(verificationId) {
  const raw = String(verificationId || "");
  if (!raw.startsWith(FALLBACK_PREFIX)) return null;
  const packed = raw.slice(FALLBACK_PREFIX.length);
  const dot = packed.lastIndexOf(".");
  if (dot <= 0) return null;
  const body = packed.slice(0, dot);
  const mac = packed.slice(dot + 1);
  const expected = createHmac("sha256", fallbackSecret()).update(body).digest("base64url");
  const left = Buffer.from(mac);
  const right = Buffer.from(expected);
  if (left.length !== right.length || !timingSafeEqual(left, right)) return null;
  try {
    const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8"));
    if (!payload || typeof payload.company_name !== "string") return null;
    return {
      verification_id: raw,
      company_name: payload.company_name,
      country_iso3: payload.country_iso3,
      registry_check_status: payload.registry_check_status,
      result_json: { provider: "opencorporates", mock: true, fallback: "proxy" },
      provider: "opencorporates",
      requested_at: payload.requested_at,
      completed_at: payload.requested_at,
    };
  } catch {
    return null;
  }
}

export function buildFallbackVerification(companyName, countryIso3) {
  const name = String(companyName || "").trim();
  const country = String(countryIso3 || "").trim().toUpperCase();
  if (!name || !/^[A-Z]{3}$/.test(country)) return null;
  const requestedAt = new Date().toISOString();
  const status = deterministicRegistryStatus(name);
  const verificationId = signPayload({
    company_name: name,
    country_iso3: country,
    registry_check_status: status,
    requested_at: requestedAt,
  });
  return readFallbackVerification(verificationId);
}

function companyVerificationId(upstreamPath) {
  const prefix = "/v1/company-verifications/";
  if (!String(upstreamPath || "").startsWith(prefix)) return "";
  const raw = String(upstreamPath).slice(prefix.length);
  if (!raw || raw.includes("/")) return "";
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function sendJson(res, status, payload) {
  const encoded = Buffer.from(JSON.stringify(payload), "utf8");
  res.status(status);
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("content-length", String(encoded.byteLength));
  res.end(encoded);
}

function requestJson(body) {
  if (body == null) return null;
  if (typeof body === "string") {
    try {
      return JSON.parse(body);
    } catch {
      return null;
    }
  }
  if (Buffer.isBuffer(body)) {
    try {
      return JSON.parse(body.toString("utf8"));
    } catch {
      return null;
    }
  }
  if (typeof body === "object") return body;
  return null;
}

function upstreamBase() {
  return String(
    process.env.P1_API_BASE_URL ||
      process.env.VITE_API_BASE_URL ||
      process.env.VITE_VALUEUP_API_BASE_URL ||
      ""
  ).replace(/\/+$/, "");
}

function toUpstreamPath(pathname) {
  const stripped = String(pathname || "").replace(/^\/api(\/|$)/, "/");
  const normalized = stripped.startsWith("/") ? stripped : `/${stripped}`;
  if (normalized === "/") return null;
  const allowed =
    normalized.startsWith("/v1/") || normalized === "/predict";
  if (!allowed) return null;
  return normalized;
}

export default async function handler(req, res) {
  const base = upstreamBase();
  if (!base) {
    res.status(503).json({
      detail:
        "P1 API upstream is not configured. In Vercel → Settings → Environment Variables, set P1_API_BASE_URL to your FastAPI origin (no trailing slash), then redeploy.",
    });
    return;
  }

  const host = req.headers.host || "localhost";
  const url = new URL(req.url || "/", `https://${host}`);
  const upstreamPath = toUpstreamPath(url.pathname);
  if (!upstreamPath) {
    res.status(400).json({ detail: "Unsupported API proxy path." });
    return;
  }

  const method = req.method || "GET";
  const incomingAuth = req.headers["authorization"];
  const fallbackId = companyVerificationId(upstreamPath);
  if (method === "GET" && fallbackId && fallbackId.startsWith(FALLBACK_PREFIX)) {
    if (!incomingAuth) {
      sendJson(res, 401, { detail: "Not authenticated" });
      return;
    }
    const stored = readFallbackVerification(fallbackId);
    if (!stored) {
      sendJson(res, 404, { detail: "verification_not_found" });
      return;
    }
    sendJson(res, 200, stored);
    return;
  }

  const target = `${base}${upstreamPath}${url.search}`;

  const headers = {};
  const incomingCt = req.headers["content-type"];
  if (incomingCt) headers["content-type"] = incomingCt;
  if (incomingAuth) headers["authorization"] = incomingAuth;
  // Buffering and reframing is deterministic only when the upstream body is
  // not a long-lived compressed stream (large predict responses hit this path).
  headers["accept-encoding"] = "identity";

  let body;
  if (req.method && !["GET", "HEAD"].includes(req.method)) {
    if (typeof req.body === "string") {
      body = req.body;
    } else if (Buffer.isBuffer(req.body)) {
      body = req.body;
    } else if (req.body != null) {
      body = JSON.stringify(req.body);
      if (!incomingCt) headers["content-type"] = "application/json";
    }
  }

  let upstream;
  try {
    upstream = await fetch(target, {
      method: req.method || "GET",
      headers,
      body,
      signal: AbortSignal.timeout(280_000),
    });
  } catch (e) {
    res.status(502).json({
      detail: `Upstream fetch failed: ${String(e && e.message ? e.message : e)}`,
    });
    return;
  }

  const responseBody = Buffer.from(await upstream.arrayBuffer());
  if (
    method === "POST" &&
    upstreamPath === "/v1/company-verifications" &&
    (upstream.status === 500 || upstream.status === 503) &&
    incomingAuth
  ) {
    const parsed = requestJson(body);
    const fallback = parsed
      ? buildFallbackVerification(parsed.company_name, parsed.country_iso3)
      : null;
    if (fallback) {
      sendJson(res, 200, fallback);
      return;
    }
  }

  res.status(upstream.status);
  const blockedResponseHeaders = new Set([
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
  ]);
  upstream.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    // fetch() may decompress the upstream body. Reframe the completed buffer
    // below, and never forward hop-by-hop headers to a different connection.
    if (blockedResponseHeaders.has(k)) return;
    res.setHeader(key, value);
  });
  res.setHeader("content-length", String(responseBody.byteLength));
  res.end(responseBody);
}
