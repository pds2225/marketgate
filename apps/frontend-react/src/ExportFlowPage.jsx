import { startTransition, useDeferredValue, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Calculator,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  FileText,
  Globe,
  LoaderCircle,
  Mail,
  Search,
  Ship,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { buildP1Url, ENDPOINTS } from "./config";
import BuyerReport from "./BuyerReport";

const hsExamples = [
  { code: "330499", label: "화장품" },
  { code: "854231", label: "반도체" },
  { code: "870899", label: "자동차 부품" },
  { code: "190230", label: "즉석면" },
  { code: "850650", label: "리튬전지" },
];

const countryInfo = {
  AUS: { name: "호주", flag: "🇦🇺", region: "오세아니아" },
  BRA: { name: "브라질", flag: "🇧🇷", region: "중남미" },
  CAN: { name: "캐나다", flag: "🇨🇦", region: "북미" },
  CHN: { name: "중국", flag: "🇨🇳", region: "동아시아" },
  DEU: { name: "독일", flag: "🇩🇪", region: "유럽" },
  FRA: { name: "프랑스", flag: "🇫🇷", region: "유럽" },
  GBR: { name: "영국", flag: "🇬🇧", region: "유럽" },
  HKG: { name: "홍콩", flag: "🇭🇰", region: "동아시아" },
  IDN: { name: "인도네시아", flag: "🇮🇩", region: "동남아" },
  IND: { name: "인도", flag: "🇮🇳", region: "남아시아" },
  JPN: { name: "일본", flag: "🇯🇵", region: "동아시아" },
  MEX: { name: "멕시코", flag: "🇲🇽", region: "북중미" },
  MYS: { name: "말레이시아", flag: "🇲🇾", region: "동남아" },
  NLD: { name: "네덜란드", flag: "🇳🇱", region: "유럽" },
  PHL: { name: "필리핀", flag: "🇵🇭", region: "동남아" },
  SGP: { name: "싱가포르", flag: "🇸🇬", region: "동남아" },
  THA: { name: "태국", flag: "🇹🇭", region: "동남아" },
  TWN: { name: "대만", flag: "🇹🇼", region: "동아시아" },
  USA: { name: "미국", flag: "🇺🇸", region: "북미" },
  VNM: { name: "베트남", flag: "🇻🇳", region: "동남아" },
};

const p1MetricMeta = {
  trade_volume_score: { label: "무역 실적", tone: "positive" },
  growth_score: { label: "성장률", tone: "positive" },
  gdp_score: { label: "GDP 규모", tone: "positive" },
  distance_score: { label: "거리 이점", tone: "positive" },
  soft_adjustment: { label: "보정 점수", tone: "neutral" },
};

const factorNames = {
  historical_trade_value_usd: "기존 무역 실적",
  partner_gdp_growth_pct: "GDP 성장률",
  partner_gdp_usd: "시장 규모(GDP)",
  distance_km: "거리",
};

const currencyFormatter = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function clampMetric(key, value) {
  if (value == null || Number.isNaN(Number(value))) return 0;
  if (key === "soft_adjustment") {
    const normalized = (Number(value) + 15) / 30;
    return Math.max(0, Math.min(1, normalized));
  }
  if (key in p1MetricMeta) return Math.max(0, Math.min(1, Number(value)));
  const legacyNormalized = (Number(value) + 1) / 2;
  return Math.max(0, Math.min(1, legacyNormalized));
}

function getCountryMeta(iso3) {
  const safe = String(iso3 || "").toUpperCase();
  return {
    iso3: safe,
    name: countryInfo[safe]?.name || safe,
    flag: countryInfo[safe]?.flag || "🌐",
    region: countryInfo[safe]?.region || "지역 미확인",
  };
}

function formatUsd(value) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return currencyFormatter.format(Number(value));
}

function formatMetricValue(key, value) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  if (key === "soft_adjustment") return `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(1)}점`;
  if (key in p1MetricMeta) return `${Math.round(Number(value) * 100)}점`;
  return `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(2)}`;
}

