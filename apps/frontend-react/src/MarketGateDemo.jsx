import { useEffect, useMemo, useState } from 'react'
import { ENDPOINTS } from './config'

/*
 * MarketGateDemo — 바이어 매칭 + 바이어 데이터 수집 (실데이터 기반, 로그인 불필요)
 * 데이터: GET /v1/demo/snapshot (공개·무인증) — buyer_candidate.csv 36,241건 실시간 집계
 *   응답: { summary:{total,countryCount,byCountry[],bySource[]}, buyers:[...] }
 *   연락처(이메일·전화)는 서버에서 마스킹된 형태로만 내려옴(평문 노출 없음).
 * 초점:
 *  (1) 바이어 매칭 — HS·국가·신뢰도 실시간 필터 + FitScore 정렬 + 바이어 상세 매칭 프로필
 *  (2) 바이어 데이터 수집 — 14종 소스·규모·수집 추이 현황 + 자동 필터링 파이프라인
 * 벤치마킹(deep-research): ITC EPI 3축 설명점수 · Alibaba 검증배지 · Volza 컨택 언락 · buyKOREA 수동매칭 대비 자동 FitScore
 */

const AMBER = '#f59e0b'
const UNLOCK_COST = 5

/* ── ITC EPI 스타일 설명가능 적합도: 수요 × 무역용이성 × 공급신뢰 ── */
function computeFit(buyer, countryRank, countryCount) {
  const demand = countryRank != null
    ? Math.round(60 + 40 * (1 - countryRank / Math.max(1, countryCount)))
    : 60
  const d = buyer.distanceKm || 9000
  const ease = Math.max(35, Math.min(98, Math.round(100 - (d / 16000) * 65)))
  const supply = buyer.trust === 'platinum' ? 95 : buyer.trust === 'gold' ? 82 : 66
  const score = Math.round(demand * 0.4 + ease * 0.25 + supply * 0.35)
  return { score, demand, ease, supply }
}

const TRUST = {
  platinum: { label: 'Platinum', bg: '#1e293b', fg: '#fff', desc: '공식출처·검증 연락처' },
  gold: { label: 'Gold', bg: '#fffbeb', fg: '#b45309', bd: '#fde68a', desc: '공식출처 확인' },
  silver: { label: 'Silver', bg: '#f1f5f9', fg: '#475569', bd: '#e2e8f0', desc: '민간/추정 데이터' },
}

/* 매칭 근거 생성 (실데이터 필드 기반) */
function matchReasons(b, fit, countryRank, countryInfo) {
  const reasons = []
  reasons.push({
    axis: '수요', color: '#2563eb',
    text: countryRank === 0
      ? `${b.country}는 수집 바이어 ${countryInfo ? countryInfo.count.toLocaleString() : ''}개로 최대 시장`
      : countryRank != null && countryRank < 3
        ? `${b.country}는 상위 ${countryRank + 1}위 수출 유망시장 (바이어 ${countryInfo ? countryInfo.count.toLocaleString() : ''}개)`
        : `${b.country} 시장 내 화장품 관심 바이어`,
  })
  reasons.push({
    axis: '무역용이성', color: '#059669',
    text: b.distanceKm
      ? `한국에서 ${b.distanceKm.toLocaleString()}km — ${b.distanceKm < 4000 ? '근거리 물류 이점' : '주요 항로 연결'}`
      : '물류 경로 분석 대상',
  })
  reasons.push({
    axis: '공급신뢰', color: AMBER,
    text: `${b.source} 출처 · ${b.trust === 'platinum' ? '연락처까지 검증됨' : b.trust === 'gold' ? '공식 데이터 확인' : '추정 데이터'}`,
  })
  return reasons
}

