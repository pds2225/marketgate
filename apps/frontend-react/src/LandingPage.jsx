import {
  ArrowRight,
  ChartNoAxesCombined,
  Database,
  Globe2,
  MoveRight,
  Orbit,
  ShieldCheck,
  Sparkles,
  Heart,
  Shirt,
} from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

const proofItems = [
  {
    icon: Globe2,
    label: "추천 엔진",
    value: "HS 코드와 수출국 기준으로 유망 국가를 점수화",
  },
  {
    icon: Database,
    label: "근거 데이터",
    value: "KOTRA, 무역실적, GDP, 성장률, 국가 간 거리 결합",
  },
  {
    icon: ShieldCheck,
    label: "현재 구조",
    value: "DB 없이 CSV 파일을 직접 읽는 1차 버전",
  },
];

const workflowRows = [
  {
    step: "01",
    title: "품목 입력",
    description:
      "HS 코드(국제 상품 분류 코드)와 수출국을 넣으면 분석이 시작됩니다.",
  },
  {
    step: "02",
    title: "지표 결합",
    description:
      "국가코드, 무역 데이터, GDP, 성장률, 거리 정보를 한 줄의 점수로 합칩니다.",
  },
  {
    step: "03",
    title: "추천 결과",
    description:
      "국가별 추천 점수와 함께 왜 추천됐는지 핵심 지표를 바로 보여줍니다.",
  },
];

const sourceNotes = [
  "KOTRA 추천 데이터",
  "외교부 국가표준코드",
  "무역 실적",
  "GDP / GDP 성장률",
  "국가 간 거리",
];

const quickStartItems = [
  {
    id: "kbeauty",
    icon: Sparkles,
    label: "K-뷰티",
    sub: "지금 시작",
    hsCode: "330499",
    available: true,
  },
  {
    id: "health",
    icon: Heart,
    label: "건강식품",
    sub: "곧 만나요",
    hsCode: "210690",
    available: false,
  },
  {
    id: "kfashion",
    icon: Shirt,
    label: "K-패션",
    sub: "곧 만나요",
    hsCode: "611030",
    available: false,
  },
];

