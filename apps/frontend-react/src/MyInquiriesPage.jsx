import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Mail, RefreshCw } from 'lucide-react'
import api from './lib/api'

const STATUS_LABEL = {
  draft: '초안',
  review_required: '검토 대기',
  approved: '승인됨',
  queued: '발송 큐',
  sent: '발송됨',
  failed: '발송 실패',
  rejected: '반려됨',
  delivered: '수신 확인',
  bounced: '반송',
  replied: '회신',
  no_response: '무응답',
}

/**
 * 고객용 인콰이어리 현황 — 제출 후 E2E 상태 확인 (실발송은 관리자).
 */
export default function MyInquiriesPage({ onBack }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/v1/inquiries')
      setItems(res.data?.items || [])
    } catch (err) {
      setItems([])
      setError(err.response?.data?.detail || err.message || '목록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="analysis-page" style={{ paddingTop: 64 }}>
      <header className="analysis-header">
        <div className="analysis-header-main">
          <button className="ui-button ui-button--ghost" onClick={onBack}>
            <ArrowLeft size={16} />
            첫 화면으로
          </button>
          <div>
            <p className="analysis-kicker">My Inquiries</p>
            <h1>내 인콰이어리</h1>
          </div>
        </div>
        <div className="analysis-header-status">
          <Mail size={16} />
          <span>제출·검토·발송 결과 확인 (자동 메일 발송 아님)</span>
        </div>
      </header>

      <main className="analysis-layout" style={{ gridTemplateColumns: '1fr' }}>
        <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
          <button type="button" className="ui-button ui-button--ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} />
            {loading ? '불러오는 중…' : '새로고침'}
          </button>
          <span style={{ fontSize: 13, color: '#94a3b8' }}>{items.length}건</span>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
        {!loading && items.length === 0 && !error ? (
          <p style={{ color: '#94a3b8', padding: 32, textAlign: 'center' }}>
            제출한 인콰이어리가 없습니다. 분석·수출 플로우에서 「발송 검토 요청」을 하면 여기에 표시됩니다.
          </p>
        ) : null}
        <div style={{ display: 'grid', gap: 10 }}>
          {items.map((row) => (
            <article
              key={row.inquiry_id}
              style={{
                background: 'rgba(15,23,42,0.65)',
                border: '1px solid rgba(148,163,184,0.2)',
                borderRadius: 12,
                padding: '14px 16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <strong>{row.buyer_name || '바이어'}</strong>
                <span style={{ fontSize: 12, color: '#fbbf24' }}>
                  {STATUS_LABEL[row.status] || row.status}
                </span>
              </div>
              <p style={{ margin: '8px 0 0', fontSize: 13, color: '#cbd5e1' }}>
                {[row.recipient_email, row.hs_code, row.country].filter(Boolean).join(' · ') || '부가 정보 없음'}
              </p>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#64748b' }}>
                ID {String(row.inquiry_id || '').slice(0, 8)}…
                {row.updated_at || row.created_at
                  ? ` · ${new Date(row.updated_at || row.created_at).toLocaleString()}`
                  : ''}
              </p>
              {row.reject_reason || row.failure_reason ? (
                <p style={{ margin: '6px 0 0', fontSize: 12, color: '#f87171' }}>
                  {row.reject_reason || row.failure_reason}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      </main>
    </div>
  )
}
