import { expect, request as requestFactory, test } from '@playwright/test'
import process from 'node:process'

/**
 * MG-004 acceptance: on production (marketgate.vercel.app) the real journey
 * 로그인 → 바이어 검색 → 상세 → 기업검증 works, i.e. POST /v1/company-verifications
 * returns 200 and the UI shows a BASIC_* status with official lookup links.
 *
 * Unlike company-verification.spec.js this does NOT mock the API — it hits the
 * live Render backend. Gated behind E2E_WRITE_ENABLED because it registers a
 * throwaway account; the account is cleaned via /v1/e2e/cleanup when
 * E2E_API_BASE_URL points at the isolated e2e service, otherwise left (prod
 * has no cleanup route and the account is inert e2e-*@example.com).
 *
 * Observed 2026-09-04: navigation + auth + search + detail all PASS on prod
 * (Render is redeployed, routes present). POST /v1/company-verifications
 * returns 503 "verification_store_unavailable" because company_verification_store
 * is DB-only ("DB-only, no file fallback") and Render prod has no DATABASE_URL.
 * This test stays RED until prod gets a Postgres or CV-02 gains a fallback.
 */
const writeEnabled = process.env.E2E_WRITE_ENABLED === 'true'
const BASIC_LABELS = [
  '기본 확인 완료',
  '부분 확인',
  '데이터 불일치',
  '비활성 법인',
  '신용조사 필요',
]

function runEmail() {
  const seed = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  return `e2e-mg004-${seed}@example.com`
}

test.describe('MG-004 production company verification', () => {
  test.skip(!writeEnabled, 'Set E2E_WRITE_ENABLED=true')

  test('@journey 로그인 → 바이어 검색 → 상세 → 기업검증 (live API, not mocked)', async ({
    page,
  }) => {
    test.setTimeout(600_000)

    const apiBase = String(process.env.E2E_API_BASE_URL || '').replace(/\/+$/, '')
    if (!apiBase) throw new Error('E2E_API_BASE_URL is required')
    const adminToken = String(process.env.E2E_ADMIN_TOKEN || '')

    const email = runEmail()
    const password = 'MgE2E-2026-safe-password'
    const verifyResponses = []
    page.on('response', (r) => {
      const p = new URL(r.url()).pathname
      if (p.endsWith('/v1/company-verifications') && r.request().method() === 'POST') {
        verifyResponses.push(r.status())
      }
    })

    const api = await requestFactory.newContext({ baseURL: apiBase })
    try {
      const reg = await api.post('/v1/auth/register', { data: { email, password } })
      expect(reg.ok(), `register ${reg.status()}`).toBeTruthy()
      const tokens = await reg.json()

      // Warm the free-tier backend before the browser drives predict through Vercel.
      const warm = await api.post('/v1/predict', {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
        data: { hs_code: '330499', exporter_country_iso3: 'KOR', top_n: 5, year: 2023 },
        timeout: 300_000,
      })
      expect(warm.status(), 'direct predict').toBe(200)

      await page.goto('/', { waitUntil: 'domcontentloaded' })
      await page.evaluate(
        ([a, r]) => {
          localStorage.setItem('access_token', a)
          if (r) localStorage.setItem('refresh_token', r)
        },
        [tokens.access_token, tokens.refresh_token || '']
      )
      await page.goto('/', { waitUntil: 'domcontentloaded' })

      await page.getByRole('button', { name: '바이어 검색' }).first().click()
      await expect(
        page.getByText('위 검색바에 제품 키워드나 HS코드를 입력해 바이어를 찾아보세요')
      ).toBeVisible({ timeout: 30_000 })

      await page.getByPlaceholder(/HS|검색|코드/).first().fill('330499')
      await page.getByRole('button', { name: '검색', exact: true }).click()
      await expect(page.getByTestId('buyer-search-loading')).toBeHidden({
        timeout: 300_000,
      })
      await expect(page.getByText('국가 후보 리스트')).toBeVisible({ timeout: 30_000 })

      // Country card is a <button> whose body carries "바이어 후보 N개"; the
      // list subtitle also contains "바이어 후보" as plain <p>, so filter to buttons.
      await page
        .getByRole('button')
        .filter({ hasText: /바이어 후보 \d+개/ })
        .first()
        .click()
      await expect(page.getByText(/바이어 리스트/).first()).toBeVisible({ timeout: 30_000 })

      // First buyer card in the list panel (also a <button>). Company-name-ish text.
      await page
        .getByRole('button')
        .filter({ hasText: /Inc\.?|Ltd|LLC|GmbH|Corp|Co\.|Company|Cosmetic|Trading|Beauty|Group|International/i })
        .first()
        .click()
      await expect(page.getByText(/BUYER DETAIL REPORT|바이어 상세/).first()).toBeVisible({
        timeout: 30_000,
      })

      await page.getByRole('button', { name: '기업 검증' }).first().click()
      await expect(page.getByRole('heading', { name: '기업 기본 검증' })).toBeVisible({
        timeout: 20_000,
      })

      await page
        .locator('[data-slot="button"]')
        .filter({ hasText: /^기업 검증$/ })
        .click()

      // Live mock-provider status: one of the five BASIC_* labels, not "검증 실패".
      await expect(page.getByText('검증 요청 중입니다')).toBeHidden({ timeout: 120_000 })
      const body = await page.locator('body').innerText()
      const seen = BASIC_LABELS.filter((l) => body.includes(l))
      expect(
        verifyResponses.at(-1),
        `POST /v1/company-verifications -> ${verifyResponses.at(-1)} (404 = Render not deployed)`
      ).toBe(200)
      expect(seen, `no BASIC_* label; body had: ${body.slice(0, 300)}`).not.toHaveLength(0)
      expect(body.includes('검증 실패')).toBeFalsy()

      for (const name of ['D-U-N-S 조회', 'K-SURE 기업 조회', 'K-SURE 신용조사 신청']) {
        await expect(page.getByRole('link', { name })).toBeVisible()
      }

      await page.screenshot({
        path: test.info().outputPath('mg004-prod-verification.png'),
        fullPage: true,
      })
    } finally {
      if (adminToken.length >= 32) {
        await api
          .post('/v1/e2e/cleanup', {
            data: { email },
            headers: { 'X-E2E-Admin-Token': adminToken },
          })
          .catch(() => {})
      }
      await api.dispose()
    }
  })
})
