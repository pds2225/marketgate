/**
 * MG-004 live E2E against marketgate.vercel.app.
 * Throwaway signup only. Never prints passwords or tokens.
 */
import { chromium } from 'file:///C:/Users/ekth3/dev/marketgate/apps/frontend-react/node_modules/playwright/index.mjs'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'

const BASE = 'https://marketgate.vercel.app'
const STATUS_LABELS = [
  '기본 확인 완료',
  '부분 확인',
  '데이터 불일치',
  '비활성 법인',
  '신용조사 필요',
  'BASIC_CONFIRMED',
  'BASIC_PARTIAL',
  'DATA_MISMATCH',
  'INACTIVE_ENTITY',
  'CREDIT_CHECK_REQUIRED',
]
const LINK_LABELS = ['D-U-N-S 조회', 'K-SURE 기업 조회', 'K-SURE 신용조사 신청']

const notes = []
const log = (m) => {
  notes.push(m)
  console.log(m)
}

const email = `mg004.live.${Date.now()}@example.com`
const password = `Mg004-Live-${Math.random().toString(36).slice(2, 10)}-Aa1!`

const outDir = process.env.TEMP || '.'
const shot = (name) => join(outDir, `mg004-${name}.png`)

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } })
page.setDefaultTimeout(45_000)
page.setDefaultNavigationTimeout(90_000)

const cvNet = []
page.on('response', async (res) => {
  const url = res.url()
  if (url.includes('company-verifications')) {
    cvNet.push(`${res.request().method()} ${res.status()} ${url.replace(/https?:\/\/[^/]+/, '')}`)
  }
})

let failed = 'FAIL'
try {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  log(`landed title=${await page.title()}`)

  const loginBtn = page.getByRole('button', { name: '로그인' })
  await loginBtn.first().click()
  await page.getByRole('button', { name: '회원가입' }).click()
  await page.getByPlaceholder('you@company.com').fill(email)
  await page.locator('input[type="password"]').fill(password)
  await page.getByRole('button', { name: /계정 생성/ }).click()
  await page.getByRole('button', { name: '로그아웃' }).waitFor({ timeout: 40_000 })
  log('login=PASS (throwaway signup, email not printed)')

  const home = page.getByRole('button', { name: /MarketGate/ }).first()
  if (await home.count()) {
    try {
      await home.click({ timeout: 5000 })
    } catch {
      /* already on landing */
    }
  }

  const buyerNav = page.getByRole('button', { name: /바이어 검색/ })
  if (await buyerNav.count()) {
    await buyerNav.first().click()
  } else {
    log('buyer-search-nav=missing, trying 바이어 찾기')
    const findBtn = page.getByRole('button', { name: /바이어 찾기|바이어 검색 시작/ })
    if (await findBtn.count()) await findBtn.first().click()
  }

  const hs = page.getByPlaceholder(/330499/)
  await hs.first().waitFor({ timeout: 20_000 })
  await hs.first().fill('330499')
  await page.getByRole('button', { name: '검색', exact: true }).click()
  log('search=submitted HS 330499')

  const loading = page.getByTestId('buyer-search-loading')
  try {
    await loading.waitFor({ state: 'visible', timeout: 15_000 })
  } catch {
    log('loading-overlay=not-seen-early')
  }
  await loading.waitFor({ state: 'hidden', timeout: 240_000 })
  log('search-loading=hidden')

  const countryHeading = page.getByText('국가 후보 리스트')
  await countryHeading.waitFor({ timeout: 30_000 })
  log('country-list=PASS')
  await page.screenshot({ path: shot('countries'), fullPage: true })

  const countryRow = page.locator('button, [role="button"], div').filter({ hasText: /바이어 후보/ }).first()
  await countryRow.click({ timeout: 20_000 })
  log('country-open=clicked')

  await page.getByText(/바이어 리스트/).first().waitFor({ timeout: 20_000 })
  log('buyer-list=PASS')

  // Click first buyer name-ish row (skip header)
  const buyerItem = page.locator('button, [role="button"], div.cursor-pointer').filter({ hasText: /.+/ }).nth(0)
  // Prefer clicking a company-looking line in the list panel
  const named = page.getByText(/Inc\.|Ltd|LLC|GmbH|Corp|Co\./).first()
  if (await named.count()) {
    await named.click()
    log('buyer-open=by-company-suffix')
  } else {
    await page.locator('.cursor-pointer').first().click()
    log('buyer-open=first-pointer')
  }

  await page.getByText(/BUYER DETAIL|바이어 상세|기업 검증/).first().waitFor({ timeout: 20_000 })
  log('buyer-detail=PASS')
  await page.screenshot({ path: shot('detail'), fullPage: true })

  const tab = page.getByRole('button', { name: '기업 검증' })
  if (await tab.count()) {
    await tab.first().click()
    log('verify-tab=clicked')
  }

  const heading = page.getByRole('heading', { name: /기업 기본 검증|기업 검증/ })
  await heading.first().waitFor({ timeout: 15_000 }).catch(() => {})

  const linksOk = []
  for (const label of LINK_LABELS) {
    const link = page.getByRole('link', { name: label })
    const n = await link.count()
    if (n) {
      const href = await link.first().getAttribute('href')
      linksOk.push(`${label} -> ${href}`)
    }
  }
  log(`official-links=${linksOk.length} ${linksOk.join(' | ')}`)

  const verifyBtn = page.getByRole('button', { name: '기업 검증', exact: true })
  if (await verifyBtn.count()) {
    await verifyBtn.last().click()
    log('verify-request=clicked')
  } else {
    const anyVerify = page.locator('button').filter({ hasText: /^기업 검증$/ })
    if (await anyVerify.count()) {
      await anyVerify.last().click()
      log('verify-request=clicked-filter')
    } else {
      log('verify-request=NO-BUTTON')
    }
  }

  await page.getByText('검증 요청 중입니다').waitFor({ state: 'hidden', timeout: 90_000 }).catch(() => {})

  const bodyText = await page.locator('body').innerText()
  const seenStatus = STATUS_LABELS.filter((s) => bodyText.includes(s))
  const failText = bodyText.includes('검증 실패') || bodyText.includes('찾을 수 없습니다')
  log(`status-labels=${seenStatus.join(',') || 'NONE'}`)
  log(`verify-fail-banner=${failText}`)
  log(`cv-network=${cvNet.join(' ; ') || 'none'}`)
  await page.screenshot({ path: shot('verify'), fullPage: true })

  const hasStatus = seenStatus.length > 0
  const hasLinks = linksOk.length >= 2
  if (hasStatus && hasLinks && !failText) {
    failed = 'PASS'
  } else {
    failed = `FAIL status=${hasStatus} links=${hasLinks} failBanner=${failText}`
  }
} catch (err) {
  failed = `FAIL ${err.message.split('\n')[0]}`
  log(`error=${err.message.split('\n')[0]}`)
  try {
    await page.screenshot({ path: shot('error'), fullPage: true })
    log(`url=${page.url()}`)
    const t = (await page.locator('body').innerText()).slice(0, 800)
    log(`visible-text=${t.replace(/\s+/g, ' ')}`)
  } catch {
    /* ignore */
  }
} finally {
  log(`RESULT=${failed}`)
  writeFileSync(join(outDir, 'mg004-live-e2e-notes.txt'), notes.join('\n'), 'utf8')
  await browser.close()
}

if (!String(failed).startsWith('PASS')) process.exit(1)
