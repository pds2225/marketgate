import { useEffect, useState } from 'react'
import {
  activePackages,
  approxUnlockCount,
  creditConfig,
  formatPrice,
} from '../config/creditConfig.js'
import { isTossPaymentEnabled } from '../config/paymentConfig.js'
import { getWallet, subscribeWallet, topUpPackage } from '../lib/creditWallet.js'
import { startTossCheckout } from '../lib/tossCheckout.js'

/**
 * 크레딧 충전 시트.
 * - sim(기본): 파일럿 charge
 * - toss: /v1/payment/checkout 리다이렉트 (키 준비 후 paymentConfig.mode='toss')
 */
export default function CreditTopUpSheet({ open, onClose, onToppedUp }) {
  const [wallet, setWallet] = useState(getWallet)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')
  const useToss = isTossPaymentEnabled()

  useEffect(() => subscribeWallet(setWallet), [])

  if (!open) return null

  const packages = activePackages()

  const handleTopUp = async (pkgId) => {
    setError('')
    setBusy(pkgId)
    try {
      if (useToss) {
        const result = await startTossCheckout({ product_type: 'credit', package: pkgId })
        if (!result.ok) {
          setError(
            result.reason === 'toss_not_ready' || result.data?.message
              ? (result.data?.message || '토스 결제 키가 아직 없습니다. sim 모드로 두거나 서버 env를 설정하세요.')
              : '결제 페이지를 열지 못했습니다.'
          )
          return
        }
        window.location.href = result.checkout_url
        return
      }
      const result = await topUpPackage(pkgId)
      if (!result.ok) return
      setWallet(result.wallet)
      onToppedUp?.(result)
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '충전에 실패했습니다.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="크레딧 충전"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2000,
        background: 'rgba(0,0,0,0.55)',
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'center',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(440px, 100%)',
          background: '#fff',
          borderRadius: '16px 16px 0 0',
          padding: '20px 20px 28px',
          color: '#0f172a',
          fontFamily: 'inherit',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <strong style={{ fontSize: 16 }}>크레딧 충전</strong>
          <button type="button" onClick={onClose} style={{ border: 'none', background: 'transparent', fontSize: 18, cursor: 'pointer' }}>✕</button>
        </div>
        <p style={{ margin: '0 0 14px', fontSize: 12, color: '#64748b' }}>
          잔액 <strong style={{ color: '#b45309' }}>{wallet.balance}C</strong>
          {' · '}언락 {creditConfig.unlockCost}C/건
          {' · '}
          <span style={{ color: useToss ? '#059669' : '#b45309' }}>
            {useToss ? '토스 PG 결제' : '크레딧 충전 (결제 시스템 오픈 준비 중)'}
          </span>
        </p>
        {error ? (
          <p style={{ margin: '0 0 12px', fontSize: 12, color: '#dc2626' }}>{error}</p>
        ) : null}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {packages.map((pkg) => (
            <button
              key={pkg.id}
              type="button"
              disabled={!!busy}
              onClick={() => handleTopUp(pkg.id)}
              style={{
                textAlign: 'left',
                border: '1px solid #e2e8f0',
                borderRadius: 12,
                padding: '12px 14px',
                background: '#f8fafc',
                cursor: busy ? 'wait' : 'pointer',
                opacity: busy && busy !== pkg.id ? 0.6 : 1,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: 14 }}>
                <span>{pkg.name}</span>
                <span>{formatPrice(pkg.price)}</span>
              </div>
              <div style={{ marginTop: 4, fontSize: 12, color: '#64748b' }}>
                {pkg.credits}C · 약 {approxUnlockCount(pkg.credits)}건 열람
                {busy === pkg.id ? ' · 처리 중…' : ''}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
