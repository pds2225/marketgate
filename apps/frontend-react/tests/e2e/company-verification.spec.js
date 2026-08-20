import { expect, test } from '@playwright/test'

/**
 * CV-04: login → buyer search → detail → basic verification.
 *
 * Intercepts CV-02/auth/predict so this never calls paid OpenCorporates/D&B/K-SURE.
 * Isolation of GET-by-owner is covered by backend pytest; this journey checks the
 * UI POST then GET round-trip and official lookup links.
 */
const BASIC_STATUSES = new Set([
  'BASIC_CONFIRMED',
  'BASIC_PARTIAL',
  'DATA_MISMATCH',
  'INACTIVE_ENTITY',
  'CREDIT_CHECK_REQUIRED',
])

const STATUS_LABELS = {
  BASIC_CONFIRMED: '기본 확인 완료',
  BASIC_PARTIAL: '부분 확인',
  DATA_MISMATCH: '데이터 불일치',
  INACTIVE_ENTITY: '비활성 법인',
  CREDIT_CHECK_REQUIRED: '신용조사 필요',
}

async function installCv04Mocks(page) {
  const store = new Map()
  const calls = { login: 0, predict: 0, postVerify: 0, getVerify: 0 }

  await page.route('**/v1/**', async (route) => {
    const req = route.request()
    const url = new URL(req.url())
    const path = url.pathname.replace(/^\/api/, '')
    const method = req.method()

    const json = (status, body) =>
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(body),
      })

    if (method === 'GET' && path.endsWith('/v1/health')) {
      return json(200, { status: 'ok' })
    }
    if (method === 'GET' && path.endsWith('/v1/demo/summary')) {
      return json(200, { total: 0, countryCount: 0 })
    }
    if (method === 'GET' && path.endsWith('/v1/credits/balance')) {
      return json(200, { balance: 0 })
    }
    if (method === 'GET' && path.endsWith('/v1/auth/me')) {
      return json(200, { user_id: 'user-a', email: 'cv04@example.com', role: 'user' })
    }
    if (method === 'POST' && path.endsWith('/v1/auth/login')) {
      calls.login += 1
      return json(200, {
        access_token: 'cv04-access',
        refresh_token: 'cv04-refresh',
      })
    }
    if (method === 'POST' && path.endsWith('/v1/predict')) {
      calls.predict += 1
      return json(200, {
        data: {
          buyers: {
            status: 'ok',
            items: [
              {
                buyer_name: 'Acme Trading GmbH',
                source_dataset: 'kotra_trade_leads',
                country_norm: 'germany',
                source_target_country_iso3: 'DEU',
                source_target_country_name: '독일',
                has_contact: true,
                contact_email: 'buy@acme.de',
                final_score: 91,
                source_verification: 'verified',
                recommendation_lines: ['테스트 근거'],
                matched_terms: ['skincare'],
              },
            ],
          },
        },
      })
    }
    if (method === 'POST' && path.endsWith('/v1/company-verifications')) {
      calls.postVerify += 1
      const body = req.postDataJSON() || {}
      if (!body.company_name || !/^[A-Z]{3}$/.test(String(body.country_iso3 || ''))) {
        return json(422, { detail: 'country_iso3 required' })
      }
      const rec = {
        verification_id: '11111111-1111-4111-8111-111111111111',
        company_name: body.company_name,
        country_iso3: String(body.country_iso3).toUpperCase(),
        registry_check_status: 'BASIC_PARTIAL',
        result_json: { provider: 'opencorporates', match_status: 'BASIC_PARTIAL', mock: true },
        provider: 'opencorporates',
        requested_at: '2026-08-19T00:00:00+00:00',
        completed_at: '2026-08-19T00:00:00+00:00',
        owner_id: 'user-a',
      }
      store.set(rec.verification_id, rec)
      return json(200, rec)
    }
    if (method === 'GET' && path.includes('/v1/company-verifications/')) {
      calls.getVerify += 1
      const id = path.split('/').pop()
      const rec = store.get(id)
      if (!rec) return json(404, { detail: 'verification_not_found' })
      return json(200, rec)
    }
    return route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"not_mocked"}' })
  })

  return calls
}

test.describe('CV-04 company verification journey', () => {
  test('@journey @smoke 로그인 후 바이어 상세에서 기본검증 결과가 API와 연결된다', async ({
    page,
  }) => {
    const calls = await installCv04Mocks(page)

    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '바이어 검색' }).first().click()
    await expect(page.getByRole('button', { name: '로그인 →' })).toBeVisible()

    await page.locator('input[type="email"]').fill('cv04@example.com')
    await page.locator('input[type="password"]').fill('Cv04-pass-2026')
    await page.getByRole('button', { name: '로그인 →' }).click()

    await expect(
      page.getByText('위 검색바에 제품 키워드나 HS코드를 입력해 바이어를 찾아보세요')
    ).toBeVisible()
    expect(calls.login).toBe(1)

    await page.getByPlaceholder(/HS|검색|코드/).first().fill('330499')
    await page.getByRole('button', { name: '검색', exact: true }).click()
    await expect(page.getByTestId('buyer-search-loading')).toBeHidden({ timeout: 30_000 })
    await expect(page.getByText('국가 후보 리스트')).toBeVisible()
    expect(calls.predict).toBe(1)

    await page.getByText('독일').first().click()
    await page.getByText('Acme Trading GmbH').first().click()
    await page.getByRole('button', { name: '기업 검증' }).first().click()
    await expect(page.getByRole('heading', { name: '기업 기본 검증' })).toBeVisible()
    await expect(page.getByText(/법적 실체와 등록정보/)).toBeVisible()
    await expect(page.getByText(/데이터 소스를 참조/)).toHaveCount(0)

    await page.locator('[data-slot="button"]').filter({ hasText: /^기업 검증$/ }).click()
    await expect(page.getByText(STATUS_LABELS.BASIC_PARTIAL)).toBeVisible()
    expect(calls.postVerify).toBe(1)
    expect(calls.getVerify).toBe(1)

    await expect(page.getByRole('link', { name: 'D-U-N-S 조회' })).toHaveAttribute(
      'href',
      'https://www.dnb.com/duns-number/lookup.html'
    )
    await expect(page.getByRole('link', { name: 'K-SURE 기업 조회' })).toHaveAttribute(
      'href',
      'https://ksight.ksure.or.kr/find-buyer'
    )
    await expect(page.getByRole('link', { name: 'K-SURE 신용조사 신청' })).toHaveAttribute(
      'href',
      'https://www.ksure.or.kr/rh-kr/cntnts/i-115/web.do'
    )
    await expect(page.locator('a[href*="ksure.go.kr"]')).toHaveCount(0)
    expect(BASIC_STATUSES.has('BASIC_PARTIAL')).toBeTruthy()
    await page.screenshot({ path: test.info().outputPath('cv04-verification-result.png'), fullPage: true })
  })
})
