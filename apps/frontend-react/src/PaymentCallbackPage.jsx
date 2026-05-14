import { useEffect, useState } from 'react'

export default function PaymentCallbackPage({ onBack, onBalanceRefresh }) {
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const s = params.get('status')
    setStatus(s === 'success' ? 'success' : 'fail')
    if (s === 'success' && onBalanceRefresh) onBalanceRefresh()
  }, [])

  return (
    <div style={{ minHeight: '100vh', background: '#0d1117', color: '#e6edf3', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'Segoe UI, sans-serif' }}>
      {status === 'loading' && <div>처리 중...</div>}
      {status === 'success' && (
        <>
          <div style={{ fontSize: '3rem', marginBottom: 16 }}>✅</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: 8 }}>결제가 완료되었습니다</div>
          <div style={{ color: '#8b949e', marginBottom: 32 }}>크레딧 또는 플랜이 곧 반영됩니다.</div>
          <button onClick={onBack} style={{ padding: '10px 24px', background: '#1a7f37', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>홈으로 돌아가기</button>
        </>
      )}
      {status === 'fail' && (
        <>
          <div style={{ fontSize: '3rem', marginBottom: 16 }}>❌</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: 8 }}>결제가 취소되었습니다</div>
          <div style={{ color: '#8b949e', marginBottom: 32 }}>결제가 완료되지 않았습니다.</div>
          <button onClick={onBack} style={{ padding: '10px 24px', background: '#30363d', color: '#e6edf3', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>돌아가기</button>
        </>
      )}
    </div>
  )
}
