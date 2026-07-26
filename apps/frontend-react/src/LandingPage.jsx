import {
  ArrowRight,
  BarChart3,
  ChartNoAxesCombined,
  Clock,
  Database,
  Globe2,
  MapPin,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Heart,
  Shirt,
} from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";
import { resolveProductToHs } from "./lib/hsKeywordMap";

const trustMetrics = [
  { icon: Globe2, value: "20+", label: "분석 대상 국가" },
  { icon: Search, value: "6자리", label: "HS 코드 정밀 분석" },
  { icon: Database, value: "실제 데이터", label: "KOTRA · 무역통계 기반" },
  { icon: BarChart3, value: "5가지", label: "핵심 추천 지표" },
];

const problemQuestions = [
  { icon: MapPin, text: "어느 국가에 팔아야 할지 모르겠나요?" },
  { icon: Clock, text: "바이어 후보를 찾는 데 시간이 오래 걸리나요?" },
  { icon: Target, text: "수출 가능성을 빠르게 검토하고 싶나요?" },
];

const valueItems = [
  {
    icon: TrendingUp,
    label: "시장성 분석",
    value: "HS 코드와 수출국 기준으로 유망 국가를 점수화",
  },
  {
    icon: Database,
    label: "HS/품목 기반",
    value: "6자리 HS 코드로 정교한 수출 적합도 측정",
  },
  {
    icon: Globe2,
    label: "국가별 기회 탐색",
    value: "GDP, 성장률, 거리, 무역실적을 종합 판단",
  },
  {
    icon: Users,
    label: "바이어 후보 추천",
    value: "추천 국가 기반 유력 바이어 숏리스트 제공",
  },
];

