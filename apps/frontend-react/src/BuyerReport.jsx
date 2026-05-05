import { useState } from "react";
import { motion } from "framer-motion";
import { Mail, Phone, Globe, FileText, HelpCircle, ChevronLeft, ChevronRight, X } from "lucide-react";

const trustLabels = {
  verified: { emoji: "✅", label: "검증됨", desc: "공공데이터 직접 확인" },
  estimated: { emoji: "🟡", label: "추정", desc: "AI 분석 · 샘플 부족" },
  limited: { emoji: "🔴", label: "제한적", desc: "단일 출처 · 미확인" },
};

const fitCriteria = [
  {
    key: "trade_history",
    label: "수입 이력 매칭",
    desc: "해당 HS 코드의 과거 수입 실적이 많을수록 높은 점수를 받습니다.",
    source: "KOTRA 수출입통계 · 관세청",
  },
  {
    key: "growth",
    label: "시장 성장률",
    desc: "목표 국가의 해당 품목 수입 성장률을 반영합니다. 성장 중인 시장에 가점.",
    source: "UN Comtrade · World Bank",
  },
  {
    key: "gdp",
    label: "GDP 규모",
    desc: "시장 규모가 클수록 높은 점수.",
    source: "World Bank Open Data",
  },
  {
    key: "logistics",
    label: "거리/물류 이점",
    desc: "한국과의 거리, FTA 혜택, 물류 인프라를 종합 평가합니다.",
    source: "KOTRA · 대한무역투자진흥공사",
  },
];

