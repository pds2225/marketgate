import { expect, request as requestFactory, test } from '@playwright/test'
import process from 'node:process'

/**
 * 바이어 검색 실사용 흐름 E2E.
 *
 * 스크린샷으로 보고된 "결과 화면이 안 나옴"의 회귀 방지용이다. 이 화면의 유일한
 * 데이터 호출인 POST /v1/predict 가 200 을 주고, 국가 후보 목록까지 실제로
 * 렌더링되는지를 로딩 오버레이가 사라지는 시점까지 확인한다.
 *
 * 계정이 필요해(predict 는 인증 필수) 격리된 E2E 백엔드에서만 돈다.
 */
const writeEnabled = process.env.E2E_WRITE_ENABLED === 'true'

function buildRunEmail(testInfo) {
  const seed = [
    process.env.GITHUB_RUN_ID || Date.now(),
    process.env.GITHUB_RUN_ATTEMPT || '1',
    testInfo.retry,
  ]
    .join('-')
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
  return `e2e-buyer-search-${seed}@example.com`
}

/** 브라우저의 /api(및 절대 /v1) 호출을 격리 백엔드로 고정한다. */
async function pinBrowserApiToIsolated(page, apiBase) {
  const base = String(apiBase || '').replace(/\/+$/, '')
  if (!base) throw new Error('E2E_API_BASE_URL is required to pin browser API')

  await page.route('**/*', async (route) => {
    const req = route.request()
    const url = new URL(req.url())
    const path = url.pathname
    const isSameOriginApi = path.startsWith('/api/v1/')
    const isDirectV1 =
      path.startsWith('/v1/') && url.origin.replace(/\/+$/, '') !== base
    if (!isSameOriginApi && !isDirectV1) {
      await route.continue()
      return
    }
    const upstreamPath = `${path.replace(/^\/api/, '')}${url.search}`
    const headers = { ...req.headers() }
    delete headers.host
    await route.continue({ url: `${base}${upstreamPath}`, headers })
  })
}

test.describe('buyer search real-usage journey', () => {
  test.skip(!writeEnabled, 'Set E2E_WRITE_ENABLED=true only for isolated staging')

  test('@journey 로그인 사용자가 바이어 검색에서 결과 화면까지 도달한다', async ({
    page,
  }, testInfo) => {
    // 유휴 상태의 백엔드는 첫 요청에서 40초 이상 걸린다(실측). 콜드 스타트를 실패로
    // 오인하지 않도록 넉넉히 잡는다.
    test.setTimeout(420_000)

    const apiBase = String(process.env.E2E_API_BASE_URL || '').replace(/\/+$/, '')
    if (!apiBase) throw new Error('E2E_API_BASE_URL is required for buyer search E2E')

    const email = buildRunEmail(testInfo)
    const password = 'MgE2E-2026-safe-password'
    const predictResponses = []

    await pinBrowserApiToIsolated(page, apiBase)
    page.on('response', (response) => {
      if (new URL(response.url()).pathname.endsWith('/v1/predict')) {
        predictResponses.push(response.status())
      }
    })

    const isolatedApi = await requestFactory.newContext({ baseURL: apiBase })
    try {
      // predict 는 인증 필수다. UI 회원가입 폼 대신 API 로 계정을 만들어
      // 검색 흐름 자체에만 집중한다.
      const registered = await isolatedApi.post('/v1/auth/register', {
        data: { email, password },
      })
      expect(
        registered.ok(),
        `register failed: ${registered.status()}`
      ).toBeTruthy()
      const tokens = await registered.json()
      expect(tokens.access_token, 'register did not return access_token').toBeTruthy()

      await page.goto('/', { waitUntil: 'domcontentloaded' })
      await page.evaluate(
        ([access, refresh]) => {
          localStorage.setItem('access_token', access)
          if (refresh) localStorage.setItem('refresh_token', refresh)
        },
        [tokens.access_token, tokens.refresh_token || '']
      )
      await page.goto('/', { waitUntil: 'domcontentloaded' })

      await page.getByRole('button', { name: '바이어 검색' }).first().click()
      await expect(
        page.getByText('위 검색바에 제품 키워드나 HS코드를 입력해 바이어를 찾아보세요')
      ).toBeVisible()

      await page.getByPlaceholder(/HS|검색|코드/).first().fill('330499')
      await page.getByRole('button', { name: '검색', exact: true }).click()

      // 핵심 회귀 지점: 로딩 오버레이가 끝까지 남아 결과가 안 나오던 증상.
      await expect(page.getByTestId('buyer-search-loading')).toBeHidden({
        timeout: 180_000,
      })

      expect(
        predictResponses,
        'no /v1/predict response was observed'
      ).not.toHaveLength(0)
      expect(
        predictResponses.at(-1),
        `predict returned ${predictResponses.at(-1)}`
      ).toBe(200)

      // 결과 화면이 실제로 렌더링됐는지 — 오류/빈 상태 패널이 아니라 국가 후보 목록.
      await expect(page.getByText('국가 후보 리스트')).toBeVisible()
      await expect(
        page.getByText('위 검색바에 제품 키워드나 HS코드를 입력해 바이어를 찾아보세요')
      ).toBeHidden()
    } finally {
      await isolatedApi.dispose()
    }
  })
})
