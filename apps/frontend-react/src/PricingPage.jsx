import { useState, useEffect, useRef } from 'react'
import {
  activePackages,
  approxUnlockCount,
  creditConfig,
} from './config/creditConfig.js'
import { isTossPaymentEnabled } from './config/paymentConfig.js'
import { startTossCheckout } from './lib/tossCheckout.js'

const PLANS = [
  {
    key: 'Basic',
    label: 'BASIC',
    price: 0,
    priceLabel: '무료',
    tag: '시작하기',
    color: '#a8a29e',
    features: [
      { text: '수출국 탐색', ok: true },
      { text: 'BEP·수익성 계산', ok: true },
      { text: '바이어 상세정보', ok: false },
      { text: '수익분석 고급', ok: false },
      { text: '바이어 신용레포트', ok: false },
      { text: '바이어 컨택 발송/추적', ok: false },
    ],
  },
  {
    key: 'Pro',
    label: 'PRO',
    price: 29000,
    priceLabel: '29,000',
    tag: '인기',
    color: '#f59e0b',
    features: [
      { text: '수출국 탐색', ok: true },
      { text: 'BEP·수익성 계산', ok: true },
      { text: '바이어 상세정보', ok: true },
      { text: '수익분석 고급', ok: true },
      { text: '바이어 신용레포트', ok: false },
      { text: '바이어 컨택 발송/추적', ok: false },
    ],
  },
  {
    key: 'Advanced',
    label: 'ADVANCED',
    price: 79000,
    priceLabel: '79,000',
    tag: '전체 기능',
    color: '#e2e8f0',
    features: [
      { text: '수출국 탐색', ok: true },
      { text: 'BEP·수익성 계산', ok: true },
      { text: '바이어 상세정보', ok: true },
      { text: '수익분석 고급', ok: true },
      { text: '바이어 신용레포트', ok: true },
      { text: '바이어 컨택 발송/추적', ok: true },
    ],
  },
]

const PACKAGES = activePackages().map((pkg, idx, arr) => {
  const credits = Number(pkg.credits) || 0
  const price = Number(pkg.price) || 0
  const per = credits > 0 ? Math.round(price / credits) : 0
  return {
    key: pkg.id,
    label: `${credits}C`,
    sub: pkg.name,
    price: price.toLocaleString('ko-KR'),
    per: `${per.toLocaleString('ko-KR')}원/C`,
    hint: `약 ${approxUnlockCount(credits)}건 열람`,
    best: idx === arr.length - 1,
  }
})

function useCountUp(target, duration = 900) {
  const [val, setVal] = useState(0)
  const frame = useRef(null)
  useEffect(() => {
    let start = null
    const step = (ts) => {
      if (!start) start = ts
      const p = Math.min((ts - start) / duration, 1)
      setVal(Math.floor(p * p * target))
      if (p < 1) frame.current = requestAnimationFrame(step)
    }
    frame.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame.current)
  }, [target])
  return val
}

function PriceCounter({ value }) {
  const n = useCountUp(value)
  return <>{n.toLocaleString()}</>
}

