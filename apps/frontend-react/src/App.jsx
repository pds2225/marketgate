import { startTransition, useEffect, useState } from 'react'
import LandingPage from './LandingPage'
import AnalysisPage from './AnalysisPage'
import AdminDashboard from './AdminDashboard'
import ExportFlowPage from './ExportFlowPage'
import BuyerSearchPage from './pages/BuyerSearch'
import AuthPage from './AuthPage'
import SimulationPage from './SimulationPage'
import PricingPage from './PricingPage'
import PaymentCallbackPage from './PaymentCallbackPage'
import CreditTopUpSheet from './components/CreditTopUpSheet'
import { getWallet, subscribeWallet } from './lib/creditWallet'
import api from './lib/api'
import './App.css'

// 결제 게이트웨이(successUrl/failUrl)가 SPA로 돌려보내는 경로를 초기 화면으로 매핑한다.
// 이 처리가 없으면 결제 후 /payment/callback 으로 돌아와도 항상 landing 이 떠서
// 결제 확인 화면(PaymentCallbackPage)이 영영 보이지 않는다(정상 결제인데 고장처럼 보임).
function getInitialPage() {
  if (typeof window === 'undefined') return 'landing'
  if (window.location.pathname.replace(/\/+$/, '') === '/payment/callback') {
    return 'paymentCallback'
  }
  return 'landing'
}

