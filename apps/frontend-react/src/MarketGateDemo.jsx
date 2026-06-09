import { useEffect, useMemo, useState } from 'react'

/*
 * MarketGateDemo — 실데이터 기반 IR 데모 화면 (백엔드·로그인 불필요)
 * 데이터: /data/summary.json, /data/buyers.json  (buyer_candidate.csv 36,241건 ETL 결과)
 * 벤치마킹 반영(deep-research):
 *  1) 검증 배지 (Alibaba Business Verification / Trade Assurance)
 *  2) 크레딧 게이지 + 컨택 언락 차감 (Volza pay-per-record / Decision Maker Direct)
 *  3) 설명가능 적합도 = 수요×무역용이성×공급신뢰 (ITC Export Potential EPI)
 *  4) 무료→유료 경계 (Global Sources MATCH: 추천 무료, 컨택부터 과금)
 *  5) 출처 기반 신뢰도 (buyKOREA 수동매칭 대비 자동 FitScore — 핵심 차별점)
 */

const AMBER = '#f59e0b'

/* ── ITC EPI 스타일 설명가능 적합도: 수요 × 무역용이성 × 공급신뢰 ── */
function computeFit(buyer, countryRank, maxCount, countryCount) {
  // 수요(Demand): 해당국 바이어 밀집도(시장 수요 대용치) — 순위 높을수록 ↑
  const demand = countryRank != null
    ? Math.round(60 + 40 * (1 - countryRank / Math.max(1, countryCount)))
    : 60
  // 무역용이성(Ease): 한국과의 거리 — 가까울수록 ↑ (ITC 거리 요소)
  const d = buyer.distanceKm || 9000
  const ease = Math.max(35, Math.min(98, Math.round(100 - (d / 16000) * 65)))
  // 공급신뢰(Supply/Trust): 출처 공식성 + 검증 컨택
  const supply = buyer.trust === 'platinum' ? 95 : buyer.trust === 'gold' ? 82 : 66
  const score = Math.round(demand * 0.4 + ease * 0.25 + supply * 0.35)
  return { score, demand, ease, supply }
}

const TRUST = {
  platinum: { label: 'Platinum', bg: '#1e293b', fg: '#fff', desc: '공식출처·검증 연락처' },
  gold: { label: 'Gold', bg: '#fffbeb', fg: '#b45309', bd: '#fde68a', desc: '공식출처 확인' },
  silver: { label: 'Silver', bg: '#f1f5f9', fg: '#475569', bd: '#e2e8f0', desc: '민간/추정 데이터' },
}

function Bar({ label, value, max, sub, accent = '#2563eb' }) {
  const pct = Math.round((value / max) * 100)
  return (
    <div className="mg-bar">
      <div className="mg-bar-top">
        <span className="mg-bar-label">{label}</span>
        <span className="mg-bar-val">{value.toLocaleString()}{sub ? <em>{sub}</em> : null}</span>
      </div>
      <div className="mg-bar-track"><div className="mg-bar-fill" style={{ width: `${pct}%`, background: accent }} /></div>
    </div>
  )
}

function FitMini({ fit }) {
  const rows = [
    { k: '수요', v: fit.demand, c: '#2563eb' },
    { k: '무역용이성', v: fit.ease, c: '#059669' },
    { k: '공급신뢰', v: fit.supply, c: '#f59e0b' },
  ]
  return (
    <div className="mg-fitmini">
      {rows.map(r => (
        <div key={r.k} className="mg-fitrow">
          <span className="mg-fitk">{r.k}</span>
          <div className="mg-fittrack"><div className="mg-fitfill" style={{ width: `${r.v}%`, background: r.c }} /></div>
          <span className="mg-fitv">{r.v}</span>
        </div>
      ))}
    </div>
  )
}

