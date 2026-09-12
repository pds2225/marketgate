import { useState } from 'react'
import CalcShell from './CalcShell'
import api from '../lib/api'

const TABS = [
  { id: 'export-price', label: '수출단가', icon: '$' },
  { id: 'cbm', label: 'CBM', icon: 'm³' },
  { id: 'landed-cost', label: '도착원가', icon: '%' },
]

const COUNTRIES = [
  { code: 'us', name: '미국', flag: '🇺🇸' },
  { code: 'jp', name: '일본', flag: '🇯🇵' },
  { code: 'cn', name: '중국', flag: '🇨🇳' },
  { code: 'de', name: '독일', flag: '🇩🇪' },
  { code: 'vn', name: '베트남', flag: '🇻🇳' },
  { code: 'in', name: '인도', flag: '🇮🇳' },
  { code: 'au', name: '호주', flag: '🇦🇺' },
  { code: 'ca', name: '캐나다', flag: '🇨🇦' },
  { code: 'gb', name: '영국', flag: '🇬🇧' },
  { code: 'fr', name: '프랑스', flag: '🇫🇷' },
]

export default function LandedCostCalc({ onBack, onNavigate }) {
  const [form, setForm] = useState({
    hs_code: '330499',
    country: 'us',
    cif_usd: '46095',
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
        hs_code: form.hs_code.trim(),
        country: form.country,
        cif_usd: parseFloat(form.cif_usd) || 0,
        fx_rate: parseFloat(form.fx_rate) || 1372.50,
      }
      const res = await api.post('/v1/calculators/landed-cost', payload)
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
      {/* 핵심 숫자 */}
      <div className="calc-result-highlights">
        <div className="calc-highlight-card calc-highlight-card--primary">
          <span className="calc-highlight-label">바이어 도착원가</span>
          <span className="calc-highlight-value">${fmt(result.landed_usd)}</span>
          <span className="calc-highlight-sub">{fmtKRW(result.landed_krw)}</span>
        </div>
        <div className="calc-highlight-card">
          <span className="calc-highlight-label">관세</span>
          <span className="calc-highlight-value">{(result.tariff_rate * 100).toFixed(1)}%</span>
          <span className="calc-highlight-sub">${fmt(result.tariff_cost_usd)}</span>
        </div>
        <div className="calc-highlight-card">
          <span className="calc-highlight-label">부가세</span>
          <span className="calc-highlight-value">{(result.vat_rate * 100).toFixed(0)}%</span>
          <span className="calc-highlight-sub">${fmt(result.vat_cost_usd)}</span>
        </div>
      </div>

      {/* 비용 분해 */}
      <div className="calc-landed-breakdown">
        <h3 className="calc-section-title">도착원가 구성</h3>
        <table className="calc-stages-table">
          <tbody>
            <tr>
              <td className="calc-stage-label">CIF 금액</td>
              <td className="calc-stage-amount">${fmt(result.cif_usd)}</td>
              <td className="calc-stage-krw">{fmtKRW(result.cif_krw)}</td>
            </tr>
            <tr>
              <td className="calc-stage-label">+ 관세 ({(result.tariff_rate * 100).toFixed(1)}%)</td>
              <td className="calc-stage-amount">${fmt(result.tariff_cost_usd)}</td>
              <td className="calc-stage-krw">{fmtKRW(result.tariff_cost_krw)}</td>
            </tr>
            <tr>
              <td className="calc-stage-label">+ 현지 부가세 ({(result.vat_rate * 100).toFixed(0)}%)</td>
              <td className="calc-stage-amount">${fmt(result.vat_cost_usd)}</td>
              <td className="calc-stage-krw">{fmtKRW(result.vat_cost_krw)}</td>
            </tr>
            <tr>
              <td className="calc-stage-label">+ 현지 통관비</td>
              <td className="calc-stage-amount">${fmt(result.local_customs_usd)}</td>
              <td className="calc-stage-krw">{fmtKRW(result.local_customs_krw)}</td>
            </tr>
            <tr className="is-stage">
              <td className="calc-stage-label">= 도착원가</td>
              <td className="calc-stage-amount">${fmt(result.landed_usd)}</td>
              <td className="calc-stage-krw">{fmtKRW(result.landed_krw)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* FTA 절감 */}
      {result.has_fta && (
        <div className="calc-fta-section">
          <h3 className="calc-section-title">FTA 적용 시 절감액</h3>
          <div className="calc-fta-card">
            <div className="calc-fta-row">
              <span>기본 관세율</span>
              <span>{(result.tariff_rate * 100).toFixed(1)}%</span>
            </div>
            <div className="calc-fta-row">
              <span>FTA 협정세율</span>
              <span>{(result.fta_rate * 100).toFixed(1)}%</span>
            </div>
            <div className="calc-fta-row calc-fta-row--saving">
              <span>절감액</span>
              <span>${fmt(result.fta_saving_usd)} ({fmtKRW(result.fta_saving_krw)})</span>
            </div>
          </div>
        </div>
      )}

      {/* 추정치 경고 */}
      {result.is_fallback && (
        <div className="calc-warning">
          ⚠️ 기본 관세율(5%)이 적용되었습니다. 정확한 관세율은 HS코드와 도착국에 따라 다릅니다.
        </div>
      )}

      {/* 면책 문구 */}
      <p className="calc-note-inline">
        관세율은 HS코드·도착국 조합 기준 추정치입니다. 정확한 세율은 관세청 또는 포워더에 확인하세요.
      </p>

      {/* CTA */}
      <div className="calc-cta">
        <p className="calc-cta-text">
          이 HS코드로 잠재 바이어를 찾아보시겠어요?
        </p>
        <button className="ui-button ui-button--solid calc-cta-button">
          HS코드로 바이어 찾기 →
        </button>
      </div>
    </div>
  ) : (
    <div className="calc-result-empty">
      <p>HS코드와 도착국을 입력하고 <strong>계산하기</strong>를 눌러 보세요.</p>
    </div>
  )

  return (
    <CalcShell
      title="바이어 도착원가 계산기"
      description="상대국 관세·부가세를 더해 바이어가 실제 부담할 금액을 계산합니다"
      tabs={TABS}
      activeTab="landed-cost"
      onTabChange={(id) => onNavigate(id)}
      onBack={onBack}
      result={resultNode}
    >
      <div className="calc-form">
        <label className="calc-field">
          <span className="calc-field-label">HS코드 (6자리)</span>
          <input
            type="text"
            value={form.hs_code}
            onChange={set('hs_code')}
            className="calc-input"
            placeholder="예: 330499 (화장품)"
            maxLength={6}
          />
        </label>

        <div className="calc-field">
          <span className="calc-field-label">도착국</span>
          <div className="calc-country-grid">
            {COUNTRIES.map((c) => (
              <button
                key={c.code}
                className={`calc-country-card${form.country === c.code ? ' is-selected' : ''}`}
                onClick={() => setForm({ ...form, country: c.code })}
              >
                <span className="calc-country-flag">{c.flag}</span>
                <span className="calc-country-name">{c.name}</span>
              </button>
            ))}
          </div>
        </div>

        <label className="calc-field">
          <span className="calc-field-label">CIF 금액</span>
          <div className="calc-input-row">
            <input type="number" value={form.cif_usd} onChange={set('cif_usd')} className="calc-input" />
            <span className="calc-input-suffix">USD</span>
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
