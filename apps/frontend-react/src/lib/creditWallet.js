/**
 * 로컬 크레딧 지갑 (서버 미연동).
 * localStorage 기반 — 파일럿 UX 검증용. 조작·기기 간 불일치는 알려진 한계.
 */
import { creditConfig } from '../config/creditConfig.js'

const STORAGE_KEY = 'mg_credit_wallet_v1'
const EVENT = 'mg:wallet'

function emptyWallet() {
  return {
    balance: Number(creditConfig.startingBalance) || 0,
    unlockedKeys: [],
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

/**
 * @returns {{ ok: true, wallet, already: boolean } | { ok: false, reason: 'insufficient'|'empty_key'|'no_contact', wallet, need?: number }}
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
  }
  writeRaw(next)
  return { ok: true, already: false, wallet: next }
}

/**
 * 목업 충전 — 결제 없이 즉시 가산. UI에 시뮬레이션임을 표시할 것.
 */
export function topUpPackage(packageId) {
  const pkg = (creditConfig.packages || []).find((p) => p.id === packageId && p.active !== false)
  if (!pkg) {
    return { ok: false, reason: 'unknown_package', wallet: readRaw() }
  }
  const wallet = readRaw()
  const next = {
    ...wallet,
    balance: wallet.balance + Number(pkg.credits || 0),
  }
  writeRaw(next)
  return { ok: true, wallet: next, package: pkg }
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
