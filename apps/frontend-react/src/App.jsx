import { startTransition, useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import LandingPage from './LandingPage'
import AnalysisPage from './AnalysisPage'
import AdminDashboard from './AdminDashboard'
import ExportFlowPage from './ExportFlowPage'
import BuyerSearchPage from './pages/BuyerSearch'
import AuthPage from './AuthPage'
import SimulationPage from './SimulationPage'
import PricingPage from './PricingPage'
import PaymentCallbackPage from './PaymentCallbackPage'
import OpportunityExplorePage from './OpportunityExplorePage'
import ComparePage from './ComparePage'
import MyInquiriesPage from './MyInquiriesPage'
import CreditTopUpSheet from './components/CreditTopUpSheet'
import { getWallet, subscribeWallet, syncBalanceFromServer } from './lib/creditWallet'
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
    // Send refresh_token so the server can revoke it (L024). Access-only
    // blacklist leaves a usable refresh that can mint a new session.
    const refreshToken = localStorage.getItem('refresh_token')
    try {
      await api.post('/v1/auth/logout', refreshToken ? { refresh_token: refreshToken } : {})
    } catch {}
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
    // 결제 콜백 URL은 지우지 않는다 — paymentKey/orderId/amount가 사라지면
    // 재로그인 후에도 confirm을 호출할 수 없다 (docs/LESSONS.md L023).
    const onLogout = () => {
      setSessionExpired(true)
      setAuthed(false)
      setIsAdmin(false)
      const onPaymentCallback =
        typeof window !== 'undefined' &&
        window.location.pathname.replace(/\/+$/, '') === '/payment/callback'
      if (!onPaymentCallback) navigate('landing')
    }
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [])

  // 서버 크레딧 잔액 동기화 (실패 시 로컬 폴백)
  useEffect(() => {
    setBalance(getWallet().balance)
    const unsub = subscribeWallet((w) => setBalance(w.balance))
    if (authed) {
      syncBalanceFromServer().then((r) => {
        if (r.ok) setBalance(r.wallet.balance)
      })
    }
    return unsub
  }, [authed])

  const refreshBalance = async () => {
    const r = await syncBalanceFromServer()
    setBalance(r.wallet.balance)
  }
  useEffect(() => {
    if (!authed) return
    let cancelled = false
    api.get('/v1/auth/me')
      .then(r => { if (!cancelled) setIsAdmin(r.data?.role === 'admin') })
      .catch(() => { if (!cancelled) setIsAdmin(false) })
    return () => { cancelled = true }
  }, [authed])

  if (!authed && page !== 'landing') {
    return (
      <AuthPage
        sessionExpired={sessionExpired}
        onSuccess={() => { setSessionExpired(false); setAuthed(true) }}
      />
    )
  }

  return (
    <div className={`app-shell app-shell--${page}`}>
      {page !== 'admin' && page !== 'landing' && (
        <header className="app-global-header">
          <button className="app-global-brand" onClick={() => navigate('landing')}>
            MarketGate
          </button>
          <nav className="app-global-nav" aria-label="주요 메뉴">
            {[
              { label: '내 인콰이어리', page: 'myInquiries' },
              { label: '해외 수요 찾기', page: 'opportunities' },
              { label: '국가·바이어 비교', page: 'compare' },
              { label: '요금제', page: 'pricing' },
              { label: '시뮬레이션', page: 'simulation' },
              // 관리자 메뉴는 서버가 role=admin 을 내려준 계정에만 노출 (서버 403이 최종 방어선)
              ...(isAdmin ? [{ label: '관리자', page: 'admin' }] : []),
            ].map(({ label, page: p }) => (
              <button
                key={p}
                className={`app-global-nav-link${page === p ? ' is-active' : ''}`}
                aria-current={page === p ? 'page' : undefined}
                onClick={() => navigate(p)}
              >
                {label}
              </button>
            ))}
            {balance !== null && (
              <button
                className="app-global-credit"
                onClick={() => setTopUpOpen(true)}
                title="서버 크레딧 잔액 — 클릭하여 충전"
              >
                {balance}C
              </button>
            )}
            <button
              className={`app-global-search${page === 'buyerSearch' ? ' is-active' : ''}`}
              onClick={() => navigate('buyerSearch')}
            >
              <Search size={18} strokeWidth={2} aria-hidden="true" />
              바이어 검색
            </button>
            <button
              className="app-global-logout"
              onClick={logout}
            >
              로그아웃
            </button>
          </nav>
        </header>
      )}

      {page === 'landing' && (
        <LandingPage
          onStartFlow={() => navigate('exportFlow')}
          onStartBuyerSearch={() => navigate('buyerSearch')}
          onStartAnalysis={(preset) => navigate('analysis', preset || null)}
          onStartOpportunities={(preset) => navigate('opportunities', preset || null)}
          onStartCompare={() => navigate('compare')}
          onStartMyInquiries={() => navigate('myInquiries')}
        />
      )}

      {page === 'buyerSearch' && (
        <main className="app-detail-page app-detail-page--buyer-search">
          <BuyerSearchPage onClose={() => navigate('landing')} onBalanceRefresh={refreshBalance} />
        </main>
      )}

      {page === 'opportunities' && (
        <main className="app-detail-page"><OpportunityExplorePage onBack={() => navigate('landing')} preset={chatPreset} /></main>
      )}

      {page === 'myInquiries' && (
        <main className="app-detail-page"><MyInquiriesPage onBack={() => navigate('landing')} /></main>
      )}

      {page === 'compare' && (
        <main className="app-detail-page"><ComparePage onBack={() => navigate('landing')} /></main>
      )}

      {page === 'analysis' && (
        <main className="app-detail-page"><AnalysisPage onBack={() => navigate('landing')} preset={chatPreset} /></main>
      )}

      {page === 'exportFlow' && (
        <main className="app-detail-page"><ExportFlowPage onBack={() => navigate('landing')} /></main>
      )}

      {page === 'pricing' && (
        <main className="app-detail-page"><PricingPage onBack={() => navigate('landing')} /></main>
      )}

      {page === 'paymentCallback' && (
        <main className="app-detail-page"><PaymentCallbackPage onBack={() => navigate('landing')} onBalanceRefresh={refreshBalance} /></main>
      )}

      {page === 'simulation' && (
        <main className="app-detail-page"><SimulationPage onBack={() => navigate('landing')} /></main>
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
