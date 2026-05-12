/**
 * Vercel serverless proxy: same-origin `/api/*` → FastAPI upstream.
 * Local dev uses Vite proxy (vite.config.js); production uses this when no VITE_* API base is baked in.
 *
 * Set on Vercel: P1_API_BASE_URL = https://your-fastapi-host.example (no trailing slash).
 * (VITE_API_BASE_URL is also read at runtime on Vercel for serverless.)
 */
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

  const target = `${base}${upstreamPath}${url.search}`;

  const headers = {};
  const incomingCt = req.headers["content-type"];
  if (incomingCt) headers["content-type"] = incomingCt;

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
    });
  } catch (e) {
    res.status(502).json({
      detail: `Upstream fetch failed: ${String(e && e.message ? e.message : e)}`,
    });
    return;
  }

  const text = await upstream.text();
  res.status(upstream.status);
  upstream.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (k === "content-encoding" || k === "transfer-encoding") return;
    res.setHeader(key, value);
  });
  res.send(text);
}
