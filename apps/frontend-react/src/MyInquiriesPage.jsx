import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ChevronDown, ChevronUp, Mail, RefreshCw, Send } from 'lucide-react'
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

// 대시보드 집계 그룹 — 카드와 필터가 이 그룹 단위로 움직인다.
const STATUS_GROUPS = [
  { key: 'all', label: '전체', match: () => true },
  { key: 'draft', label: '초안', match: (s) => s === 'draft' },
  { key: 'in_review', label: '검토·승인', match: (s) => ['review_required', 'approved', 'queued'].includes(s) },
  { key: 'sent', label: '발송 완료', match: (s) => ['sent', 'delivered', 'no_response'].includes(s) },
  { key: 'replied', label: '회신', match: (s) => s === 'replied' },
  { key: 'problem', label: '실패·반려·반송', match: (s) => ['failed', 'rejected', 'bounced'].includes(s) },
]

const STATUS_COLOR = {
  draft: '#94a3b8',
  review_required: '#fbbf24',
  approved: '#34d399',
  queued: '#34d399',
  sent: '#60a5fa',
  delivered: '#60a5fa',
  replied: '#a78bfa',
  no_response: '#64748b',
  failed: '#f87171',
  rejected: '#f87171',
  bounced: '#f87171',
}

function formatTime(value) {
  if (!value) return ''
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString()
}

/**
 * 고객용 인콰이어리 관리 대시보드 — 상태별 집계, 필터, 초안·이력 열기, 초안 검토 요청.
 * (실발송은 관리자가 수행; 고객은 여기서 진행 상태와 결과를 추적한다.)
 */
