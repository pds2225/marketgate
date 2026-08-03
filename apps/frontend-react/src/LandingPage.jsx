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
  Cpu,
} from "lucide-react";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { resolveProductToHs } from "./lib/hsKeywordMap";
import api from "./lib/api";

function persistSearchQuery(value) {
  const q = String(value ?? "").trim();
  if (!q) return;
  try {
    sessionStorage.setItem("mg_search_query", q);
  } catch {
    /* 저장 실패는 무시(시크릿 모드 등) */
  }
}

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
    icon: Search,
    title: "상품 정보 입력",
    description: "HS 코드와 수출국, 기준 연도를 입력합니다.",
  },
  {
    step: "02",
    icon: BarChart3,
    title: "시장성 분석",
    description: "AI가 무역 데이터, GDP, 성장률, 거리 등을 종합해 점수를 계산합니다.",
  },
  {
    step: "03",
    icon: Globe2,
    title: "추천 국가 확인",
    description: "국가별 추천 점수와 핵심 지표를 바로 확인합니다.",
  },
  {
    step: "04",
    icon: Users,
    title: "바이어 후보 확인",
    description: "Top 추천 국가 기반 연락 가능한 바이어 후보를 매칭합니다.",
  },
  {
    step: "05",
    icon: ChartNoAxesCombined,
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
  { id: "kbeauty", icon: Sparkles, label: "K-뷰티", hsCode: "330499" },
  { id: "health", icon: Heart, label: "건강식품", hsCode: "210690" },
  { id: "kfashion", icon: Shirt, label: "K-패션", hsCode: "6203" },
  { id: "semi", icon: Cpu, label: "반도체", hsCode: "8541" },
];

