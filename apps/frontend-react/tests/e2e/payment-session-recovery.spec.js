import { expect, request as requestFactory, test } from '@playwright/test'
import process from 'node:process'

/**
 * 결제 콜백에서 세션이 끊겼을 때의 복구 흐름 E2E.
 *
 * 결제는 돈이 이미 나간 뒤라 결과 화면을 잃으면 안 된다. 토스가 successUrl 로
 * 돌려보내는 사이 토큰이 만료되면 로그인 화면이 뜨는데, 이때 URL 의
 * paymentKey/orderId/amount 가 보존돼야 재로그인 후 승인을 이어갈 수 있다
 * (docs/LESSONS.md L023).
 *
 * 이 경로는 그동안 로컬 재현으로만 확인했고 CI 가 잡지 못했다. 회귀하면
 * "결제했는데 확인이 안 된다"는 형태로 사용자에게 직접 드러난다.
 *
 * 검증 대상은 결제 성공 여부가 아니라 인증 복구다. 실재하지 않는 주문을 쓰므로
 * 서버는 결국 승인을 거절하지만, 그 거절이 401(인증 실패)이 아니라 주문 판정
 * 단계에서 나온다는 것이 곧 인증 관문을 통과했다는 뜻이다.
 *
 * 계정을 만들기 때문에 격리 백엔드에서만 돈다.
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
  return `e2e-payment-recovery-${seed}@example.com`
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
    const target = base + (isSameOriginApi ? path.replace(/^\/api/, '') : path) + url.search
    await route.continue({ url: target })
  })
}

test.describe('payment callback session recovery', () => {
  test.skip(!writeEnabled, 'Set E2E_WRITE_ENABLED=true only for isolated staging')

  test('@journey 결제 콜백에서 세션이 끊겨도 재로그인하면 승인이 이어진다', async ({
    page,
  }, testInfo) => {
    // 유휴 백엔드 콜드 스타트(실측 40초 이상)를 실패로 오인하지 않도록 넉넉히 잡는다.
    test.setTimeout(420_000)

    const apiBase = String(process.env.E2E_API_BASE_URL || '').replace(/\/+$/, '')
    if (!apiBase) throw new Error('E2E_API_BASE_URL is required for payment recovery E2E')

    const email = buildRunEmail(testInfo)
    const password = 'MgE2E-2026-safe-password'
    /** confirm 호출의 응답 코드를 순서대로 모은다. 401 → 비401 전환이 핵심 증거다. */
    const confirmStatuses = []

    await pinBrowserApiToIsolated(page, apiBase)
    page.on('response', (response) => {
      if (new URL(response.url()).pathname.endsWith('/v1/payment/confirm')) {
        confirmStatuses.push(response.status())
      }
    })

    const isolatedApi = await requestFactory.newContext({ baseURL: apiBase })
    try {
      const registered = await isolatedApi.post('/v1/auth/register', {
        data: { email, password },
      })
      expect(
        registered.ok(),
        `register failed: ${registered.status()}`
      ).toBeTruthy()

      // 주문 ID 는 {user_id}.{product_type}.{item}.{uuid} 형식이라야 서버가
      // 소유자를 판별한다. 형식이 틀리면 인증과 무관하게 즉시 거절돼
      // 이 테스트가 검증하려는 지점에 도달하지 못한다.
      const me = await isolatedApi.get('/v1/auth/me', {
        headers: { authorization: `Bearer ${(await registered.json()).access_token}` },
      })
      expect(me.ok(), `auth/me failed: ${me.status()}`).toBeTruthy()
      const userId = (await me.json()).user_id
      expect(userId, 'auth/me did not return user_id').toBeTruthy()

      const orderId = `${userId}.credit.10C.${testInfo.testId.slice(0, 12)}`
      const callbackUrl =
        `/payment/callback?status=success&type=credit&item=10C` +
        `&paymentKey=e2e_pk_recovery&orderId=${encodeURIComponent(orderId)}&amount=20000`

      // 만료 세션 재현: 서버가 거부하는 access_token 을 심고 refresh_token 은 없앤다.
      // 재발급이 실패해야 auth:logout 이 발생해 실제 만료 상황과 같아진다.
      await page.goto('/', { waitUntil: 'domcontentloaded' })
      await page.evaluate(() => {
        localStorage.setItem('access_token', 'expired.invalid.token')
        localStorage.removeItem('refresh_token')
      })

      await page.goto(callbackUrl, { waitUntil: 'domcontentloaded' })

      // 1) 로그인 화면으로 넘어가되, 결제 전용 안내가 떠야 한다.
      //    일반 만료 문구만 보이면 사용자는 결제가 취소된 것으로 읽는다.
      await expect(page.locator('.auth-root')).toBeVisible({ timeout: 120_000 })
      await expect(page.locator('.auth-notice')).toContainText('결제는 취소되지 않았습니다')

      // 2) 결제 파라미터가 URL 에 남아 있어야 재로그인 후 승인을 재호출할 수 있다.
      const urlAfterLogout = new URL(page.url())
      expect(urlAfterLogout.pathname).toBe('/payment/callback')
      expect(urlAfterLogout.searchParams.get('paymentKey')).toBe('e2e_pk_recovery')
      expect(urlAfterLogout.searchParams.get('orderId')).toBe(orderId)
      expect(urlAfterLogout.searchParams.get('amount')).toBe('20000')

      const beforeRelogin = confirmStatuses.length
      expect(
        confirmStatuses.slice(0, beforeRelogin),
        'expired session should have produced 401 on confirm'
      ).toContain(401)

      // 3) 재로그인
      await page.locator('.auth-input').first().fill(email)
      await page.locator('.auth-input').nth(1).fill(password)
      await page.locator('.auth-submit').click()

      // 4) 결제 확인 화면으로 돌아오고, 승인이 새 토큰으로 재호출돼야 한다.
      await expect(page.locator('.cb-root')).toBeVisible({ timeout: 120_000 })
      await expect
        .poll(() => confirmStatuses.length, {
          message: 'confirm was not retried after re-login',
          timeout: 120_000,
        })
        .toBeGreaterThan(beforeRelogin)

      // 인증 관문 통과가 이 테스트의 판정 기준이다. 실재하지 않는 주문이라
      // 서버는 승인을 거절하지만, 그 거절이 401 이면 안 된다.
      const afterRelogin = confirmStatuses.slice(beforeRelogin)
      expect(
        afterRelogin.every((status) => status !== 401),
        `confirm still unauthorized after re-login: ${afterRelogin.join(', ')}`
      ).toBeTruthy()
    } finally {
      await isolatedApi.dispose()
    }
  })
})
