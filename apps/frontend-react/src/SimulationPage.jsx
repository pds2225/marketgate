import { useState } from 'react'
import api from './lib/api'

const inp = {
  width: '100%',
  background: '#ffffff',
  border: '1px solid #dbe3ef',
  borderRadius: 12,
  padding: '10px 14px',
  color: '#07152f',
  boxSizing: 'border-box',
  fontSize: 14,
}

const GRADE_COLOR = { 우수: '#059669', 보통: '#d97706', 손익분기: '#ea580c', 적자: '#dc2626' }

export default function SimulationPage({ onBack }) {
  const [form, setForm] = useState({ hs_code: '', country: '', unit_price: '', qty: '', logistics: 'sea' })
  const [result, setResult] = useState(null)
  const [lcError, setLcError] = useState('')
  const [lcLoading, setLcLoading] = useState(false)

  const [bepForm, setBepForm] = useState({ price: '', fixed_cost: '', variable_cost: '' })
  const [bepResult, setBepResult] = useState(null)
  const [bepError, setBepError] = useState('')

  const handleLandedCost = async (e) => {
    e.preventDefault()
    setLcError('')
    setLcLoading(true)
    try {
      const { data } = await api.post('/v1/simulation/landed-cost', {
        hs_code: form.hs_code,
        country: form.country,
        unit_price: parseFloat(form.unit_price),
        qty: parseInt(form.qty),
        logistics: form.logistics,
      })
      setResult(data)
    } catch (err) {
      setLcError(err.response?.data?.detail || '계산 오류가 발생했습니다.')
    } finally {
      setLcLoading(false)
    }
  }

  const handleBep = async (e) => {
    e.preventDefault()
    setBepError('')
    try {
      const { data } = await api.post('/v1/simulation/bep', {
        price: parseFloat(bepForm.price),
        fixed_cost: parseFloat(bepForm.fixed_cost),
        variable_cost: parseFloat(bepForm.variable_cost),
      })
      setBepResult(data)
    } catch (err) {
      setBepError(err.response?.data?.detail || '계산 오류가 발생했습니다.')
    }
  }

  const card = { background: '#ffffff', border: '1px solid #dbe3ef', borderRadius: 16, padding: 24, maxWidth: 520, marginBottom: 24, boxShadow: '0 1px 3px rgba(15,23,42,.05)' }

  return (
    <div style={{ minHeight: '100vh', background: '#f7f9fc', color: '#07152f', padding: 24 }}>
      <button onClick={onBack} style={{ background: 'none', border: '1px solid #dbe3ef', color: '#59677d', cursor: 'pointer', marginBottom: 20, fontSize: 13, padding: '7px 14px', borderRadius: 4 }}>
        ← 돌아가기
      </button>
      <h2 style={{ marginBottom: 24, fontSize: 20 }}>수익성 시뮬레이션</h2>

      {/* Landed Cost */}
      <div style={card}>
        <h3 style={{ marginBottom: 20, fontSize: 15, color: '#07152f' }}>Landed Cost 계산</h3>
        <form onSubmit={handleLandedCost}>
          {[
            { key: 'hs_code', label: 'HS 코드', type: 'text', placeholder: '330499' },
            { key: 'country', label: '수출 대상국 코드', type: 'text', placeholder: 'us' },
            { key: 'unit_price', label: '단가 (USD)', type: 'number', placeholder: '10.00' },
            { key: 'qty', label: '수량 (개)', type: 'number', placeholder: '1000' },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key} style={{ marginBottom: 12 }}>
              <label style={{ color: '#59677d', fontSize: 12, display: 'block', marginBottom: 4 }}>{label}</label>
              <input
                type={type}
                value={form[key]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                placeholder={placeholder}
                required
                style={inp}
              />
            </div>
          ))}
          <div style={{ marginBottom: 18 }}>
            <label style={{ color: '#8b949e', fontSize: 12, display: 'block', marginBottom: 4 }}>물류 방식</label>
            <select
              value={form.logistics}
              onChange={e => setForm(f => ({ ...f, logistics: e.target.value }))}
              style={{ ...inp, width: 'auto' }}
            >
              <option value="sea">해상</option>
              <option value="air">항공</option>
            </select>
          </div>
          {lcError && <p style={{ color: '#dc2626', fontSize: 12, marginBottom: 12 }}>{lcError}</p>}
          <button
            type="submit"
            disabled={lcLoading}
            style={{ background: '#1463f3', border: 'none', borderRadius: 12, padding: '10px 18px', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600, opacity: lcLoading ? 0.7 : 1 }}
          >
            {lcLoading ? '계산 중...' : '계산'}
          </button>
        </form>

        {result && (
          <div style={{ marginTop: 20, borderTop: '1px solid #dbe3ef', paddingTop: 16 }}>
            {result.warning && (
              <p style={{ color: '#92400e', fontSize: 12, marginBottom: 12, background: '#fffbeb', padding: '8px 12px', borderRadius: 8, border: '1px solid #fde68a' }}>
                {result.warning}
              </p>
            )}
            <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
              <tbody>
                {[
                  ['제품 총액', `$${result.product_total.toLocaleString()}`],
                  ['관세', `$${result.tariff_cost.toLocaleString()}`],
                  ['물류비', `$${result.logistics_cost.toLocaleString()}`],
                  ['보험료', `$${result.insurance_cost.toLocaleString()}`],
                  ['Landed Cost', `$${result.landed_cost.toLocaleString()}`],
                  ['마진율', `${(result.margin_rate * 100).toFixed(2)}%`],
                ].map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid #e2e8f0' }}>
                    <td style={{ padding: '6px 0', color: '#59677d' }}>{k}</td>
                    <td style={{ textAlign: 'right', color: '#07152f', fontWeight: k === 'Landed Cost' ? 600 : 400 }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ marginTop: 14, fontWeight: 700, color: GRADE_COLOR[result.profit_grade] || '#e6edf3', fontSize: 15 }}>
              수익성 등급: {result.profit_grade}
            </p>
          </div>
        )}
      </div>

      {/* BEP */}
      <div style={card}>
        <h3 style={{ marginBottom: 20, fontSize: 15, color: '#07152f' }}>BEP (손익분기) 계산</h3>
        <form onSubmit={handleBep}>
          {[
            { key: 'price', label: '판매단가 (USD)' },
            { key: 'fixed_cost', label: '고정비 합계 (USD)' },
            { key: 'variable_cost', label: '단위당 변동비 (USD)' },
          ].map(({ key, label }) => (
            <div key={key} style={{ marginBottom: 12 }}>
              <label style={{ color: '#59677d', fontSize: 12, display: 'block', marginBottom: 4 }}>{label}</label>
              <input
                type="number"
                step="0.01"
                value={bepForm[key]}
                onChange={e => setBepForm(f => ({ ...f, [key]: e.target.value }))}
                required
                style={inp}
              />
            </div>
          ))}
          {bepError && <p style={{ color: '#dc2626', fontSize: 12, marginBottom: 12 }}>{bepError}</p>}
          <button
            type="submit"
            style={{ background: '#1463f3', border: 'none', borderRadius: 12, padding: '10px 18px', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
          >
            계산
          </button>
        </form>
        {bepResult && (
          <div style={{ marginTop: 16, borderTop: '1px solid #dbe3ef', paddingTop: 14 }}>
            <p style={{ fontSize: 14, color: '#59677d', marginBottom: 6 }}>
              BEP 수량: <span style={{ color: '#059669', fontWeight: 600 }}>{bepResult.bep_qty.toLocaleString()}개</span>
            </p>
            <p style={{ fontSize: 14, color: '#59677d' }}>
              BEP 매출: <span style={{ color: '#059669', fontWeight: 600 }}>${bepResult.bep_revenue.toLocaleString()}</span>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
