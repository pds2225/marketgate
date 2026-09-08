import { Component } from 'react'

/**
 * Top-level render-error guard. Without this, any uncaught error in the
 * component tree unmounts the whole app and leaves a blank white screen with
 * no way for the user to recover except a manual refresh they have to guess
 * at (docs/e2e-status-and-followups.md, 2026-09-04 follow-up).
 *
 * Deliberately dependency-free and minimal — this must never itself throw.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary] unhandled render error', error, info?.componentStack)
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          padding: '24px',
          textAlign: 'center',
          fontFamily: 'system-ui, sans-serif',
          color: '#1e293b',
          background: '#f8fafc',
        }}
      >
        <p style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>
          화면을 불러오는 중 오류가 발생했습니다
        </p>
        <p style={{ fontSize: '13px', color: '#64748b', margin: 0 }}>
          새로고침해도 계속되면 잠시 후 다시 시도해 주세요.
        </p>
        <button
          type="button"
          onClick={this.handleReload}
          style={{
            marginTop: '8px',
            padding: '8px 20px',
            borderRadius: '8px',
            border: 'none',
            background: '#2563eb',
            color: '#fff',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          새로고침
        </button>
      </div>
    )
  }
}