export default function LandingPage({ onStartAnalysis, onStartChat, onStartFlow }) {
  const [toast, setToast] = useState(null);

  const handleChipClick = (item) => {
    if (item.available) {
      onStartChat?.({ hsCode: item.hsCode, category: item.label });
    } else {
      setToast(`🚧 ${item.label}는 아직 준비 중이에요. 오픈되면 가장 먼저 알려드릴게요.`);
      setTimeout(() => setToast(null), 3000);
    }
  };

  return (
    <div className="landing-page">
      <header className="landing-topbar">
        <div className="landing-brand">
          <span className="landing-brand-mark">MarketGate</span>
        </div>
        <button className="ui-button ui-button--ghost" onClick={() => onStartChat?.()}>
          분석 시작
          <ArrowRight size={16} />
        </button>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <motion.p
            className="landing-kicker"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
          >
            Export Intelligence Platform
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.05 }}
          >
            MarketGate
          </motion.h1>
          <motion.p
            className="landing-hero-description"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.12 }}
          >
            이 화면은 바이어 업체를 직접 연결하는 기능이 아니라, 먼저 어떤 나라가
            유망한지 선별하는 분석 도구입니다. API는 다른 프로그램이 이 기능을
            호출하는 통로이고, CSV는 엑셀과 비슷한 데이터 파일입니다.
          </motion.p>

          <motion.div
            className="landing-data-banner"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.16 }}
          >
            <ShieldCheck size={16} />
            <span>
              <strong>ChatGPT와 다릅니다.</strong> 모든 추천은 KOTRA 수출입통계, 관세청, World Bank
              실제 데이터를 정량 분석한 결과입니다.
            </span>
          </motion.div>

          <motion.div
            className="landing-hero-actions"
            initial={{ opacity: 0, y: 26 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.72, delay: 0.18 }}
          >
            <button className="ui-button ui-button--solid" onClick={() => onStartChat?.()}>
              추천 결과 보기
              <MoveRight size={18} />
            </button>
            <div className="landing-hero-note">
              <Orbit size={18} />
              <span>HS 코드 6자리 기준으로 더 정교한 추천 시도</span>
            </div>
          </motion.div>
        </div>

        <motion.aside
          className="landing-signal-rail"
          initial={{ opacity: 0, x: 28 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.75, delay: 0.16 }}
        >
          <div className="landing-signal-card landing-signal-card--accent">
            <span className="landing-signal-label">현재 초점</span>
            <strong>바이어 발굴보다 유망 국가 선별</strong>
            <p>수출 후보국을 1차로 걸러내는 판단 보조 화면입니다.</p>
          </div>
          <div className="landing-signal-card">
            <span className="landing-signal-label">입력</span>
            <strong>HS 코드 + 수출국 + 연도 + 제외 국가</strong>
          </div>
          <div className="landing-signal-card">
            <span className="landing-signal-label">출력</span>
            <strong>추천 국가 목록과 점수</strong>
          </div>
        </motion.aside>
      </section>

      {/* Quick Start Chips */}
      <section className="landing-quickstart">
        <div className="landing-section-head">
          <p className="landing-section-kicker">Quick Start</p>
          <h2>아래에서 바로 시작하거나, 직접 입력해 보세요.</h2>
        </div>
        <div className="landing-quickstart-grid">
          {quickStartItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <motion.button
                key={item.id}
                className={`landing-quickstart-chip ${item.available ? "" : "landing-quickstart-chip--soon"}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                onClick={() => handleChipClick(item)}
              >
                <Icon size={28} />
                <div className="landing-quickstart-chip-info">
                  <strong>{item.label}</strong>
                  <span>{item.sub}</span>
                </div>
                {!item.available && <span className="landing-quickstart-soon-badge">Coming Soon</span>}
              </motion.button>
            );
          })}
        </div>
        {toast && (
          <motion.div
            className="landing-toast"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            {toast}
          </motion.div>
        )}
      </section>

      <section className="landing-proof">
        <div className="landing-section-head">
          <p className="landing-section-kicker">What Is Built</p>
          <h2>이미 구현된 핵심은 분석 파이프라인입니다.</h2>
        </div>
        <div className="landing-proof-grid">
          {proofItems.map(({ icon: Icon, label, value }, index) => (
            <motion.article
              key={label}
              className="landing-proof-card"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.55, delay: index * 0.08 }}
            >
              <div className="landing-proof-icon">
                <Icon size={20} />
              </div>
              <span>{label}</span>
              <strong>{value}</strong>
            </motion.article>
          ))}
        </div>
      </section>

      <section className="landing-detail">
        <div className="landing-section-head">
          <p className="landing-section-kicker">How It Reads</p>
          <h2>화면은 복잡한 모델 설명보다, 의사결정 흐름이 먼저 보이게 설계합니다.</h2>
        </div>

        <div className="landing-workflow">
          {workflowRows.map((row, index) => (
            <motion.div
              key={row.step}
              className="landing-workflow-row"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 0.55, delay: index * 0.06 }}
            >
              <span className="landing-workflow-step">{row.step}</span>
              <div>
                <h3>{row.title}</h3>
                <p>{row.description}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="landing-source-line">
          <div className="landing-source-copy">
            <ChartNoAxesCombined size={18} />
            <span>추천 점수는 아래 데이터 묶음을 합쳐 계산합니다.</span>
          </div>
          <div className="landing-source-tags">
            {sourceNotes.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-cta">
        <div>
          <p className="landing-section-kicker">Full Export Flow</p>
          <h2>국가 추천부터 주문서까지 한 번에.</h2>
          <p>수출 전 과정 One-Stop 플로우를 체험해 보세요.</p>
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button className="ui-button ui-button--solid" onClick={onStartFlow}>
            수출 플로우 시작
            <ArrowRight size={18} />
          </button>
          <button className="ui-button ui-button--ghost" onClick={onStartAnalysis}>
            분석 작업면 열기
            <ArrowRight size={18} />
          </button>
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button className="ui-button ui-button--solid" onClick={onStartFlow}>
            수출 플로우 시작
            <ArrowRight size={18} />
          </button>
          <button className="ui-button ui-button--ghost" onClick={onStartAnalysis}>
            분석 작업면 열기
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      <footer className="landing-footer">
        <span>MarketGate</span>
        <span>HS 코드 기반 수출 유망국 추천 & 바이어 매칭</span>
      </footer>
    </div>
  );
}
