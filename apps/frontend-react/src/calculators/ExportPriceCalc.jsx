import { useState } from 'react'
import CalcShell from './CalcShell'
import api from '../lib/api'

const TABS = [
  { id: 'export-price', label: '수출단가', icon: '$' },
  { id: 'cbm', label: 'CBM', icon: 'm³' },
  { id: 'landed-cost', label: '도착원가', icon: '%' },
]

export default function ExportPriceCalc({ onBack, onNavigate }) {
  const [form, setForm] = useState({
    unit_price: '12000',
    qty: '5000',
    inland_transport: '850000',
    customs_docs: '320000',
    freight_usd: '1450',
    insurance_rate: '0.15',
    fx_rate: '1372.50',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const handleCalc = async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = {
        unit_price: parseFloat(form.unit_price) || 0,
        qty: parseInt(form.qty) || 0,
        inland_transport: parseFloat(form.inland_transport) || 0,
        customs_docs: parseFloat(form.customs_docs) || 0,
        freight_usd: parseFloat(form.freight_usd) || 0,
        insurance_rate: (parseFloat(form.insurance_rate) || 0) / 100,
        fx_rate: parseFloat(form.fx_rate) || 1372.50,
      }
      const res = await api.post('/v1/calculators/export-price', payload)
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || '계산 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const fmt = (n, d = 0) => {
    if (n == null) return '-'
    return Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
  }
  const fmtKRW = (n) => {
    if (n == null) return '-'
    if (n >= 1e8) return `₩${(n / 1e8).toFixed(1)}억`
    if (n >= 1e4) return `₩${(n / 1e4).toFixed(0)}만`
    return `₩${Number(n).toLocaleString()}`
  }

  const resultNode = result ? (
    <div className="calc-result">
      {/* 핵심 숫자 3개 */}
      <div className="calc-result-highlights">
        <div className="calc-highlight-card calc-highlight-card--primary">
          <span className="calc-highlight-label">FOB 총액</span>
          <span className="calc-highlight-value">${fmt(result.fob_usd, 0)}</span>
          <span className="calc-highlight-sub">단가 ${fmt(result.fob_unit_usd, 2)} / EA</span>
        </div>
        <div className="calc-highlight-card">
          <span className="calc-highlight-label">CIF 총액</span>
          <span className="calc-highlight-value">${fmt(result.cif_usd, 0)}</span>
          <span className="calc-highlight-sub">단가 ${fmt(result.cif_unit_usd, 2)} / EA</span>
        </div>
        <div className="calc-highlight-card">
          <span className="calc-highlight-label">원화 환산</span>
          <span className="calc-highlight-value">{fmtKRW(result.cif_krw)}</span>
          <span className="calc-highlight-sub">@ {fmt(result.fx_rate, 2)}</span>
        </div>
      </div>

      {/* 비용 구성 */}
      <div className="calc-breakdown-section">
        <h3 className="calc-section-title">비용 구성</h3>
        <div className="calc-bar-chart">
          {result.breakdown?.map((item, i) => (
            <div key={i} className="calc-bar-item">
              <div className="calc-bar-track">
                <div
                  className="calc-bar-fill"
                  style={{ width: `${Math.max(item.percent, 1)}%` }}
                  data-index={i}
                />
              </div>
              <span className="calc-bar-label">{item.label} {item.percent}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* 단계별 분해표 */}
      <div className="calc-stages-section">
        <h3 className="calc-section-title">단계별 계산</h3>
        <table className="calc-stages-table">
          <tbody>
            {result.stages?.map((stage, i) => (
              <tr key={i} className={stage.is_stage ? 'is-stage' : ''}>
                <td className="calc-stage-label">{stage.label}</td>
                <td className="calc-stage-formula">{stage.formula || ''}</td>
                <td className="calc-stage-amount">
                  {stage.is_stage ? '' : `₩${fmt(stage.amount_krw)}`}
                </td>
                <td className="calc-stage-cumulative">
                  {stage.is_stage ? `₩${fmt(stage.amount_krw)}` : stage.cumulative_krw != null ? `₩${fmt(stage.cumulative_krw)}` : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 면책 문구 */}
      <p className="calc-note-inline">
        보험료는 무역 관례에 따라 CFR 금액의 110%를 보험가액으로 잡아 계산했습니다.
        환율은 입력하신 {fmt(result.fx_rate, 2)}원 기준이며, 실제 계약 시점 환율에 따라 달라집니다.
      </p>

      {/* CTA */}
      <div className="calc-cta">
        <p className="calc-cta-text">
          CIF ${fmt(result.cif_unit_usd, 2)} 조건이면 어느 나라 바이어가 받을까요?
        </p>
        <button className="ui-button ui-button--solid calc-cta-button">
          이 조건으로 바이어 보기 →
        </button>
      </div>
    </div>
  ) : (
    <div className="calc-result-empty">
      <p>입력값을 넣고 <strong>계산하기</strong>를 눌러 보세요.</p>
    </div>
  )

  return (
    <CalcShell
      title="수출단가 계산기 (EXW → FOB → CIF)"
      description="공장 출고가에 어떤 비용이 얼마씩 붙어 최종 견적가가 되는지 단계별로 보여줍니다"
      tabs={TABS}
      activeTab="export-price"
      onTabChange={(id) => onNavigate(id)}
      onBack={onBack}
      result={resultNode}
      footer={
        <p className="calc-disclaimer">
          계산된 비용은 예상치이며, 실제 비용은 포워더 견적과 다를 수 있습니다.
        </p>
      }
    >
      <div className="calc-form">
        <label className="calc-field">
          <span className="calc-field-label">제품 단가 (공장도)</span>
          <div className="calc-input-row">
            <input type="number" value={form.unit_price} onChange={set('unit_price')} className="calc-input" />
            <span className="calc-input-suffix">KRW</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">수량</span>
          <div className="calc-input-row">
            <input type="number" value={form.qty} onChange={set('qty')} className="calc-input" />
            <span className="calc-input-suffix">EA</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">국내 내륙운송비</span>
          <div className="calc-input-row">
            <input type="number" value={form.inland_transport} onChange={set('inland_transport')} className="calc-input" />
            <span className="calc-input-suffix">KRW</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">수출통관 · 서류비</span>
          <div className="calc-input-row">
            <input type="number" value={form.customs_docs} onChange={set('customs_docs')} className="calc-input" />
            <span className="calc-input-suffix">KRW</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">국제운임 (해상 LCL)</span>
          <div className="calc-input-row">
            <input type="number" value={form.freight_usd} onChange={set('freight_usd')} className="calc-input" />
            <span className="calc-input-suffix">USD</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">적하보험 요율</span>
          <div className="calc-input-row">
            <input type="number" step="0.01" value={form.insurance_rate} onChange={set('insurance_rate')} className="calc-input" />
            <span className="calc-input-suffix">%</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">적용 환율</span>
          <div className="calc-input-row">
            <input type="number" step="0.01" value={form.fx_rate} onChange={set('fx_rate')} className="calc-input" />
            <span className="calc-input-suffix">KRW/USD</span>
          </div>
        </label>

        {error && <p className="calc-error">{error}</p>}

        <button
          className="ui-button ui-button--solid calc-submit"
          onClick={handleCalc}
          disabled={loading}
        >
          {loading ? '계산 중...' : '계산하기'}
        </button>
      </div>
    </CalcShell>
  )
}
