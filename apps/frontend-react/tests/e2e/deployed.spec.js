import {
  expect,
  request as requestFactory,
  test,
} from '@playwright/test'
import process from 'node:process'

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
  return `e2e-${seed}@example.com`
}

async function openAuthScreen(page) {
  const signupButton = page.getByRole('button', { name: '회원가입' })
  if (await signupButton.isVisible()) {
    return
  }

  const loginButton = page.getByRole('button', { name: '로그인', exact: true })
  const inquiryButton = page.getByRole('button', {
    name: '내 인콰이어리',
    exact: true,
  })
  if (await inquiryButton.isVisible()) {
    await inquiryButton.click()
  } else if (await loginButton.isVisible()) {
    await loginButton.click()
  }

  await expect(signupButton).toBeVisible({ timeout: 30_000 })
}

async function returnToLanding(page) {
  const homeButton = page.getByRole('button', {
    name: 'MarketGate',
    exact: true,
  })
  if (await homeButton.isVisible()) {
    await homeButton.click()
  } else {
    await page.getByText('MARKETGATE', { exact: true }).click()
  }
  await expect(
    page.getByRole('heading', { name: '무엇을 수출하시나요?' })
  ).toBeVisible()
}

async function openMyInquiries(page) {
  const currentButton = page.getByRole('button', {
    name: '내 인콰이어리',
    exact: true,
  })
  if (await currentButton.isVisible()) {
    await currentButton.click()
  } else {
    await page
      .getByRole('button', { name: '인콰이어리', exact: true })
      .click()
  }
  await expect(
    page.getByRole('heading', { name: '내 인콰이어리' })
  ).toBeVisible()
}

/** Pin browser API traffic to the isolated E2E backend (prod UI + e2e API). */
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

    await route.continue({
      url: `${base}${upstreamPath}`,
      headers,
    })
  })
}

test.describe('deployed production-safe smoke', () => {
  test('@smoke renders the app and reaches the configured API', async ({
    page,
    request,
  }) => {
    const pageErrors = []
    const assetFailures = []

    page.on('pageerror', (error) => pageErrors.push(error.message))
    page.on('response', (response) => {
      const type = response.request().resourceType()
      if (
        (type === 'script' || type === 'stylesheet') &&
        response.status() >= 400
      ) {
        assetFailures.push(`${response.status()} ${response.url()}`)
      }
    })

    const navigation = await page.goto('/', { waitUntil: 'domcontentloaded' })
    expect(navigation, 'top-level navigation must return a response').not.toBeNull()
    expect(navigation.ok(), `navigation failed: ${navigation.status()}`).toBeTruthy()

    const loginButton = page.getByRole('button', { name: '로그인' })
    const landingHeading = page.getByRole('heading', {
      name: '무엇을 수출하시나요?',
    })
    const authVisible = await loginButton.isVisible()
    const landingVisible = await landingHeading.isVisible()
    expect(
      authVisible || landingVisible,
      'neither the authentication screen nor the authenticated landing rendered'
    ).toBeTruthy()
    if (authVisible) {
      await expect(page.getByRole('button', { name: '회원가입' })).toBeVisible()
    } else {
      await expect(
        page.getByRole('button', { name: 'MarketGate 홈으로' })
      ).toBeVisible()
    }

    const health = await request.get('/api/v1/health', { timeout: 90_000 })
    expect(health.status()).toBe(200)
    await expect(health.json()).resolves.toMatchObject({ status: 'ok' })

    expect(assetFailures, 'script or stylesheet requests failed').toEqual([])
    expect(pageErrors, 'uncaught browser errors were observed').toEqual([])
  })
})

