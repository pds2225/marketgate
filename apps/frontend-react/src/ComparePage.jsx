import { useMemo, useState } from 'react'
import { ArrowLeft, GitCompare } from 'lucide-react'
import api from './lib/api'

const STORAGE_KEY = 'mg_compare_snapshot_v1'

export function saveCompareSnapshot(snapshot) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
  } catch {
    /* ignore quota */
  }
}

function loadSnapshot() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

/**
 * 국가/바이어 비교 테이블 — 분석·검색 스냅샷 또는 즉시 predict.
 */
export default function ComparePage({ onBack }) {
  const [hsCode, setHsCode] = useState('330499')
  const [snapshot, setSnapshot] = useState(() => loadSnapshot())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const countries = useMemo(() => snapshot?.countries || [], [snapshot])
  const buyers = useMemo(() => snapshot?.buyers || [], [snapshot])

  const runPredict = async () => {
    const hs = String(hsCode || '').replace(/\D/g, '').slice(0, 6)
    if (hs.length < 4) {
      setError('HS 코드를 입력해 주세요.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.post('/v1/predict', {
        hs_code: hs,
        exporter_country_iso3: 'KOR',
        top_n: 8,
        year: 2023,
      })
      const results = res.data?.data?.results || []
      const buyerItems = res.data?.data?.buyers?.items || res.data?.data?.buyers?.buyers || []
      const next = {
        hs_code: hs,
        generated_at: new Date().toISOString(),
        countries: results.map((r, i) => ({
          rank: i + 1,
          iso3: r.country_iso3 || r.iso3,
          name: r.country_name || r.name || r.country_iso3,
          score: r.final_score ?? r.score,
          trade: r.score_components?.trade_volume_score,
          growth: r.score_components?.growth_score,
          gdp: r.score_components?.gdp_score,
          distance: r.score_components?.distance_score,
        })),
        buyers: (Array.isArray(buyerItems) ? buyerItems : []).slice(0, 20).map((b, i) => ({
          rank: i + 1,
          name: b.buyer_name || b.name,
          country: b.country_norm || b.source_target_country_name || '',
          score: b.final_score ?? b.score,
          has_contact: !!b.has_contact,
          source: b.source_dataset || '',
          hs: b.hs_code_norm || hs,
          matched_by: b.matched_by || '',
        })),
      }
      saveCompareSnapshot(next)
      setSnapshot(next)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '비교 데이터를 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
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
            <p className="analysis-kicker">Compare</p>
            <h1>국가 · 바이어 비교</h1>
          </div>
        </div>
        <div className="analysis-header-status">
          <GitCompare size={16} />
          <span>점수·연락처 보유 등 실측 가능한 열만 표시</span>
        </div>
      </header>

      <main className="analysis-layout" style={{ gridTemplateColumns: '1fr' }}>
        <section className="analysis-input-card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'end' }}>
            <label className="analysis-field" style={{ minWidth: 160 }}>
              <span>HS 코드</span>
              <input value={hsCode} onChange={(e) => setHsCode(e.target.value)} placeholder="330499" />
            </label>
            <button type="button" className="ui-button ui-button--solid" onClick={runPredict} disabled={loading}>
              {loading ? '분석 중…' : '비교표 생성'}
            </button>
            {snapshot?.hs_code ? (
              <span style={{ fontSize: 13, color: '#94a3b8' }}>
                현재: HS {snapshot.hs_code}
                {snapshot.generated_at ? ` · ${new Date(snapshot.generated_at).toLocaleString()}` : ''}
              </span>
            ) : null}
          </div>
          {error ? <p style={{ color: '#f87171', marginTop: 10 }}>{error}</p> : null}
          {!snapshot ? (
            <p style={{ marginTop: 12, fontSize: 13, color: '#94a3b8' }}>
              유망국 분석 후 자동으로 스냅샷이 저장되거나, 위에서 HS로 바로 생성할 수 있습니다.
            </p>
          ) : null}
        </section>

        <section className="analysis-input-card" style={{ marginBottom: 16, overflowX: 'auto' }}>
          <h2 style={{ fontSize: 16, margin: '0 0 12px' }}>국가 비교</h2>
          {countries.length === 0 ? (
            <p style={{ color: '#94a3b8', fontSize: 13 }}>국가 데이터 없음</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: '#94a3b8', borderBottom: '1px solid rgba(148,163,184,0.25)' }}>
                  <th style={{ padding: 8 }}>#</th>
                  <th style={{ padding: 8 }}>국가</th>
                  <th style={{ padding: 8 }}>종합</th>
                  <th style={{ padding: 8 }}>무역</th>
                  <th style={{ padding: 8 }}>성장</th>
                  <th style={{ padding: 8 }}>GDP</th>
                  <th style={{ padding: 8 }}>거리</th>
                </tr>
              </thead>
              <tbody>
                {countries.map((c) => (
                  <tr key={c.iso3 || c.rank} style={{ borderBottom: '1px solid rgba(148,163,184,0.12)' }}>
                    <td style={{ padding: 8 }}>{c.rank}</td>
                    <td style={{ padding: 8 }}>{c.name} {c.iso3 ? `(${c.iso3})` : ''}</td>
                    <td style={{ padding: 8 }}>{fmtScore(c.score)}</td>
                    <td style={{ padding: 8 }}>{fmtScore(c.trade)}</td>
                    <td style={{ padding: 8 }}>{fmtScore(c.growth)}</td>
                    <td style={{ padding: 8 }}>{fmtScore(c.gdp)}</td>
                    <td style={{ padding: 8 }}>{fmtScore(c.distance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="analysis-input-card" style={{ overflowX: 'auto' }}>
          <h2 style={{ fontSize: 16, margin: '0 0 12px' }}>바이어 비교</h2>
          {buyers.length === 0 ? (
            <p style={{ color: '#94a3b8', fontSize: 13 }}>바이어 데이터 없음</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: '#94a3b8', borderBottom: '1px solid rgba(148,163,184,0.25)' }}>
                  <th style={{ padding: 8 }}>#</th>
                  <th style={{ padding: 8 }}>바이어</th>
                  <th style={{ padding: 8 }}>국가</th>
                  <th style={{ padding: 8 }}>점수</th>
                  <th style={{ padding: 8 }}>연락처</th>
                  <th style={{ padding: 8 }}>출처</th>
                  <th style={{ padding: 8 }}>매칭</th>
                </tr>
              </thead>
              <tbody>
                {buyers.map((b) => (
                  <tr key={`${b.name}-${b.rank}`} style={{ borderBottom: '1px solid rgba(148,163,184,0.12)' }}>
                    <td style={{ padding: 8 }}>{b.rank}</td>
                    <td style={{ padding: 8 }}>{b.name || '—'}</td>
                    <td style={{ padding: 8 }}>{b.country || '—'}</td>
                    <td style={{ padding: 8 }}>{fmtScore(b.score)}</td>
                    <td style={{ padding: 8 }}>{b.has_contact ? '보유' : '없음'}</td>
                    <td style={{ padding: 8 }}>{b.source || '—'}</td>
                    <td style={{ padding: 8 }}>{b.matched_by || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>
    </div>
  )
}

function fmtScore(v) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  const n = Number(v)
  if (n <= 1 && n >= 0) return Math.round(n * 100)
  return Math.round(n)
}
