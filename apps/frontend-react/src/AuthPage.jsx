import { useState, useEffect } from 'react'
import api from './lib/api'

// duringPayment: 결제 콜백에서 세션이 끊긴 경우. 돈이 이미 나간 직후라
// 일반 만료 문구는 결제가 날아간 것으로 읽힌다. 실제로는 URL 의 paymentKey 가
// 보존돼 재로그인 후 승인이 이어지므로(App.jsx onLogout), 그 사실을 알린다.
export default function AuthPage({ onSuccess, sessionExpired = false, duringPayment = false }) {
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
    // 통계는 로그인 화면 장식용 — 로그인 속도를 막지 않게 타임아웃을 짧게 두고
    // 실패해도 조용히 넘긴다. 백엔드 유휴 시 첫 요청이 느리므로 10초 상한.
    let alive = true
    api.get('/v1/demo/summary', { timeout: 10_000 })
      .then((r) => {
        if (alive) setDataStats({ total: r.data?.total, countryCount: r.data?.countryCount })
      })
      .catch(() => {
        if (alive) setDataStats(null)
      })
    return () => { alive = false }
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
        /* 시안 A: 포트 배경 + 밝은 폼 */
        .auth-root {
          --auth-blue: #1463f3;
          --auth-blue-dark: #0b4ed1;
          --auth-navy: #07152f;
          --auth-muted: #59677d;
          min-height: 100vh;
          background: #f7fbff;
          display: grid;
          grid-template-columns: 1fr min(440px, 42vw);
          position: relative;
          overflow: hidden;
        }
        @media (max-width: 700px) {
          .auth-root { grid-template-columns: 1fr; }
          .auth-left { min-height: 180px; padding: 28px 24px; }
          .auth-hero-title { font-size: 2rem !important; }
          .auth-stats { display: none !important; }
          .auth-right { padding: 28px 20px 40px; }
        }

        /* LEFT: 시안 A 포트 배경 */
        .auth-left {
          position: relative;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          padding: 40px 48px;
          border-right: 1px solid #dbe3ef;
          background:
            linear-gradient(120deg, rgba(7, 21, 47, 0.72) 0%, rgba(7, 21, 47, 0.45) 55%, rgba(20, 99, 243, 0.28) 100%),
            url("/hero-port.png") center / cover no-repeat;
          overflow: hidden;
        }
        .auth-brand { position: relative; z-index: 1; }
        .auth-brand-name {
          font-size: 1.55rem;
          font-weight: 800;
          letter-spacing: -0.04em;
          color: #ffffff;
        }
        .auth-brand-sub {
          font-size: 0.72rem;
          letter-spacing: 0.08em;
          color: rgba(255,255,255,0.72);
          text-transform: uppercase;
          margin-top: 6px;
        }
        .auth-hero { position: relative; z-index: 1; }
        .auth-hero-title {
          font-size: clamp(2.4rem, 4.5vw, 4.2rem);
          font-weight: 850;
          letter-spacing: -0.045em;
          line-height: 1.05;
          color: #ffffff;
          margin-bottom: 16px;
          word-break: keep-all;
        }
        .auth-hero-title em {
          color: #9ec0ff;
          font-style: normal;
          display: block;
        }
        .auth-hero-desc {
          font-size: 0.95rem;
          color: rgba(255,255,255,0.82);
          font-weight: 450;
          line-height: 1.7;
          max-width: 360px;
          word-break: keep-all;
        }
        .auth-stats {
          position: relative;
          z-index: 1;
          display: flex;
          gap: 28px;
        }
        .auth-stat-val {
          font-size: 1.35rem;
          color: #ffffff;
          font-weight: 750;
        }
        .auth-stat-lbl {
          font-size: 0.72rem;
          letter-spacing: 0.02em;
          color: rgba(255,255,255,0.7);
          margin-top: 4px;
        }

        /* RIGHT: 랜딩과 같은 밝은 폼 */
        .auth-right {
          background: #ffffff;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: 48px 40px;
          position: relative;
        }
        .auth-mode-row {
          display: flex;
          gap: 0;
          margin-bottom: 28px;
          border-bottom: 1px solid #dbe3ef;
        }
        .auth-mode-btn {
          background: none;
          border: none;
          padding: 10px 0;
          margin-right: 24px;
          font-size: 0.92rem;
          font-weight: 700;
          cursor: pointer;
          color: var(--auth-muted);
          border-bottom: 2px solid transparent;
          margin-bottom: -1px;
          transition: color 0.2s, border-color 0.2s;
        }
        .auth-mode-btn.active { color: var(--auth-blue); border-bottom-color: var(--auth-blue); }

        .auth-demo {
          margin-bottom: 20px;
          padding: 12px 14px;
          border: 1px solid #dbe3ef;
          border-radius: 12px;
          background: #f2f7ff;
          color: var(--auth-navy);
          font-size: 0.82rem;
          line-height: 1.55;
        }
        .auth-demo strong { font-weight: 750; }
        .auth-demo-fill {
          display: inline-flex;
          margin-top: 8px;
          padding: 7px 12px;
          border: 0;
          border-radius: 10px;
          background: var(--auth-blue);
          color: #fff;
          font-size: 0.78rem;
          font-weight: 700;
          cursor: pointer;
        }
        .auth-demo-fill:hover { background: var(--auth-blue-dark); }

        .auth-form { display: flex; flex-direction: column; gap: 18px; }

        .auth-field { display: flex; flex-direction: column; gap: 6px; }
        .auth-label {
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: 0.02em;
          color: var(--auth-muted);
          transition: color 0.2s;
        }
        .auth-field:focus-within .auth-label { color: var(--auth-blue); }

        .auth-input {
          width: 100%;
          background: #ffffff;
          border: 1px solid #ccd7e6;
          border-radius: 12px;
          color: var(--auth-navy);
          padding: 12px 14px;
          font-size: 0.95rem;
          outline: none;
          transition: border-color 0.2s, box-shadow 0.2s;
          box-sizing: border-box;
        }
        .auth-input:focus {
          border-color: var(--auth-blue);
          box-shadow: 0 0 0 4px rgba(20, 99, 243, 0.12);
        }
        .auth-input::placeholder { color: #8fa0b8; }

        .auth-error {
          font-size: 0.82rem;
          color: #b91c1c;
          background: #fef2f2;
          border: 1px solid #fecaca;
          padding: 10px 12px;
          border-radius: 10px;
        }

        .auth-notice {
          font-size: 0.82rem;
          line-height: 1.55;
          color: #92400e;
          background: #fffbeb;
          border: 1px solid #fde68a;
          padding: 12px 14px;
          border-radius: 10px;
          margin-bottom: 20px;
        }

        .auth-submit {
          width: 100%;
          min-height: 48px;
          padding: 12px;
          background: var(--auth-blue);
          border: none;
          border-radius: 12px;
          color: #ffffff;
          cursor: pointer;
          font-size: 0.95rem;
          font-weight: 750;
          transition: background 0.2s, transform 0.15s;
        }
        .auth-submit:hover:not(:disabled) { background: var(--auth-blue-dark); transform: translateY(-1px); }
        .auth-submit:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }

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
            <div className="auth-brand-name">MarketGate</div>
            <div className="auth-brand-sub">Export Intelligence Platform</div>
          </div>
          <div className="auth-hero">
            <div className="auth-hero-title">
              해외 바이어를<br />
              <em>한 번에 찾으세요</em>
            </div>
            <p className="auth-hero-desc">
              HS 코드와 무역 데이터로 유망 국가와 바이어 후보를 바로 추천합니다.
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
                {duringPayment
                  ? '결제를 마치고 돌아오는 사이 로그인 세션이 만료되었습니다. 결제는 취소되지 않았습니다 — 다시 로그인하시면 결제 결과를 이어서 확인합니다.'
                  : '보안을 위해 로그인 세션이 만료되었습니다. 작업을 이어가려면 다시 로그인해 주세요.'}
              </div>
            )}
            <div className="auth-mode-row">
              <button
                type="button"
                className={`auth-mode-btn ${mode === 'login' ? 'active' : ''}`}
                onClick={() => { setMode('login'); setError('') }}
              >로그인</button>
              <button
                type="button"
                className={`auth-mode-btn ${mode === 'register' ? 'active' : ''}`}
                onClick={() => { setMode('register'); setError('') }}
              >회원가입</button>
            </div>

            {mode === 'login' && (
              <div className="auth-demo">
                <div><strong>테스트 계정</strong></div>
                <div>이메일: demo@marketgate.test</div>
                <div>비밀번호: MarketGateDemo2026!</div>
                <button
                  type="button"
                  className="auth-demo-fill"
                  onClick={() => {
                    setEmail('demo@marketgate.test')
                    setPassword('MarketGateDemo2026!')
                    setError('')
                  }}
                >
                  테스트 계정 입력
                </button>
              </div>
            )}

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

              {error && <div className="auth-error">{error}</div>}

              <button className="auth-submit" type="submit" disabled={loading}>
                {loading ? '처리중...' : mode === 'login' ? '로그인' : '계정 생성'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  )
}