function Bar({ label, value, max, accent = '#2563eb', sub }) {
  return (
    <div className="mg-bar">
      <div className="mg-bar-top"><span className="mg-bar-label">{label}</span><span className="mg-bar-val">{value.toLocaleString()}{sub ? <em>{sub}</em> : null}</span></div>
      <div className="mg-bar-track"><div className="mg-bar-fill" style={{ width: `${Math.round(value / max * 100)}%`, background: accent }} /></div>
    </div>
  )
}

export default function MarketGateDemo() {
  const [summary, setSummary] = useState(null)
  const [buyers, setBuyers] = useState([])
  const [credits, setCredits] = useState(1000)
  const [unlocked, setUnlocked] = useState({})
  const [err, setErr] = useState(null)

  // 매칭 필터
  const [query, setQuery] = useState('')
  const [fCountry, setFCountry] = useState('all')
  const [fTrust, setFTrust] = useState('all')
  const [fContact, setFContact] = useState(false)
  const [selected, setSelected] = useState(null) // 상세 모달 대상

  useEffect(() => {
    fetch(ENDPOINTS.demoSnapshot)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(({ summary: s, buyers: b }) => { setSummary(s); setBuyers(Array.isArray(b) ? b : []) })
      .catch(e => setErr(String(e)))
  }, [])

  const countryRankMap = useMemo(() => {
    const m = {}
    if (summary) summary.byCountry.forEach((c, i) => { m[c.name] = i })
    return m
  }, [summary])
  const countryInfoMap = useMemo(() => {
    const m = {}
    if (summary) summary.byCountry.forEach(c => { m[c.name] = c })
    return m
  }, [summary])

  const enriched = useMemo(() => {
    if (!summary) return []
    return buyers.map(b => ({ ...b, fit: computeFit(b, countryRankMap[b.country], summary.countryCount) }))
      .sort((a, b) => b.fit.score - a.fit.score)
  }, [buyers, summary, countryRankMap])

  // 공유 딥링크: ?b=<id> 로 특정 바이어 상세 매칭 프로필을 바로 연다
  useEffect(() => {
    if (!enriched.length) return
    const id = new URLSearchParams(window.location.search).get('b')
    if (id) {
      const m = enriched.find(x => x.id === id)
      if (m) setSelected(m)
    }
  }, [enriched])

  // 필터 적용
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return enriched.filter(b => {
      if (fCountry !== 'all' && b.country !== fCountry) return false
      if (fTrust !== 'all' && b.trust !== fTrust) return false
      if (fContact && !b.hasContact) return false
      if (q && !(`${b.name} ${b.country} ${b.industry} ${b.iso3}`.toLowerCase().includes(q))) return false
      return true
    })
  }, [enriched, query, fCountry, fTrust, fContact])

  // 필터용 국가 옵션 (샘플에 등장하는 국가, 빈도순)
  const countryOptions = useMemo(() => {
    const c = {}
    enriched.forEach(b => { c[b.country] = (c[b.country] || 0) + 1 })
    return Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k]) => k)
  }, [enriched])

  const unlock = (id) => {
    if (unlocked[id] || credits < UNLOCK_COST) return
    setCredits(c => c - UNLOCK_COST); setUnlocked(u => ({ ...u, [id]: true }))
  }

  if (err) return <div style={{ padding: 40, color: '#b91c1c', fontFamily: 'sans-serif' }}>데이터 로드 실패: {err}</div>
  if (!summary) return <div style={{ padding: 40, fontFamily: 'sans-serif', color: '#64748b' }}>실데이터 불러오는 중…</div>

  const creditPct = Math.round((credits / 1000) * 100)
  const maxSource = summary.bySource[0].count
  const officialCount = summary.bySource.filter(s => s.official).length

  return (
    <div className="mg-root">
      <style>{STYLE}</style>

      <header className="mg-top">
        <div className="mg-brand">MARKETGATE</div>
        <nav className="mg-tabs">
          <button className="mg-tab active">바이어 매칭</button>
          <button className="mg-tab" onClick={() => { window.location.hash = 'simulation' }}>수익성 시뮬레이션</button>
        </nav>
        <div className="mg-top-right">
          <div className="mg-credit" title="크레딧 — 바이어 컨택 시 차감">
            <span className="mg-credit-num">{credits.toLocaleString()}C</span>
            <div className="mg-credit-track"><div className="mg-credit-fill" style={{ width: `${creditPct}%` }} /></div>
          </div>
          <span className="mg-navitem">요금제</span>
          <span className="mg-logout">로그아웃</span>
        </div>
      </header>

      {/* Hero + Search */}
      <div className="mg-hero">
        <div className="mg-hero-inner">
          <p className="mg-eyebrow">AI BUYER MATCHING</p>
          <h1 className="mg-h1">살 의향 있는 <span className="amber">해외 바이어</span>를, 알고리즘이 골라냅니다</h1>
          <p className="mg-hsub">KOTRA 수동매칭(5주·전환율 2%) 대신 — 14종 소스 <b>{summary.total.toLocaleString()}건</b>에서 FitScore로 자동 선별</p>
          <div className="mg-search">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
            <input className="mg-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="회사명·국가·품목으로 검색 (예: cosmetic, 인도)" />
            <span className="mg-hs-badge">HS 330499 화장품</span>
          </div>
        </div>
      </div>

      <div className="mg-body">
        {/* LEFT: 데이터 수집 현황 */}
        <div className="mg-col-left">
          <div className="mg-card mg-panel mg-collect">
            <h3 className="mg-h3">바이어 데이터 수집 현황</h3>
            <div className="mg-collect-stats">
              <div><div className="mg-cs-num">{summary.total.toLocaleString()}</div><div className="mg-cs-lbl">수집 바이어</div></div>
              <div><div className="mg-cs-num">{summary.countryCount}</div><div className="mg-cs-lbl">개국</div></div>
              <div><div className="mg-cs-num">{officialCount}</div><div className="mg-cs-lbl">공식 출처</div></div>
            </div>
          </div>

          <div className="mg-card mg-panel">
            <h3 className="mg-h3">데이터 출처 <span className="mg-h3-sub">14종 통합</span></h3>
            {summary.bySource.map(s => (
              <div key={s.name} className="mg-src">
                <span className={`mg-src-badge ${s.official ? 'off' : 'pri'}`}>{s.official ? '공식' : '민간'}</span>
                <span className="mg-src-name">{s.name}</span>
                <div className="mg-src-track"><div className="mg-src-fill" style={{ width: `${Math.round(s.count / maxSource * 100)}%` }} /></div>
                <span className="mg-src-num">{s.count.toLocaleString()}</span>
              </div>
            ))}
          </div>

          <div className="mg-card mg-panel">
            <h3 className="mg-h3">국가별 분포 <span className="mg-h3-sub">상위</span></h3>
            {summary.byCountry.slice(0, 8).map(c => (
              <Bar key={c.iso3 + c.name} label={`${c.name} (${c.iso3})`} value={c.count} max={summary.byCountry[0].count} accent="#2563eb" />
            ))}
          </div>

          <div className="mg-card mg-pipe">
            <div className="mg-pipe-h">⚙ 자동 수집 파이프라인</div>
            <p>신규 CSV 업로드 → 컬럼 통일 → 화장품 키워드·HS 필터 → 중복 제거 → 통합. <b>KOTRA·관세청·NIPA·무역보험공사</b> 14종 소스 자동 정규화.</p>
          </div>
        </div>

        {/* RIGHT: 바이어 매칭 */}
        <div className="mg-col-right">
          {/* Filter bar */}
          <div className="mg-filterbar">
            <select className="mg-select" value={fCountry} onChange={e => setFCountry(e.target.value)}>
              <option value="all">전체 국가 ({countryOptions.length})</option>
              {countryOptions.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <select className="mg-select" value={fTrust} onChange={e => setFTrust(e.target.value)}>
              <option value="all">전체 신뢰도</option>
              <option value="platinum">Platinum</option>
              <option value="gold">Gold</option>
              <option value="silver">Silver</option>
            </select>
            <label className={`mg-toggle ${fContact ? 'on' : ''}`}>
              <input type="checkbox" checked={fContact} onChange={e => setFContact(e.target.checked)} />
              검증 연락처 보유
            </label>
            {(fCountry !== 'all' || fTrust !== 'all' || fContact || query) && (
              <button className="mg-reset" onClick={() => { setFCountry('all'); setFTrust('all'); setFContact(false); setQuery('') }}>필터 초기화</button>
            )}
            <span className="mg-result-cnt"><b>{filtered.length}</b>건 매칭</span>
          </div>

          <div className="mg-list-sub">FitScore = <b style={{ color: '#2563eb' }}>수요</b> × <b style={{ color: '#059669' }}>무역용이성</b> × <b style={{ color: AMBER }}>공급신뢰</b> · 적합도순 정렬</div>

          {filtered.length === 0 && <div className="mg-empty">조건에 맞는 바이어가 없습니다. 필터를 완화해 보세요.</div>}

          {filtered.slice(0, 40).map((b, i) => {
            const t = TRUST[b.trust]
            return (
              <button key={b.id} className={`mg-card mg-buyer ${i === 0 ? 'top' : ''}`} onClick={() => setSelected(b)}>
                {i === 0 && <span className="mg-rank">BEST MATCH</span>}
                <div className="mg-logo">{b.iso3 || '🌐'}</div>
                <div className="mg-buyer-id">
                  <div className="mg-name-row">
                    <span className="mg-bname">{b.name}</span>
                    <span className="mg-trust" style={{ background: t.bg, color: t.fg, border: t.bd ? `1px solid ${t.bd}` : 'none' }}>{t.label}</span>
                    {b.emailEstimated && <span className="mg-est">이메일 추정</span>}
                  </div>
                  <div className="mg-meta">
                    <span className="mg-meta-chip">{b.country}</span>
                    <span>{b.industry}</span>
                    {b.distanceKm ? <span className="mg-dist">{b.distanceKm.toLocaleString()}km</span> : null}
                    <span className="mg-src-tag">{b.source}</span>
                  </div>
                </div>
                <div className="mg-score-box">
                  <div className="mg-score">{b.fit.score}</div>
                  <div className="mg-score-lbl">적합도 ▸</div>
                </div>
              </button>
            )
          })}
          {filtered.length > 40 && <p className="mg-more">+ {filtered.length - 40}건 더 — 필터로 좁혀보세요</p>}
          <p className="mg-foot">실수집 {summary.total.toLocaleString()}건 중 표본 {buyers.length}건 표시 · 연락처는 개인정보 보호를 위해 마스킹 · © 2026 MarketGate</p>
        </div>
      </div>

      {/* 바이어 상세 매칭 프로필 모달 */}
      {selected && (() => {
        const b = selected
        const rank = countryRankMap[b.country]
        const reasons = matchReasons(b, b.fit, rank, countryInfoMap[b.country])
        const t = TRUST[b.trust]
        const isOpen = !!unlocked[b.id]
        return (
          <div className="mg-modal-bg" onClick={() => setSelected(null)}>
            <div className="mg-modal" onClick={e => e.stopPropagation()}>
              <button className="mg-modal-x" onClick={() => setSelected(null)}>✕</button>
              <div className="mg-modal-head">
                <div className="mg-logo lg">{b.iso3 || '🌐'}</div>
                <div>
                  <div className="mg-name-row">
                    <span className="mg-modal-name">{b.name}</span>
                    <span className="mg-trust" style={{ background: t.bg, color: t.fg, border: t.bd ? `1px solid ${t.bd}` : 'none' }}>{t.label}</span>
                  </div>
                  <div className="mg-modal-meta">{b.country} · {b.industry} {b.hs ? `· HS ${b.hs}` : ''}</div>
                </div>
                <div className="mg-modal-score"><div className="mg-modal-score-v">{b.fit.score}</div><div className="mg-modal-score-l">적합도</div></div>
              </div>

              <div className="mg-modal-sec">
                <h4 className="mg-modal-h4">매칭 근거 <span>왜 이 바이어인가</span></h4>
                {reasons.map(r => (
                  <div key={r.axis} className="mg-reason">
                    <span className="mg-reason-axis" style={{ color: r.color, borderColor: r.color }}>{r.axis}</span>
                    <span className="mg-reason-text">{r.text}</span>
                  </div>
                ))}
                <div className="mg-fitbars">
                  {[{ k: '수요', v: b.fit.demand, c: '#2563eb' }, { k: '무역용이성', v: b.fit.ease, c: '#059669' }, { k: '공급신뢰', v: b.fit.supply, c: AMBER }].map(x => (
                    <div key={x.k} className="mg-fitrow">
                      <span className="mg-fitk">{x.k}</span>
                      <div className="mg-fittrack"><div className="mg-fitfill" style={{ width: `${x.v}%`, background: x.c }} /></div>
                      <span className="mg-fitv">{x.v}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mg-modal-sec">
                <h4 className="mg-modal-h4">데이터 출처 추적</h4>
                <div className="mg-trace">
                  <span className="mg-trace-chip">{b.source}</span>
                  <span className="mg-trace-chip">{b.iso3}</span>
                  {b.hs ? <span className="mg-trace-chip">HS {b.hs}</span> : null}
                  <span className={`mg-trace-chip ${b.emailEstimated ? 'warn' : 'ok'}`}>{b.emailEstimated ? '연락처 추정' : '연락처 검증'}</span>
                </div>
              </div>

              <div className="mg-modal-sec">
                <h4 className="mg-modal-h4">검증 연락처</h4>
                {isOpen ? (
                  <div className="mg-contact-open">
                    <div>✉ {b.emailMasked || '—'}</div>
                    <div>☎ {b.phoneMasked || '—'}</div>
                    {b.website && <div>🌐 {b.website}</div>}
                    <p className="mg-contact-note">※ 데모: 실연락처는 마스킹 표시 (실서비스는 원본 제공)</p>
                  </div>
                ) : (
                  <div className="mg-contact-locked">
                    <span>🔒 이메일 · 전화 · 웹사이트 — 잠김</span>
                    <button className="mg-unlock" disabled={credits < UNLOCK_COST} onClick={() => unlock(b.id)}>컨택 언락 · {UNLOCK_COST}C</button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}

const STYLE = `
.mg-root{font-family:'Pretendard','Malgun Gothic',sans-serif;background:#f8fafc;color:#1e293b;min-height:100vh;-webkit-font-smoothing:antialiased}
.mg-root *{box-sizing:border-box}
.mg-top{height:52px;background:#0c0a09;display:flex;align-items:center;justify-content:space-between;padding:0 24px;border-bottom:1px solid rgba(245,158,11,.12);position:sticky;top:0;z-index:40}
.mg-brand{font-family:'DM Mono',monospace;font-weight:700;letter-spacing:.14em;color:${AMBER};font-size:15px}
.mg-tabs{display:flex;gap:4px}
.mg-tab{background:none;border:none;color:#78716c;font-size:13px;padding:8px 14px;cursor:pointer;font-family:inherit;border-radius:7px;transition:.15s}
.mg-tab:hover{color:#e7e5e4}
.mg-tab.active{color:#0c0a09;background:${AMBER};font-weight:700}
.mg-top-right{display:flex;align-items:center;gap:10px}
.mg-credit{display:flex;flex-direction:column;gap:3px;min-width:120px}
.mg-credit-num{font-family:'DM Mono',monospace;color:${AMBER};font-size:12px;font-weight:600;text-align:right}
.mg-credit-track{height:4px;background:rgba(245,158,11,.18);border-radius:3px;overflow:hidden}
.mg-credit-fill{height:100%;background:${AMBER};border-radius:3px;transition:width .3s}
.mg-navitem{color:#78716c;font-size:12px;font-family:'DM Mono',monospace;letter-spacing:.05em}
.mg-logout{color:#a8a29e;font-size:12px;border:1px solid rgba(239,68,68,.22);border-radius:4px;padding:5px 10px;font-family:'DM Mono',monospace}
.mg-hero{background:radial-gradient(ellipse 75% 60% at 22% 0%,rgba(245,158,11,.09) 0%,transparent 55%),#0c0a09;padding:34px 24px 28px;border-bottom:1px solid rgba(245,158,11,.07)}
.mg-hero-inner{max-width:1180px;margin:0 auto}
.mg-eyebrow{font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.22em;color:${AMBER};margin:0 0 10px}
.mg-h1{font-size:28px;font-weight:800;line-height:1.25;margin:0;color:#fafaf9;letter-spacing:-.01em}
.mg-h1 .amber{color:${AMBER}}
.mg-hsub{margin:10px 0 18px;font-size:13.5px;color:#a8a29e}
.mg-hsub b{color:#fafaf9}
.mg-search{display:flex;align-items:center;gap:10px;background:#fff;border-radius:12px;padding:13px 16px;box-shadow:0 8px 24px rgba(0,0,0,.25);max-width:680px}
.mg-input{flex:1;border:none;outline:none;font-size:15px;color:#1e293b;font-family:inherit;background:transparent}
.mg-hs-badge{font-size:12px;color:#64748b;background:#f1f5f9;border-radius:6px;padding:5px 10px;white-space:nowrap}
.mg-body{max-width:1180px;margin:20px auto;padding:0 24px;display:grid;grid-template-columns:330px 1fr;gap:18px;align-items:start}
.mg-card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 1px 3px rgba(15,23,42,.05)}
.mg-panel{padding:16px 18px;margin-bottom:14px}
.mg-h3{font-size:13.5px;font-weight:800;color:#0f172a;margin:0 0 13px;display:flex;justify-content:space-between;align-items:baseline}
.mg-h3-sub{font-size:11px;color:#94a3b8;font-weight:500}
.mg-collect{background:linear-gradient(135deg,#0f172a,#1e293b);border:none}
.mg-collect .mg-h3{color:#fff}
.mg-collect-stats{display:flex;justify-content:space-between;text-align:center;gap:8px}
.mg-cs-num{font-size:22px;font-weight:800;color:${AMBER};font-family:'DM Sans',sans-serif;line-height:1}
.mg-cs-lbl{font-size:11px;color:#94a3b8;margin-top:5px}
.mg-src{display:flex;align-items:center;gap:8px;margin-bottom:9px}
.mg-src-badge{font-size:10px;font-weight:700;border-radius:4px;padding:2px 6px;flex-shrink:0}
.mg-src-badge.off{background:#dcfce7;color:#15803d}
.mg-src-badge.pri{background:#f1f5f9;color:#64748b}
.mg-src-name{font-size:11.5px;color:#334155;width:96px;flex-shrink:0}
.mg-src-track{flex:1;height:6px;background:#f1f5f9;border-radius:3px;overflow:hidden}
.mg-src-fill{height:100%;background:#0ea5e9;border-radius:3px}
.mg-src-num{font-size:11px;color:#64748b;width:46px;text-align:right;font-family:'DM Sans',sans-serif}
.mg-bar{margin-bottom:10px}
.mg-bar-top{display:flex;justify-content:space-between;margin-bottom:4px}
.mg-bar-label{font-size:12px;color:#475569}
.mg-bar-val{font-size:12px;font-weight:700;color:#0f172a;font-family:'DM Sans',sans-serif}
.mg-bar-track{height:6px;background:#f1f5f9;border-radius:4px;overflow:hidden}
.mg-bar-fill{height:100%;border-radius:4px;transition:width .5s}
.mg-pipe{padding:14px 16px;background:#fffbeb;border:1px solid #fde68a}
.mg-pipe-h{font-size:12.5px;font-weight:700;color:#b45309;margin-bottom:6px}
.mg-pipe p{font-size:11.5px;color:#92400e;line-height:1.6;margin:0}
.mg-pipe b{color:#b45309}
.mg-col-right{min-width:0}
.mg-filterbar{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:12px}
.mg-select{font-family:inherit;font-size:13px;color:#334155;background:#fff;border:1.5px solid #e2e8f0;border-radius:9px;padding:8px 11px;cursor:pointer;outline:none}
.mg-select:focus{border-color:${AMBER}}
.mg-toggle{display:flex;align-items:center;gap:7px;font-size:13px;color:#475569;background:#fff;border:1.5px solid #e2e8f0;border-radius:9px;padding:8px 12px;cursor:pointer}
.mg-toggle.on{border-color:#059669;background:#f0fdf4;color:#15803d;font-weight:600}
.mg-toggle input{accent-color:#059669;width:14px;height:14px}
.mg-reset{background:none;border:none;color:#94a3b8;font-size:12.5px;cursor:pointer;text-decoration:underline;font-family:inherit}
.mg-result-cnt{margin-left:auto;font-size:13px;color:#64748b}
.mg-result-cnt b{color:#2563eb;font-size:15px;font-weight:800}
.mg-list-sub{font-size:12px;color:#94a3b8;margin-bottom:12px}
.mg-list-sub b{font-weight:700}
.mg-empty{padding:40px;text-align:center;color:#94a3b8;font-size:14px;background:#fff;border:1px dashed #e2e8f0;border-radius:14px}
.mg-buyer{display:flex;align-items:center;gap:13px;width:100%;text-align:left;padding:14px 16px;margin-bottom:10px;position:relative;cursor:pointer;font-family:inherit;transition:border-color .12s,box-shadow .12s}
.mg-buyer:hover{border-color:#93c5fd;box-shadow:0 4px 14px rgba(37,99,235,.08)}
.mg-buyer.top{border-color:#bbf7d0;box-shadow:0 4px 16px rgba(5,150,105,.10)}
.mg-rank{position:absolute;top:-9px;left:14px;background:${AMBER};color:#3b2606;font-family:'DM Mono',monospace;font-size:10px;font-weight:700;border-radius:6px;padding:3px 9px;letter-spacing:.05em;box-shadow:0 2px 6px rgba(245,158,11,.35)}
.mg-logo{width:44px;height:44px;border-radius:10px;background:#0f172a;color:#fff;display:flex;align-items:center;justify-content:center;font-family:'DM Mono',monospace;font-size:12px;font-weight:700;flex-shrink:0}
.mg-logo.lg{width:54px;height:54px;font-size:14px;border-radius:12px}
.mg-buyer-id{flex:1;min-width:0}
.mg-name-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.mg-bname{font-size:15px;font-weight:700;color:#0f172a}
.mg-trust{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:2px 9px;font-size:10.5px;font-weight:700}
.mg-est{font-size:10px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:999px;padding:1px 7px}
.mg-meta{display:flex;flex-wrap:wrap;gap:5px 12px;margin-top:6px;font-size:12px;color:#64748b;align-items:center}
.mg-meta-chip{font-weight:600;color:#334155}
.mg-dist{font-size:11.5px;color:#94a3b8}
.mg-src-tag{font-size:10.5px;color:#64748b;background:#f1f5f9;border-radius:5px;padding:1px 7px}
.mg-score-box{text-align:center;flex-shrink:0;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px;padding:6px 12px}
.mg-score{font-size:21px;font-weight:800;color:#047857;font-family:'DM Sans',sans-serif;line-height:1}
.mg-score-lbl{font-size:9.5px;color:#059669;margin-top:1px}
.mg-more{text-align:center;font-size:12.5px;color:#94a3b8;padding:8px}
.mg-foot{margin-top:14px;font-size:11px;color:#94a3b8;line-height:1.6}
/* modal */
.mg-modal-bg{position:fixed;inset:0;background:rgba(12,10,9,.55);backdrop-filter:blur(3px);z-index:100;display:flex;align-items:flex-start;justify-content:center;padding:48px 20px;overflow-y:auto}
.mg-modal{background:#fff;border-radius:18px;max-width:540px;width:100%;padding:26px;position:relative;box-shadow:0 30px 80px rgba(0,0,0,.4);animation:mgpop .2s ease}
@keyframes mgpop{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.mg-modal-x{position:absolute;top:16px;right:18px;background:none;border:none;font-size:18px;color:#94a3b8;cursor:pointer}
.mg-modal-head{display:flex;align-items:flex-start;gap:14px;padding-bottom:18px;border-bottom:1px solid #f1f5f9}
.mg-modal-name{font-size:18px;font-weight:800;color:#0f172a}
.mg-modal-meta{font-size:12.5px;color:#64748b;margin-top:5px}
.mg-modal-score{margin-left:auto;text-align:center;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:12px;padding:8px 14px;flex-shrink:0}
.mg-modal-score-v{font-size:26px;font-weight:800;color:#047857;font-family:'DM Sans',sans-serif;line-height:1}
.mg-modal-score-l{font-size:10px;color:#059669}
.mg-modal-sec{padding:16px 0;border-bottom:1px solid #f1f5f9}
.mg-modal-sec:last-child{border-bottom:none;padding-bottom:0}
.mg-modal-h4{font-size:13px;font-weight:800;color:#0f172a;margin:0 0 12px;display:flex;gap:8px;align-items:baseline}
.mg-modal-h4 span{font-size:11px;color:#94a3b8;font-weight:500}
.mg-reason{display:flex;gap:10px;align-items:flex-start;margin-bottom:9px}
.mg-reason-axis{font-size:10.5px;font-weight:700;border:1px solid;border-radius:6px;padding:2px 8px;flex-shrink:0;background:#fff}
.mg-reason-text{font-size:13px;color:#334155;line-height:1.5}
.mg-fitbars{margin-top:14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px}
.mg-fitrow{display:flex;align-items:center;gap:9px;margin-bottom:8px}
.mg-fitrow:last-child{margin-bottom:0}
.mg-fitk{font-size:11.5px;color:#475569;width:70px;flex-shrink:0}
.mg-fittrack{flex:1;height:7px;background:#e2e8f0;border-radius:4px;overflow:hidden}
.mg-fitfill{height:100%;border-radius:4px;transition:width .4s}
.mg-fitv{font-size:12px;font-weight:700;color:#0f172a;width:26px;text-align:right;font-family:'DM Sans',sans-serif}
.mg-trace{display:flex;flex-wrap:wrap;gap:7px}
.mg-trace-chip{font-size:11.5px;color:#475569;background:#f1f5f9;border-radius:7px;padding:5px 10px;font-family:'DM Mono',monospace}
.mg-trace-chip.ok{background:#dcfce7;color:#15803d}
.mg-trace-chip.warn{background:#fffbeb;color:#b45309}
.mg-contact-open{font-size:13.5px;color:#334155;line-height:1.9}
.mg-contact-note{font-size:11px;color:#94a3b8;margin-top:8px}
.mg-contact-locked{display:flex;align-items:center;justify-content:space-between;gap:12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;font-size:13px;color:#64748b}
.mg-unlock{background:${AMBER};color:#3b2606;border:none;border-radius:8px;padding:9px 15px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;white-space:nowrap}
.mg-unlock:disabled{opacity:.4;cursor:not-allowed}
@media(max-width:980px){.mg-body{grid-template-columns:1fr}}
`
