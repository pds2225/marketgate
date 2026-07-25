import { useState } from "react";
import { motion } from "framer-motion";
import { Mail, Phone, Globe, HelpCircle, X } from "lucide-react";
import { displayPhone } from "./lib/phone";

// 검증 상태 3축 — 연락처 보유만으로 '검증 완료'를 표시하지 않는다
const contactStatusLabels = {
  unavailable: { emoji: "⚠️", label: "연락처 없음", desc: "자료 내 확인 불가" },
  discovered: { emoji: "🟡", label: "연락처 보유(미검증)", desc: "형식·소유 검증 전" },
  format_validated: { emoji: "🟢", label: "형식 검증됨", desc: "이메일 형식 검증 완료" },
  ownership_verified: { emoji: "✅", label: "소유 검증됨", desc: "수신자 소유 확인 완료" },
};
const tradeStatusLabels = {
  unavailable: { label: "수입실적 자료 내 확인 불가" },
  source_confirmed: { label: "출처 확인됨" },
  recent_activity_confirmed: { label: "최근 활동 확인됨" },
};
const creditStatusLabels = {
  not_requested: { label: "신용조사 미신청" },
  pending: { label: "신용조사 진행 중" },
  report_received: { label: "신용보고서 수신" },
  expired: { label: "신용보고서 만료" },
};

const fitCriteria = [
  {
    key: "trade_history",
    label: "수입 이력 매칭",
    desc: "공공데이터 내 거래·품목 신호와의 매칭 정도를 반영합니다.",
    source: "P1 스코어링 (KOTRA 공공데이터 CSV)",
  },
  {
    key: "growth",
    label: "시장 성장률",
    desc: "목표 국가의 GDP 성장률 지표를 반영합니다.",
    source: "World Bank WDI CSV",
  },
  {
    key: "gdp",
    label: "GDP 규모",
    desc: "시장 규모가 클수록 높은 점수.",
    source: "World Bank WDI CSV",
  },
  {
    key: "logistics",
    label: "거리/물류 이점",
    desc: "한국과의 거리 기반 물류 이점을 평가합니다.",
    source: "국가 간 거리 CSV",
  },
];

export default function BuyerReport({ buyer }) {
  const [showCriteria, setShowCriteria] = useState(false);
  const contact = contactStatusLabels[buyer.contactStatus] || contactStatusLabels.unavailable;
  const trade = tradeStatusLabels[buyer.tradeStatus] || tradeStatusLabels.unavailable;
  const credit = creditStatusLabels[buyer.creditStatus] || creditStatusLabels.not_requested;

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
          <p>공공데이터 CSV 기반 바이어 후보 분석 결과입니다. 수입실적·신용정보는 원본 자료에 포함되어 있지 않으며, 원본에 없는 값은 표시하지 않습니다.</p>
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
            <span><strong>전화</strong> {displayPhone(buyer.company.phone)}</span>
          </div>
          <div className="buyer-report-contact-row">
            <Globe size={16} />
            <span><strong>웹사이트</strong> {buyer.company.website}</span>
          </div>
          <div className="buyer-report-contact-status">
            {contact.emoji} {contact.label} — {contact.desc}
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

      {/* 검증 상태 — contact / trade / credit 분리 */}
      <section className="buyer-report-section">
        <h3 className="buyer-report-section-title">【검증 상태】</h3>
        <div className="buyer-report-trust">
          <div className={`buyer-report-trust-badge buyer-report-trust-badge--${buyer.contactStatus === "unavailable" ? "limited" : "estimated"}`}>
            <span className="buyer-report-trust-emoji">{contact.emoji}</span>
            <div>
              <strong>연락처: {contact.label}</strong>
              <p>거래(출처): {trade.label} · 신용: {credit.label}</p>
            </div>
          </div>
          <div className="buyer-report-trust-meta">
            <span>검증일: {buyer.lastVerified}</span>
            <span>원본 파일: {buyer.sourceFile}</span>
          </div>
        </div>
      </section>

      <div className="buyer-report-divider" />

      {/* 액션 버튼 — 발송 요청은 바이어 카드의 '발송 요청' 버튼에서 관리자 승인 큐로 접수된다 */}
      <div className="buyer-report-actions">
        <button className="buyer-report-action-btn" onClick={() => setShowCriteria(true)}>
          <HelpCircle size={16} />
          <span>적합도 산정 기준</span>
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
                <p>📌 데이터 갱신 주기·기준일: 원본 CSV 스냅샷 기준 — 자료 내 확인 불가 시 표시하지 않습니다.</p>
              </div>
            </div>
          </motion.div>
        </div>
      )}

    </div>
  );
}
