# Deployed Write E2E Staging Setup

Production (`https://marketgate.vercel.app`) stays read-only smoke only.
Write journeys require an isolated Render API with `APP_ENV=e2e`.

## 1. Render (isolated E2E API)

Create a **separate** service (not production). Set:

| Key | Value |
|-----|--------|
| `APP_ENV` | `e2e` |
| `E2E_ADMIN_TOKEN` | random string, length ≥ 32 |
| Other API secrets | same pattern as staging, **not** production data files |

Confirm:

```http
GET {E2E_API_BASE_URL}/v1/e2e/identity
→ 200 {"environment":"e2e"}
```

Production must return 404 for `/v1/e2e/*` (router not registered unless `APP_ENV=e2e`).

## 2. Vercel

- Keep Preview Deployment Protection as needed.
- Create Automation Bypass secret in Vercel project settings.
- Point Preview (or a dedicated preview env) API base at the Render E2E service when running write journeys.

## 3. GitHub repository

**Secrets** (Actions → Secrets):

- `E2E_ADMIN_TOKEN` — same value as Render
- `VERCEL_AUTOMATION_BYPASS_SECRET` — same as Vercel bypass

**Variables** (Actions → Variables):

- `DEPLOYED_E2E_ENABLED=true` — allows Preview job on `deployment_status`
- `E2E_API_BASE_URL` — Render E2E API origin (no trailing slash)
- `DEPLOYED_E2E_WRITE_ENABLED=true` — **only** after staging isolation is verified

Fail-closed defaults: if these are unset, Preview write is skipped / validation fails before mutating data.

## 4. Run write journey

Actions → **Deployed E2E** → `workflow_dispatch`:

- `target_environment`: `preview`
- `base_url`: Preview URL (never `marketgate.vercel.app`)
- `api_base_url`: Render E2E API URL
- `run_write_journey`: `true`

Workflow refuses write when hostname is `marketgate.vercel.app`.

## 5. Local verification (no secrets required)

```powershell
cd services/p1-export-fit-api
python -m pytest tests/test_e2e_cleanup.py tests/test_require_plan.py -q

cd ../../apps/frontend-react
npm run build
npm run test:e2e:smoke
```

## Appendix — intentionally not merged

| Branch pattern | Reason |
|----------------|--------|
| `backup/WIN-*` | auto-snapshots |
| `cursor/demo-unmask-contacts-*` | temporary contact disclosure |
| `cursor/dev-sheet-by-section-*` | discarded Google Sheets tooling |
| `feature/p1-scoring-fix` | WIP + large CSV dumps |
| `marketgate-realdata-ui` | superseded demo UI |
| require_plan / UUID cloud branches | already on `main` (patch-equivalent or tests-only residual) |
