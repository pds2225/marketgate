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
                onClick={() => navigate('pricing')}
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
                title="크레딧 잔액 — 클릭하여 충전"
              >
                {balance}C
              </span>
            )}
            {[
              { label: '요금제', page: 'pricing' },
              { label: '시뮬레이션', page: 'simulation' },
              { label: '관리자', page: 'admin' },
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
