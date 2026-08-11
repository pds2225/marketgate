import { Calculator, Package, Percent, ArrowRightLeft, Weight, TrendingUp, BarChart3, Search, CheckCircle } from 'lucide-react'

const calculators = [
  {
    id: 'export-price',
    title: '수출단가 계산기',
    desc: '공장도가에서 FOB·CIF까지 단계별로 얼마인지 계산합니다',
    icon: '$',
    priority: 'MVP',
  },
  {
    id: 'cbm',
    title: 'CBM · 컨테이너',
    desc: '박스 크기와 수량으로 부피와 컨테이너 적재율을 확인합니다',
    icon: 'm³',
    priority: 'MVP',
  },
  {
    id: 'landed-cost',
    title: '바이어 도착원가',
    desc: '상대국 관세·부가세를 더해 바이어가 실제 부담할 금액을 봅니다',
    icon: '%',
    priority: 'MVP',
  },
  {
    id: 'logistics-compare',
    title: '물류비 비교',
    desc: '해상과 항공 중 어느 쪽이 싼지 리드타임과 함께 비교합니다',
    icon: '⇄',
    priority: 'P1',
  },
  {
    id: 'air-chargeable',
    title: '항공 청구중량',
    desc: '실제 무게와 부피 무게 중 무엇으로 청구되는지 확인합니다',
    icon: 'kg',
    priority: 'P1',
  },
  {
    id: 'fx-margin',
    title: '환율 손익',
    desc: '환율이 오르내릴 때 원화 수익이 얼마나 흔들리는지 봅니다',
    icon: '₩',
    priority: 'P1',
  },
  {
    id: 'bep',
    title: '손익분기 수량',
    desc: '몇 개를 팔아야 남는지, 목표 마진을 맞추려면 얼마에 팔지',
    icon: 'BEP',
    priority: 'P1',
  },
  {
    id: 'hs-search',
    title: 'HS코드 조회',
    desc: '품목 이름으로 HS코드 후보를 찾습니다',
    icon: 'HS',
    priority: 'P2',
  },
  {
    id: 'export-req',
    title: '수출요건 체크',
    desc: '도착국이 요구하는 인증과 서류를 체크리스트로 봅니다',
    icon: '✓',
    priority: 'P2',
  },
]

export default function CalculatorHubPage({ onNavigate, onBack }) {
  return (
    <div className="calc-hub">
      <div className="calc-hub-header">
        <button className="calc-hub-back" onClick={onBack}>
          ← 홈으로
        </button>
        <h1 className="calc-hub-title">수출 계산기</h1>
        <p className="calc-hub-subtitle">
          가입 없이 바로 쓰는 수출 실무 계산기 9종 · 계산 결과는 그대로 바이어 매칭으로 이어집니다
        </p>
      </div>

      <div className="calc-hub-grid">
        {calculators.map((calc) => {
          const isMVP = calc.priority === 'MVP'
          const isReady = isMVP
          return (
            <button
              key={calc.id}
              className={`calc-hub-card${isMVP ? ' calc-hub-card--mvp' : ''}`}
              onClick={() => isReady && onNavigate(calc.id)}
              disabled={!isReady}
            >
              <div className="calc-hub-card-icon">{calc.icon}</div>
              <div className="calc-hub-card-body">
                <h3 className="calc-hub-card-title">
                  {calc.title}
                  {isMVP && <span className="calc-hub-badge">MVP</span>}
                  {!isMVP && <span className="calc-hub-badge calc-hub-badge--soon">{calc.priority}</span>}
                </h3>
                <p className="calc-hub-card-desc">{calc.desc}</p>
              </div>
            </button>
          )
        })}
      </div>

      {/* 하단 CTA */}
      <div className="calc-hub-cta">
        <p className="calc-hub-cta-text">
          계산은 끝났고, 이제 살 사람을 찾을 차례입니다
        </p>
        <button className="ui-button ui-button--solid calc-hub-cta-button">
          HS코드로 바이어 찾기 →
        </button>
      </div>
    </div>
  )
}
