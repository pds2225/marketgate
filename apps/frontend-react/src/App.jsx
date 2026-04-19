import { startTransition, useState } from 'react'
import LandingPage from './LandingPage'
import AnalysisPage from './AnalysisPage'
import AdminDashboard from './AdminDashboard'
import './App.css'

function App() {
  const [page, setPage] = useState('landing')
  const navigate = (nextPage) => {
    startTransition(() => {
      setPage(nextPage)
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
        <LandingPage onStartAnalysis={() => navigate('analysis')} />
      )}

      {page === 'analysis' && (
        <AnalysisPage onBack={() => navigate('landing')} />
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
