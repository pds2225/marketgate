import { useState, useEffect } from 'react'
import api from './lib/api'

export default function AuthPage({ onSuccess, sessionExpired = false }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [visible, setVisible] = useState(false)
  const [focused, setFocused] = useState(null)
  // 실측 집계(/v1/demo/summary)만 표시 — 근거 없는 수치(50K+, 98% 등)는 사용하지 않는다
  const [dataStats, setDataStats] = useState(null)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 80)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    // 유휴 상태의 백엔드는 첫 요청에 40초 이상 걸린다(실측). 상한이 없으면 응답이
    // 끊겨도 '—' 가 영구히 남으므로, 상한을 두고 응답 없는 실패만 1회 재시도한다.
    let alive = true
    const fetchSummary = () => api.get('/v1/demo/summary', { timeout: 90_000 })
    fetchSummary()
      .catch((err) => (err?.response ? Promise.reject(err) : fetchSummary()))
      .then((r) => {
        if (alive) setDataStats({ total: r.data?.total, countryCount: r.data?.countryCount })
      })
      .catch(() => {
        if (alive) setDataStats(null)
      })
    return () => {
      alive = false
    }
  }, [])

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
        localStorage.setItem('access_token', data.access_token || data.token)
        if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
      }
      onSuccess()
    } catch (err) {
      let msg
      if (!err.response) {
        // 서버 무응답 — 네트워크 끊김·서버 다운·CORS. 비번이 틀린 게 아님을 분명히 안내.
        msg = '서버에 연결하지 못했습니다. 인터넷 연결을 확인하고 잠시 후 다시 시도해 주세요.'
      } else {
        const detail = err.response?.data?.detail
        msg = {
          email_already_exists: '이미 가입된 이메일입니다.',
          invalid_credentials: '이메일 또는 비밀번호가 틀립니다.',
          account_locked: '로그인 시도 초과. 15분 후 재시도하세요.',
        }[detail] || (typeof detail === 'string' && detail) || '오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'
      }
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

        /* 색상은 랜딩(App.css --landing-*)과 동일한 팔레트를 쓴다.
           blue #1463f3 / blue-dark #0b4ed1 / navy #07152f / muted #59677d
           line #dbe3ef / pale #f2f7ff */
        .auth-root {
          min-height: 100vh;
          background: #ffffff;
          display: grid;
          grid-template-columns: 1fr 420px;
          position: relative;
          overflow: hidden;
        }
        @media (max-width: 700px) {
          .auth-root { grid-template-columns: 1fr; }
          .auth-left { display: none !important; }
          .auth-right { padding: 32px 20px; }
        }

        /* LEFT PANEL */
        .auth-left {
          position: relative;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          padding: 40px 48px;
          border-right: 1px solid #dbe3ef;
          background:
            radial-gradient(ellipse 70% 50% at 30% 30%, rgba(20,99,243,0.08) 0%, transparent 60%),
            #f2f7ff;
          overflow: hidden;
        }
        .auth-left::after {
          content: '';
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(20,99,243,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(20,99,243,0.05) 1px, transparent 1px);
          background-size: 48px 48px;
          pointer-events: none;
        }
        .auth-brand {
          position: relative;
          z-index: 1;
        }
        .auth-brand-name {
          font-family: 'Bebas Neue', sans-serif;
          font-size: 1.5rem;
          letter-spacing: 0.12em;
          color: #1463f3;
        }
        .auth-brand-sub {
          font-family: 'DM Mono', monospace;
          font-size: 0.6rem;
          letter-spacing: 0.15em;
          color: #59677d;
          text-transform: uppercase;
          margin-top: 4px;
        }
        .auth-hero {
          position: relative;
          z-index: 1;
        }
        .auth-hero-title {
          font-family: 'Bebas Neue', sans-serif;
          font-size: clamp(3rem, 5vw, 5.5rem);
          line-height: 0.9;
          color: #07152f;
          margin-bottom: 20px;
        }
        .auth-hero-title em {
          color: #1463f3;
          font-style: normal;
          display: block;
        }
        .auth-hero-desc {
          font-size: 0.82rem;
          color: #59677d;
          font-weight: 300;
          line-height: 1.8;
          max-width: 320px;
        }
        .auth-stats {
          position: relative;
          z-index: 1;
          display: flex;
          gap: 32px;
        }
        .auth-stat-val {
          font-family: 'DM Mono', monospace;
          font-size: 1.4rem;
          color: #1463f3;
          font-weight: 500;
        }
        .auth-stat-lbl {
          font-family: 'DM Mono', monospace;
          font-size: 0.6rem;
          letter-spacing: 0.1em;
          color: #59677d;
          text-transform: uppercase;
          margin-top: 2px;
        }

        /* RIGHT PANEL */
        .auth-right {
          background: #ffffff;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: 48px 44px;
          position: relative;
        }
        .auth-mode-row {
          display: flex;
          gap: 0;
          margin-bottom: 40px;
          border-bottom: 1px solid #dbe3ef;
        }
        .auth-mode-btn {
          background: none;
          border: none;
          padding: 10px 0;
          margin-right: 24px;
          font-family: 'DM Mono', monospace;
          font-size: 0.68rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          cursor: pointer;
          color: #59677d;
          border-bottom: 2px solid transparent;
          margin-bottom: -1px;
          transition: color 0.2s, border-color 0.2s;
        }
        .auth-mode-btn.active { color: #1463f3; border-bottom-color: #1463f3; }

        .auth-form { display: flex; flex-direction: column; gap: 20px; }

        .auth-field { display: flex; flex-direction: column; gap: 6px; }
        .auth-label {
          font-family: 'DM Mono', monospace;
          font-size: 0.62rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: #59677d;
          transition: color 0.2s;
        }
        .auth-field:focus-within .auth-label { color: #1463f3; }

        .auth-input {
          width: 100%;
          background: #ffffff;
          border: 1px solid #dbe3ef;
          border-radius: 3px;
          color: #07152f;
          padding: 12px 14px;
          font-family: 'DM Mono', monospace;
          font-size: 0.82rem;
          outline: none;
          transition: border-color 0.2s, background 0.2s;
          box-sizing: border-box;
        }
        .auth-input:focus {
          border-color: #1463f3;
          background: #f2f7ff;
        }
        .auth-input::placeholder { color: #8fa0b8; }

        .auth-error {
          font-family: 'DM Mono', monospace;
          font-size: 0.68rem;
          color: #b91c1c;
          background: #fef2f2;
          border: 1px solid #fecaca;
          padding: 10px 12px;
          border-radius: 3px;
          letter-spacing: 0.04em;
        }

        .auth-notice {
          font-family: 'DM Mono', monospace;
          font-size: 0.68rem;
          line-height: 1.6;
          color: #0b4ed1;
          background: #f2f7ff;
          border: 1px solid #bfd6ff;
          padding: 12px 14px;
          border-radius: 3px;
          letter-spacing: 0.03em;
          margin-bottom: 24px;
        }

        .auth-submit {
          width: 100%;
          padding: 13px;
          background: #1463f3;
          border: none;
          border-radius: 3px;
          color: #ffffff;
          cursor: pointer;
          font-family: 'DM Mono', monospace;
          font-size: 0.72rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          font-weight: 500;
          transition: opacity 0.2s, transform 0.15s;
          position: relative;
          overflow: hidden;
        }
        .auth-submit:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
        .auth-submit:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

        .auth-guest {
          width: 100%;
          padding: 12px;
          background: transparent;
          border: 1px solid #dbe3ef;
          border-radius: 3px;
          color: #59677d;
          cursor: pointer;
          font-family: 'DM Mono', monospace;
          font-size: 0.68rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          transition: border-color 0.2s, color 0.2s;
          margin-top: 4px;
        }
        .auth-guest:hover { border-color: #1463f3; color: #0b4ed1; }

        .auth-divider {
          display: flex;
          align-items: center;
          gap: 12px;
          color: #8fa0b8;
          font-family: 'DM Mono', monospace;
          font-size: 0.6rem;
          letter-spacing: 0.1em;
        }
        .auth-divider::before, .auth-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: #dbe3ef;
        }

        .auth-panel {
          opacity: 0;
          transform: translateX(16px);
          transition: opacity 0.5s ease, transform 0.5s ease;
        }
        .auth-panel.in { opacity: 1; transform: translateX(0); }
      `}</style>

      <div className="auth-root">
        {/* LEFT */}
        <div className="auth-left">
          <div className="auth-brand">
            <div className="auth-brand-name">MARKETGATE</div>
            <div className="auth-brand-sub">Export Intelligence Platform</div>
          </div>
          <div className="auth-hero">
            <div className="auth-hero-title">
              GLOBAL<br />
              BUYER<br />
              <em>MATCH.</em>
            </div>
            <p className="auth-hero-desc">
              AI 기반 수출 바이어 적합성 분석.<br />
              BEP 계산부터 컨택까지 하나의 플랫폼에서.
            </p>
          </div>
          <div className="auth-stats">
            <div>
              <div className="auth-stat-val">{dataStats?.countryCount != null ? dataStats.countryCount.toLocaleString() : '—'}</div>
              <div className="auth-stat-lbl">개국 데이터 (등록 기준)</div>
            </div>
            <div>
              <div className="auth-stat-val">{dataStats?.total != null ? dataStats.total.toLocaleString() : '—'}</div>
              <div className="auth-stat-lbl">바이어 후보 (등록 데이터 기준)</div>
            </div>
            <div>
              <div className="auth-stat-val">HS 330499</div>
              <div className="auth-stat-lbl">K-뷰티 파일럿 품목</div>
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="auth-right">
          <div className={`auth-panel ${visible ? 'in' : ''}`}>
            {sessionExpired && (
              <div className="auth-notice" role="status">
                보안을 위해 로그인 세션이 만료되었습니다. 작업을 이어가려면 다시 로그인해 주세요.
              </div>
            )}
            <div className="auth-mode-row">
              <button
                className={`auth-mode-btn ${mode === 'login' ? 'active' : ''}`}
                onClick={() => { setMode('login'); setError('') }}
              >로그인</button>
              <button
                className={`auth-mode-btn ${mode === 'register' ? 'active' : ''}`}
                onClick={() => { setMode('register'); setError('') }}
              >회원가입</button>
            </div>

            <form className="auth-form" onSubmit={submit}>
              <div className="auth-field">
                <label className="auth-label">이메일</label>
                <input
                  className="auth-input"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  required
                />
              </div>
              <div className="auth-field">
                <label className="auth-label">비밀번호</label>
                <input
                  className="auth-input"
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder={mode === 'register' ? '8자 이상' : '••••••••'}
                  required
                  minLength={8}
                />
              </div>

              {error && <div className="auth-error">ERR: {error}</div>}

              <button className="auth-submit" type="submit" disabled={loading}>
                {loading ? '처리중...' : mode === 'login' ? '로그인 →' : '계정 생성 →'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  )
}