function buildP1Recommendation(entry) {
  const meta = getCountryMeta(entry.partner_country_iso3);
  const components = entry.score_components || {};
  const explanation = entry.explanation || {};
  const topFactors = (explanation.top_factors || [])
    .map((item) => factorNames[item.factor] || item.factor)
    .filter(Boolean);

  return {
    id: `${meta.iso3}-${entry.rank}`,
    country: meta,
    rank: entry.rank,
    score: Number(entry.fit_score || 0),
    badge: "P1 API",
    summary:
      topFactors.length > 0
        ? `${topFactors.join(" · ")} 쪽에서 점수가 높게 반영됐습니다.`
        : "CSV 기반 지표를 합산한 적합도 점수입니다.",
    metrics: Object.entries(p1MetricMeta).map(([key, metaInfo]) => ({
      key,
      label: metaInfo.label,
      tone: metaInfo.tone,
      value: clampMetric(key, components[key]),
      displayValue: formatMetricValue(key, components[key]),
    })),
    detailRows: [
      { label: "주요 근거", value: topFactors.join(", ") || "표시 가능한 상위 요인 없음" },
      { label: "적용 필터", value: (explanation.filters_applied || []).join(", ") || "없음" },
      { label: "데이터 출처", value: (explanation.data_sources || []).join(", ") || "CSV 파일 기준" },
    ],
  };
}

function normalizeP1Response(payload) {
  const results = Array.isArray(payload?.data?.results) ? payload.data.results : [];
  const input = payload?.data?.input || {};
  const diagnostics = payload?.data?.diagnostics ?? null;
  const buyers = payload?.data?.buyers ?? null;

  return {
    engine: "p1",
    hint: "CSV 기반 P1 추천 점수를 표시하고 있습니다.",
    request: { hsCode: input.hs_code, topN: input.top_n, year: input.year },
    recommendations: results.map((entry) => buildP1Recommendation(entry)),
    diagnostics,
    buyers,
  };
}

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

async function fetchJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const detail = payload?.detail || payload?.message || `요청 실패 (${response.status})`;
    throw new Error(String(detail));
  }
  return payload;
}

async function requestAnalysis(hsCode, topN, year) {
  const normalizedHs = hsCode.trim();
  const isP1ReadyHs = /^\d{6}$/.test(normalizedHs);
  let p1Issue = null;
  let p1EmptyResult = null;

  if (isP1ReadyHs) {
    try {
      const p1Payload = await fetchJson(ENDPOINTS.predict, {
        hs_code: normalizedHs,
        exporter_country_iso3: "KOR",
        top_n: topN,
        year,
        filters: { min_trade_value_usd: 0 },
      });
      const normalized = normalizeP1Response(p1Payload);
      if (normalized.recommendations.length > 0) return normalized;
      p1Issue = "P1 API는 응답했지만 추천 결과가 비었습니다.";
      p1EmptyResult = { ...normalized, hint: "P1 API는 응답했지만 현재 데이터 기준 추천 국가가 없습니다." };
    } catch (error) {
      p1Issue = `P1 API 오류: ${error.message}`;
    }
  }

  try {
    const legacyPayload = await fetchJson(buildP1Url("/predict"), {
      hs_code: normalizedHs,
      exporter_country: "KOR",
      top_n: topN,
    });
    const normalizedLegacy = {
      engine: "legacy",
      hint: "예전 실험형 추천 엔진 응답을 표시하고 있습니다.",
      request: { hsCode: normalizedHs, topN },
      recommendations: (legacyPayload.top_countries || legacyPayload.data?.top_countries || []).map((c, i) => ({
        id: `${c.country}-${i}`,
        country: getCountryMeta(c.country),
        rank: i + 1,
        score: (c.score || 0) * 100,
        badge: "실험형 엔진",
        summary: "중력모형과 보정 모델을 함께 반영한 추천입니다.",
        metrics: [],
        detailRows: [
          { label: "예상 수출액", value: formatUsd(c.expected_export_usd) },
          { label: "강한 요인", value: "계산 가능 데이터 기준 일반 추천" },
          { label: "분석 방식", value: "중력모형 + XGBoost 실험형 예측" },
        ],
      })),
      diagnostics: legacyPayload.diagnostics || legacyPayload.data?.diagnostics || null,
      buyers: null,
    };
    if (normalizedLegacy.recommendations.length > 0) {
      return { ...normalizedLegacy, hint: p1Issue ? `${normalizedLegacy.hint} (${p1Issue})` : normalizedLegacy.hint };
    }
    if (p1EmptyResult) return p1EmptyResult;
    return { ...normalizedLegacy, hint: p1Issue ? `두 엔진 모두 결과가 충분하지 않았습니다. (${p1Issue})` : "추천 결과가 비어 있습니다." };
  } catch (legacyError) {
    if (p1EmptyResult) return { ...p1EmptyResult, hint: `${p1EmptyResult.hint} 예전 엔진도 확인했지만 결과를 보강하지 못했습니다.` };
    if (p1Issue) throw new Error(`${p1Issue} / 예전 엔진 오류: ${legacyError.message}`);
    throw legacyError;
  }
}

