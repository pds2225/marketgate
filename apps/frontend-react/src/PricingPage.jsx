import { useState } from 'react'
import api from './lib/api'

const PLANS = [
  { key: 'Basic',    label: 'Basic',    price: '무료',    features: ['수출국 탐색', 'BEP·수익성 계산'] },
  { key: 'Pro',      label: 'Pro',      price: '29,000원/월', features: ['Basic 전체', '바이어 상세정보', '수익분석 고급'] },
  { key: 'Advanced', label: 'Advanced', price: '79,000원/월', features: ['Pro 전체', '바이어 신용레포트', '바이어 컨택 발송/추적', 'K-SURE·D&B 연동'] },
]

const PACKAGES = [
  { key: 'small',  label: '소형',  credits: 10,  price: '20,000원' },
  { key: 'medium', label: '중형',  credits: 30,  price: '54,000원' },
  { key: 'large',  label: '대형',  credits: 100, price: '160,000원' },
]

export default function PricingPage({ onBack }) {
  const [loading, setLoading] = useState(null)
  const [error, setError] = useState('')

  async function handleCheckout(product_type, item) {
    setLoading(item)
    setError('')
    try {
      const payload = product_type === 'credit'
        ? { product_type, package: item }
        : { product_type, plan: item }
      const res = await api.post('/v1/payment/checkout', payload)
      window.location.href = res.data.checkout_url
    } catch (e) {
      setError(e?.response?.data?.detail || '결제 요청 실패')
      setLoading(null)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0d1117', color: '#e6edf3', padding: '40px 20px', fontFamily: 'Segoe UI, sans-serif' }}>
      <div style={{ maxWidth: 860, margin: '0 auto' }}>
        <button onClick={onBack} style={{ background: 'none', border: '1px solid #30363d', color: '#8b949e', borderRadius: 8, padding: '6px 14px', cursor: 'pointer', marginBottom: 32 }}>← 돌아가기</button>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 8 }}>플랜 & 크레딧</h1>
        <p style={{ color: '#8b949e', marginBottom: 40 }}>구독 플랜 또는 크레딧 패키지를 선택하세요.</p>

        {error && <div style={{ background: '#4a1c1c', color: '#ff7b72', borderRadius: 8, padding: '10px 16px', marginBottom: 24 }}>{error}</div>}

        <h2 style={{ fontSize: '1rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 16 }}>구독 플랜</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 48 }}>
          {PLANS.map(plan => (
            <div key={plan.key} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 12, padding: 24 }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 4 }}>{plan.label}</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#58a6ff', marginBottom: 16 }}>{plan.price}</div>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 20px', color: '#8b949e', fontSize: '0.85rem', lineHeight: 1.8 }}>
                {plan.features.map(f => <li key={f}>✓ {f}</li>)}
              </ul>
              {plan.key !== 'Basic' && (
                <button
                  disabled={loading === plan.key}
                  onClick={() => handleCheckout('subscription', plan.key)}
                  style={{ width: '100%', padding: '10px', background: '#1a7f37', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600, opacity: loading === plan.key ? 0.6 : 1 }}
                >
                  {loading === plan.key ? '처리 중...' : '결제하기'}
                </button>
              )}
            </div>
          ))}
        </div>

        <h2 style={{ fontSize: '1rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 16 }}>크레딧 패키지</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {PACKAGES.map(pkg => (
            <div key={pkg.key} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 12, padding: 24 }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 4 }}>{pkg.label} 패키지</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#58a6ff', marginBottom: 4 }}>{pkg.credits}C</div>
              <div style={{ color: '#8b949e', fontSize: '0.9rem', marginBottom: 20 }}>{pkg.price}</div>
              <button
                disabled={loading === pkg.key}
                onClick={() => handleCheckout('credit', pkg.key)}
                style={{ width: '100%', padding: '10px', background: '#1f6feb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600, opacity: loading === pkg.key ? 0.6 : 1 }}
              >
                {loading === pkg.key ? '처리 중...' : '결제하기'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