export default function MarketGateDemo() {
  const [summary, setSummary] = useState(null)
  const [buyers, setBuyers] = useState([])
  const [credits, setCredits] = useState(1000)
  const [unlocked, setUnlocked] = useState({})
  const [query, setQuery] = useState('스킨케어')
  const [openFit, setOpenFit] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/data/summary.json').then(r => r.json()),
      fetch('/data/buyers.json').then(r => r.json()),
    ]).then(([s, b]) => { setSummary(s); setBuyers(b) })
      .catch(e => setErr(String(e)))
  }, [])

  const countryRankMap = useMemo(() => {
    const m = {}
    if (summary) summary.byCountry.forEach((c, i) => { m[c.name] = i })
    return m
  }, [summary])

  const maxCountry = summary ? summary.byCountry[0].count : 1
  const maxHs = summary ? summary.byHs[0].count : 1
  const maxSource = summary ? summary.bySource[0].count : 1

  const enriched = useMemo(() => {
    if (!summary) return []
    return buyers.map(b => ({
      ...b,
      fit: computeFit(b, countryRankMap[b.country], maxCountry, summary.countryCount),
    })).sort((a, b) => b.fit.score - a.fit.score)
  }, [buyers, summary, countryRankMap, maxCountry])

  const UNLOCK_COST = 5

  const unlock = (id) => {
    if (unlocked[id]) return
    if (credits < UNLOCK_COST) return
    setCredits(c => c - UNLOCK_COST)
    setUnlocked(u => ({ ...u, [id]: true }))
  }

  if (err) return <div style={{ padding: 40, color: '#b91c1c', fontFamily: 'sans-serif' }}>데이터 로드 실패: {err}<br />(개발 서버에서 /data/summary.json 접근 가능해야 합니다)</div>
  if (!summary) return <div style={{ padding: 40, fontFamily: 'sans-serif', color: '#64748b' }}>실데이터 불러오는 중…</div>

  const creditPct = Math.round((credits / 1000) * 100)

  return (
    <div className="mg-root">
      <style>{STYLE}</style>

      {/* Top bar */}
      <header className="mg-top">
        <div className="mg-brand">MARKETGATE</div>
        <nav className="mg-tabs">
          <button className="mg-tab active">바이어 검색</button>
          <button className="mg-tab" onClick={() => { window.location.hash = 'simulation' }}>수익성 시뮬레이션</button>
        </nav>
        <div className="mg-top-right">
          {/* Volza식 크레딧 게이지 */}
          <div className="mg-credit" title="크레딧 — 바이어 컨택 시 차감">
            <span className="mg-credit-num">{credits.toLocaleString()}C</span>
            <div className="mg-credit-track"><div className="mg-credit-fill" style={{ width: `${creditPct}%` }} /></div>
          </div>
          <span className="mg-navitem">요금제</span>
          <span className="mg-logout">로그아웃</span>
        </div>
      </header>

      {/* Search + HS auto-recognition (Panjiva) */}
      <div className="mg-searchwrap">
        <div className="mg-search">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
          <input className="mg-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="품목·키워드 입력 (예: 스킨케어, 홍삼, 비누)" />
          <span className="mg-hs-badge">HS 자동인식 · 330499</span>
        </div>
        <p className="mg-free-note">국가 추천 · 바이어 리스트는 <b>무료</b> · 검증 연락처 <b>컨택 시점부터 {UNLOCK_COST}크레딧</b> 차감</p>
      </div>

      {/* Dashboard strip — 실데이터 */}
      <section className="mg-stats">
        <div className="mg-stat"><div className="mg-stat-num">{summary.total.toLocaleString()}</div><div className="mg-stat-lbl">수집 바이어</div></div>
        <div className="mg-stat-div" />
        <div className="mg-stat"><div className="mg-stat-num">{summary.countryCount}</div><div className="mg-stat-lbl">개국</div></div>
        <div className="mg-stat-div" />
        <div className="mg-stat"><div className="mg-stat-num">{summary.bySource.filter(s => s.official).length}</div><div className="mg-stat-lbl">공식 데이터 출처</div></div>
        <div className="mg-stat-div" />
        <div className="mg-stat"><div className="mg-stat-num">{summary.contact.hasContact.toLocaleString()}</div><div className="mg-stat-lbl">연락처 보유 ({summary.contact.hasContactPct}%)</div></div>
        <div className="mg-stat-live"><span className="mg-dot" />KOTRA·NIPA·무역보험공사·GoBizKorea 실데이터</div>
      </section>

      <div className="mg-body">
        {/* Left: distributions */}
        <div className="mg-col-left">
          <div className="mg-card mg-panel">
            <h3 className="mg-h3">국가별 바이어 분포 <span className="mg-h3-sub">상위 12개국</span></h3>
            {summary.byCountry.map(c => (
              <Bar key={c.iso3 + c.name} label={`${c.name} (${c.iso3})`} value={c.count} max={maxCountry} accent="#2563eb" />
            ))}
          </div>

          <div className="mg-card mg-panel">
            <h3 className="mg-h3">품목(HS코드)별 분포 <span className="mg-h3-sub">화장품 중심</span></h3>
            {summary.byHs.map(h => (
              <Bar key={h.hs} label={`${h.label} · HS ${h.hs}`} value={h.count} max={maxHs} accent="#7c3aed" />
            ))}
          </div>

          <div className="mg-card mg-panel">
            <h3 className="mg-h3">데이터 출처 <span className="mg-h3-sub">공식 vs 민간</span></h3>
            {summary.bySource.map(s => (
              <div key={s.name} className="mg-src">
                <span className={`mg-src-badge ${s.official ? 'off' : 'pri'}`}>{s.official ? '공식' : '민간'}</span>
                <span className="mg-src-name">{s.name}</span>
                <div className="mg-src-track"><div className="mg-src-fill" style={{ width: `${Math.round(s.count / maxSource * 100)}%` }} /></div>
                <span className="mg-src-num">{s.count.toLocaleString()}</span>
              </div>
            ))}
            <p className="mg-diff">⚡ buyKOREA(KOTRA)는 직원 <b>수동 매칭</b> · 마켓게이트는 <b>자동 FitScore 필터링</b></p>
          </div>
        </div>

        {/* Right: buyer list */}
        <div className="mg-col-right">
          <div className="mg-list-head">
            <div>
              <h2 className="mg-h2">바이어 검색 결과 <span className="mg-cnt">{enriched.length}건</span></h2>
              <p className="mg-h2-sub">“{query}” · 적합도(FitScore) 순 · 실제 수집 데이터</p>
            </div>
            <span className="mg-engine">FitScore = 수요 × 무역용이성 × 공급신뢰</span>
          </div>

          {enriched.map((b, i) => {
            const t = TRUST[b.trust]
            const isOpen = !!unlocked[b.id]
            return (
              <div key={b.id} className={`mg-card mg-buyer ${i === 0 ? 'top' : ''}`}>
                {i === 0 && <span className="mg-rank">RANK 01</span>}
                <div className="mg-buyer-head">
                  <div className="mg-logo">{b.iso3 || '🌐'}</div>
                  <div className="mg-buyer-id">
                    <div className="mg-name-row">
                      <span className="mg-bname">{b.name}</span>
                      <span className="mg-trust" style={{ background: t.bg, color: t.fg, border: t.bd ? `1px solid ${t.bd}` : 'none' }} title={t.desc}>
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />{b.trust === 'platinum' && <path d="m9 12 2 2 4-4" />}</svg>
                        {t.label}
                      </span>
                      {b.emailEstimated && <span className="mg-est">이메일 추정</span>}
                    </div>
                    <div className="mg-meta">
                      <span className="mg-meta-chip">{b.flag !== '🌐' ? b.flag + ' ' : ''}{b.country}</span>
                      <span>{b.industry}</span>
                      {b.hs ? <span className="mg-hschip">HS {b.hs}</span> : null}
                      {b.distanceKm ? <span className="mg-dist">한국까지 {b.distanceKm.toLocaleString()}km</span> : null}
                    </div>
                  </div>
                  <div className="mg-score-box" onClick={() => setOpenFit(openFit === b.id ? null : b.id)}>
                    <div className="mg-score">{b.fit.score}</div>
                    <div className="mg-score-lbl">적합도</div>
                  </div>
                </div>

                {openFit === b.id && <FitMini fit={b.fit} />}

                <div className="mg-buyer-foot">
                  <div className="mg-contact">
                    {isOpen ? (
                      <>
                        <span className="mg-c-item">✉ {b.emailMasked || '—'}</span>
                        <span className="mg-c-item">☎ {b.phoneMasked || '—'}</span>
                        {b.website && <span className="mg-c-item">🌐 {b.website}</span>}
                        <span className="mg-c-note">※ 데모: 실연락처는 마스킹 표시</span>
                      </>
                    ) : (
                      <span className="mg-locked">🔒 검증 연락처 (이메일·전화·웹) — 잠김</span>
                    )}
                  </div>
                  {!isOpen ? (
                    <button className="mg-unlock" disabled={credits < UNLOCK_COST} onClick={() => unlock(b.id)}>
                      컨택 언락 · {UNLOCK_COST}C
                    </button>
                  ) : (
                    <span className="mg-unlocked">✓ 언락됨</span>
                  )}
                </div>
                {!b.fit && null}
                <button className="mg-why" onClick={() => setOpenFit(openFit === b.id ? null : b.id)}>
                  {openFit === b.id ? '적합도 근거 닫기 ▲' : '왜 이 점수? (수요·무역용이성·공급신뢰) ▼'}
                </button>
              </div>
            )
          })}
          <p className="mg-foot">데이터: KOTRA SNS·NIPA·무역보험공사·GoBizKorea·EC21·buyKOREA·ITC TradeMap 실수집 {summary.total.toLocaleString()}건 · 연락처는 개인정보 보호를 위해 마스킹 · © 2026 MarketGate</p>
        </div>
      </div>
    </div>
  )
}