/* ── ProfitSimulator (Step 3) ── */
function ProfitSimulator({ selectedBuyer, hsCode, onComplete }) {
  const [unitPrice, setUnitPrice] = useState(100);
  const [quantity, setQuantity] = useState(1000);
  const [logisticsCost, setLogisticsCost] = useState(2500);
  const [tariffRate, setTariffRate] = useState(8);
  const [exchangeRate, setExchangeRate] = useState(1350);
  const [otherCost, setOtherCost] = useState(500);

  const revenueUSD = unitPrice * quantity;
  const tariffUSD = revenueUSD * (tariffRate / 100);
  const totalCostUSD = logisticsCost + tariffUSD + otherCost;
  const profitUSD = revenueUSD - totalCostUSD;
  const profitRate = revenueUSD > 0 ? (profitUSD / revenueUSD) * 100 : 0;
  const revenueKRW = revenueUSD * exchangeRate;
  const profitKRW = profitUSD * exchangeRate;

  const isProfitable = profitUSD > 0;

  return (
    <div>
      <div className="analysis-overview" style={{ marginBottom: 20 }}>
        <div>
          <p className="analysis-kicker">Step 3 — Profit Simulator</p>
          <h2>수출 수익성 검증</h2>
          <p>
            {selectedBuyer?.buyer_name || "선택된 바이어"}와의 거래 조건을 입력하면 예상 수익을 계산합니다.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14, marginBottom: 20 }}>
        <label className="analysis-field">
          <span>단가 (USD)</span>
          <input type="number" value={unitPrice} onChange={(e) => setUnitPrice(Number(e.target.value))} min={0} />
        </label>
        <label className="analysis-field">
          <span>수량 (개)</span>
          <input type="number" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} min={0} />
        </label>
        <label className="analysis-field">
          <span>물류비 (USD)</span>
          <input type="number" value={logisticsCost} onChange={(e) => setLogisticsCost(Number(e.target.value))} min={0} />
        </label>
        <label className="analysis-field">
          <span>관세율 (%)</span>
          <input type="number" value={tariffRate} onChange={(e) => setTariffRate(Number(e.target.value))} min={0} max={100} />
        </label>
        <label className="analysis-field">
          <span>환율 (KRW/USD)</span>
          <input type="number" value={exchangeRate} onChange={(e) => setExchangeRate(Number(e.target.value))} min={1} />
        </label>
        <label className="analysis-field">
          <span>기타 비용 (USD)</span>
          <input type="number" value={otherCost} onChange={(e) => setOtherCost(Number(e.target.value))} min={0} />
        </label>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            padding: 18,
            borderRadius: 16,
            background: "rgba(15,23,42,0.5)",
            border: "1px solid rgba(148,163,184,0.25)",
          }}
        >
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>예상 매출</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{formatUsd(revenueUSD)}</div>
          <div style={{ fontSize: 13, color: "#cbd5e1" }}>≈ {Math.round(revenueKRW).toLocaleString()}원</div>
        </div>
        <div
          style={{
            padding: 18,
            borderRadius: 16,
            background: "rgba(15,23,42,0.5)",
            border: "1px solid rgba(148,163,184,0.25)",
          }}
        >
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>총 비용</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{formatUsd(totalCostUSD)}</div>
          <div style={{ fontSize: 13, color: "#cbd5e1" }}>물류 {formatUsd(logisticsCost)} + 관세 {formatUsd(tariffUSD)} + 기타 {formatUsd(otherCost)}</div>
        </div>
        <div
          style={{
            padding: 18,
            borderRadius: 16,
            background: isProfitable ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
            border: `1px solid ${isProfitable ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
          }}
        >
          <div style={{ fontSize: 13, color: isProfitable ? "#86efac" : "#fca5a5", marginBottom: 6 }}>예상 순이익</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: isProfitable ? "#4ade80" : "#f87171" }}>
            {profitUSD >= 0 ? "" : "-"}{formatUsd(Math.abs(profitUSD))}
          </div>
          <div style={{ fontSize: 13, color: "#cbd5e1" }}>≈ {Math.round(Math.abs(profitKRW)).toLocaleString()}원</div>
        </div>
        <div
          style={{
            padding: 18,
            borderRadius: 16,
            background: "rgba(15,23,42,0.5)",
            border: "1px solid rgba(148,163,184,0.25)",
          }}
        >
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>수익률</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: isProfitable ? "#4ade80" : "#f87171" }}>
            {profitRate.toFixed(1)}%
          </div>
          <div style={{ fontSize: 13, color: "#cbd5e1" }}>{isProfitable ? "수익 예상" : "적자 예상"}</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button className="ui-button ui-button--solid" onClick={() => onComplete?.({ unitPrice, quantity, logisticsCost, tariffRate, exchangeRate, otherCost, profitUSD, profitRate })}>
          수익성 확인 완료 — 주문서 작성으로
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}

/* ── PurchaseOrderGenerator (Step 4) ── */
function PurchaseOrderGenerator({ selectedBuyer, simulationParams, hsCode, onReset }) {
  const today = new Date();
  const poId = `PO-${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, "0")}${String(today.getDate()).padStart(2, "0")}-${Math.floor(Math.random() * 9000 + 1000)}`;

  const buyerName = selectedBuyer?.buyer_name || "Buyer Name";
  const buyerEmail = selectedBuyer?.contact_email || "-";
  const buyerCountry = selectedBuyer?.source_target_country_name || selectedBuyer?.country_norm || "-";
  const productDesc = hsCode ? `HS ${hsCode} 수출 품목` : "수출 품목";

  const sp = simulationParams || {};
  const qty = sp.quantity || 0;
  const price = sp.unitPrice || 0;
  const total = qty * price;

  const poText = [
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
    `  PURCHASE ORDER (주문서)`,
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
    ``,
    `주문번호 (PO No.): ${poId}`,
    `발행일 (Date): ${today.toISOString().split("T")[0]}`,
    ``,
    `【공급자 (Seller)】`,
    `  회사명: ${sp.senderCompany || "___________"}`,
    `  담당자: ${sp.senderName || "___________"}`,
    ``,
    `【수요자 (Buyer)】`,
    `  회사명: ${buyerName}`,
    `  국가: ${buyerCountry}`,
    `  이메일: ${buyerEmail}`,
    ``,
    `【제품 정보】`,
    `  품목: ${productDesc}`,
    `  수량: ${qty.toLocaleString()} EA`,
    `  단가: USD ${price.toLocaleString()}`,
    `  총액: USD ${total.toLocaleString()}`,
    ``,
    `【거래 조건】`,
    `  Incoterms: FOB (협의 가능)`,
    `  결제 조건: T/T 30% 선수금, 70% 선적 후`,
    `  선적 예정일: 발주 확인 후 30일 이내`,
    ``,
    `【비용 요약】`,
    `  매출액: USD ${total.toLocaleString()}`,
    `  물류비: USD ${(sp.logisticsCost || 0).toLocaleString()}`,
    `  관세: USD ${(Math.round(total * ((sp.tariffRate || 0) / 100) * 100) / 100).toLocaleString()}`,
    `  기타비용: USD ${(sp.otherCost || 0).toLocaleString()}`,
    `  예상 순이익: USD ${(sp.profitUSD || 0).toLocaleString()} (${(sp.profitRate || 0).toFixed(1)}%)`,
    ``,
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
    `  본 주문서는 MarketGate 수출지원 플랫폼`,
    `  자동 생성 초안입니다. 법적 검토 후 사용하세요.`,
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
  ].join("\n");

  return (
    <div>
      <div className="analysis-overview" style={{ marginBottom: 20 }}>
        <div>
          <p className="analysis-kicker">Step 4 — Purchase Order</p>
          <h2>주문서 자동 생성</h2>
          <p>수익성 검증 결과를 반영한 주문서 초안입니다. 법무 검토 후 바이어에게 전송하세요.</p>
        </div>
      </div>

      <div
        style={{
          background: "rgba(15,23,42,0.6)",
          border: "1px solid rgba(148,163,184,0.25)",
          borderRadius: 16,
          padding: 20,
          fontFamily: "monospace",
          fontSize: 13,
          lineHeight: 1.7,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          marginBottom: 16,
        }}
      >
        {poText}
      </div>

      <div style={{ display: "flex", gap: 10, justifyContent: "space-between", flexWrap: "wrap" }}>
        <button
          className="ui-button ui-button--ghost"
          onClick={() => {
            const blob = new Blob([poText], { type: "text/plain;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${poId}.txt`;
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          <FileText size={16} />
          TXT 다운로드
        </button>
        <button
          className="ui-button ui-button--ghost"
          onClick={async () => {
            try {
              const { jsPDF } = await import("jspdf");
              const doc = new jsPDF();
              const lines = poText.split("\n");
              let y = 10;
              lines.forEach((line) => {
                if (y > 280) {
                  doc.addPage();
                  y = 10;
                }
                doc.text(line, 10, y);
                y += 6;
              });
              doc.save(`${poId}.pdf`);
            } catch (e) {
              alert("PDF 생성을 위해 jspdf 패키지 설치가 필요합니다.\n로컬에서: npm install jspdf");
            }
          }}
        >
          <FileText size={16} />
          PDF 다운로드
        </button>
        <button className="ui-button ui-button--ghost" onClick={() => navigator.clipboard?.writeText?.(poText)}>
          <FileText size={16} />
          전문 복사
        </button>
        <button className="ui-button ui-button--solid" onClick={onReset}>
          <ArrowRight size={16} />
          새로운 수출 건 시작
        </button>
      </div>
    </div>
  );
}

