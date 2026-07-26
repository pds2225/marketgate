import { useEffect, useState } from 'react'
import { creditConfig } from '../config/creditConfig.js'
import {
  displayContact,
  getWallet,
  isUnlocked,
  subscribeWallet,
  unlockBuyerServer,
} from '../lib/creditWallet.js'
import CreditTopUpSheet from './CreditTopUpSheet.jsx'

/**
 * 연락처 마스킹 + 크레딧 언락 패널 (로컬 지갑).
 */
export default function CreditUnlockPanel({
  buyerKey,
  email = '',
  phone = '',
  website = '',
  variant = 'light',
}) {
  const [wallet, setWallet] = useState(getWallet)
  const [topUpOpen, setTopUpOpen] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => subscribeWallet(setWallet), [])

  const unlocked = isUnlocked(buyerKey)
  const hasContact = !!(String(email).trim() || String(phone).trim() || String(website).trim())
  const cost = creditConfig.unlockCost
  const dark = variant === 'dark'

  const box = {
    marginTop: 10,
    padding: '12px 14px',
    borderRadius: 10,
    border: dark ? '1px solid rgba(148,163,184,0.25)' : '1px solid #e2e8f0',
    background: dark ? 'rgba(15,23,42,0.55)' : '#f8fafc',
    color: dark ? '#e2e8f0' : '#0f172a',
    fontSize: 13,
  }

  const muted = { color: dark ? '#94a3b8' : '#64748b', fontSize: 11, marginTop: 8 }

  const tryUnlock = async () => {
    setMessage('')
    const result = await unlockBuyerServer(buyerKey, { hasContact })
    if (result.ok) {
      setWallet(result.wallet)
      setMessage(result.already ? '이미 열람한 연락처입니다.' : `${cost}C 차감 · 연락처 열림`)
      return
    }
    if (result.reason === 'insufficient') {
      setTopUpOpen(true)
      setMessage(`잔액 부족 (필요 ${result.need}C · 보유 ${result.wallet.balance}C)`)
      return
    }
    if (result.reason === 'no_contact') {
      setMessage('열람할 연락처가 없습니다.')
      return
    }
    setMessage(typeof result.reason === 'string' ? `열람 실패: ${result.reason}` : '열람에 실패했습니다.')
  }

  const showEmail = displayContact(email, { unlocked, kind: 'email' })
  const showPhone = displayContact(phone, { unlocked, kind: 'phone' })
  const showWeb = unlocked ? website : website ? '••••••••' : ''

  return (
    <>
      <div style={box}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <strong style={{ fontSize: 13 }}>연락처 {unlocked ? '' : '(잠김)'}</strong>
          <span style={{ fontSize: 11, color: dark ? '#fbbf24' : '#b45309' }}>잔액 {wallet.balance}C</span>
        </div>
        {!hasContact ? (
          <p style={{ margin: 0, fontSize: 12, color: dark ? '#94a3b8' : '#64748b' }}>자료 내 연락처 없음</p>
        ) : (
          <>
            <div style={{ display: 'grid', gap: 4 }}>
              <div>✉ {showEmail || '—'}</div>
              <div>☎ {showPhone || '—'}</div>
              {website ? <div>🌐 {showWeb}</div> : null}
            </div>
            {!unlocked && (
              <button
                type="button"
                onClick={tryUnlock}
                style={{
                  marginTop: 10,
                  border: 'none',
                  borderRadius: 8,
                  padding: '8px 12px',
                  background: '#f59e0b',
                  color: '#3b2606',
                  fontWeight: 700,
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                컨택 열기 · {cost}C
              </button>
            )}
          </>
        )}
        {message ? <p style={muted}>{message}</p> : null}
        {!unlocked && hasContact ? (
          <p style={muted}>서버 지갑 차감 · 단가·패키지는 creditConfig</p>
        ) : null}
      </div>
      <CreditTopUpSheet
        open={topUpOpen}
        onClose={() => setTopUpOpen(false)}
        onToppedUp={() => {
          setTopUpOpen(false)
          setMessage('충전됨 · 다시 컨택 열기를 눌러주세요')
        }}
      />
    </>
  )
}