const STYLE = `
.mg-root{font-family:'Pretendard','Malgun Gothic',sans-serif;background:#f8fafc;color:#1e293b;min-height:100vh;-webkit-font-smoothing:antialiased}
.mg-root *{box-sizing:border-box}
.mg-top{height:52px;background:#0c0a09;display:flex;align-items:center;justify-content:space-between;padding:0 24px;border-bottom:1px solid rgba(245,158,11,.12)}
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
.mg-searchwrap{max-width:1180px;margin:0 auto;padding:22px 24px 0}
.mg-search{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 16px;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.mg-input{flex:1;border:none;outline:none;font-size:15px;color:#1e293b;font-family:inherit;background:transparent}
.mg-hs-badge{font-size:12px;color:#64748b;background:#f1f5f9;border-radius:6px;padding:5px 10px;white-space:nowrap}
.mg-free-note{font-size:12.5px;color:#64748b;margin:9px 2px 0}
.mg-free-note b{color:#047857}
.mg-stats{max-width:1180px;margin:16px auto 0;padding:14px 24px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;display:flex;align-items:center;gap:18px}
.mg-stat{text-align:center}
.mg-stat-num{font-size:20px;font-weight:800;color:#0f172a;font-family:'DM Sans',sans-serif}
.mg-stat-lbl{font-size:11.5px;color:#64748b;margin-top:2px}
.mg-stat-div{width:1px;height:32px;background:#e2e8f0}
.mg-stat-live{margin-left:auto;display:flex;align-items:center;gap:7px;font-size:11.5px;color:#94a3b8}
.mg-dot{width:7px;height:7px;border-radius:50%;background:#34d399;box-shadow:0 0 0 3px rgba(52,211,153,.18)}
.mg-body{max-width:1180px;margin:18px auto;padding:0 24px;display:grid;grid-template-columns:380px 1fr;gap:18px;align-items:start}
.mg-card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 1px 3px rgba(15,23,42,.05)}
.mg-panel{padding:18px;margin-bottom:16px}
.mg-h3{font-size:14px;font-weight:700;color:#0f172a;margin:0 0 14px;display:flex;justify-content:space-between;align-items:baseline}
.mg-h3-sub{font-size:11px;color:#94a3b8;font-weight:500}
.mg-bar{margin-bottom:11px}
.mg-bar-top{display:flex;justify-content:space-between;margin-bottom:4px}
.mg-bar-label{font-size:12.5px;color:#475569}
.mg-bar-val{font-size:12.5px;font-weight:700;color:#0f172a;font-family:'DM Sans',sans-serif}
.mg-bar-val em{font-style:normal;color:#94a3b8;font-weight:500;margin-left:2px}
.mg-bar-track{height:7px;background:#f1f5f9;border-radius:4px;overflow:hidden}
.mg-bar-fill{height:100%;border-radius:4px;transition:width .5s}
.mg-src{display:flex;align-items:center;gap:8px;margin-bottom:9px}
.mg-src-badge{font-size:10px;font-weight:700;border-radius:4px;padding:2px 6px}
.mg-src-badge.off{background:#dcfce7;color:#15803d}
.mg-src-badge.pri{background:#f1f5f9;color:#64748b}
.mg-src-name{font-size:12px;color:#334155;width:108px;flex-shrink:0}
.mg-src-track{flex:1;height:6px;background:#f1f5f9;border-radius:3px;overflow:hidden}
.mg-src-fill{height:100%;background:#0ea5e9;border-radius:3px}
.mg-src-num{font-size:11.5px;color:#64748b;width:48px;text-align:right;font-family:'DM Sans',sans-serif}
.mg-diff{margin:12px 0 0;font-size:11.5px;color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:9px 11px;line-height:1.5}
.mg-diff b{color:#b45309}
.mg-list-head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px}
.mg-h2{font-size:17px;font-weight:800;color:#0f172a;margin:0}
.mg-cnt{font-size:13px;color:#2563eb;font-weight:700;margin-left:6px}
.mg-h2-sub{font-size:12.5px;color:#64748b;margin:4px 0 0}
.mg-engine{font-size:11px;color:#7c3aed;background:#f5f3ff;border:1px solid #ddd6fe;border-radius:8px;padding:6px 10px;white-space:nowrap}
.mg-buyer{padding:16px 18px;margin-bottom:13px;position:relative}
.mg-buyer.top{border-color:#bbf7d0;box-shadow:0 4px 16px rgba(5,150,105,.10)}
.mg-rank{position:absolute;top:-9px;left:16px;background:${AMBER};color:#3b2606;font-family:'DM Mono',monospace;font-size:10.5px;font-weight:700;border-radius:6px;padding:3px 9px;box-shadow:0 2px 6px rgba(245,158,11,.35)}
.mg-buyer-head{display:flex;align-items:flex-start;gap:13px}
.mg-logo{width:46px;height:46px;border-radius:10px;background:#0f172a;color:#fff;display:flex;align-items:center;justify-content:center;font-family:'DM Mono',monospace;font-size:13px;font-weight:700;flex-shrink:0;letter-spacing:.02em}
.mg-buyer-id{flex:1;min-width:0}
.mg-name-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.mg-bname{font-size:16px;font-weight:700;color:#0f172a}
.mg-trust{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:3px 10px;font-size:11px;font-weight:700}
.mg-est{font-size:10.5px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:999px;padding:2px 8px}
.mg-meta{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:8px;font-size:12.5px;color:#64748b;align-items:center}
.mg-meta-chip{font-weight:600;color:#334155}
.mg-hschip{font-size:11px;background:#eef2ff;color:#4338ca;border-radius:5px;padding:2px 7px}
.mg-dist{font-size:11.5px;color:#94a3b8}
.mg-score-box{text-align:center;cursor:pointer;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px;padding:6px 12px;flex-shrink:0}
.mg-score{font-size:22px;font-weight:800;color:#047857;font-family:'DM Sans',sans-serif;line-height:1}
.mg-score-lbl{font-size:10px;color:#059669;margin-top:1px}
.mg-fitmini{margin:12px 0 4px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:11px 13px}
.mg-fitrow{display:flex;align-items:center;gap:9px;margin-bottom:7px}
.mg-fitrow:last-child{margin-bottom:0}
.mg-fitk{font-size:11.5px;color:#475569;width:64px;flex-shrink:0}
.mg-fittrack{flex:1;height:6px;background:#e2e8f0;border-radius:3px;overflow:hidden}
.mg-fitfill{height:100%;border-radius:3px}
.mg-fitv{font-size:11.5px;font-weight:700;color:#0f172a;width:24px;text-align:right;font-family:'DM Sans',sans-serif}
.mg-buyer-foot{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:13px;padding-top:12px;border-top:1px solid #f1f5f9}
.mg-contact{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;font-size:12.5px;color:#334155;min-width:0}
.mg-c-item{white-space:nowrap}
.mg-c-note{font-size:10.5px;color:#94a3b8}
.mg-locked{font-size:12.5px;color:#94a3b8}
.mg-unlock{background:${AMBER};color:#3b2606;border:none;border-radius:8px;padding:8px 14px;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit;white-space:nowrap;flex-shrink:0}
.mg-unlock:disabled{opacity:.4;cursor:not-allowed}
.mg-unlocked{font-size:12.5px;color:#047857;font-weight:700;flex-shrink:0}
.mg-why{margin-top:10px;background:none;border:none;color:#7c3aed;font-size:11.5px;cursor:pointer;padding:0;font-family:inherit}
.mg-foot{margin-top:16px;font-size:11px;color:#94a3b8;line-height:1.6}
@media(max-width:980px){.mg-body{grid-template-columns:1fr}}
`
