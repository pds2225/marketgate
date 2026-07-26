import test from 'node:test'
import assert from 'node:assert/strict'
import { approxUnlockCount, creditConfig } from '../src/config/creditConfig.js'
import {
  makeBuyerKey,
  maskEmail,
  maskPhone,
} from '../src/lib/creditWallet.js'

test('creditConfig exposes editable unlockCost and packages', () => {
  assert.equal(typeof creditConfig.unlockCost, 'number')
  assert.ok(Array.isArray(creditConfig.packages))
  assert.ok(creditConfig.packages.length >= 1)
})

test('approxUnlockCount follows unlockCost', () => {
  assert.equal(approxUnlockCount(creditConfig.unlockCost * 3), 3)
})

test('maskEmail hides local and domain host', () => {
  const masked = maskEmail('alice@example.com')
  assert.ok(masked.includes('***'))
  assert.ok(!masked.includes('alice@example.com'))
})

test('maskPhone keeps last 4 digits only', () => {
  const masked = maskPhone('+1-555-123-9876')
  assert.ok(masked.endsWith('9876'))
  assert.ok(masked.includes('***'))
})

test('makeBuyerKey is stable for same parts', () => {
  const a = makeBuyerKey({ name: 'Acme', country: 'US', source: 'KOTRA' })
  const b = makeBuyerKey({ name: 'Acme', country: 'US', dataSource: 'KOTRA' })
  assert.equal(a, b)
})