export default function MyInquiriesPage({ onBack }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [openId, setOpenId] = useState(null)
  const [draftLang, setDraftLang] = useState('en')
  const [submittingId, setSubmittingId] = useState(null)
  const [actionError, setActionError] = useState('')

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

  const counts = useMemo(() => {
    const result = {}
    for (const group of STATUS_GROUPS) {
      result[group.key] = items.filter((row) => group.match(row.status)).length
    }
    return result
  }, [items])

  const visibleItems = useMemo(() => {
    const group = STATUS_GROUPS.find((g) => g.key === filter) || STATUS_GROUPS[0]
    return items.filter((row) => group.match(row.status))
  }, [items, filter])

  const submitForReview = async (inquiryId) => {
    setSubmittingId(inquiryId)
    setActionError('')
    try {
      await api.post(`/v1/inquiries/${inquiryId}/submit`)
      await load()
    } catch (err) {
      setActionError(err.response?.data?.detail || err.message || '검토 요청에 실패했습니다.')
    } finally {
      setSubmittingId(null)
    }
  }

  const toggleOpen = (inquiryId) => {
    setOpenId((prev) => (prev === inquiryId ? null : inquiryId))
  }

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
            <h1>내 인콰이어리 대시보드</h1>
          </div>
        </div>
        <div className="analysis-header-status">
          <Mail size={16} />
          <span>제출·검토·발송 결과 확인 (자동 메일 발송 아님)</span>
        </div>
      </header>

      <main className="analysis-layout" style={{ gridTemplateColumns: '1fr' }}>
        {/* 상태별 집계 카드 = 대시보드 요약. 클릭하면 해당 그룹으로 필터된다. */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: 10,
            marginBottom: 16,
          }}
        >
          {STATUS_GROUPS.map((group) => {
            const active = filter === group.key
            return (
              <button
                key={group.key}
                type="button"
                onClick={() => setFilter(group.key)}
                style={{
                  background: active ? 'rgba(59,130,246,0.18)' : 'rgba(15,23,42,0.65)',
                  border: `1px solid ${active ? '#3b82f6' : 'rgba(148,163,184,0.2)'}`,
                  borderRadius: 12,
                  padding: '12px 14px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  color: '#e2e8f0',
                }}
              >
                <div style={{ fontSize: 12, color: '#94a3b8' }}>{group.label}</div>
                <div style={{ fontSize: 24, fontWeight: 700 }}>{counts[group.key] ?? 0}</div>
              </button>
            )
          })}
        </div>

        <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
          <button type="button" className="ui-button ui-button--ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} />
            {loading ? '불러오는 중…' : '새로고침'}
          </button>
          <span style={{ fontSize: 13, color: '#94a3b8' }}>
            {visibleItems.length}건 표시 / 전체 {items.length}건
          </span>
        </div>

        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
        {actionError ? <p style={{ color: '#f87171' }}>{actionError}</p> : null}

        {!loading && visibleItems.length === 0 && !error ? (
          <p style={{ color: '#94a3b8', padding: 32, textAlign: 'center' }}>
            {items.length === 0
              ? '제출한 인콰이어리가 없습니다. 분석·수출 플로우에서 「발송 검토 요청」을 하면 여기에 표시됩니다.'
              : '이 상태에 해당하는 인콰이어리가 없습니다.'}
          </p>
        ) : null}

        <div style={{ display: 'grid', gap: 10 }}>
          {visibleItems.map((row) => {
            const opened = openId === row.inquiry_id
            const history = Array.isArray(row.history) ? row.history : []
            return (
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
                  <span style={{ fontSize: 12, color: STATUS_COLOR[row.status] || '#fbbf24', fontWeight: 600 }}>
                    {STATUS_LABEL[row.status] || row.status}
                  </span>
                </div>
                <p style={{ margin: '8px 0 0', fontSize: 13, color: '#cbd5e1' }}>
                  {[row.recipient_email, row.hs_code, row.country].filter(Boolean).join(' · ') || '부가 정보 없음'}
                </p>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: '#64748b' }}>
                  ID {String(row.inquiry_id || '').slice(0, 8)}…
                  {formatTime(row.updated_at || row.created_at)
                    ? ` · 최종 변경 ${formatTime(row.updated_at || row.created_at)}`
                    : ''}
                </p>
                {row.review_note || row.failure_reason ? (
                  <p style={{ margin: '6px 0 0', fontSize: 12, color: '#f87171' }}>
                    {row.review_note || row.failure_reason}
                  </p>
                ) : null}

                <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="ui-button ui-button--ghost"
                    onClick={() => toggleOpen(row.inquiry_id)}
                  >
                    {opened ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    {opened ? '닫기' : '상세 보기'}
                  </button>
                  {row.status === 'draft' ? (
                    <button
                      type="button"
                      className="ui-button ui-button--ghost"
                      disabled={submittingId === row.inquiry_id}
                      onClick={() => submitForReview(row.inquiry_id)}
                    >
                      <Send size={14} />
                      {submittingId === row.inquiry_id ? '요청 중…' : '발송 검토 요청'}
                    </button>
                  ) : null}
                </div>

                {opened ? (
                  <div
                    style={{
                      marginTop: 12,
                      borderTop: '1px solid rgba(148,163,184,0.15)',
                      paddingTop: 12,
                    }}
                  >
                    <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                      <button
                        type="button"
                        className="ui-button ui-button--ghost"
                        style={draftLang === 'en' ? { borderColor: '#3b82f6' } : undefined}
                        onClick={() => setDraftLang('en')}
                      >
                        영문 초안
                      </button>
                      <button
                        type="button"
                        className="ui-button ui-button--ghost"
                        style={draftLang === 'ko' ? { borderColor: '#3b82f6' } : undefined}
                        onClick={() => setDraftLang('ko')}
                      >
                        한글 초안
                      </button>
                    </div>
                    <pre
                      style={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        background: 'rgba(2,6,23,0.6)',
                        borderRadius: 8,
                        padding: 12,
                        fontSize: 13,
                        color: '#e2e8f0',
                        margin: 0,
                      }}
                    >
                      {(draftLang === 'en' ? row.draft_en : row.draft_ko) || '저장된 초안이 없습니다.'}
                    </pre>

                    {history.length > 0 ? (
                      <div style={{ marginTop: 12 }}>
                        <p style={{ margin: '0 0 6px', fontSize: 12, color: '#94a3b8' }}>처리 이력</p>
                        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: '#cbd5e1' }}>
                          {history.map((h, idx) => (
                            <li key={`${h.at}-${idx}`}>
                              {STATUS_LABEL[h.status] || h.status}
                              {formatTime(h.at) ? ` — ${formatTime(h.at)}` : ''}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </article>
            )
          })}
        </div>
      </main>
    </div>
  )
}
