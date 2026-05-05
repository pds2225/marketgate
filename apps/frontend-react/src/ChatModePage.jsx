import { useState, useRef, useEffect } from "react";
import { ArrowLeft, Send, Mic, LayoutTemplate } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import BuyerReport from "./BuyerReport";
import { API_BASE, buildApiUrl } from "./config";

const quickStartItems = [
  { id: "kbeauty", label: "K-뷰티", hsCode: "330499", available: true, status: "지금 시작" },
  { id: "health", label: "건강식품", hsCode: "210690", available: false, status: "Coming Soon" },
  { id: "kfashion", label: "K-패션", hsCode: "611030", available: false, status: "Coming Soon" },
];

const dummyMessages = [
  {
    id: 1,
    role: "assistant",
    text: "안녕하세요. 어떤 제품의 해외 바이어를 찾아드릴까요? 아래 GTM Pack에서 바로 시작하거나, 직접 입력해 주세요.",
  },
];

function buildBuyerReportFromApi(item, hsLabel) {
  const today = new Date();
  const dateStr = `${today.getFullYear()}년 ${today.getMonth() + 1}월 ${today.getDate()}일`;
  const dataDateStr = `${today.getFullYear()}년 ${today.getMonth() + 1}월`;

  const score = item.final_score ?? 0;
  const bars = item.score_breakdown || {};
  const toBar = (val) => {
    const n = Math.max(0, Math.min(1, Number(val) || 0));
    const filled = Math.round(n * 16);
    return "█".repeat(filled) + "░".repeat(16 - filled);
  };

  return {
    reportId: `#MG-${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, "0")}${String(today.getDate()).padStart(2, "0")}-${Math.floor(Math.random() * 900 + 100)}`,
    issuedAt: dateStr,
    targetCountry: item.source_target_country_name || item.country_norm || "미확인",
    targetCountryIso3: item.source_target_country_iso3 || "",
    hsCode: item.hs_code_norm || "",
    hsLabel: hsLabel || "수출품목",
    dataDate: dataDateStr,
    company: {
      name: item.buyer_name || "이름 미확인",
      normalizedName: (item.buyer_name || "").toLowerCase(),
      industry: item.source_dataset || "유통/바이어",
      region: item.country_norm || "미확인",
      country: item.source_target_country_name || item.country_norm || "미확인",
      contactName: item.contact_name || "-",
      email: item.contact_email || "",
      phone: item.contact_phone || "",
      website: item.contact_website || "",
      hasContact: !!item.has_contact,
    },
    fitScore: Math.round(score),
    fitBars: {
      trade_history: toBar(bars.trade_history_score ?? bars.trade_volume_score ?? score / 100),
      growth: toBar(bars.growth_score ?? score / 100),
      gdp: toBar(bars.gdp_score ?? score / 100),
      logistics: toBar(bars.distance_score ?? score / 100),
    },
    matchedTerms: item.matched_terms || [],
    recommendations: item.recommendation_lines?.length
      ? item.recommendation_lines
      : item.explanation_reasons?.length
        ? item.explanation_reasons
        : ["해당 바이어는 추천 점수 기준으로 선정되었습니다."],
    dataSource: item.source_dataset || "KOTRA 글로벌 바이어 정보",
    sourceFile: item.source_dataset ? `${item.source_dataset}.csv` : "-",
    sourceRow: "-",
    lastVerified: dateStr,
    trustStatus: item.has_contact ? "verified" : "estimated",
  };
}

async function fetchPredict(hsCode) {
  const res = await fetch(buildApiUrl("/v1/predict", API_BASE), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hs_code: hsCode,
      exporter_country_iso3: "KOR",
      top_n: 5,
      year: 2023,
      filters: { min_trade_value_usd: 0 },
    }),
  });
  if (!res.ok) throw new Error("분석 요청에 실패했습니다.");
  const payload = await res.json();
  const buyers = payload?.data?.buyers;
  if (!buyers || buyers.status !== "ok" || !buyers.items?.length) {
    throw new Error("현재 조건에 맞는 바이어를 찾지 못했습니다.");
  }
  return buyers;
}