const workflowSteps = [
  {
    step: "01",
    title: "상품 정보 입력",
    description: "HS 코드와 수출국, 기준 연도를 입력합니다.",
  },
  {
    step: "02",
    title: "시장성 분석",
    description: "AI가 무역 데이터, GDP, 성장률, 거리 등을 종합해 점수를 계산합니다.",
  },
  {
    step: "03",
    title: "추천 국가 확인",
    description: "국가별 추천 점수와 핵심 지표를 바로 확인합니다.",
  },
  {
    step: "04",
    title: "바이어 후보 확인",
    description: "Top 추천 국가 기반 연락 가능한 바이어 후보를 매칭합니다.",
  },
  {
    step: "05",
    title: "문의/리포트 생성",
    description: "AI 초안 인콰이어리를 생성하고 PDF 리포트로 저장합니다.",
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

export default function LandingPage({
  onStartAnalysis,
  onStartFlow,
  onStartBuyerSearch,
  onStartOpportunities,
  onStartCompare,
}) {
  const [toast, setToast] = useState(null);
  const [query, setQuery] = useState("");

  // 검색-우선 메인: 제품명/HS코드를 입력하면 바이어 검색 흐름을 연다.
  // 입력값은 sessionStorage에 남겨 이후 검색 화면이 프리필로 활용할 수 있게 한다(없어도 동작).
  const handleSearch = (e) => {
    e?.preventDefault?.();
    const q = query.trim();
    if (q) {
      try {
        sessionStorage.setItem("mg_search_query", q);
      } catch {
        /* 저장 실패는 무시(시크릿 모드 등) */
      }
    }
    onStartBuyerSearch?.();
  };

  const handleChipClick = (item) => {
    if (item.available) {
      setQuery(`${item.label} ${item.hsCode}`);
      try {
        sessionStorage.setItem("mg_search_query", item.hsCode);
      } catch {
        /* noop */
      }
      onStartBuyerSearch?.();
    } else {
      setToast(
        `🚧 ${item.label}는 아직 준비 중이에요. 오픈되면 가장 먼저 알려드릴게요.`
      );
      setTimeout(() => setToast(null), 3000);
    }
  };

  // 하단 CTA: 검색창에 HS/키워드가 있으면 분석·바이어 화면으로 이어 준다.
  const resolveHsFromQuery = () => {
    const q = query.trim();
    if (!q) return null;
    const mapped = resolveProductToHs(q);
    if (mapped?.hsCode) return mapped.hsCode;
    const six = q.match(/\b(\d{6})\b/);
    if (six) return six[1];
    const fourToSix = q.match(/\b(\d{4,6})\b/);
    if (fourToSix) return fourToSix[1];
    return null;
  };

  const persistQueryForBuyerSearch = () => {
    const q = query.trim();
    if (!q) return;
    try {
      sessionStorage.setItem("mg_search_query", q);
    } catch {
      /* noop */
    }
  };

  const startAnalysis = () => {
    const hs = resolveHsFromQuery();
    onStartAnalysis?.(hs ? { hsCode: hs } : undefined);
  };

  const startBuyerSearch = () => {
    persistQueryForBuyerSearch();
    onStartBuyerSearch?.();
  };

  return (
    <div className="landing-page">
      <header className="landing-topbar">
        <div className="landing-brand">
          <span className="landing-brand-mark">MarketGate</span>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            className="ui-button ui-button--ghost"
            onClick={() => onStartOpportunities?.()}
          >
            구매신호 탐색
          </button>
          <button
            className="ui-button ui-button--ghost"
            onClick={() => onStartCompare?.()}
          >
            국가·바이어 비교
          </button>
          <button
            className="ui-button ui-button--ghost"
            onClick={startBuyerSearch}
          >
            바이어 검색
            <ArrowRight size={16} />
          </button>
        </div>
      </header>

      {/* === Hero === */}
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
            무엇을 수출하시나요?
          </motion.h1>
          <motion.p
            className="landing-hero-description"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.12 }}
          >
            HS 코드 기반으로 유망 수출국을 AI가 점수화하고,
            추천 국가별 실제 바이어 후보까지 매칭해 드립니다.
          </motion.p>

          <motion.form
            className="landing-search"
            onSubmit={handleSearch}
            initial={{ opacity: 0, y: 26 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.72, delay: 0.18 }}
          >
            <div className="landing-search-field">
              <Search size={20} className="landing-search-icon" aria-hidden="true" />
              <input
                className="landing-search-input"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="제품명 또는 HS 코드 입력  ·  예: 화장품 또는 330499"
                aria-label="제품명 또는 HS 코드로 수출국·바이어 검색"
                autoComplete="off"
              />
              <button type="submit" className="landing-search-button">
                검색
                <ArrowRight size={18} />
              </button>
            </div>
            <div className="landing-search-examples">
              <span className="landing-search-examples-label">바로 시작</span>
              {quickStartItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    type="button"
                    key={item.id}
                    className={`landing-search-chip ${
                      item.available ? "" : "landing-search-chip--soon"
                    }`}
                    onClick={() => handleChipClick(item)}
                    title={
                      item.available
                        ? `${item.label} (HS ${item.hsCode})로 검색`
                        : `${item.label} 준비 중`
                    }
                  >
                    <Icon size={15} />
                    <span>{item.label}</span>
                    <code>{item.hsCode}</code>
                    {!item.available && <em>준비중</em>}
                  </button>
                );
              })}
            </div>
          </motion.form>

          <motion.div
            className="landing-hero-note"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <ShieldCheck size={16} />
            <span>
              모든 추천은 KOTRA 수출입통계, 관세청, World Bank
              실제 데이터를 정량 분석한 결과입니다.
            </span>
          </motion.div>

          {toast && (
            <motion.div
              className="landing-toast"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {toast}
            </motion.div>
          )}
        </div>
      </section>

      {/* === Trust Metrics === */}
      <section className="landing-trust">
        <div className="landing-section-head">
          <p className="landing-section-kicker">Trust</p>
          <h2>실제 데이터 기반, 보수적인 지표로 신뢰를 만듭니다.</h2>
        </div>
        <div className="landing-trust-grid">
          {trustMetrics.map(({ icon: Icon, value, label }, index) => (
            <motion.div
              key={label}
              className="landing-trust-item"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.55, delay: index * 0.08 }}
            >
              <div className="landing-trust-icon">
                <Icon size={22} />
              </div>
              <strong>{value}</strong>
              <span>{label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* === Problem Questions === */}
      <section className="landing-problems">
        <div className="landing-section-head">
          <p className="landing-section-kicker">Pain Points</p>
          <h2>이런 고민, MarketGate가 해결해 드립니다.</h2>
        </div>
        <div className="landing-problem-list">
          {problemQuestions.map(({ icon: Icon, text }, index) => (
            <motion.div
              key={index}
              className="landing-problem-item"
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Icon size={24} />
              <p>{text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* === Value Props === */}
      <section className="landing-proof">
        <div className="landing-section-head">
          <p className="landing-section-kicker">Capabilities</p>
          <h2>수출 전 과정을 AI가 정리해 드립니다.</h2>
        </div>
        <div className="landing-proof-grid">
          {valueItems.map(({ icon: Icon, label, value }, index) => (
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

      {/* === Workflow === */}
      <section className="landing-detail">
        <div className="landing-section-head">
          <p className="landing-section-kicker">How It Works</p>
          <h2>상품 입력부터 바이어 매칭까지 5단계로 진행됩니다.</h2>
        </div>

        <div className="landing-workflow landing-workflow--5">
          {workflowSteps.map((row, index) => (
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

      {/* === Bottom CTA === */}
      <section className="landing-cta">
        <div>
          <p className="landing-section-kicker">Get Started</p>
          <h2>지금 상품 분석 시작하기</h2>
          <p>
            HS 코드만 입력하면 10초 만에 유망 국가와 바이어 후보를 확인하세요.
          </p>
        </div>
        <div className="landing-cta-actions">
          <button
            className="ui-button ui-button--ghost"
            onClick={() => onStartOpportunities?.()}
          >
            구매신호 탐색
          </button>
          <button
            className="ui-button ui-button--ghost"
            onClick={() => onStartCompare?.()}
          >
            비교 테이블
          </button>
          <button
            className="ui-button ui-button--ghost"
            onClick={startAnalysis}
          >
            유망국 분석
          </button>
          <button
            className="ui-button ui-button--ghost"
            onClick={() => onStartFlow?.()}
          >
            수출 플로우
          </button>
          <button
            className="ui-button ui-button--solid"
            onClick={startBuyerSearch}
          >
            바이어 검색 시작
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
