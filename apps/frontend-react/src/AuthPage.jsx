import { useState } from 'react'
import api from './lib/api'

const inp = {
  width: '100%',
  background: '#0d1117',
  border: '1px solid #30363d',
  borderRadius: 6,
  padding: '8px 12px',
  color: '#e6edf3',
  boxSizing: 'border-box',
  fontSize: 14,
}

export default function AuthPage({ onSuccess }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        const { data } = await api.post('/v1/auth/login', { email, password })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
      } else {
        const { data } = await api.post('/v1/auth/register', { email, password })
        localStorage.setItem('access_token', data.token)
      }
      onSuccess()
    } catch (err) {
      const detail = err.response?.data?.detail
      const msg = {
        email_already_exists: '이미 가입된 이메일입니다.',
        invalid_credentials: '이메일 또는 비밀번호가 틀립니다.',
        account_locked: '로그인 시도 초과. 15분 후 재시도하세요.',
      }[detail] || '오류가 발생했습니다.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0d1117' }}>
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 12, padding: 32, width: 360 }}>
        <h2 style={{ color: '#e6edf3', marginBottom: 24, fontSize: 18 }}>
          {mode === 'login' ? '로그인' : '회원가입'}
        </h2>
        <form onSubmit={submit}>
          <div style={{ marginBottom: 14 }}>
            <label style={{ color: '#8b949e', fontSize: 13, display: 'block', marginBottom: 5 }}>이메일</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required style={inp} />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label style={{ color: '#8b949e', fontSize: 13, display: 'block', marginBottom: 5 }}>비밀번호</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} style={inp} />
          </div>
          {error && <p style={{ color: '#f85149', fontSize: 13, marginBottom: 14 }}>{error}</p>}
          <button
            type="submit"
            disabled={loading}
            style={{ width: '100%', background: '#238636', border: 'none', borderRadius: 6, padding: '10px 0', color: '#fff', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1, fontSize: 14 }}
          >
            {loading ? '처리 중...' : mode === 'login' ? '로그인' : '회원가입'}
          </button>
        </form>
        <p style={{ color: '#8b949e', textAlign: 'center', marginTop: 20, fontSize: 13 }}>
          {mode === 'login' ? '계정이 없으신가요? ' : '이미 계정이 있으신가요? '}
          <button
            onClick={() => { setMode(m => m === 'login' ? 'register' : 'login'); setError('') }}
            style={{ background: 'none', border: 'none', color: '#58a6ff', cursor: 'pointer', fontSize: 13, padding: 0 }}
          >
            {mode === 'login' ? '회원가입' : '로그인'}
          </button>
        </p>
      </div>
    </div>
  )
}