export default function ChatModePage({ preset, onBack, onSwitchToForm, onStartWizard }) {
  const [messages, setMessages] = useState(dummyMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [currentBuyer, setCurrentBuyer] = useState(null);
  const [apiError, setApiError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (preset?.hsCode) {
      const item = quickStartItems.find((i) => i.hsCode === preset.hsCode);
      if (item) handleChipClick(item);
    }
  }, [preset]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { id: Date.now(), role: "user", text: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);
    setApiError("");

    try {
      const buyers = await fetchPredict("330499");
      const first = buyers.items[0];
      const report = buildBuyerReportFromApi(first, "스킨케어");
      setCurrentBuyer(report);
      setShowReport(true);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: `${report.targetCountry} ${report.hsLabel} 바이어를 검색했습니다. 적합도 기준 상위 결과입니다. 우측에서 확인해 보세요.`,
        },
      ]);
    } catch (err) {
      setApiError(err.message || "분석 중 오류가 발생했습니다.");
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: `죄송합니다. ${err.message || "분석 중 오류가 발생했습니다."} 폼 모드에서 직접 시도해 보세요.`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUnavailableChip = (item) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        role: "assistant",
        text: `${item.label} GTM Pack은 아직 준비 중입니다. 지금은 K-뷰티(HS ${quickStartItems[0].hsCode})로 먼저 시작할 수 있습니다.`,
      },
    ]);
  };

  const handleChipClick = async (item) => {
    if (!item.available) {
      handleUnavailableChip(item);
      return;
    }

    if (typeof onStartWizard === "function") {
      onStartWizard({ hsCode: item.hsCode, label: item.label, source: "chat" });
      return;
    }

    const userMsg = { id: Date.now(), role: "user", text: `${item.label} 수출하고 싶어요` };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setApiError("");

    try {
      const buyers = await fetchPredict(item.hsCode);
      const first = buyers.items[0];
      const report = buildBuyerReportFromApi(first, item.label);
      setCurrentBuyer(report);
      setShowReport(true);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: `${item.label} ${report.targetCountry} 바이어를 검색했습니다. 적합도 기준 상위 결과입니다. 우측에서 확인해 보세요.`,
        },
      ]);
    } catch (err) {
      setApiError(err.message || "분석 중 오류가 발생했습니다.");
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: `죄송합니다. ${err.message || "분석 중 오류가 발생했습니다."} 폼 모드에서 직접 시도해 보세요.`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-mode-page">
      <header className="chat-mode-header">
        <button className="chat-back-btn" onClick={onBack}>
          <ArrowLeft size={18} />
          <span>뒤로</span>
        </button>
        <div className="chat-brand">MarketGate 비서</div>
        <div className="chat-mode-actions">
          <button className="chat-mode-toggle" aria-current="page">
            <span>챗 모드</span>
          </button>
          <button className="chat-mode-toggle" onClick={onSwitchToForm}>
            <LayoutTemplate size={16} />
            <span>폼 모드</span>
          </button>
        </div>
      </header>

      <div className="chat-mode-body">
        <div className={`chat-pane ${showReport ? "chat-pane--narrow" : ""}`}>
          <div className="chat-history">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                className={`chat-bubble chat-bubble--${msg.role}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <span className="chat-bubble-role">
                  {msg.role === "user" ? "💬" : "🤖"}
                </span>
                <p>{msg.text}</p>
              </motion.div>
            ))}
            {isLoading && (
              <div className="chat-bubble chat-bubble--assistant">
                <span className="chat-bubble-role">🤖</span>
                <p className="chat-loading">분석 중...</p>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="chat-quick-chips">
            {quickStartItems.map((item) => (
              <button
                key={item.id}
                className={`chat-chip ${item.available ? "" : "chat-chip--soon"}`}
                onClick={() => handleChipClick(item)}
              >
                {item.label}
                <span className="chat-chip-badge">{item.status}</span>
              </button>
            ))}
          </div>

          <div className="chat-input-bar">
            <button className="chat-mic-btn">
              <Mic size={18} />
            </button>
            <input
              className="chat-input"
              placeholder="예: K-뷰티 독일 바이어 찾아줘"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button className="chat-send-btn" onClick={handleSend}>
              <Send size={18} />
            </button>
          </div>
        </div>

        <AnimatePresence>
          {showReport && currentBuyer && (
            <motion.div
              className="chat-report-pane"
              initial={{ opacity: 0, x: 60 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 60 }}
              transition={{ duration: 0.4 }}
            >
              <BuyerReport buyer={currentBuyer} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
