import { useMemo, useState } from 'react'

/*
 * SimulationDemo — 수출 수익성 시뮬레이션 (Landed Cost + BEP)
 * 2차 deep-research 벤치마킹 반영:
 *  - Zonos: itemized 분해(상품원가+운송+관세+세금+수수료) · 결제 전 총원가 공개("no surprises")
 *  - Avalara: 관세+VAT 단일 패널 통합
 *  - SimplyDuty: 분류 단계 / 계산 단계 분리 (과금 포인트)
 *  - ITC EPI: 관세 우위(FTA) 반영
 *  - 마진율·BEP는 벤치마크에 없는 마켓게이트 고유 로직(차별 가치)
 *
 * 관세·VAT는 화장품(HS 3304) 주요국 공개 관세 스케줄·FTA 양허표 기반 대표값.
 * 실제 적용 시 HS 세부코드·연도·원산지증명에 따라 재확인 필요(화면에 명시).
 */

const KRW = 1350 // USD→KRW 환산(표기용)

// 화장품(HS 3304) 주요국 대표 관세율/부가세 — 공개 관세 스케줄·FTA 양허 근거
const DEST = {
  IND: { name: '인도', iso: 'IND', dutyMfn: 0.20, dutyFta: 0.10, vat: 0.18, vatName: 'GST', fta: '한-인도 CEPA' },
  USA: { name: '미국', iso: 'USA', dutyMfn: 0.00, dutyFta: 0.00, vat: 0.00, vatName: 'Sales Tax(주별 별도)', fta: '한-미 FTA' },
  VNM: { name: '베트남', iso: 'VNM', dutyMfn: 0.20, dutyFta: 0.00, vat: 0.10, vatName: 'VAT', fta: '한-아세안 FTA' },
  CHN: { name: '중국', iso: 'CHN', dutyMfn: 0.10, dutyFta: 0.02, vat: 0.13, vatName: '증치세', fta: '한-중 FTA' },
  IDN: { name: '인도네시아', iso: 'IDN', dutyMfn: 0.10, dutyFta: 0.05, vat: 0.11, vatName: 'PPN', fta: '한-아세안 FTA' },
  PHL: { name: '필리핀', iso: 'PHL', dutyMfn: 0.10, dutyFta: 0.00, vat: 0.12, vatName: 'VAT', fta: '한-아세안 FTA' },
  JPN: { name: '일본', iso: 'JPN', dutyMfn: 0.00, dutyFta: 0.00, vat: 0.10, vatName: '소비세', fta: 'RCEP' },
  ARE: { name: 'UAE', iso: 'ARE', dutyMfn: 0.05, dutyFta: 0.05, vat: 0.05, vatName: 'VAT', fta: '한-GCC(협상)' },
}

const FREIGHT_RATE = 0.08 // 상품가 대비 국제운송비 추정율
const INSURANCE_RATE = 0.01 // CIF 보험료
const CUSTOMS_FEE = 60 // 통관/브로커 고정 수수료 USD

function compute({ unitPrice, qty, dest, fta, sellPrice, fixedCost }) {
  const c = DEST[dest]
  const commercial = unitPrice * qty
  const freight = commercial * FREIGHT_RATE
  const insurance = commercial * INSURANCE_RATE
  const cif = commercial + freight + insurance
  const dutyRate = fta ? c.dutyFta : c.dutyMfn
  const duty = cif * dutyRate
  const vatBase = cif + duty
  const vat = vatBase * c.vat
  const totalLanded = commercial + freight + insurance + duty + vat + CUSTOMS_FEE
  const unitLanded = totalLanded / qty

  const revenue = sellPrice * qty
  const unitMargin = sellPrice - unitLanded
  const marginRate = sellPrice > 0 ? unitMargin / sellPrice : 0
  const grossProfit = unitMargin * qty
  const netProfit = grossProfit - fixedCost
  const bepQty = unitMargin > 0 ? Math.ceil(fixedCost / unitMargin) : null
  const bepRevenue = bepQty != null ? bepQty * sellPrice : null

  return {
    c, dutyRate, commercial, freight, insurance, cif, duty, vat, customsFee: CUSTOMS_FEE,
    totalLanded, unitLanded, revenue, unitMargin, marginRate, grossProfit, netProfit, bepQty, bepRevenue,
  }
}

