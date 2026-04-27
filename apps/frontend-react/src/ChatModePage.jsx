import { useState, useRef, useEffect } from "react";
import { ArrowLeft, Send, Mic, LayoutTemplate } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import BuyerReport from "./BuyerReport";

const quickStartItems = [
  { id: "kbeauty", label: "K-뷰티", hsCode: "330499", available: true },
  { id: "health", label: "건강식품", hsCode: "210690", available: false },
  { id: "kfashion", label: "K-패션", hsCode: "611030", available: false },
];

const dummyMessages = [
  { id: 1, role: "assistant", text: "안녕하세요! 어떤 제품의 해외 바이어를 찾아드릴까요? 아래에서 바로 시작하거나, 직접 입력해 주세요." },
];

const dummyBuyer = {
  reportId: "#MG-0427-001",
  issuedAt: "2026년 4월 27일",
  targetCountry: "독일",
  targetCountryIso3: "DEU",
  hsCode: "330499",
  hsLabel: "스킨케어",
  dataDate: "2026년 4월",
  company: {
    name: "Beauty Wholesale GmbH",
    normalizedName: "beauty wholesale gmbh",
    industry: "뷰티 유통사",
    region: "함부르크",
    country: "독일",
    contactName: "Procurement Team / Ms. Anna Schmidt",
    email: "contact@beauty-wholesale.de",
    phone: "+49-40-1234-5678",
    website: "www.beauty-wholesale.de",
    hasContact: true,
  },
  fitScore: 92,
  fitBars: {
    trade_history: "████████████████",
    growth: "████████████",
    gdp: "██████████",
    logistics: "████████",
  },
  matchedTerms: ["skincare", "serum", "k-beauty", "moisturizing"],
  recommendations: [
    "최근 2년간 스킨케어 품목 수입 실적 보유",
    "한국 화장품 유통 채널 확장 중",
    "온라인/오프라인 복합 유통망 보유",
  ],
  dataSource: "KOTRA 글로벌 바이어 정보",
  sourceFile: "kotra_buyers_202604.csv",
  sourceRow: "1,847",
  lastVerified: "2026-04-10",
  trustStatus: "verified",
};

export default function ChatModePage({ preset, onBack, onSwitchToForm }) {
  const [messages, setMessages] = useState(dummyMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [currentBuyer, setCurrentBuyer] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    const userMsg = { id: Date.now(), role: "user", text: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      const reply = {
        id: Date.now() + 1,
        role: "assistant",
        text: `독일 K-뷰티 바이어를 검색했습니다. 적합도 기준 상위 결과입니다. 우측에서 확인해 보세요.`,
      };
      setMessages((prev) => [...prev, reply]);
      setCurrentBuyer(dummyBuyer);
      setShowReport(true);
    }, 1200);
  };

  const handleChipClick = (item) => {
    if (!item.available) return;
    const userMsg = { id: Date.now(), role: "user", text: `${item.label} 수출하고 싶어요` };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      const reply = {
        id: Date.now() + 1,
        role: "assistant",
        text: `${item.label} 독일 바이어를 검색했습니다. 적합도 기준 상위 결과입니다. 우측에서 확인해 보세요.`,
      };
      setMessages((prev) => [...prev, reply]);
      setCurrentBuyer(dummyBuyer);
      setShowReport(true);
    }, 1200);
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
                {!item.available && <span className="chat-chip-badge">Soon</span>}
              </button>
            ))}
          </div>

          <div className="chat-input-bar">
            <button className="chat-mic-btn">
              <Mic size={18} />
            </button>
            <input
              className="chat-input"
              placeholder="메시지를 입력하세요..."
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