export default function LandingPage({
  onStartAnalysis,
  onStartFlow,
  onStartBuyerSearch,
  onStartOpportunities,
  onStartCompare,
  onStartMyInquiries,
}) {
  const [query, setQuery] = useState("");

  // 유휴 상태의 백엔드는 첫 요청에 40초 이상 걸린다(프로덕션 실측 43.8초, 웜 0.67초).
  // 바이어 검색 화면에서도 깨우지만, 그 화면에 닿기까지의 시간만큼 늦다.
  // 랜딩은 모든 방문자의 첫 화면이므로 여기서 깨워 두면 가장 이르다.
  // 검색으로 이어지지 않아도 손해가 없는 단발 GET 이고, 실패는 무시한다
  // (워밍은 부가 조치이고 실제 안전망은 검색 화면의 상한·재시도다).
  useEffect(() => {
    api.get("/v1/health", { timeout: 90_000 }).catch(() => {});
  }, []);

  // 검색-우선 메인: 제품명/HS코드를 입력하면 바이어 검색 흐름을 연다.
  // 입력값은 sessionStorage에 남겨 이후 검색 화면이 프리필로 활용할 수 있게 한다(없어도 동작).
  const handleSearch = (e) => {
    e?.preventDefault?.();
    persistSearchQuery(query);
    onStartBuyerSearch?.();
  };

  const handleChipClick = (item) => {
    setQuery(`${item.label} ${item.hsCode}`);
    persistSearchQuery(item.hsCode);
    onStartBuyerSearch?.();
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

  const startAnalysis = () => {
    const hs = resolveHsFromQuery();
    onStartAnalysis?.(hs ? { hsCode: hs } : undefined);
  };

  const startBuyerSearch = () => {
    persistSearchQuery(query);
    onStartBuyerSearch?.();
  };

  return (
    <div className="landing-page">
      <header className="landing-topbar">
        <button
          type="button"
          className="landing-brand"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          aria-label="MarketGate 홈으로"
        >
          <span className="landing-brand-mark">MarketGate</span>
        </button>
        <nav className="landing-nav" aria-label="주요 메뉴">
          <button
            className="landing-nav-link"
            onClick={() => onStartMyInquiries?.()}
          >
            내 인콰이어리
          </button>
          <button
            className="landing-nav-link"
            onClick={() => onStartOpportunities?.()}
          >
            해외 수요 찾기
          </button>
          <button
            className="landing-nav-link"
            onClick={() => onStartCompare?.()}
          >
            국가·바이어 비교
          </button>
          <button
            className="landing-nav-cta"
            onClick={startBuyerSearch}
          >
            <Search size={17} aria-hidden="true" />
            바이어 검색
          </button>
        </nav>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <motion.h1
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65 }}
          >
            무엇을 수출하시나요?
          </motion.h1>
          <motion.p
            className="landing-hero-description"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.08 }}
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
                바이어 찾기
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
                    className="landing-search-chip"
                    onClick={() => handleChipClick(item)}
                    title={`${item.label} (HS ${item.hsCode})로 검색`}
                  >
                    <Icon size={15} />
                    <span>{item.label}</span>
                    <code>{item.hsCode}</code>
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
        </div>
      </section>

      <section className="landing-compare">
        <div className="landing-section-head">
          <h2>감이 아닌 데이터로, 수출 기회를 찾습니다.</h2>
          <p>
            흩어진 정보와 경험에 의존하던 수출 준비를 하나의 근거 있는
            의사결정 흐름으로 바꿉니다.
          </p>
        </div>
        <div className="landing-compare-grid">
          <div className="landing-compare-column landing-compare-column--muted">
            <h3>기존 방식의 한계</h3>
            <div className="landing-problem-list">
              {problemQuestions.map(({ icon: Icon, text }, index) => (
                <motion.div
                  key={text}
                  className="landing-problem-item"
                  initial={{ opacity: 0, x: -18 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, amount: 0.4 }}
                  transition={{ duration: 0.45, delay: index * 0.08 }}
                >
                  <Icon size={20} aria-hidden="true" />
                  <p>{text}</p>
                </motion.div>
              ))}
            </div>
          </div>
          <div className="landing-compare-divider" aria-hidden="true">
            <ArrowRight size={22} />
          </div>
          <div className="landing-compare-column landing-compare-column--accent">
            <h3>MarketGate로 해결</h3>
            <div className="landing-value-list">
              {valueItems.map(({ icon: Icon, label, value }, index) => (
                <motion.article
                  key={label}
                  className="landing-value-item"
                  initial={{ opacity: 0, x: 18 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, amount: 0.35 }}
                  transition={{ duration: 0.45, delay: index * 0.07 }}
                >
                  <Icon size={20} aria-hidden="true" />
                  <div>
                    <strong>{label}</strong>
                    <p>{value}</p>
                  </div>
                </motion.article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="landing-detail">
        <div className="landing-section-head">
          <h2>수출 전 과정을 하나의 흐름으로 연결합니다.</h2>
          <p>상품 입력부터 바이어 매칭과 문의 준비까지 순서대로 이어집니다.</p>
        </div>

        <ol className="landing-workflow landing-workflow--5">
          {workflowSteps.map((row, index) => {
            const StepIcon = row.icon;
            return (
              <motion.li
                key={row.step}
                className="landing-workflow-row"
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.4 }}
                transition={{ duration: 0.55, delay: index * 0.06 }}
              >
                <span className="landing-workflow-step">{row.step}</span>
                <span className="landing-workflow-icon" aria-hidden="true">
                  <StepIcon size={30} />
                </span>
                <div>
                  <h3>{row.title}</h3>
                  <p>{row.description}</p>
                </div>
              </motion.li>
            );
          })}
        </ol>

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

      <section className="landing-trust">
        <div className="landing-section-head">
          <h2>검증 가능한 데이터만 사용합니다.</h2>
        </div>
        <div className="landing-trust-grid">
          {trustMetrics.map(({ icon: Icon, value, label }, index) => (
            <motion.div
              key={label}
              className="landing-trust-item"
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.45, delay: index * 0.06 }}
            >
              <div className="landing-trust-icon">
                <Icon size={24} aria-hidden="true" />
              </div>
              <div>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="landing-cta">
        <div>
          <h2>수출 기회를 찾을 준비가 되셨나요?</h2>
          <p>
            HS 코드 하나로 유망 국가와 실제 바이어 후보를 확인하세요.
          </p>
        </div>
        <div className="landing-cta-actions">
          <button
            className="landing-cta-button landing-cta-button--secondary"
            onClick={startAnalysis}
          >
            유망국 분석
          </button>
          <button
            className="landing-cta-link"
            onClick={() => onStartFlow?.()}
          >
            수출 플로우
          </button>
          <button
            className="landing-cta-button landing-cta-button--primary"
            onClick={startBuyerSearch}
          >
            바이어 검색 시작
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      <footer className="landing-footer">
        <strong>MarketGate</strong>
        <span aria-hidden="true" />
        <p>HS 코드 기반 수출 유망국 추천 &amp; 바이어 매칭</p>
      </footer>
    </div>
  );
}