test.describe('deployed staging write journey', () => {
  test.skip(!writeEnabled, 'Set E2E_WRITE_ENABLED=true only for isolated staging')

  test('@journey register → analyze → inquiry → re-login → cleanup', async ({
    page,
  }, testInfo) => {
    const apiBase = String(process.env.E2E_API_BASE_URL || '').replace(/\/+$/, '')
    const adminToken = String(process.env.E2E_ADMIN_TOKEN || '')
    if (!apiBase) throw new Error('E2E_API_BASE_URL is required for write E2E')
    if (adminToken.length < 32) {
      throw new Error('E2E_ADMIN_TOKEN must contain at least 32 characters')
    }

    const email = buildRunEmail(testInfo)
    const password = 'MgE2E-2026-safe-password'
    let accountCreated = false
    let buyerName = ''
    let journeyError = null
    const stagingApi = await requestFactory.newContext({ baseURL: apiBase })

    try {
      const directIdentity = await stagingApi.get('/v1/e2e/identity')
      expect(directIdentity.status()).toBe(200)
      await expect(directIdentity.json()).resolves.toEqual({
        environment: 'e2e',
      })

      // Prod frontend proxies to the real API; pin browser /api (and stray
      // absolute /v1) calls to the isolated Render E2E backend instead.
      await pinBrowserApiToIsolated(page, apiBase)

      await page.goto('/', { waitUntil: 'domcontentloaded' })
      const pinnedIdentity = await page.evaluate(async () => {
        const response = await fetch('/api/v1/e2e/identity')
        return { status: response.status, body: await response.json() }
      })
      expect(pinnedIdentity.status).toBe(200)
      expect(pinnedIdentity.body).toEqual({ environment: 'e2e' })

      await openAuthScreen(page)
      await page.getByRole('button', { name: '회원가입' }).click()
      await page.getByPlaceholder('you@company.com').fill(email)
      await page.locator('input[type="password"]').fill(password)
      await page.getByRole('button', { name: '계정 생성 →' }).click()
      await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible()
      accountCreated = true

      await returnToLanding(page)
      await page.getByRole('button', { name: '수출 플로우' }).click()
      await expect(
        page.getByRole('heading', { name: '수출 국가 추천' })
      ).toBeVisible()
      await page.getByPlaceholder('예: 330499').fill('330499')
      await page.getByRole('button', { name: '추천 국가 계산' }).click()

      const nextButton = page.getByRole('button', { name: '바이어 선정으로' })
      await expect(nextButton).toBeEnabled({ timeout: 120_000 })
      await nextButton.click()
      await expect(
        page.getByRole('heading', { name: '저품질·저적합 바이어 필터링' })
      ).toBeVisible()

      const candidateCards = page.locator('.analysis-card')
      await expect(candidateCards.first()).toBeVisible({ timeout: 60_000 })

      let selectedCard = null
      const count = await candidateCards.count()
      for (let index = 0; index < count; index += 1) {
        const card = candidateCards.nth(index)
        if ((await card.getByRole('button', { name: /컨택 열기/ }).count()) === 0) {
          continue
        }
        await card.click()
        const sendButton = card.getByRole('button', { name: '발송 요청' })
        if ((await sendButton.count()) > 0 && (await sendButton.isEnabled())) {
          selectedCard = card
          break
        }
      }
      expect(
        selectedCard,
        'no buyer with an email-backed send action was available'
      ).not.toBeNull()

      await selectedCard.scrollIntoViewIfNeeded()
      await selectedCard.getByRole('button', { name: /컨택 열기/ }).click()
      await expect(
        selectedCard.getByText(/연락처 열림|이미 열람한 연락처/)
      ).toBeVisible()
      await selectedCard.getByRole('button', { name: '발송 요청' }).click()

      const modalHeading = page.getByRole('heading', {
        name: /인콰이어리 발송 요청/,
      })
      await expect(modalHeading).toBeVisible()
      buyerName = String(await modalHeading.textContent())
        .split('—')
        .slice(1)
        .join('—')
        .trim()

      await page.getByPlaceholder('예: (주)마켓게이트').fill('MarketGate E2E')
      await page.getByPlaceholder('예: 홍길동').fill('배포 테스트')
      await page.getByRole('button', { name: '초안 생성' }).click()
      await expect(page.getByText(/영문 초안 미리보기/)).toBeVisible()
      await page.getByRole('button', { name: '관리자 검토 요청' }).click()
      await expect(page.getByText('관리자 검토 대기 중')).toBeVisible()

      await page.reload({ waitUntil: 'domcontentloaded' })
      await openMyInquiries(page)
      const inquiry = page.locator('article').filter({ hasText: buyerName }).first()
      await expect(inquiry).toContainText('검토 대기')

      await page.getByRole('button', { name: '로그아웃' }).click()
      await expect(page.getByRole('button', { name: '로그아웃' })).toBeHidden({
        timeout: 30_000,
      })
      await openAuthScreen(page)
      await expect(page.getByRole('button', { name: '로그인 →' })).toBeVisible()
      await page.getByPlaceholder('you@company.com').fill(email)
      await page.locator('input[type="password"]').fill(password)
      await page.getByRole('button', { name: '로그인 →' }).click()
      await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible()
      await openMyInquiries(page)
      await expect(
        page.locator('article').filter({ hasText: buyerName }).first()
      ).toContainText('검토 대기')
    } catch (error) {
      journeyError = error
    }

    let cleanupError = null
    try {
      const cleanup = await stagingApi.post('/v1/e2e/cleanup', {
        data: { email },
        headers: { 'X-E2E-Admin-Token': adminToken },
      })
      const cleanupBody = await cleanup.text()
      if (!cleanup.ok()) {
        throw new Error(`E2E cleanup failed with HTTP ${cleanup.status()}`)
      }
      if (accountCreated && !JSON.parse(cleanupBody).deleted) {
        throw new Error('E2E cleanup did not delete the generated account')
      }
    } catch (error) {
      cleanupError = error
    } finally {
      await stagingApi.dispose()
    }

    if (journeyError && cleanupError) {
      throw new Error(
        `E2E journey failed; cleanup also failed: ${cleanupError.message}`,
        { cause: journeyError }
      )
    }
    if (cleanupError) throw cleanupError
    if (journeyError) throw journeyError
  })
})
