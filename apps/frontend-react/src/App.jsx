import { startTransition, useState } from 'react'
import LandingPage from './LandingPage'
import AnalysisPage from './AnalysisPage'
import AdminDashboard from './AdminDashboard'
import ChatModePage from './ChatModePage'
import ExportFlowPage from './ExportFlowPage'
import BuyerSearchPage from './pages/BuyerSearch'
import './App.css'

function App() {
  const [page, setPage] = useState('landing')
  const [chatPreset, setChatPreset] = useState(null)
  const navigate = (nextPage, preset = null) => {
    startTransition(() => {
      setPage(nextPage)
      setChatPreset(preset)
    })
  }

  return (
    <div className="app-shell">
      {page !== 'admin' && (
        <button className="app-admin-toggle" onClick={() => navigate('admin')}>
          관리자
        </button>
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
          <BuyerSearchPage onClose={() => navigate('landing')} />
        </div>
      )}

      {page === 'analysis' && (
        <AnalysisPage onBack={() => navigate('landing')} preset={chatPreset} />
      )}

      {page === 'exportFlow' && (
        <ExportFlowPage onBack={() => navigate('landing')} />
      )}

      {page === 'chat' && (
        <ChatModePage
          preset={chatPreset}
          onBack={() => navigate('landing')}
          onSwitchToForm={() => navigate('analysis')}
          onStartWizard={(preset) => navigate('analysis', preset)}
        />
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