/* ── ExportFlowPage ── */
export default function ExportFlowPage({ onBack }) {
  const [step, setStep] = useState(1);
  const totalSteps = 4;

  const [hsCode, setHsCode] = useState("330499");
  const [topN, setTopN] = useState(5);
  const [year, setYear] = useState(2023);
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [selectedRecId, setSelectedRecId] = useState(null);
  const [selectedBuyer, setSelectedBuyer] = useState(null);
  const [simulationParams, setSimulationParams] = useState(null);

  const [showBuyerReport, setShowBuyerReport] = useState(false);
  const [reportBuyer, setReportBuyer] = useState(null);

  const deferredSelectedId = useDeferredValue(selectedRecId);
  const selectedRecommendation =
    analysisResult?.recommendations.find((item) => item.id === deferredSelectedId) ||
    analysisResult?.recommendations[0] ||
    null;

  const handleAnalyze = async () => {
    if (!/^\d{2,6}$/.test(hsCode.trim())) {
      setAnalysisError("HS 코드는 숫자 2자리에서 6자리까지 입력해야 합니다.");
      return;
    }
    setLoading(true);
    setAnalysisError("");
    try {
      const analysis = await requestAnalysis(hsCode, topN, year);
      startTransition(() => {
        setAnalysisResult(analysis);
        setSelectedRecId(analysis.recommendations[0]?.id || null);
        setSelectedBuyer(null);
      });
    } catch (requestError) {
      setAnalysisResult(null);
      setSelectedRecId(null);
      setAnalysisError(requestError.message || "분석 요청에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const stepLabels = [
    { num: 1, label: "국가 추천", icon: Globe },
    { num: 2, label: "바이어 선정", icon: Users },
    { num: 3, label: "수익 검증", icon: Calculator },
    { num: 4, label: "주문서 생성", icon: FileText },
  ];

  const goNext = () => setStep((s) => Math.min(s + 1, totalSteps));
  const goPrev = () => setStep((s) => Math.max(s - 1, 1));

  return (
    <div className="analysis-page">
      <header className="analysis-header">
        <div className="analysis-header-main">
          <button className="ui-button ui-button--ghost" onClick={onBack}>
            <ArrowLeft size={16} />
            첫 화면으로
          </button>
          <div>
            <p className="analysis-kicker">AI·데이터 기반 수출지원 One-Stop 플랫폼</p>
            <h1>수출 전 과정 플로우</h1>
          </div>
        </div>
      </header>

      {/* Stepper */}
      <div style={{ padding: "0 24px", maxWidth: 960, margin: "0 auto 20px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
            background: "rgba(15,23,42,0.45)",
            border: "1px solid rgba(148,163,184,0.2)",
            borderRadius: 16,
            padding: "14px 18px",
          }}
        >
          {stepLabels.map((s, i) => {
            const Icon = s.icon;
            const isActive = step === s.num;
            const isDone = step > s.num;
            return (
              <div key={s.num} style={{ display: "flex", alignItems: "center", gap: 8, flex: 1 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 13,
                    fontWeight: 700,
                    flexShrink: 0,
                    background: isActive ? "#3b82f6" : isDone ? "#22c55e" : "rgba(148,163,184,0.2)",
                    color: isActive || isDone ? "#fff" : "#94a3b8",
                  }}
                >
                  {isDone ? <CheckCircle2 size={18} /> : <Icon size={16} />}
                </div>
                <div style={{ fontSize: 13, color: isActive ? "#e2e8f0" : "#94a3b8", fontWeight: isActive ? 600 : 400 }}>
                  {s.label}
                </div>
                {i < stepLabels.length - 1 && (
                  <ChevronRight size={14} style={{ marginLeft: "auto", color: "#64748b", flexShrink: 0 }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <main className="analysis-layout" style={{ maxWidth: 960, margin: "0 auto", padding: "0 24px 40px" }}>
        <AnimatePresence mode="wait">
          {/* ===== Step 1: 국가 추천 ===== */}
          {step === 1 && (
            <motion.div key="step1" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <div className="analysis-overview" style={{ marginBottom: 20 }}>
                <div>
                  <p className="analysis-kicker">Step 1</p>
                  <h2>수출 국가 추천</h2>
                  <p>HS 코드를 입력하면 데이터 기반으로 적합한 수출 대상국을 추천합니다.</p>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
                <label className="analysis-field">
                  <span>HS 코드</span>
                  <input type="text" inputMode="numeric" value={hsCode} onChange={(e) => setHsCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="예: 330499" />
                </label>
                <div style={{ display: "flex", gap: 10 }}>
                  <label className="analysis-field" style={{ flex: 1 }}>
                    <span>추천 수</span>
                    <select value={topN} onChange={(e) => setTopN(Number(e.target.value))}>
                      <option value={3}>3개</option>
                      <option value={5}>5개</option>
                      <option value={8}>8개</option>
                      <option value={10}>10개</option>
                    </select>
                  </label>
                  <label className="analysis-field" style={{ flex: 1 }}>
                    <span>연도</span>
                    <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
                      <option value={2023}>2023</option>
                      <option value={2022}>2022</option>
                      <option value={2021}>2021</option>
                    </select>
                  </label>
                </div>
              </div>

              <div className="analysis-example-list" style={{ marginBottom: 16 }}>
                {hsExamples.map((item) => (
                  <button key={item.code} className={`analysis-chip ${hsCode === item.code ? "is-active" : ""}`} onClick={() => setHsCode(item.code)}>
                    <span>{item.label}</span>
                    <strong>{item.code}</strong>
                  </button>
                ))}
              </div>

              <button className="ui-button ui-button--solid" onClick={handleAnalyze} disabled={loading} style={{ marginBottom: 16 }}>
                {loading ? <LoaderCircle size={18} className="analysis-spin" /> : <Search size={18} />}
                {loading ? "분석 중..." : "추천 국가 계산"}
              </button>

              {analysisError ? (
                <div className="analysis-inline-alert" style={{ marginBottom: 16 }}>
                  <CircleAlert size={16} />
                  <span>{analysisError}</span>
                </div>
              ) : null}

              {analysisResult && !loading && (
                <div>
                  <div style={{ marginBottom: 12, fontSize: 14, color: "#94a3b8" }}>
                    HS {analysisResult.request.hsCode} 기준 · {analysisResult.recommendations.length}개 국가 · {analysisResult.engine === "p1" ? "P1 엔진" : "실험형 엔진"}
                  </div>
                  <div style={{ display: "grid", gap: 10 }}>
                    {analysisResult.recommendations.map((item) => (
                      <div
                        key={item.id}
                        className={`analysis-card ${selectedRecommendation?.id === item.id ? "is-selected" : ""}`}
                        onClick={() => setSelectedRecId(item.id)}
                        style={{ cursor: "pointer" }}
                      >
                        <div className="analysis-card-rank">{item.rank}</div>
                        <div className="analysis-card-body">
                          <div className="analysis-card-title">
                            <div>
                              <strong>{item.country.flag} {item.country.name}</strong>
                              <span>{item.country.region}</span>
                            </div>
                            <span className="analysis-card-badge">{item.badge}</span>
                          </div>
                          <p>{item.summary}</p>
                          <div className="analysis-metrics" style={{ marginTop: 8 }}>
                            {item.metrics.slice(0, 3).map((m) => (
                              <div className="analysis-metric" key={m.key}>
                                <div className="analysis-metric-head">
                                  <span>{m.label}</span>
                                  <strong>{m.displayValue}</strong>
                                </div>
                                <div className="analysis-metric-track">
                                  <div className={`analysis-metric-fill analysis-metric-fill--${m.tone}`} style={{ width: `${m.value * 100}%` }} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="analysis-card-score">
                          <strong>{item.score.toFixed(1)}</strong>
                          <span>점</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {selectedRecommendation && (
                    <div style={{ marginTop: 14, padding: 16, borderRadius: 14, background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.2)" }}>
                      <strong style={{ fontSize: 15 }}>선택: {selectedRecommendation.country.flag} {selectedRecommendation.country.name}</strong>
                      <p style={{ marginTop: 6, fontSize: 13, color: "#94a3b8" }}>이 국가를 기준으로 바이어를 검색합니다.</p>
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
                <button className="ui-button ui-button--solid" onClick={goNext} disabled={!analysisResult?.recommendations?.length}>
                  바이어 선정으로
                  <ArrowRight size={16} />
                </button>
              </div>
            </motion.div>
          )}

          {/* ===== Step 2: 바이어 선정 ===== */}
          {step === 2 && (
            <motion.div key="step2" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <div className="analysis-overview" style={{ marginBottom: 20 }}>
                <div>
                  <p className="analysis-kicker">Step 2</p>
                  <h2>저품질·저적합 바이어 필터링</h2>
                  <p>추천된 국가에서 검증된 바이어 후보를 확인하고 인콰이어리 대상을 선택하세요.</p>
                </div>
              </div>

              {!analysisResult?.buyers?.items?.length ? (
                <div className="analysis-empty analysis-empty--compact">
                  <CircleAlert size={18} />
                  <h3>현재 조건에 맞는 바이어가 없습니다.</h3>
                  <p>1단계에서 다른 HS 코드나 국가를 시도해 보세요.</p>
                </div>
              ) : (
                <div style={{ display: "grid", gap: 12 }}>
                  {analysisResult.buyers.items.map((item, index) => (
                    <div
                      key={`${item.buyer_name}-${index}`}
                      className="analysis-card"
                      style={{
                        cursor: "pointer",
                        textAlign: "left",
                        border: selectedBuyer?.buyer_name === item.buyer_name ? "1px solid #3b82f6" : undefined,
                        background: selectedBuyer?.buyer_name === item.buyer_name ? "rgba(59,130,246,0.08)" : undefined,
                      }}
                      onClick={() => setSelectedBuyer(item)}
                    >
                      <div className="analysis-card-rank">{index + 1}</div>
                      <div className="analysis-card-body">
                        <div className="analysis-card-title">
                          <div>
                            <strong>{item.buyer_name}</strong>
                            <span>{item.country_norm || "국가 미상"} · {item.source_dataset || "출처 미상"}</span>
                          </div>
                          <span className="analysis-card-badge">{item.final_score?.toFixed?.(1) || item.final_score}점</span>
                        </div>
                        <p>{(item.explanation_reasons || []).join(" · ") || "추천 사유 없음"}</p>
                        <div className="analysis-detail-grid" style={{ marginTop: 10 }}>
                          <div className="analysis-detail-row"><span>추천 국가</span><strong>{item.source_target_country_name || item.source_target_country_iso3 || "-"}</strong></div>
                          <div className="analysis-detail-row"><span>이메일</span><strong>{item.contact_email || "-"}</strong></div>
                          <div className="analysis-detail-row"><span>전화</span><strong>{item.contact_phone || "-"}</strong></div>
                          <div className="analysis-detail-row"><span>웹사이트</span><strong>{item.contact_website || "-"}</strong></div>
                        </div>
                        {selectedBuyer?.buyer_name === item.buyer_name && (
                          <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                            <span style={{ fontSize: 13, color: "#3b82f6" }}>✓ 선택됨</span>
                            <button
                              className="ui-button ui-button--ghost"
                              style={{ fontSize: 12, padding: "6px 10px" }}
                              onClick={(e) => {
                                e.stopPropagation();
                                const report = buildBuyerReportFromApi(item, hsCode);
                                setReportBuyer(report);
                                setShowBuyerReport(true);
                              }}
                            >
                              <FileText size={14} />
                              상세 리포트 보기
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20 }}>
                <button className="ui-button ui-button--ghost" onClick={goPrev}>
                  <ArrowLeft size={16} />
                  이전
                </button>
                <button className="ui-button ui-button--solid" onClick={goNext} disabled={!selectedBuyer}>
                  수익 검증으로
                  <ArrowRight size={16} />
                </button>
              </div>

              {/* BuyerReport 모달 */}
              <AnimatePresence>
                {showBuyerReport && reportBuyer && (
                  <motion.div
                    className="analysis-modal-overlay"
                    style={{
                      position: "fixed",
                      inset: 0,
                      zIndex: 200,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: "rgba(2, 6, 23, 0.72)",
                      padding: 24,
                    }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setShowBuyerReport(false)}
                  >
                    <motion.div
                      style={{
                        width: "100%",
                        maxWidth: 600,
                        maxHeight: "85vh",
                        overflowY: "auto",
                        background: "#0f172a",
                        border: "1px solid rgba(148,163,184,0.28)",
                        borderRadius: 20,
                        padding: 24,
                      }}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 20 }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                        <h3 style={{ margin: 0, fontSize: 18 }}>📋 바이어 상세 리포트</h3>
                        <button className="ui-button ui-button--ghost" onClick={() => setShowBuyerReport(false)} style={{ padding: 6 }}>
                          <X size={18} />
                        </button>
                      </div>
                      <BuyerReport buyer={reportBuyer} />
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* ===== Step 3: 수익 검증 ===== */}
          {step === 3 && (
            <motion.div key="step3" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <ProfitSimulator
                selectedBuyer={selectedBuyer}
                hsCode={hsCode}
                onComplete={(params) => {
                  setSimulationParams(params);
                  goNext();
                }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20 }}>
                <button className="ui-button ui-button--ghost" onClick={goPrev}>
                  <ArrowLeft size={16} />
                  이전
                </button>
              </div>
            </motion.div>
          )}

          {/* ===== Step 4: 주문서 생성 ===== */}
          {step === 4 && (
            <motion.div key="step4" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <PurchaseOrderGenerator
                selectedBuyer={selectedBuyer}
                simulationParams={simulationParams}
                hsCode={hsCode}
                onReset={() => {
                  setStep(1);
                  setAnalysisResult(null);
                  setSelectedRecId(null);
                  setSelectedBuyer(null);
                  setSimulationParams(null);
                  setAnalysisError("");
                }}
              />
              <div style={{ display: "flex", justifyContent: "flex-start", marginTop: 20 }}>
                <button className="ui-button ui-button--ghost" onClick={goPrev}>
                  <ArrowLeft size={16} />
                  이전 단계
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
