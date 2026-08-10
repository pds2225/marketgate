import { ArrowLeft } from 'lucide-react'

/**
 * 계산기 공통 껍데기.
 * 좌측: 입력 폼 / 우측: 결과 (모바일에서는 1단)
 */
export default function CalcShell({
  title,
  description,
  tabs,
  activeTab,
  onTabChange,
  onBack,
  children,   // 좌측 입력
  result,     // 우측 결과
  footer,     // 하단 면책·링크
}) {
  return (
    <div className="calc-shell">
      {/* 상단 */}
      <div className="calc-header">
        <button className="calc-back" onClick={onBack}>
          <ArrowLeft size={18} />
          계산기 허브
        </button>
        <h1 className="calc-title">{title}</h1>
        <p className="calc-desc">{description}</p>

        {/* 탭 네비게이션 */}
        {tabs && (
          <nav className="calc-tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={`calc-tab${activeTab === tab.id ? ' is-active' : ''}`}
                onClick={() => onTabChange(tab.id)}
              >
                <span className="calc-tab-icon">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        )}
      </div>

      {/* 본문 */}
      <div className="calc-body">
        <div className="calc-input-panel">{children}</div>
        <div className="calc-result-panel">{result}</div>
      </div>

      {/* 하단 */}
      {footer && <div className="calc-footer">{footer}</div>}
    </div>
  )
}
