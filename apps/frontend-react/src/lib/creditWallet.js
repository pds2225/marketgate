/**
 * 크레딧 지갑 — 서버(/v1/credits) 잔액 + 로컬 unlockedKeys.
 * 잔액은 서버가 권위, 열람 키는 기기 로컬(파일럿).
 */
import { creditConfig } from '../config/creditConfig.js'
import api from './api.js'

const STORAGE_KEY = 'mg_credit_wallet_v1'
const EVENT = 'mg:wallet'

function emptyWallet() {
  return {
    balance: Number(creditConfig.startingBalance) || 0,
    unlockedKeys: [],
    source: 'local',
  }
}

function readRaw() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return emptyWallet()
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return emptyWallet()
    return {
      balance: Math.max(0, Number(parsed.balance) || 0),
      unlockedKeys: Array.isArray(parsed.unlockedKeys)
        ? parsed.unlockedKeys.map(String)
        : [],
      source: parsed.source || 'local',
    }
  } catch {
    return emptyWallet()
  }
}

function writeRaw(wallet) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(wallet))
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(EVENT, { detail: wallet }))
  }
  return wallet
}

export function getWallet() {
  return readRaw()
}

export function subscribeWallet(listener) {
  const handler = (e) => listener(e.detail || getWallet())
  window.addEventListener(EVENT, handler)
  return () => window.removeEventListener(EVENT, handler)
}

export function makeBuyerKey(parts = {}) {
  const bits = [
    parts.id,
    parts.name,
    parts.country,
    parts.source || parts.dataSource,
  ]
    .map((v) => String(v || '').trim().toLowerCase())
    .filter(Boolean)
  return bits.join('|') || 'unknown'
}

export function isUnlocked(buyerKey) {
  if (!buyerKey) return false
  return getWallet().unlockedKeys.includes(String(buyerKey))
}

function setBalanceLocal(balance, { source = 'server' } = {}) {
  const wallet = readRaw()
  return writeRaw({ ...wallet, balance: Math.max(0, Number(balance) || 0), source })
}

/** 서버 잔액 동기화. 실패 시 로컬 잔액 유지. */
export async function syncBalanceFromServer() {
  try {
    const { data } = await api.get('/v1/credits/balance')
    const balance = Number(data?.balance)
    if (Number.isFinite(balance)) {
      return { ok: true, wallet: setBalanceLocal(balance, { source: 'server' }) }
    }
    return { ok: false, reason: 'invalid', wallet: readRaw() }
  } catch (err) {
    return { ok: false, reason: err.response?.status || 'network', wallet: readRaw() }
  }
}

/**
 * 로컬 전용 언락(오프라인 폴백).
 */
export function unlockBuyer(buyerKey, { hasContact = true } = {}) {
  const key = String(buyerKey || '').trim()
  const wallet = readRaw()
  if (!key) return { ok: false, reason: 'empty_key', wallet }
  if (!hasContact) return { ok: false, reason: 'no_contact', wallet }
  if (wallet.unlockedKeys.includes(key)) {
    return { ok: true, already: true, wallet }
  }
  const cost = Math.max(1, Number(creditConfig.unlockCost) || 1)
  if (wallet.balance < cost) {
    return { ok: false, reason: 'insufficient', wallet, need: cost }
  }
  const next = {
    balance: wallet.balance - cost,
    unlockedKeys: [...wallet.unlockedKeys, key],
    source: wallet.source || 'local',
  }
  writeRaw(next)
  return { ok: true, already: false, wallet: next }
}

/**
 * 서버 차감(contact_unlock) 후 로컬 키 기록. 실패 시 로컬 폴백하지 않음(이중 차감 방지).
 */
export async function unlockBuyerServer(buyerKey, { hasContact = true } = {}) {
  const key = String(buyerKey || '').trim()
  const wallet = readRaw()
  if (!key) return { ok: false, reason: 'empty_key', wallet }
  if (!hasContact) return { ok: false, reason: 'no_contact', wallet }
  if (wallet.unlockedKeys.includes(key)) {
    return { ok: true, already: true, wallet }
  }
  try {
    const { data } = await api.post('/v1/credits/deduct', { action: 'contact_unlock' })
    const next = {
      balance: Number(data.balance),
      unlockedKeys: [...wallet.unlockedKeys, key],
      source: 'server',
    }
    writeRaw(next)
    return { ok: true, already: false, wallet: next, deducted: data.deducted }
  } catch (err) {
    if (err.response?.status === 402 || err.response?.data?.detail === 'insufficient_credits') {
      const synced = await syncBalanceFromServer()
      return {
        ok: false,
        reason: 'insufficient',
        wallet: synced.wallet,
        need: creditConfig.unlockCost,
      }
    }
    return {
      ok: false,
      reason: err.response?.data?.detail || 'server_error',
      wallet: readRaw(),
    }
  }
}

/**
 * 시뮬레이션 충전 — 서버 charge 우선, 실패 시 로컬만.
 */
export async function topUpPackage(packageId) {
  const pkg = (creditConfig.packages || []).find((p) => p.id === packageId && p.active !== false)
  if (!pkg) {
    return { ok: false, reason: 'unknown_package', wallet: readRaw() }
  }
  const credits = Number(pkg.credits || 0)
  try {
    const { data } = await api.post('/v1/credits/charge', {
      amount: credits,
      note: `sim_topup_${pkg.id}`,
    })
    const wallet = readRaw()
    const next = writeRaw({
      ...wallet,
      balance: Number(data.balance),
      source: 'server',
    })
    return { ok: true, wallet: next, package: pkg, via: 'server' }
  } catch {
    const wallet = readRaw()
    const next = writeRaw({
      ...wallet,
      balance: wallet.balance + credits,
      source: 'local',
    })
    return { ok: true, wallet: next, package: pkg, via: 'local' }
  }
}

export function maskEmail(email) {
  const text = String(email || '').trim()
  if (!text || !text.includes('@')) return text ? '***@***' : ''
  const [local, domain] = text.split('@')
  const maskedLocal = local ? `${local[0]}***` : '***'
  if (!domain.includes('.')) return `${maskedLocal}@***`
  const host = domain.slice(0, domain.lastIndexOf('.'))
  const tld = domain.slice(domain.lastIndexOf('.') + 1)
  const maskedDomain = `${host ? `${host[0]}***` : '***'}.${tld}`
  return `${maskedLocal}@${maskedDomain}`
}

export function maskPhone(phone) {
  const text = String(phone || '').trim()
  if (!text) return ''
  const digits = text.replace(/\D/g, '')
  if (digits.length < 4) return '***'
  return `***-****-${digits.slice(-4)}`
}

export function displayContact(value, { unlocked, kind }) {
  const text = String(value || '').trim()
  if (!text) return ''
  if (unlocked) return text
  return kind === 'phone' ? maskPhone(text) : kind === 'email' ? maskEmail(text) : '••••••••'
}