export default function BuyerReport({ buyer }) {
  const [showCriteria, setShowCriteria] = useState(false);
  const [showInquiry, setShowInquiry] = useState(false);
  const trust = trustLabels[buyer.trustStatus] || trustLabels.limited;

  const scoreColor = buyer.fitScore >= 90 ? "#22c55e" : buyer.fitScore >= 75 ? "#f59e0b" : "#ef4444";

  return (
    <div className="buyer-report">
      <div className="buyer-report-header">
        <div className="buyer-report-id">
          <span className="buyer-report-badge">📄 MARKETGATE BUYER ANALYSIS REPORT</span>
          <span className="buyer-report-meta">리포트 ID: {buyer.reportId}</span>
        </div>
        <div className="buyer-report-meta-line">
          <span>발행일: {buyer.issuedAt}</span>
          <span>데이터 기준일: {buyer.dataDate}</span>
        </div>
        <div className="buyer-report-target">
          분석 대상: {buyer.targetCountry} ({buyer.targetCountryIso3}) · HS {buyer.hsCode} ({buyer.hsLabel})
        </div>
        <div className="buyer-report-data-banner">
          <span>🛡️</span>
          <p>이 보고서는 AI가 생성한 것이 아닙니다. KOTRA, 관세청, World Bank 실제 데이터를 정량 분석하여 산출한 결과입니다.</p>
        </div>
      </div>

      <div className="buyer-report-divider" />

      {/* 기본 프로필 */}
      <section className="buyer-report-section">
        <h3 className="buyer-report-section-title">【기본 프로필】</h3>
        <div className="buyer-report-profile">
          <div className="buyer-report-profile-main">
            <h2 className="buyer-report-company">{buyer.company.name}</h2>
            <p className="buyer-report-normalized">({buyer.company.normalizedName})</p>
          </div>
          <div className="buyer-report-profile-grid">
            <div><strong>업종</strong><span>{buyer.company.industry}</span></div>
            <div><strong>국가/지역</strong><span>🇩🇪 {buyer.company.country} · {buyer.company.region}</span></div>
            <div><strong>데이터 출처</strong><span>{buyer.dataSource}</span></div>
            <div><strong>원본 추적</strong><span>{buyer.sourceFile} / row {buyer.sourceRow}</span></div>
            <div><strong>데이터 수집일</strong><span>{buyer.lastVerified}</span></div>
          </div>
        </div>
      </section>

      {/* 연락처 정보 */}
      <section className="buyer-report-section">
        <h3 className="buyer-report-section-title">【연락처 정보】</h3>
        <div className="buyer-report-contact">
          <div className="buyer-report-contact-row">
            <Mail size={16} />
            <span><strong>담당자</strong> {buyer.company.contactName}</span>
          </div>
          <div className="buyer-report-contact-row">
            <Mail size={16} />
            <span><strong>이메일</strong> {buyer.company.email}</span>
          </div>
          <div className="buyer-report-contact-row">
            <Phone size={16} />
            <span><strong>전화</strong> {buyer.company.phone}</span>
          </div>
          <div className="buyer-report-contact-row">
            <Globe size={16} />
            <span><strong>웹사이트</strong> {buyer.company.website}</span>
          </div>
          <div className="buyer-report-contact-status">
            {buyer.company.hasContact ? "✅ 연락처 확인됨" : "⚠️ 연락처 미확인"}
          </div>
        </div>
      </section>

      {/* 수출 적합도 분석 */}
      <section className="buyer-report-section">
        <h3 className="buyer-report-section-title">【수출 적합도 분석】</h3>
        <div className="buyer-report-fit">
          <div className="buyer-report-fit-score">
            <div className="buyer-report-fit-number" style={{ color: scoreColor }}>
              {buyer.fitScore}점
            </div>
            <div className="buyer-report-fit-label">
              {buyer.fitScore >= 90 ? "🟢 매우 적합" : buyer.fitScore >= 75 ? "🟡 적합" : "🔴 검토 필요"}
            </div>
          </div>
          <div className="buyer-report-fit-bars">
            {Object.entries(buyer.fitBars).map(([key, bar]) => {
              const crit = fitCriteria.find((c) => c.key === key);
              return (
                <div key={key} className="buyer-report-fit-bar-row">
                  <span className="buyer-report-fit-bar-label">{crit?.label || key}</span>
                  <div className="buyer-report-fit-bar-track">
                    <div
                      className="buyer-report-fit-bar-fill"
                      style={{ width: `${(bar.length / 16) * 100}%`, backgroundColor: scoreColor }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 매칭 상세 */}
      <section className="buyer-report-section">
        <h3 className="buyer-report-section-title">【매칭 상세】</h3>
        <div className="buyer-report-match">
          <div className="buyer-report-match-row">
            <strong>매칭 HS 코드</strong>
            <span>{buyer.hsCode} ({buyer.hsLabel})</span>
          </div>
          <div className="buyer-report-match-row">
            <strong>매칭 키워드</strong>
            <div className="buyer-report-tags">
              {buyer.matchedTerms.map((t) => (
                <span key={t} className="buyer-report-tag">{t}</span>
              ))}
            </div>
          </div>
          <div className="buyer-report-match-row">
            <strong>추천 이유</strong>
            <ol className="buyer-report-reasons">
              {buyer.recommendations.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* 데이터 신뢰도 */}
      <section className="buyer-report-section">
        <h3 className="buyer-report-section-title">【데이터 신뢰도】</h3>
        <div className="buyer-report-trust">
          <div className={`buyer-report-trust-badge buyer-report-trust-badge--${buyer.trustStatus}`}>
            <span className="buyer-report-trust-emoji">{trust.emoji}</span>
            <div>
              <strong>{trust.label}</strong>
              <p>{trust.desc}</p>
            </div>
          </div>
          <div className="buyer-report-trust-meta">
            <span>최종 확인: {buyer.lastVerified}</span>
            <span>원본 파일: {buyer.sourceFile}</span>
          </div>
        </div>
      </section>

      <div className="buyer-report-divider" />

      {/* 액션 버튼 */}
      <div className="buyer-report-actions">
        <button className="buyer-report-action-btn" onClick={() => setShowCriteria(true)}>
          <HelpCircle size={16} />
          <span>적합도 산정 기준</span>
        </button>
        <button className="buyer-report-action-btn buyer-report-action-btn--primary" onClick={() => setShowInquiry(true)}>
          <Mail size={16} />
          <span>인콰이어리 작성</span>
        </button>
      </div>

      {/* 적합도 기준 모달 */}
      {showCriteria && (
        <div className="buyer-report-modal-overlay" onClick={() => setShowCriteria(false)}>
          <motion.div
            className="buyer-report-modal"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="buyer-report-modal-header">
              <h3>❓ 적합도는 어떻게 계산되나요?</h3>
              <button onClick={() => setShowCriteria(false)}><X size={18} /></button>
            </div>
            <div className="buyer-report-modal-body">
              <p>이 점수는 아래 4가지 지표를 종합 평가하여 산출합니다. 모든 지표는 동일한 척도로 정규화 후 가중합됩니다.</p>
              {fitCriteria.map((c) => (
                <div key={c.key} className="buyer-report-criteria-item">
                  <h4>{c.label}</h4>
                  <p>{c.desc}</p>
                  <span className="buyer-report-criteria-source">출처: {c.source}</span>
                </div>
              ))}
              <div className="buyer-report-criteria-footer">
                <p>📌 데이터 업데이트 주기: 분기별 (1/4/7/10월)</p>
                <p>📌 최종 업데이트: 2026년 4월</p>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* 인콰이어리 모달 */}
      {showInquiry && (
        <div className="buyer-report-modal-overlay" onClick={() => setShowInquiry(false)}>
          <motion.div
            className="buyer-report-modal buyer-report-modal--large"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="buyer-report-modal-header">
              <h3>✉️ 인콰이어리 작성 — {buyer.company.name}</h3>
              <button onClick={() => setShowInquiry(false)}><X size={18} /></button>
            </div>
            <div className="buyer-report-modal-body">
              <div className="buyer-report-inquiry-meta">
                <p><strong>받는 사람:</strong> {buyer.company.email}</p>
                <p><strong>제품:</strong> {buyer.hsLabel} (HS {buyer.hsCode})</p>
                <p><strong>적합도:</strong> {buyer.fitScore}점 {trust.emoji} ({buyer.dataSource})</p>
              </div>
              <div className="buyer-report-inquiry-sequence">
                <h4>캠페인 시퀀스 설정</h4>
                <label><input type="checkbox" defaultChecked /> 1차: 즉시 발송</label>
                <label><input type="checkbox" defaultChecked /> 2차: 3일 후 (미응답 시)</label>
                <label><input type="checkbox" defaultChecked /> 3차: 7일 후 (미응답 시)</label>
              </div>
              <div className="buyer-report-inquiry-draft">
                <h4>1차 메일 초안</h4>
                <p><strong>Subject:</strong> Partnership Inquiry — Korean {buyer.hsLabel}</p>
                <textarea
                  className="buyer-report-draft-textarea"
                  rows={6}
                  defaultValue={`Dear ${buyer.company.name} Team,

We are a Korean ${buyer.hsLabel} manufacturer looking to expand into the ${buyer.targetCountry} market.

We believe our products would be a great fit for your distribution channel based on your recent import activities.

Would you be open to a brief call to explore a potential partnership?

Best regards,`}
                />
              </div>
              <div className="buyer-report-inquiry-actions">
                <button className="buyer-report-action-btn" onClick={() => setShowInquiry(false)}>취소</button>
                <button className="buyer-report-action-btn buyer-report-action-btn--primary">🚀 1차 발송</button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
