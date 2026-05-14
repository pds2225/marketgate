import { startTransition, useEffect, useState } from 'react'
import LandingPage from './LandingPage'
import AnalysisPage from './AnalysisPage'
import AdminDashboard from './AdminDashboard'
import ChatModePage from './ChatModePage'
import ExportFlowPage from './ExportFlowPage'
import BuyerSearchPage from './pages/BuyerSearch'
import AuthPage from './AuthPage'
import SimulationPage from './SimulationPage'
import PricingPage from './PricingPage'
import PaymentCallbackPage from './PaymentCallbackPage'
import api from './lib/api'
import './App.css'

function App() {
  const [page, setPage] = useState('landing')
  const [chatPreset, setChatPreset] = useState(null)
  const [authed, setAuthed] = useState(!!localStorage.getItem('access_token'))
  const [balance, setBalance] = useState(null)

  const navigate = (nextPage, preset = null) => {
    startTransition(() => {
      setPage(nextPage)
      setChatPreset(preset)
    })
  }

  const logout = async () => {
    try { await api.post('/v1/auth/logout') } catch {}
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setAuthed(false)
    setBalance(null)
    navigate('landing')
  }

  useEffect(() => {
    const onLogout = () => { setAuthed(false); setBalance(null); navigate('landing') }
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [])

  const refreshBalance = () => {
    api.get('/v1/credits/balance').then(r => setBalance(r.data.balance)).catch(() => {})
  }

  useEffect(() => {
    if (!authed) return
    refreshBalance()
  }, [authed, page])

  if (!authed) {
    return <AuthPage onSuccess={() => setAuthed(true)} />
  }

  return (
    <div className="app-shell">
      {page !== 'admin' && (
        <div style={{ position: 'fixed', top: 8, right: 8, display: 'flex', gap: 8, zIndex: 100, alignItems: 'center' }}>
          {balance !== null && (
            <span style={{ background: '#1f6feb', color: '#fff', borderRadius: 12, padding: '3px 10px', fontSize: 12, fontWeight: 600 }}>
              {balance}C
            </span>
          )}
          <button
            className="app-admin-toggle"
            onClick={() => navigate('pricing')}
            style={{ marginRight: 0 }}
          >
            요금제
          </button>
          <button
            className="app-admin-toggle"
            onClick={() => navigate('simulation')}
            style={{ marginRight: 0 }}
          >
            시뮬레이션
          </button>
          <button className="app-admin-toggle" onClick={() => navigate('admin')} style={{ marginRight: 0 }}>
            관리자
          </button>
          <button
            className="app-admin-toggle"
            onClick={logout}
            style={{ background: '#da3633', marginRight: 0 }}
          >
            로그아웃
          </button>
        </div>
      )}

      {page === 'landing' && (
        <LandingPage
          onStartChat={(preset) => navigate('chat', preset)}
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

      {page === 'chat' && (
        <ChatModePage
          preset={chatPreset}
          onBack={() => navigate('landing')}
          onSwitchToForm={() => navigate('analysis')}
          onStartWizard={(preset) => navigate('analysis', preset)}
        />
      )}

      {page === 'simulation' && (
        <SimulationPage onBack={() => navigate('landing')} />
      )}

      {page === 'admin' && (
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
      )}
    </div>
  )
}

export default App
