import { defineConfig, devices } from '@playwright/test'
import process from 'node:process'

const baseURL = String(process.env.E2E_BASE_URL || '').replace(/\/+$/, '')
if (!baseURL) {
  throw new Error('E2E_BASE_URL is required for deployed E2E tests')
}

const bypassSecret = String(
  process.env.VERCEL_AUTOMATION_BYPASS_SECRET || ''
).trim()
const writeJourney = process.env.E2E_WRITE_ENABLED === 'true'
const extraHTTPHeaders = bypassSecret
  ? {
      'x-vercel-protection-bypass': bypassSecret,
      'x-vercel-set-bypass-cookie': 'true',
    }
  : {}

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 180_000,
  expect: {
    timeout: 20_000,
  },
  reporter: writeJourney
    ? [['list']]
    : [
        ['list'],
        ['html', { outputFolder: 'playwright-report', open: 'never' }],
      ],
  outputDir: 'test-results',
  use: {
    baseURL,
    extraHTTPHeaders,
    actionTimeout: 20_000,
    navigationTimeout: 60_000,
    trace: writeJourney ? 'off' : 'retain-on-failure',
    screenshot: writeJourney ? 'off' : 'only-on-failure',
    video: writeJourney ? 'off' : 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
