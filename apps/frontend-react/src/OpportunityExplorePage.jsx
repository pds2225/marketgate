import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Filter, Search } from 'lucide-react'
import api from './lib/api'

const CATEGORY_PRESETS = [
  { label: 'K-뷰티', hs: '3304' },
  { label: '건강식품', hs: '2106' },
  { label: 'K-패션', hs: '62' },
  { label: '반도체', hs: '8541' },
]

/**
 * 구매신호 전체 탐색 — HS 매칭 상위만이 아니라 보유 opportunity_item 목록·검색·필터.
 */
export default function OpportunityExplorePage({ onBack, preset }) {
  const [q, setQ] = useState('')
  const [country, setCountry] = useState('')
  const [hs, setHs] = useState(() => String(preset?.hsCode || '').replace(/\D/g, '').slice(0, 6))
  const [signalType, setSignalType] = useState('')
  const [source, setSource] = useState('')
  const [usableOnly, setUsableOnly] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 40

  const load = useCallback(async (nextOffset = 0, overrides = {}) => {
    const nextHs = overrides.hs !== undefined ? overrides.hs : hs
    const nextQ = overrides.q !== undefined ? overrides.q : q
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/v1/opportunities', {
        params: {
          q: String(nextQ || '').trim() || undefined,
          country: country || undefined,
          hs: String(nextHs || '').trim() || undefined,
          signal_type: signalType || undefined,
          source: source || undefined,
          usable_only: usableOnly || undefined,
          limit,
          offset: nextOffset,
        },
      })
      setData(res.data)
      setOffset(nextOffset)
    } catch (err) {
      setData(null)
      setError(err.response?.data?.detail || err.message || '목록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }, [q, country, hs, signalType, source, usableOnly])

  useEffect(() => {
    const code = String(preset?.hsCode || '').replace(/\D/g, '').slice(0, 6)
    if (code) setHs(code)
    load(0, code ? { hs: code } : {})
  }, [preset?.hsCode]) // eslint-disable-line react-hooks/exhaustive-deps

  const applyCategory = (code) => {
    setHs(code)
    load(0, { hs: code })
  }

  const facets = data?.facets || { countries: [], sources: [], signal_types: [] }
  const items = data?.items || []
  const total = data?.total ?? 0

  return (
    <div className="analysis-page" style={{ paddingTop: 64 }}>
      <header className="analysis-header">
        <div className="analysis-header-main">
          <button className="ui-button ui-button--ghost" onClick={onBack}>
            <ArrowLeft size={16} />
            첫 화면으로
          </button>
          <div>
            <p className="analysis-kicker">Purchase Signals</p>
            <h1>구매신호 전체 탐색</h1>
          </div>
        </div>
        <div className="analysis-header-status">
          <Filter size={16} />
          <span>보유 opportunity_item · HS 무관 목록·검색·필터 (합성 데이터 없음)</span>
        </div>
      </header>

      <main className="analysis-layout" style={{ gridTemplateColumns: '1fr' }}>
        <section className="analysis-input-card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
            {CATEGORY_PRESETS.map((c) => (
              <button
                key={c.hs}
                type="button"
                className="ui-button ui-button--ghost"
                style={{
                  borderColor: hs === c.hs || String(hs).startsWith(c.hs) ? 'rgba(245,158,11,0.5)' : undefined,
                  color: hs === c.hs || String(hs).startsWith(c.hs) ? '#f59e0b' : undefined,
                }}
                onClick={() => applyCategory(c.hs)}
              >
                {c.label} · {c.hs}
              </button>
            ))}
            <button type="button" className="ui-button ui-button--ghost" onClick={() => applyCategory('')}>
              전체
            </button>
          </div>
          <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
            <label className="analysis-field">
              <span>검색</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="제목·키워드·국가·HS"
                  onKeyDown={(e) => e.key === 'Enter' && load(0)}
                />
                <button type="button" className="ui-button ui-button--solid" onClick={() => load(0)} disabled={loading}>
                  <Search size={14} />
                </button>
              </div>
            </label>
            <label className="analysis-field">
              <span>국가</span>
              <select value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="">전체</option>
                {(facets.countries || []).map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
            <label className="analysis-field">
              <span>HS</span>
              <input value={hs} onChange={(e) => setHs(e.target.value)} placeholder="예: 3304" />
            </label>
            <label className="analysis-field">
              <span>신호 유형</span>
              <select value={signalType} onChange={(e) => setSignalType(e.target.value)}>
                <option value="">전체</option>
                {(facets.signal_types || []).map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="analysis-field">
              <span>소스</span>
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="">전체</option>
                {(facets.sources || []).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontSize: 13 }}>
            <input type="checkbox" checked={usableOnly} onChange={(e) => setUsableOnly(e.target.checked)} />
            사용 가능 신호만
          </label>
          <div style={{ marginTop: 12 }}>
            <button type="button" className="ui-button ui-button--solid" onClick={() => load(0)} disabled={loading}>
              {loading ? '불러오는 중…' : '필터 적용'}
            </button>
            <span style={{ marginLeft: 12, fontSize: 13, color: '#94a3b8' }}>
              {total.toLocaleString()}건
            </span>
          </div>
          {error ? <p style={{ color: '#f87171', marginTop: 10 }}>{error}</p> : null}
        </section>

        <section style={{ display: 'grid', gap: 10 }}>
          {items.map((row, idx) => (
            <article
              key={`${row.title}-${row.hs_code_norm}-${offset + idx}`}
              style={{
                background: 'rgba(15,23,42,0.65)',
                border: '1px solid rgba(148,163,184,0.2)',
                borderRadius: 12,
                padding: '14px 16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <strong style={{ fontSize: 15 }}>{row.title}</strong>
                <span style={{ fontSize: 12, color: '#94a3b8' }}>
                  {row.country_norm || '국가 미상'}
                  {row.hs_code_norm ? ` · HS ${row.hs_code_norm}` : ''}
                </span>
              </div>
              <p style={{ margin: '8px 0 0', fontSize: 13, color: '#cbd5e1' }}>
                {[row.signal_type, row.source_dataset, row.keywords_norm].filter(Boolean).join(' · ') || '부가 필드 없음'}
              </p>
              {row.valid_until ? (
                <p style={{ margin: '4px 0 0', fontSize: 12, color: '#78716c' }}>유효: {row.valid_until}</p>
              ) : null}
              <p style={{ margin: '6px 0 0', fontSize: 12, color: row.has_contact ? '#fbbf24' : '#64748b' }}>
                {row.has_contact
                  ? `연락처 보유${row.contact_email ? ` · ${row.contact_email}` : ''}${row.contact_name ? ` · ${row.contact_name}` : ''}`
                  : '연락처 없음 (수요 신호)'}
              </p>
            </article>
          ))}
          {!loading && items.length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: 40 }}>조건에 맞는 구매신호가 없습니다.</p>
          ) : null}
        </section>

        {total > limit ? (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 16 }}>
            <button
              type="button"
              className="ui-button ui-button--ghost"
              disabled={offset <= 0 || loading}
              onClick={() => load(Math.max(0, offset - limit))}
            >
              이전
            </button>
            <button
              type="button"
              className="ui-button ui-button--ghost"
              disabled={offset + limit >= total || loading}
              onClick={() => load(offset + limit)}
            >
              다음
            </button>
          </div>
        ) : null}
      </main>
    </div>
  )
}
