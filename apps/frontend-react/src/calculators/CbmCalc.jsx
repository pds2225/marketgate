import { useState } from 'react'
import CalcShell from './CalcShell'
import api from '../lib/api'

const TABS = [
  { id: 'export-price', label: '수출단가', icon: '$' },
  { id: 'cbm', label: 'CBM', icon: 'm³' },
  { id: 'landed-cost', label: '도착원가', icon: '%' },
]

export default function CbmCalc({ onBack, onNavigate }) {
  const [form, setForm] = useState({
    box_w_cm: '60',
    box_d_cm: '40',
    box_h_cm: '35',
    qty: '420',
    weight_per_box_kg: '12.5',
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
        box_w_cm: parseFloat(form.box_w_cm) || 0,
        box_d_cm: parseFloat(form.box_d_cm) || 0,
        box_h_cm: parseFloat(form.box_h_cm) || 0,
        qty: parseInt(form.qty) || 0,
        weight_per_box_kg: parseFloat(form.weight_per_box_kg) || 0,
      }
      const res = await api.post('/v1/calculators/cbm', payload)
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || '계산 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const fmt = (n, d = 2) => {
    if (n == null) return '-'
    return Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
  }

  const resultNode = result ? (
    <div className="calc-result">
      {/* 핵심 숫자 */}
      <div className="calc-result-highlights">
        <div className="calc-highlight-card calc-highlight-card--primary">
          <span className="calc-highlight-label">총 CBM</span>
          <span className="calc-highlight-value">{fmt(result.total_cbm, 3)} m³</span>
          <span className="calc-highlight-sub">박스당 {fmt(result.box_cbm, 3)} m³</span>
        </div>
        <div className="calc-highlight-card">
          <span className="calc-highlight-label">총 중량</span>
          <span className="calc-highlight-value">{fmt(result.total_weight_kg, 1)} kg</span>
          <span className="calc-highlight-sub">R.T 기준 {fmt(result.total_cbm, 3)}</span>
        </div>
        <div className="calc-highlight-card">
          <span className="calc-highlight-label">권장 방식</span>
          <span className="calc-highlight-value">{result.recommended_mode}</span>
          <span className="calc-highlight-sub">
            {result.recommended_mode === 'FCL' ? 'LCL 대비 유리' : result.recommended_mode === 'LCL' ? '소량 적합' : '비교 필요'}
          </span>
        </div>
      </div>

      {/* 컨테이너별 적재율 */}
      <div className="calc-containers-section">
        <h3 className="calc-section-title">컨테이너별 적재율</h3>
        <div className="calc-container-grid">
          {result.containers?.map((c) => (
            <div key={c.type} className={`calc-container-card calc-container-card--${c.status === '초과' ? 'over' : c.status === '거의 참' ? 'near' : 'ok'}`}>
              <div className="calc-container-header">
                <span className="calc-container-type">{c.label}</span>
                <span className="calc-container-eff">유효 {c.effective_cbm} m³</span>
              </div>
              <div className="calc-container-bar-track">
                <div
                  className="calc-container-bar-fill"
                  style={{ width: `${Math.min(c.usage_percent, 100)}%` }}
                />
              </div>
              <div className="calc-container-footer">
                <span className="calc-container-pct">{c.usage_percent}%</span>
                <span className={`calc-container-status calc-container-status--${c.status === '초과' ? 'over' : c.status === '거의 참' ? 'near' : 'ok'}`}>
                  {c.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 권고 */}
      <div className="calc-recommendation">
        <p>{result.recommendation}</p>
      </div>

      {/* CTA */}
      <div className="calc-cta">
        <p className="calc-cta-text">
          이 부피로 최적 물류 경로를 비교해 보시겠어요?
        </p>
        <button className="ui-button ui-button--solid calc-cta-button">
          물류비 비교하기 →
        </button>
      </div>
    </div>
  ) : (
    <div className="calc-result-empty">
      <p>박스 규격과 수량을 넣고 <strong>계산하기</strong>를 눌러 보세요.</p>
    </div>
  )

  return (
    <CalcShell
      title="CBM · 컨테이너 적재 계산기"
      description="박스 크기와 수량으로 부피와 컨테이너 적재율을 확인합니다"
      tabs={TABS}
      activeTab="cbm"
      onTabChange={(id) => onNavigate(id)}
      onBack={onBack}
      result={resultNode}
    >
      <div className="calc-form">
        <label className="calc-field">
          <span className="calc-field-label">박스 가로</span>
          <div className="calc-input-row">
            <input type="number" value={form.box_w_cm} onChange={set('box_w_cm')} className="calc-input" />
            <span className="calc-input-suffix">cm</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">박스 세로</span>
          <div className="calc-input-row">
            <input type="number" value={form.box_d_cm} onChange={set('box_d_cm')} className="calc-input" />
            <span className="calc-input-suffix">cm</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">박스 높이</span>
          <div className="calc-input-row">
            <input type="number" value={form.box_h_cm} onChange={set('box_h_cm')} className="calc-input" />
            <span className="calc-input-suffix">cm</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">박스 수량</span>
          <div className="calc-input-row">
            <input type="number" value={form.qty} onChange={set('qty')} className="calc-input" />
            <span className="calc-input-suffix">박스</span>
          </div>
        </label>

        <label className="calc-field">
          <span className="calc-field-label">박스당 중량</span>
          <div className="calc-input-row">
            <input type="number" step="0.1" value={form.weight_per_box_kg} onChange={set('weight_per_box_kg')} className="calc-input" />
            <span className="calc-input-suffix">kg</span>
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
