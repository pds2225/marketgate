/**
 * Run the marketgate Playwright E2E suite against a LOCAL stack.
 *
 * The CI config (apps/frontend-react/playwright.config.js) is built for the
 * deployed environment and hard-fails without E2E_BASE_URL / secrets. This
 * wrapper points the same specs at localhost so the full journey
 * (register -> predict -> buyer select -> contact unlock -> inquiry draft ->
 * review_required -> re-login -> company verification -> cleanup) can be
 * verified before pushing.
 *
 * Prereqs (start these in two terminals first):
 *   1. Backend  : cd services/p1-export-fit-api && \
 *                 APP_ENV=e2e E2E_ADMIN_TOKEN=<32+ chars> \
 *                 .venv/Scripts/python -m uvicorn main:app --port 8000
 *   2. Frontend : cd apps/frontend-react && npm run dev   (port 5173)
 *
 * Usage:
 *   node tools/e2e-local.mjs              # whole suite (write journey included)
 *   node tools/e2e-local.mjs --grep @smoke
 *   node tools/e2e-local.mjs tests/e2e/buyer-search.spec.js
 *
 * Never point this at production. It registers throwaway e2e-*@example.com
 * accounts and deletes them through /v1/e2e/cleanup.
 */
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const FRONTEND_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'apps', 'frontend-react')
const PLAYWRIGHT_CLI = join(FRONTEND_DIR, 'node_modules', '@playwright', 'test', 'cli.js')

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173'
const API_BASE_URL = process.env.E2E_API_BASE_URL || 'http://localhost:8000'
const ADMIN_TOKEN =
  process.env.E2E_ADMIN_TOKEN || 'local-e2e-admin-token-0123456789abcdef'

async function ping(url) {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(4000) })
    return res.ok
  } catch {
    return false
  }
}

const frontendUp = await ping(BASE_URL)
const healthUp = await ping(`${API_BASE_URL}/v1/health`)
const e2eRouterUp = await ping(`${API_BASE_URL}/v1/e2e/identity`)

if (!frontendUp || !healthUp) {
  console.error(
    [
      'Local stack not reachable:',
      `  frontend ${BASE_URL}         ${frontendUp ? 'ok' : 'DOWN'}`,
      `  backend  ${API_BASE_URL}/v1/health  ${healthUp ? 'ok' : 'DOWN'}`,
      '',
      'Start both (see header of this file) and retry.',
    ].join('\n')
  )
  process.exit(2)
}
if (!e2eRouterUp) {
  console.error(
    `Backend is up but /v1/e2e/identity is 404 — restart it with APP_ENV=e2e ` +
      `and E2E_ADMIN_TOKEN set, or the write journey / cleanup will fail.`
  )
  process.exit(2)
}

const passthrough = process.argv.slice(2)
const args = [PLAYWRIGHT_CLI, 'test', '--project=chromium', '--reporter=list', ...passthrough]

console.log(`E2E_BASE_URL=${BASE_URL}`)
console.log(`E2E_API_BASE_URL=${API_BASE_URL}`)
console.log(`node ${args.join(' ')}\n`)

const result = spawnSync(process.execPath, args, {
  cwd: FRONTEND_DIR,
  stdio: 'inherit',
  env: {
    ...process.env,
    E2E_BASE_URL: BASE_URL,
    E2E_API_BASE_URL: API_BASE_URL,
    E2E_WRITE_ENABLED: process.env.E2E_WRITE_ENABLED || 'true',
    E2E_ADMIN_TOKEN: ADMIN_TOKEN,
  },
})

process.exit(result.status ?? 1)