function App() {
  const [page, setPage] = useState(getInitialPage)
  const [chatPreset, setChatPreset] = useState(null)
  const [authed, setAuthed] = useState(!!localStorage.getItem('access_token'))
  const [balance, setBalance] = useState(() => getWallet().balance)
  const [topUpOpen, setTopUpOpen] = useState(false)
  // 서버(/v1/auth/me)의 role 필드 기준으로만 관리자 메뉴를 노출한다.
  // 메뉴 숨김은 UX 차원일 뿐이며 실제 차단은 서버 403이 담당한다.
  const [isAdmin, setIsAdmin] = useState(false)
  // 세션이 본인 의사와 무관하게(토큰 만료 → 재발급 실패) 끊겼을 때만 true.
  // 직접 누른 로그아웃과 구분해, 로그인 화면에서 "다시 로그인" 안내를 띄운다.
  const [sessionExpired, setSessionExpired] = useState(false)

  const navigate = (nextPage, preset = null) => {
    // 결제 콜백 경로(/payment/callback?status=...)에서 다른 화면으로 이동할 때
    // 주소창을 정리해, 새로고침 시 지난 결제 결과 화면이 다시 뜨지 않게 한다.
    if (
      nextPage !== 'paymentCallback' &&
      typeof window !== 'undefined' &&
      window.location.pathname.replace(/\/+$/, '') === '/payment/callback'
    ) {
      window.history.replaceState(null, '', '/')
    }
    startTransition(() => {
      setPage(nextPage)
      setChatPreset(preset)
    })
  }

  const logout = async () => {
    try { await api.post('/v1/auth/logout') } catch {}
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setSessionExpired(false)
    setAuthed(false)
    setBalance(getWallet().balance)
    setIsAdmin(false)
    navigate('landing')
  }

  useEffect(() => {
    // api.js 인터셉터가 토큰 재발급 실패 시 발생시키는 이벤트.
    // 사용자가 직접 로그아웃한 게 아니라 세션이 만료돼 강제로 끊긴 경우다.
    const onLogout = () => { setSessionExpired(true); setAuthed(false); setIsAdmin(false); navigate('landing') }
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [])

  // 로컬 시뮬레이션 지갑 (서버 /v1/credits 와 분리 — 파일럿)
  useEffect(() => {
    setBalance(getWallet().balance)
    return subscribeWallet((w) => setBalance(w.balance))
  }, [])

  const refreshBalance = () => {
    setBalance(getWallet().balance)
  }
  useEffect(() => {
    if (!authed) return
    let cancelled = false
    api.get('/v1/auth/me')
      .then(r => { if (!cancelled) setIsAdmin(r.data?.role === 'admin') })
      .catch(() => { if (!cancelled) setIsAdmin(false) })
    return () => { cancelled = true }
  }, [authed])

  if (!authed) {
    return (
      <AuthPage
        sessionExpired={sessionExpired}
        onSuccess={() => { setSessionExpired(false); setAuthed(true) }}
      />
    )
  }

  return (
    <div className="app-shell">
      {page !== 'admin' && (
        <div style={{
          position: 'fixed', top: 0, right: 0, left: 0,
          zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px',
          height: 48,
          background: 'rgba(12,10,9,0.88)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(245,158,11,0.07)',
          fontFamily: "'DM Mono', 'Cascadia Code', monospace",
        }}>
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.12em', color: '#f59e0b', cursor: 'pointer' }} onClick={() => navigate('landing')}>
            MARKETGATE
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {balance !== null && (
              <span
                onClick={() => setTopUpOpen(true)}
                style={{
                  cursor: 'pointer',
                  background: 'rgba(245,158,11,0.1)',
                  border: '1px solid rgba(245,158,11,0.25)',
                  color: '#f59e0b',
                  borderRadius: 3,
                  padding: '3px 10px',
                  fontSize: 11,
                  fontFamily: "'DM Mono', monospace",
                  letterSpacing: '0.08em',
                  fontWeight: 500,
                }}
                title="시뮬레이션 크레딧 — 클릭하여 충전"
              >
                {balance}C
              </span>
            )}
            {[
              { label: '요금제', page: 'pricing' },
              { label: '시뮬레이션', page: 'simulation' },
              // 관리자 메뉴는 서버가 role=admin 을 내려준 계정에만 노출 (서버 403이 최종 방어선)
              ...(isAdmin ? [{ label: '관리자', page: 'admin' }] : []),
            ].map(({ label, page: p }) => (
              <button
                key={p}
                onClick={() => navigate(p)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#57534e',
                  cursor: 'pointer',
                  fontSize: 11,
                  letterSpacing: '0.08em',
                  padding: '6px 10px',
                  fontFamily: "'DM Mono', monospace",
                  transition: 'color 0.15s',
                }}
                onMouseEnter={e => e.target.style.color = '#e7e5e4'}
                onMouseLeave={e => e.target.style.color = '#57534e'}
              >
                {label}
              </button>
            ))}
            <button
              onClick={logout}
              style={{
                background: 'none',
                border: '1px solid rgba(239,68,68,0.2)',
                color: '#78716c',
                cursor: 'pointer',
                fontSize: 11,
                letterSpacing: '0.08em',
                padding: '5px 10px',
                fontFamily: "'DM Mono', monospace",
                borderRadius: 3,
                transition: 'color 0.15s, border-color 0.15s',
              }}
              onMouseEnter={e => { e.target.style.color='#fca5a5'; e.target.style.borderColor='rgba(239,68,68,0.5)' }}
              onMouseLeave={e => { e.target.style.color='#78716c'; e.target.style.borderColor='rgba(239,68,68,0.2)' }}
            >
              로그아웃
            </button>
          </div>
        </div>
      )}

      {page === 'landing' && (
        <LandingPage
          onStartFlow={() => navigate('exportFlow')}
          onStartBuyerSearch={() => navigate('buyerSearch')}
          onStartAnalysis={() => navigate('analysis')}
        />
      )}

      {page === 'buyerSearch' && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <BuyerSearchPage onClose={() => navigate('landing')} onBalanceRefresh={refreshBalance} />
        </div>
      )}

      {page === 'analysis' && (
        <AnalysisPage onBack={() => navigate('landing')} preset={chatPreset} />
      )}

      {page === 'exportFlow' && (
        <ExportFlowPage onBack={() => navigate('landing')} />
      )}

      {page === 'pricing' && (
        <PricingPage onBack={() => navigate('landing')} />
      )}

      {page === 'paymentCallback' && (
        <PaymentCallbackPage onBack={() => navigate('landing')} onBalanceRefresh={refreshBalance} />
      )}

      {page === 'simulation' && (
        <SimulationPage onBack={() => navigate('landing')} />
      )}

      {page === 'admin' && (
        isAdmin ? (
          <div className="app-admin-view">
            <div className="app-admin-exit">
              <button
                className="ui-button ui-button--solid app-admin-exit-button"
                onClick={() => navigate('landing')}
              >
                ← 사용자 모드로 돌아가기
              </button>
            </div>
            <AdminDashboard />
          </div>
        ) : (
          <div style={{ paddingTop: 96, textAlign: 'center', color: '#a8a29e', fontSize: 14 }}>
            관리자 권한이 없습니다 (403). 관리자 계정으로 로그인해 주세요.
            <div style={{ marginTop: 16 }}>
              <button className="ui-button ui-button--solid" onClick={() => navigate('landing')}>홈으로</button>
            </div>
          </div>
        )
      )}
      <CreditTopUpSheet open={topUpOpen} onClose={() => setTopUpOpen(false)} />
    </div>
  )
}

export default App
