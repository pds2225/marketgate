import { useEffect, useState } from 'react'
import api from './lib/api'
import { syncBalanceFromServer } from './lib/creditWallet'

const VERIFY_ATTEMPTS = 5
const VERIFY_INTERVAL_MS = 1500
const RECENT_WINDOW_MS = 15 * 60 * 1000

export default function PaymentCallbackPage({ onBack, onBalanceRefresh }) {
  const [status, setStatus] = useState('loading')
  const [dots, setDots] = useState(0)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const s = params.get('status')
    const type = params.get('type')
    const item = params.get('item')

    if (s !== 'success') {
      setStatus('fail')
      return
    }

    // 쿼리스트링만 믿지 않고 서버 결제내역으로 실제 완료를 검증한다
    let cancelled = false
    const verify = async (attempt) => {
      try {
        const { data } = await api.get('/v1/payment/history')
        const cutoff = Date.now() - RECENT_WINDOW_MS
        const confirmed = (Array.isArray(data) ? data : []).some(r =>
          r.status === 'DONE' &&
          (!type || r.product_type === type) &&
          (!item || r.package === item || r.plan === item) &&
          new Date(r.timestamp).getTime() >= cutoff
        )
        if (cancelled) return
        if (confirmed) {
          setStatus('success')
          await syncBalanceFromServer()
          if (onBalanceRefresh) onBalanceRefresh()
          return
        }
      } catch {
        // 일시 오류는 재시도
      }
      if (cancelled) return
      if (attempt < VERIFY_ATTEMPTS - 1) {
        setTimeout(() => verify(attempt + 1), VERIFY_INTERVAL_MS)
      } else {
        setStatus('pending')
      }
    }
    // 토스는 successUrl에 paymentKey/orderId/amount를 붙여 리다이렉트한다.
    // 승인(confirm)을 호출해야 실제로 매입된다 — 호출하지 않으면 카드사 인증만
    // 끝난 상태로 남아 약 10분 뒤 EXPIRE된다. 파라미터가 없으면 sim 흐름이므로
    // 기존처럼 결제내역 검증으로 바로 넘어간다.
    const confirmThenVerify = async () => {
      const paymentKey = params.get('paymentKey')
      const orderId = params.get('orderId')
      const amount = params.get('amount')

      if (paymentKey && orderId && amount) {
        try {
          await api.post('/v1/payment/confirm', {
            paymentKey,
            orderId,
            amount: Number(amount),
          })
        } catch (err) {
          if (cancelled) return
          const code = err?.response?.status
          // 4xx는 승인이 확정적으로 실패한 경우(소유자·금액 불일치, 토스 거절).
          // 503(키 미설정)·5xx·네트워크 오류는 웹훅으로 완료될 수 있으므로
          // 실패로 단정하지 않고 결제내역 검증으로 넘어간다.
          if (code >= 400 && code < 500) {
            setStatus('fail')
            return
          }
        }
      }
      if (!cancelled) verify(0)
    }

    confirmThenVerify()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (status !== 'loading') return
    const t = setInterval(() => setDots(d => (d + 1) % 4), 400)
    return () => clearInterval(t)
  }, [status])

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400&display=swap');

        .cb-root {
          min-height: 100vh;
          background: #0c0a09;
          color: #e7e5e4;
          font-family: 'DM Sans', sans-serif;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
        }
        .cb-root::before {
          content: '';
          position: fixed;
          inset: 0;
          background-image:
            linear-gradient(rgba(245,158,11,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(245,158,11,0.03) 1px, transparent 1px);
          background-size: 60px 60px;
          pointer-events: none;
        }
        .cb-glow {
          position: absolute;
          width: 500px; height: 500px;
          border-radius: 50%;
          filter: blur(120px);
          pointer-events: none;
          transition: background 0.8s ease;
        }
        .cb-inner {
          position: relative;
          z-index: 1;
          text-align: center;
          padding: 40px;
        }
        .cb-label {
          font-family: 'DM Mono', monospace;
          font-size: 0.65rem;
          letter-spacing: 0.2em;
          color: #57534e;
          text-transform: uppercase;
          margin-bottom: 32px;
        }
        .cb-icon {
          font-size: 4.5rem;
          line-height: 1;
          margin-bottom: 24px;
          display: block;
        }
        .cb-title {
          font-family: 'Bebas Neue', sans-serif;
          font-size: clamp(2.5rem, 6vw, 4.5rem);
          letter-spacing: 0.04em;
          line-height: 1;
          margin-bottom: 16px;
        }
        .cb-title.ok { color: #f59e0b; }
        .cb-title.fail { color: #ef4444; }
        .cb-title.loading { color: #44403c; }
        .cb-desc {
          font-size: 0.85rem;
          color: #78716c;
          font-weight: 300;
          margin-bottom: 40px;
          line-height: 1.7;
        }
        .cb-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 12px 28px;
          border-radius: 3px;
          cursor: pointer;
          font-family: 'DM Mono', monospace;
          font-size: 0.72rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          border: none;
          transition: opacity 0.2s, transform 0.15s;
        }
        .cb-btn:hover { opacity: 0.85; transform: translateY(-1px); }
        .cb-btn.ok { background: #f59e0b; color: #0c0a09; }
        .cb-btn.fail { background: #292524; color: #a8a29e; border: 1px solid #3d3330; }
        .cb-divider {
          width: 48px; height: 1px;
          background: rgba(245,158,11,0.2);
          margin: 24px auto;
        }
        .cb-dots { letter-spacing: 0.15em; }
      `}</style>

      <div className="cb-root">
        <div
          className="cb-glow"
          style={{
            background: status === 'success'
              ? 'rgba(245,158,11,0.08)'
              : status === 'fail'
              ? 'rgba(239,68,68,0.06)'
              : 'rgba(68,64,60,0.06)',
          }}
        />
        <div className="cb-inner">
          <div className="cb-label">MARKETGATE / PAYMENT</div>

          {status === 'loading' && (
            <>
              <div className="cb-icon">⏳</div>
              <div className="cb-title loading">
                처리중<span className="cb-dots">{'·'.repeat(dots)}</span>
              </div>
              <p className="cb-desc">결제를 확인하고 있습니다</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="cb-icon">◈</div>
              <div className="cb-title ok">PAYMENT<br />COMPLETE</div>
              <div className="cb-divider" />
              <p className="cb-desc">
                결제가 완료되었습니다.<br />
                크레딧 또는 플랜이 즉시 반영됩니다.
              </p>
              <button className="cb-btn ok" onClick={onBack}>
                ← 대시보드로
              </button>
            </>
          )}

          {status === 'pending' && (
            <>
              <div className="cb-icon">⏳</div>
              <div className="cb-title loading">VERIFYING<br />PAYMENT</div>
              <div className="cb-divider" />
              <p className="cb-desc">
                결제 승인을 아직 확인하지 못했습니다.<br />
                잠시 후 결제 내역에서 반영 여부를 확인해주세요.
              </p>
              <button className="cb-btn ok" onClick={onBack}>
                ← 대시보드로
              </button>
            </>
          )}

          {status === 'fail' && (
            <>
              <div className="cb-icon">✕</div>
              <div className="cb-title fail">PAYMENT<br />CANCELED</div>
              <div className="cb-divider" />
              <p className="cb-desc">
                결제가 취소되었습니다.<br />
                다시 시도하거나 문의해주세요.
              </p>
              <button className="cb-btn fail" onClick={onBack}>
                ← 돌아가기
              </button>
            </>
          )}
        </div>
      </div>
    </>
  )
}