export default function PricingPage({ onBack }) {
  const [loading, setLoading] = useState(null)
  const [error, setError] = useState('')
  const [hovered, setHovered] = useState(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 60)
    return () => clearTimeout(t)
  }, [])

  async function handleCheckout(product_type, item) {
    setLoading(item)
    setError('')
    try {
      // 토스 미활성(sim)이어도 checkout API는 호출해 ready 메시지를 받는다.
      // 실결제: paymentConfig.mode='toss' + 서버 TOSS_CLIENT_KEY.
      const result = await startTossCheckout(
        product_type === 'credit'
          ? { product_type, package: item }
          : { product_type, plan: item }
      )
      if (!result.ok) {
        setError(
          !isTossPaymentEnabled()
            ? '결제 시스템 준비 중입니다. 오픈 전까지는 무료 제공 크레딧으로 이용하실 수 있습니다.'
            : (result.data?.message || '결제 페이지를 열지 못했습니다. TOSS_CLIENT_KEY를 확인하세요.')
        )
        setLoading(null)
        return
      }
      window.location.href = result.checkout_url
    } catch (e) {
      setError(e?.response?.data?.detail || '결제 요청 실패')
      setLoading(null)
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

        .pg-root {
          min-height: 100vh;
          background: #0c0a09;
          color: #e7e5e4;
          font-family: 'DM Sans', sans-serif;
          overflow-x: hidden;
          position: relative;
        }
        .pg-root::before {
          content: '';
          position: fixed;
          inset: 0;
          background:
            radial-gradient(ellipse 60% 40% at 80% 10%, rgba(245,158,11,0.07) 0%, transparent 60%),
            radial-gradient(ellipse 40% 60% at 10% 80%, rgba(245,158,11,0.04) 0%, transparent 50%);
          pointer-events: none;
          z-index: 0;
        }
        .pg-grid {
          position: fixed;
          inset: 0;
          background-image:
            linear-gradient(rgba(245,158,11,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(245,158,11,0.03) 1px, transparent 1px);
          background-size: 60px 60px;
          pointer-events: none;
          z-index: 0;
        }
        .pg-inner {
          position: relative;
          z-index: 1;
          max-width: 1100px;
          margin: 0 auto;
          padding: 0 28px 80px;
        }

        /* NAV */
        .pg-nav {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 28px 0 0;
          opacity: 0;
          transform: translateY(-12px);
          transition: opacity 0.5s ease, transform 0.5s ease;
        }
        .pg-nav.in { opacity: 1; transform: translateY(0); }
        .pg-back {
          display: flex;
          align-items: center;
          gap: 8px;
          background: none;
          border: 1px solid rgba(245,158,11,0.2);
          color: #a8a29e;
          border-radius: 4px;
          padding: 7px 14px;
          cursor: pointer;
          font-family: 'DM Mono', monospace;
          font-size: 0.75rem;
          letter-spacing: 0.05em;
          transition: border-color 0.2s, color 0.2s;
        }
        .pg-back:hover { border-color: #f59e0b; color: #f59e0b; }
        .pg-nav-tag {
          font-family: 'DM Mono', monospace;
          font-size: 0.7rem;
          color: #57534e;
          letter-spacing: 0.12em;
        }

        /* HERO */
        .pg-hero {
          padding: 64px 0 56px;
          opacity: 0;
          transform: translateY(20px);
          transition: opacity 0.6s ease 0.1s, transform 0.6s ease 0.1s;
        }
        .pg-hero.in { opacity: 1; transform: translateY(0); }
        .pg-eyebrow {
          font-family: 'DM Mono', monospace;
          font-size: 0.7rem;
          letter-spacing: 0.2em;
          color: #f59e0b;
          margin-bottom: 16px;
          text-transform: uppercase;
        }
        .pg-title {
          font-family: 'Bebas Neue', sans-serif;
          font-size: clamp(3.5rem, 8vw, 7rem);
          line-height: 0.92;
          letter-spacing: 0.02em;
          color: #fafaf9;
          margin: 0 0 24px;
        }
        .pg-title span { color: #f59e0b; }
        .pg-subtitle {
          font-size: 0.9rem;
          color: #78716c;
          font-weight: 300;
          max-width: 400px;
          line-height: 1.7;
        }

        /* PLANS */
        .pg-section-label {
          font-family: 'DM Mono', monospace;
          font-size: 0.65rem;
          letter-spacing: 0.18em;
          color: #57534e;
          text-transform: uppercase;
          margin-bottom: 20px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .pg-section-label::after {
          content: '';
          flex: 1;
          height: 1px;
          background: rgba(245,158,11,0.1);
        }

        .pg-plans {
          display: grid;
          grid-template-columns: 1fr 1.15fr 1fr;
          gap: 2px;
          margin-bottom: 4px;
          opacity: 0;
          transform: translateY(24px);
          transition: opacity 0.6s ease 0.2s, transform 0.6s ease 0.2s;
        }
        .pg-plans.in { opacity: 1; transform: translateY(0); }

        .plan-card {
          background: #141210;
          border: 1px solid rgba(255,255,255,0.06);
          padding: 32px 28px 28px;
          cursor: pointer;
          transition: border-color 0.25s, background 0.25s;
          position: relative;
          overflow: hidden;
        }
        .plan-card::before {
          content: '';
          position: absolute;
          top: 0; left: 0; right: 0;
          height: 2px;
          background: var(--accent);
          transform: scaleX(0);
          transform-origin: left;
          transition: transform 0.35s ease;
        }
        .plan-card:hover::before, .plan-card.active::before { transform: scaleX(1); }
        .plan-card:hover { border-color: rgba(255,255,255,0.12); background: #1a1714; }
        .plan-card.featured { background: #16130f; border-color: rgba(245,158,11,0.18); }

        .plan-tag {
          font-family: 'DM Mono', monospace;
          font-size: 0.62rem;
          letter-spacing: 0.12em;
          color: var(--accent);
          text-transform: uppercase;
          margin-bottom: 20px;
        }
        .plan-name {
          font-family: 'Bebas Neue', sans-serif;
          font-size: 2.2rem;
          letter-spacing: 0.05em;
          color: #fafaf9;
          line-height: 1;
          margin-bottom: 6px;
        }
        .plan-price-row {
          display: flex;
          align-items: baseline;
          gap: 4px;
          margin-bottom: 28px;
        }
        .plan-price {
          font-family: 'DM Mono', monospace;
          font-size: 1.8rem;
          font-weight: 500;
          color: var(--accent);
        }
        .plan-unit {
          font-family: 'DM Mono', monospace;
          font-size: 0.72rem;
          color: #57534e;
        }

        .plan-features {
          list-style: none;
          padding: 0;
          margin: 0 0 28px;
          border-top: 1px solid rgba(255,255,255,0.05);
          padding-top: 20px;
        }
        .plan-feature {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 0.8rem;
          color: #78716c;
          padding: 5px 0;
          font-weight: 300;
        }
        .plan-feature.ok { color: #d6d3d1; }
        .feat-dot {
          width: 6px; height: 6px;
          border-radius: 50%;
          flex-shrink: 0;
          background: #292524;
        }
        .plan-feature.ok .feat-dot { background: var(--accent); }

        .plan-btn {
          width: 100%;
          padding: 11px;
          background: transparent;
          border: 1px solid var(--accent);
          color: var(--accent);
          border-radius: 3px;
          cursor: pointer;
          font-family: 'DM Mono', monospace;
          font-size: 0.72rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          transition: background 0.2s, color 0.2s;
        }
        .plan-btn:hover { background: var(--accent); color: #0c0a09; }
        .plan-btn:disabled { opacity: 0.35; cursor: default; }
        .plan-btn.free { border-color: #292524; color: #44403c; cursor: default; }
        .plan-btn.free:hover { background: transparent; color: #44403c; }

        /* CREDITS */
        .pg-credits {
          margin-top: 64px;
          opacity: 0;
          transform: translateY(24px);
          transition: opacity 0.6s ease 0.35s, transform 0.6s ease 0.35s;
        }
        .pg-credits.in { opacity: 1; transform: translateY(0); }

        .credit-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 2px;
        }

        .credit-card {
          background: #141210;
          border: 1px solid rgba(255,255,255,0.06);
          padding: 28px;
          position: relative;
          transition: border-color 0.25s, background 0.25s;
          cursor: pointer;
        }
        .credit-card:hover { background: #1a1714; border-color: rgba(245,158,11,0.15); }
        .credit-card.best-val {
          border-color: rgba(245,158,11,0.25);
          background: #16130f;
        }
        .best-badge {
          position: absolute;
          top: 16px; right: 16px;
          font-family: 'DM Mono', monospace;
          font-size: 0.58rem;
          letter-spacing: 0.1em;
          background: #f59e0b;
          color: #0c0a09;
          padding: 3px 8px;
          border-radius: 2px;
          text-transform: uppercase;
          font-weight: 500;
        }
        .credit-amount {
          font-family: 'Bebas Neue', sans-serif;
          font-size: 3.5rem;
          line-height: 1;
          color: #fafaf9;
          margin-bottom: 4px;
        }
        .credit-sub {
          font-family: 'DM Mono', monospace;
          font-size: 0.65rem;
          color: #57534e;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          margin-bottom: 20px;
        }
        .credit-price {
          font-family: 'DM Mono', monospace;
          font-size: 1.2rem;
          color: #f59e0b;
          margin-bottom: 4px;
        }
        .credit-price::before { content: '₩ '; font-size: 0.75rem; }
        .credit-per {
          font-family: 'DM Mono', monospace;
          font-size: 0.65rem;
          color: #44403c;
          margin-bottom: 22px;
        }
        .credit-btn {
          width: 100%;
          padding: 10px;
          background: transparent;
          border: 1px solid rgba(245,158,11,0.25);
          color: #f59e0b;
          border-radius: 3px;
          cursor: pointer;
          font-family: 'DM Mono', monospace;
          font-size: 0.7rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          transition: background 0.2s, color 0.2s, border-color 0.2s;
        }
        .credit-btn:hover { background: #f59e0b; color: #0c0a09; border-color: #f59e0b; }
        .credit-btn:disabled { opacity: 0.35; cursor: default; }

        /* ERROR */
        .pg-error {
          background: rgba(239,68,68,0.08);
          border: 1px solid rgba(239,68,68,0.2);
          color: #fca5a5;
          border-radius: 4px;
          padding: 12px 16px;
          font-family: 'DM Mono', monospace;
          font-size: 0.75rem;
          margin-bottom: 28px;
        }

        /* TICKER */
        .pg-ticker {
          display: flex;
          gap: 32px;
          padding: 16px 0;
          border-top: 1px solid rgba(255,255,255,0.04);
          border-bottom: 1px solid rgba(255,255,255,0.04);
          margin-bottom: 56px;
          overflow: hidden;
        }
        .ticker-item {
          display: flex;
          gap: 8px;
          align-items: center;
          flex-shrink: 0;
          font-family: 'DM Mono', monospace;
          font-size: 0.7rem;
          color: #44403c;
          letter-spacing: 0.06em;
        }
        .ticker-item span { color: #f59e0b; }

        @media (max-width: 768px) {
          .pg-plans { grid-template-columns: 1fr; }
          .credit-grid { grid-template-columns: 1fr; }
          .pg-title { font-size: 3.8rem; }
        }
      `}</style>

      <div className="pg-root">
        <div className="pg-grid" />
        <div className="pg-inner">

          <nav className={`pg-nav ${visible ? 'in' : ''}`}>
            <button className="pg-back" onClick={onBack}>
              ← 돌아가기
            </button>
            <span className="pg-nav-tag">MARKETGATE / PRICING</span>
          </nav>

          <div className={`pg-hero ${visible ? 'in' : ''}`}>
            <div className="pg-eyebrow">// 요금제 및 크레딧</div>
            <h1 className="pg-title">
              EXPORT<br />
              <span>FIT</span><br />
              PRICING
            </h1>
            <p className="pg-subtitle">
              글로벌 바이어 탐색부터 컨택까지.<br />
              비즈니스 규모에 맞는 플랜을 선택하세요.
            </p>
          </div>

          <div className="pg-ticker">
            {['BUYER_FIT_LITE · 3C', 'BUYER_FIT_PRO · 25C', 'CONTACT_SEND · 5C', 'CONTACT_REPLY · 13C', 'BUYER_FIT_LITE · 3C', 'BUYER_FIT_PRO · 25C'].map((t, i) => (
              <div key={i} className="ticker-item">
                <span>▸</span> {t}
              </div>
            ))}
          </div>

          {error && <div className="pg-error">ERR: {error}</div>}

          <div className="pg-section-label">구독 플랜 · /month</div>

          <div className={`pg-plans ${visible ? 'in' : ''}`}>
            {PLANS.map((plan) => (
              <div
                key={plan.key}
                className={`plan-card ${plan.key === 'Pro' ? 'featured' : ''} ${hovered === plan.key ? 'active' : ''}`}
                style={{ '--accent': plan.color }}
                onMouseEnter={() => setHovered(plan.key)}
                onMouseLeave={() => setHovered(null)}
              >
                <div className="plan-tag">{plan.tag}</div>
                <div className="plan-name">{plan.label}</div>
                <div className="plan-price-row">
                  {plan.price === 0 ? (
                    <span className="plan-price">FREE</span>
                  ) : (
                    <>
                      <span className="plan-price">
                        <PriceCounter value={plan.price} />
                      </span>
                      <span className="plan-unit">원/월</span>
                    </>
                  )}
                </div>

                <ul className="plan-features">
                  {plan.features.map((f, i) => (
                    <li key={i} className={`plan-feature ${f.ok ? 'ok' : ''}`}>
                      <span className="feat-dot" />
                      {f.text}
                    </li>
                  ))}
                </ul>

                {plan.key === 'Basic' ? (
                  <button className="plan-btn free">현재 플랜</button>
                ) : (
                  <button
                    className="plan-btn"
                    disabled={loading === plan.key}
                    onClick={() => handleCheckout('subscription', plan.key)}
                  >
                    {loading === plan.key ? '처리중...' : '업그레이드'}
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className={`pg-credits ${visible ? 'in' : ''}`}>
            <div className="pg-section-label">크레딧 충전 · 1회 구매</div>
            <p style={{ fontSize: 12, color: '#a8a29e', margin: '0 0 14px' }}>
              연락처 열람 {creditConfig.unlockCost}C/건 · 패키지·단가는 creditConfig에서 변경
            </p>
            <div className="credit-grid">
              {PACKAGES.map((pkg) => (
                <div
                  key={pkg.key}
                  className={`credit-card ${pkg.best ? 'best-val' : ''}`}
                >
                  {pkg.best && <span className="best-badge">최고 가성비</span>}
                  <div className="credit-amount">{pkg.label}</div>
                  <div className="credit-sub">{pkg.sub} 패키지</div>
                  <div className="credit-price">{pkg.price}</div>
                  <div className="credit-per">{pkg.per} · {pkg.hint}</div>
                  <button
                    className="credit-btn"
                    disabled={loading === pkg.key}
                    onClick={() => handleCheckout('credit', pkg.key)}
                  >
                    {loading === pkg.key ? '처리중...' : '충전하기'}
                  </button>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