const usd = (n) => `$${(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
const usd2 = (n) => `$${(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const krw = (n) => `₩${Math.round(n * KRW).toLocaleString()}`
const pct = (n) => `${(n * 100).toFixed(1)}%`

function NumField({ label, value, onChange, unit, step = 1, min = 0, hint }) {
  return (
    <label className="sf-field">
      <span className="sf-label">{label}{hint && <em className="sf-hint">{hint}</em>}</span>
      <div className="sf-input-wrap">
        <input type="number" className="sf-input" value={value} min={min} step={step}
          onChange={e => onChange(Math.max(min, Number(e.target.value) || 0))} />
        {unit && <span className="sf-unit">{unit}</span>}
      </div>
    </label>
  )
}

export default function SimulationDemo() {
  const [hs] = useState('330499')
  const [unitPrice, setUnitPrice] = useState(8)
  const [qty, setQty] = useState(1000)
  const [dest, setDest] = useState('IND')
  const [fta, setFta] = useState(true)
  const [sellPrice, setSellPrice] = useState(15)
  const [fixedCost, setFixedCost] = useState(5000)

  const r = useMemo(() => compute({ unitPrice, qty, dest, fta, sellPrice, fixedCost }), [unitPrice, qty, dest, fta, sellPrice, fixedCost])

  // itemized 분해 (waterfall)
  const items = [
    { k: '상품 원가', v: r.commercial, c: '#64748b', note: `단가 ${usd2(unitPrice)} × ${qty.toLocaleString()}개` },
    { k: '국제 운송·보험', v: r.freight + r.insurance, c: '#0ea5e9', note: `운송 ${(FREIGHT_RATE * 100).toFixed(0)}% + 보험 ${(INSURANCE_RATE * 100).toFixed(0)}%` },
    { k: `관세 (${pct(r.dutyRate)})`, v: r.duty, c: '#f59e0b', note: fta ? `${r.c.fta} 적용` : 'MFN 기본세율' },
    { k: `${r.c.vatName} (${pct(r.c.vat)})`, v: r.vat, c: '#7c3aed', note: 'CIF+관세 기준 과세' },
    { k: '통관·브로커 수수료', v: r.customsFee, c: '#94a3b8', note: '고정' },
  ]
  const maxItem = Math.max(...items.map(i => i.v), 1)
  const profitPositive = r.netProfit >= 0
  const marginPositive = r.marginRate >= 0
  const gaugePct = Math.max(0, Math.min(100, Math.round(r.marginRate * 100)))

  return (
    <div className="sf-root">
      <style>{STYLE}</style>

      {/* Top bar with tabs */}
      <header className="sf-top">
        <div className="sf-brand" onClick={() => { window.location.hash = 'buyers' }}>MARKETGATE</div>
        <nav className="sf-tabs">
          <button className="sf-tab" onClick={() => { window.location.hash = 'buyers' }}>바이어 검색</button>
          <button className="sf-tab active">수익성 시뮬레이션</button>
        </nav>
        <span className="sf-top-tag">Landed Cost · BEP</span>
      </header>

      <div className="sf-hero">
        <div className="sf-hero-inner">
          <p className="sf-eyebrow">EXPORT PROFITABILITY SIMULATOR</p>
          <h1 className="sf-h1">수출하면 <span className="amber">얼마 남는지</span>, 결제 전에 끝까지 계산합니다</h1>
          <p className="sf-sub">관세·부가세·물류비까지 포함한 <b>총 수입원가(Landed Cost)</b> 와 <b>손익분기(BEP)</b> 를 실시간으로 — 컨설팅 1,700만원 없이.</p>
        </div>
      </div>

      <div className="sf-body">
        {/* LEFT: inputs */}
        <div className="sf-card sf-inputs">
          <h3 className="sf-ph">수출 조건 입력</h3>

          <label className="sf-field">
            <span className="sf-label">품목 (HS코드)<em className="sf-hint">자동 인식</em></span>
            <div className="sf-hsbox"><span className="sf-hscode">HS {hs}</span><span className="sf-hsname">기초화장품·스킨케어</span></div>
          </label>

          <NumField label="공급 단가 (FOB)" value={unitPrice} onChange={setUnitPrice} unit="USD" step={0.5} hint="개당" />
          <NumField label="수출 수량" value={qty} onChange={setQty} unit="개" step={100} />

          <label className="sf-field">
            <span className="sf-label">목적지 국가</span>
            <div className="sf-dest-grid">
              {Object.entries(DEST).map(([code, d]) => (
                <button key={code} className={`sf-dest ${dest === code ? 'on' : ''}`} onClick={() => setDest(code)}>
                  <span className="sf-dest-iso">{d.iso}</span>
                  <span className="sf-dest-name">{d.name}</span>
                </button>
              ))}
            </div>
          </label>

          <label className="sf-fta">
            <input type="checkbox" checked={fta} onChange={e => setFta(e.target.checked)} />
            <span><b>{r.c.fta}</b> 특혜관세 적용 <em>(원산지증명 시 관세 {pct(r.c.dutyMfn)} → {pct(r.c.dutyFta)})</em></span>
          </label>

          <div className="sf-divider"><span>판매 계획</span></div>
          <NumField label="목표 판매 단가" value={sellPrice} onChange={setSellPrice} unit="USD" step={0.5} hint="현지 도매" />
          <NumField label="초기 고정비" value={fixedCost} onChange={setFixedCost} unit="USD" step={500} hint="인증·마케팅 등" />
        </div>

        {/* RIGHT: results */}
        <div className="sf-results">
          {/* Headline landed cost */}
          <div className="sf-card sf-headline">
            <div className="sf-route">
              <span className="sf-route-kr">KOR 🇰🇷</span>
              <span className="sf-route-arrow">→</span>
              <span className="sf-route-dest">{r.c.iso} {r.c.name}</span>
            </div>
            <div className="sf-total-grid">
              <div>
                <div className="sf-total-lbl">총 수입원가 (Landed Cost)</div>
                <div className="sf-total-val">{usd(r.totalLanded)}</div>
                <div className="sf-total-krw">{krw(r.totalLanded)}</div>
              </div>
              <div className="sf-unit-box">
                <div className="sf-unit-lbl">개당 원가</div>
                <div className="sf-unit-val">{usd2(r.unitLanded)}</div>
              </div>
            </div>
            <div className="sf-trust"><span className="sf-trust-dot" />결제 전 관세·세금·물류비까지 <b>전부 확정 공개</b> — 숨은 비용 없음</div>
          </div>

          {/* Itemized breakdown */}
          <div className="sf-card sf-panel">
            <h3 className="sf-ph">원가 구성 <span className="sf-ph-sub">itemized breakdown</span></h3>
            {items.map(it => (
              <div key={it.k} className="sf-item">
                <div className="sf-item-top">
                  <span className="sf-item-k">{it.k}</span>
                  <span className="sf-item-v">{usd(it.v)}</span>
                </div>
                <div className="sf-item-track"><div className="sf-item-fill" style={{ width: `${(it.v / maxItem) * 100}%`, background: it.c }} /></div>
                <span className="sf-item-note">{it.note}</span>
              </div>
            ))}
            <div className="sf-item-total">
              <span>총 Landed Cost</span><span>{usd(r.totalLanded)}</span>
            </div>
          </div>

          {/* Margin + BEP */}
          <div className="sf-kpis">
            <div className="sf-card sf-kpi">
              <div className="sf-kpi-lbl">예상 마진율</div>
              <div className={`sf-kpi-val ${marginPositive ? 'pos' : 'neg'}`}>{pct(r.marginRate)}</div>
              <div className="sf-gauge"><div className="sf-gauge-fill" style={{ width: `${gaugePct}%`, background: marginPositive ? '#059669' : '#dc2626' }} /></div>
              <div className="sf-kpi-foot">개당 {usd2(r.unitMargin)} · 매출 {usd(r.revenue)}</div>
            </div>

            <div className="sf-card sf-kpi">
              <div className="sf-kpi-lbl">손익분기 (BEP)</div>
              {r.bepQty != null ? (
                <>
                  <div className="sf-kpi-val bep">{r.bepQty.toLocaleString()}<span className="sf-kpi-unit">개</span></div>
                  <div className="sf-kpi-foot">≈ {usd(r.bepRevenue)} 판매 시 고정비 {usd(fixedCost)} 회수</div>
                </>
              ) : (
                <>
                  <div className="sf-kpi-val neg">달성 불가</div>
                  <div className="sf-kpi-foot">개당 원가가 판매가보다 높음 — 단가/조건 재검토</div>
                </>
              )}
            </div>

            <div className="sf-card sf-kpi">
              <div className="sf-kpi-lbl">순이익 (이 거래)</div>
              <div className={`sf-kpi-val ${profitPositive ? 'pos' : 'neg'}`}>{usd(r.netProfit)}</div>
              <div className="sf-kpi-foot">매출총이익 {usd(r.grossProfit)} − 고정비 {usd(fixedCost)}</div>
            </div>
          </div>

          <p className="sf-foot">
            관세·{r.c.vatName}율은 화장품(HS {hs}) 주요국 <b>공개 관세 스케줄·FTA 양허표 기반 대표값</b>입니다.
            실제 적용 세율은 HS 세부코드·원산지증명·연도별 개정에 따라 달라질 수 있어 통관 전 재확인이 필요합니다.
            · 운송 {(FREIGHT_RATE * 100).toFixed(0)}%·보험 {(INSURANCE_RATE * 100).toFixed(0)}%·수수료 {usd(CUSTOMS_FEE)}는 추정 기본값(편집 가능 예정) · 환율 ₩{KRW.toLocaleString()}/USD
          </p>
        </div>
      </div>
    </div>
  )
}

const STYLE = `
.sf-root{font-family:'Pretendard','Malgun Gothic',sans-serif;background:#0c0a09;color:#e7e5e4;min-height:100vh;-webkit-font-smoothing:antialiased}
.sf-root *{box-sizing:border-box}
.sf-top{height:54px;background:rgba(12,10,9,.96);display:flex;align-items:center;gap:24px;padding:0 24px;border-bottom:1px solid rgba(245,158,11,.14);position:sticky;top:0;z-index:50;backdrop-filter:blur(10px)}
.sf-brand{font-family:'DM Mono',monospace;font-weight:700;letter-spacing:.14em;color:#f59e0b;font-size:15px;cursor:pointer}
.sf-tabs{display:flex;gap:4px}
.sf-tab{background:none;border:none;color:#78716c;font-size:13px;padding:8px 14px;cursor:pointer;font-family:inherit;border-radius:7px;transition:.15s}
.sf-tab:hover{color:#e7e5e4}
.sf-tab.active{color:#0c0a09;background:#f59e0b;font-weight:700}
.sf-top-tag{margin-left:auto;font-family:'DM Mono',monospace;font-size:11px;color:#57534e;letter-spacing:.08em}
.sf-hero{background:radial-gradient(ellipse 80% 60% at 25% 0%,rgba(245,158,11,.10) 0%,transparent 55%),#0c0a09;border-bottom:1px solid rgba(245,158,11,.07);padding:38px 24px 30px}
.sf-hero-inner{max-width:1180px;margin:0 auto}
.sf-eyebrow{font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.22em;color:#f59e0b;margin:0 0 12px}
.sf-h1{font-size:30px;font-weight:800;line-height:1.25;margin:0;color:#fafaf9;letter-spacing:-.01em}
.sf-h1 .amber{color:#f59e0b}
.sf-sub{margin:12px 0 0;font-size:14px;color:#a8a29e;line-height:1.6;max-width:680px}
.sf-sub b{color:#e7e5e4}
.sf-body{max-width:1180px;margin:24px auto;padding:0 24px;display:grid;grid-template-columns:340px 1fr;gap:20px;align-items:start}
.sf-card{background:#fafaf9;color:#1e293b;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.28)}
.sf-inputs{padding:20px;position:sticky;top:74px}
.sf-ph{font-size:14px;font-weight:800;color:#0f172a;margin:0 0 16px;display:flex;justify-content:space-between;align-items:baseline}
.sf-ph-sub{font-size:11px;color:#94a3b8;font-weight:500;font-family:'DM Mono',monospace}
.sf-field{display:block;margin-bottom:15px}
.sf-label{display:flex;justify-content:space-between;align-items:baseline;font-size:12.5px;font-weight:600;color:#334155;margin-bottom:6px}
.sf-hint{font-style:normal;font-size:11px;color:#94a3b8;font-weight:500}
.sf-input-wrap{display:flex;align-items:center;border:1.5px solid #e2e8f0;border-radius:10px;overflow:hidden;transition:border-color .15s}
.sf-input-wrap:focus-within{border-color:#f59e0b}
.sf-input{flex:1;border:none;outline:none;padding:10px 12px;font-size:15px;font-family:'DM Sans',sans-serif;font-weight:600;color:#0f172a;width:100%}
.sf-unit{padding:0 12px;font-size:12px;color:#94a3b8;background:#f8fafc;align-self:stretch;display:flex;align-items:center;border-left:1px solid #e2e8f0}
.sf-hsbox{display:flex;align-items:center;gap:8px;background:#f1f5f9;border-radius:10px;padding:10px 12px}
.sf-hscode{font-family:'DM Mono',monospace;font-weight:700;color:#4338ca;font-size:13px;background:#e0e7ff;padding:2px 8px;border-radius:5px}
.sf-hsname{font-size:13px;color:#475569}
.sf-dest-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.sf-dest{display:flex;align-items:center;gap:7px;background:#fff;border:1.5px solid #e2e8f0;border-radius:9px;padding:8px 9px;cursor:pointer;transition:.12s;font-family:inherit}
.sf-dest:hover{border-color:#cbd5e1}
.sf-dest.on{border-color:#f59e0b;background:#fffbeb}
.sf-dest-iso{font-family:'DM Mono',monospace;font-size:10.5px;font-weight:700;color:#92400e;background:#fef3c7;border-radius:4px;padding:1px 5px}
.sf-dest.on .sf-dest-iso{background:#f59e0b;color:#fff}
.sf-dest-name{font-size:12.5px;color:#334155;font-weight:500}
.sf-fta{display:flex;align-items:flex-start;gap:9px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:11px 12px;margin-top:6px;cursor:pointer;font-size:12.5px;color:#166534;line-height:1.5}
.sf-fta input{margin-top:2px;accent-color:#059669;width:15px;height:15px;flex-shrink:0}
.sf-fta b{color:#15803d}
.sf-fta em{font-style:normal;color:#16a34a;font-size:11px}
.sf-divider{display:flex;align-items:center;gap:10px;margin:18px 0 14px;color:#94a3b8;font-size:11px;font-weight:700;letter-spacing:.1em;font-family:'DM Mono',monospace}
.sf-divider::before,.sf-divider::after{content:'';flex:1;height:1px;background:#e2e8f0}
.sf-results{display:flex;flex-direction:column;gap:16px}
.sf-headline{padding:20px 22px;background:linear-gradient(135deg,#1c1917 0%,#0c0a09 100%);color:#fafaf9;border:1px solid rgba(245,158,11,.22)}
.sf-route{display:flex;align-items:center;gap:12px;font-family:'DM Mono',monospace;font-size:13px;margin-bottom:16px;color:#d6d3d1}
.sf-route-arrow{color:#f59e0b;font-size:16px}
.sf-route-dest{color:#f59e0b;font-weight:700}
.sf-total-grid{display:flex;align-items:flex-end;justify-content:space-between;gap:16px}
.sf-total-lbl{font-size:12px;color:#a8a29e;margin-bottom:5px}
.sf-total-val{font-size:40px;font-weight:800;line-height:1;color:#f59e0b;font-family:'DM Sans',sans-serif;letter-spacing:-.02em}
.sf-total-krw{font-size:13px;color:#78716c;margin-top:6px;font-family:'DM Mono',monospace}
.sf-unit-box{text-align:right;flex-shrink:0;border-left:1px solid rgba(255,255,255,.1);padding-left:16px}
.sf-unit-lbl{font-size:11px;color:#a8a29e;margin-bottom:4px}
.sf-unit-val{font-size:22px;font-weight:700;color:#fafaf9;font-family:'DM Sans',sans-serif}
.sf-trust{display:flex;align-items:center;gap:8px;margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,255,255,.08);font-size:12px;color:#a8a29e}
.sf-trust b{color:#34d399}
.sf-trust-dot{width:7px;height:7px;border-radius:50%;background:#34d399;box-shadow:0 0 0 3px rgba(52,211,153,.2);flex-shrink:0}
.sf-panel{padding:20px 22px}
.sf-item{margin-bottom:13px}
.sf-item-top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px}
.sf-item-k{font-size:13px;color:#334155;font-weight:600}
.sf-item-v{font-size:14px;font-weight:700;color:#0f172a;font-family:'DM Sans',sans-serif}
.sf-item-track{height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden}
.sf-item-fill{height:100%;border-radius:4px;transition:width .45s cubic-bezier(.4,0,.2,1)}
.sf-item-note{font-size:11px;color:#94a3b8;margin-top:3px;display:block}
.sf-item-total{display:flex;justify-content:space-between;align-items:center;margin-top:14px;padding-top:14px;border-top:2px solid #0f172a;font-size:15px;font-weight:800;color:#0f172a}
.sf-kpis{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.sf-kpi{padding:16px 18px}
.sf-kpi-lbl{font-size:12px;color:#64748b;font-weight:600;margin-bottom:8px}
.sf-kpi-val{font-size:30px;font-weight:800;line-height:1;font-family:'DM Sans',sans-serif;letter-spacing:-.01em}
.sf-kpi-val.pos{color:#059669}
.sf-kpi-val.neg{color:#dc2626}
.sf-kpi-val.bep{color:#0f172a}
.sf-kpi-unit{font-size:15px;font-weight:600;color:#94a3b8;margin-left:3px}
.sf-gauge{height:7px;background:#f1f5f9;border-radius:4px;overflow:hidden;margin:10px 0 8px}
.sf-gauge-fill{height:100%;border-radius:4px;transition:width .45s,background .3s}
.sf-kpi-foot{font-size:11px;color:#94a3b8;line-height:1.45}
.sf-foot{font-size:11px;color:#78716c;line-height:1.7;margin:4px 2px 0}
.sf-foot b{color:#a8a29e}
@media(max-width:980px){.sf-body{grid-template-columns:1fr}.sf-inputs{position:static}.sf-kpis{grid-template-columns:1fr}}
`
