import { startTransition, useDeferredValue, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  CircleAlert,
  Database,
  LoaderCircle,
  Search,
  Sparkles,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { API_BASE, buildApiUrl, ENDPOINTS } from "./config";

const hsExamples = [
  { code: "330499", label: "K-뷰티" },
  { code: "854231", label: "반도체" },
  { code: "611030", label: "K-패션" },
  { code: "210690", label: "건강식품" },
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

const legacyMetricMeta = {
  gravity_baseline: { label: "경제 규모", tone: "positive" },
  growth_potential: { label: "성장 잠재력", tone: "positive" },
  culture_fit: { label: "문화 적합성", tone: "positive" },
  regulation_ease: { label: "규제 편의성", tone: "positive" },
  logistics: { label: "물류 인프라", tone: "positive" },
  tariff_impact: { label: "관세 혜택", tone: "neutral" },
};

const factorNames = {
  historical_trade_value_usd: "기존 무역 실적",
  partner_gdp_growth_pct: "GDP 성장률",
  partner_gdp_usd: "시장 규모(GDP)",
  distance_km: "거리",
  gravity_baseline: "경제 규모",
  growth_potential: "성장 잠재력",
  culture_fit: "문화 적합성",
  regulation_ease: "규제 편의성",
  logistics: "물류 인프라",
  tariff_impact: "관세 혜택",
};

const currencyFormatter = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function clampMetric(key, value) {
  if (value == null || Number.isNaN(Number(value))) {
    return 0;
  }

  if (key === "soft_adjustment") {
    const normalized = (Number(value) + 15) / 30;
    return Math.max(0, Math.min(1, normalized));
  }

  if (key in p1MetricMeta) {
    return Math.max(0, Math.min(1, Number(value)));
  }

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
  if (value == null || Number.isNaN(Number(value))) {
    return "-";
  }

  return currencyFormatter.format(Number(value));
}

function formatMetricValue(key, value) {
  if (value == null || Number.isNaN(Number(value))) {
    return "-";
  }

  if (key === "soft_adjustment") {
    return `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(1)}점`;
  }

  if (key in p1MetricMeta) {
    return `${Math.round(Number(value) * 100)}점`;
  }

  return `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(2)}`;
}

function strongestLegacyFactors(explanation) {
  return Object.entries(explanation || {})
    .filter(([, value]) => typeof value === "number")
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 2)
    .map(([key]) => factorNames[key] || key);
}

const diagnosticLabels = {
  NO_KOTRA_CANDIDATES_FOR_HS6: "이 HS 코드에는 후보 국가가 없습니다.",
  NO_ELIGIBLE_CANDIDATES: "조건을 만족하는 국가가 없습니다.",
  USER_EXCLUDED: "사용자 제외 목록에 포함된 국가입니다.",
  MIN_TRADE_VALUE: "최소 무역액 기준에 미달했습니다.",
  NO_TRADE_DATA: "무역 데이터가 없습니다.",
  NO_DISTANCE_DATA: "거리 데이터가 없습니다.",
  TRADE_SIGNAL_USES_WORLD_TOTAL_FALLBACK: "일부 무역값을 세계 합계로 보강했습니다.",
  ALL_ELIGIBLE_RESULTS_USE_ALLOCATED_TRADE_SIGNAL: "모든 결과가 보강된 무역 신호를 사용합니다.",
  GDP_DATA_PARTIALLY_MISSING: "일부 국가의 GDP 데이터가 비어 있습니다.",
  GDP_GROWTH_DATA_PARTIALLY_MISSING: "일부 국가의 GDP 성장률 데이터가 비어 있습니다.",
};

function joinList(items, emptyText = "없음") {
  const values = (items || []).filter(Boolean);
  return values.length > 0 ? values.join(" · ") : emptyText;
}

function formatDiagnosticText(items) {
  const values = (items || []).map((item) => diagnosticLabels[item] || item).filter(Boolean);
  return values.length > 0 ? values.join(" · ") : "없음";
}

function DiagnosticsPanel({ diagnostics }) {
  if (!diagnostics) {
    return null;
  }

  return (
    <div
      style={{
        marginTop: 16,
        padding: 16,
        borderRadius: 16,
        border: "1px solid rgba(148, 163, 184, 0.35)",
        background: "rgba(15, 23, 42, 0.35)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <p className="analysis-kicker">Diagnostics</p>
          <h3 style={{ margin: "6px 0 0", fontSize: 18 }}>결과가 왜 나왔는지</h3>
        </div>
        <strong style={{ color: "#cbd5e1" }}>{diagnostics.returned_count ?? 0}개 반환</strong>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
          gap: 12,
          marginTop: 14,
        }}
      >
        <div className="analysis-detail-row">
          <span>후보 수</span>
          <strong>{diagnostics.candidate_count ?? "-"}</strong>
        </div>
        <div className="analysis-detail-row">
          <span>조건 충족</span>
          <strong>{diagnostics.eligible_count ?? "-"}</strong>
        </div>
        <div className="analysis-detail-row">
          <span>반환 수</span>
          <strong>{diagnostics.returned_count ?? "-"}</strong>
        </div>
        <div className="analysis-detail-row">
          <span>무역 신호</span>
          <strong>
            {joinList(
              Object.entries(diagnostics.trade_signal_counts || {}).map(([key, value]) => `${key}: ${value}`)
            )}
          </strong>
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <div style={{ fontSize: 13, color: "#cbd5e1", marginBottom: 6 }}>0건 사유</div>
        <div style={{ fontSize: 14 }}>{formatDiagnosticText(diagnostics.zero_result_reasons)}</div>
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={{ fontSize: 13, color: "#cbd5e1", marginBottom: 6 }}>경고</div>
        <div style={{ fontSize: 14 }}>{formatDiagnosticText(diagnostics.quality_warnings)}</div>
      </div>
    </div>
  );
}

function buildLegacyRecommendation(country, rank) {
  const meta = getCountryMeta(country.country);
  const explanation = country.explanation || {};
  const topFactors = strongestLegacyFactors(explanation);

  return {
    id: `${meta.iso3}-${rank}`,
    country: meta,
    rank,
    score: Number(country.score || 0) * 100,
    badge: "실험형 엔진",
    summary:
      topFactors.length > 0
        ? `${topFactors.join(" · ")} 기준으로 상대적 우위가 보였습니다.`
        : "중력모형과 보정 모델을 함께 반영한 추천입니다.",
    metrics: Object.entries(legacyMetricMeta).map(([key, metaInfo]) => ({
      key,
      label: metaInfo.label,
      tone: metaInfo.tone,
      value: clampMetric(key, explanation[key]),
      displayValue: formatMetricValue(key, explanation[key]),
    })),
    detailRows: [
      { label: "예상 수출액", value: formatUsd(country.expected_export_usd) },
      { label: "강한 요인", value: topFactors.join(", ") || "계산 가능 데이터 기준 일반 추천" },
      { label: "분석 방식", value: "중력모형 + XGBoost 실험형 예측" },
    ],
  };
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
      {
        label: "적용 필터",
        value: (explanation.filters_applied || []).join(", ") || "없음",
      },
      {
        label: "데이터 출처",
        value: (explanation.data_sources || []).join(", ") || "CSV 파일 기준",
      },
    ],
  };
}

function normalizeLegacyResponse(payload, hsCode, topN) {
  const countries = Array.isArray(payload?.top_countries)
    ? payload.top_countries
    : Array.isArray(payload?.data?.top_countries)
      ? payload.data.top_countries
      : [];

  return {
    engine: "legacy",
    hint: "예전 실험형 추천 엔진 응답을 표시하고 있습니다.",
    request: { hsCode, topN },
    recommendations: countries.map((country, index) => buildLegacyRecommendation(country, index + 1)),
    diagnostics: payload?.diagnostics || payload?.data?.diagnostics || null,
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

function BuyerShortlistPanel({ buyers }) {
  if (!buyers) {
    return null;
  }

  const sourceCountries = Array.isArray(buyers.source_countries) ? buyers.source_countries : [];
  const sourceCountryLabel =
    sourceCountries.length > 0
      ? sourceCountries
          .map((item) => item.target_country_name || item.partner_country_iso3)
          .filter(Boolean)
          .join(" · ")
      : buyers.target_country_name || buyers.target_country_iso3 || "연결 국가 미확정";

  return (
    <div
      style={{
        marginTop: 20,
        padding: 18,
        borderRadius: 20,
        border: "1px solid rgba(148, 163, 184, 0.28)",
        background: "rgba(15, 23, 42, 0.42)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <div>
          <p className="analysis-kicker">Buyer Shortlist</p>
          <h3 style={{ margin: "6px 0 0", fontSize: 20 }}>Top 3 국가 병합 바이어 후보</h3>
          <p style={{ margin: "8px 0 0", color: "#94a3b8", fontSize: 14 }}>{sourceCountryLabel}</p>
        </div>
        <strong style={{ color: "#cbd5e1" }}>{buyers.items?.length || 0}개 후보</strong>
      </div>

      {buyers.status !== "ok" ? (
        <div className="analysis-inline-alert" style={{ marginTop: 14 }}>
          <CircleAlert size={16} />
          <span>{buyers.error || "바이어 숏리스트를 아직 연결하지 못했습니다."}</span>
        </div>
      ) : null}

      {buyers.status === "ok" && (buyers.items?.length || 0) === 0 ? (
        <div className="analysis-empty analysis-empty--compact" style={{ marginTop: 14 }}>
          <CircleAlert size={18} />
          <h3>현재 조건에 맞는 바이어가 없습니다.</h3>
          <p>HS 코드와 대상 국가 기준으로 연락 가능한 후보를 찾지 못했습니다.</p>
        </div>
      ) : null}

      {buyers.status === "ok" && (buyers.items?.length || 0) > 0 ? (
        <div style={{ display: "grid", gap: 12, marginTop: 14 }}>
          {buyers.items.map((item, index) => (
            <div
              key={`${item.buyer_name}-${index}`}
              className="analysis-card"
              style={{ cursor: "default", textAlign: "left" }}
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
                <div className="analysis-detail-grid" style={{ marginTop: 12 }}>
                  <div className="analysis-detail-row">
                    <span>추천 국가</span>
                    <strong>
                      {item.source_target_country_name || item.source_target_country_iso3 || "-"}
                      {item.source_target_country_rank ? ` (Top ${item.source_target_country_rank})` : ""}
                    </strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>이메일</span>
                    <strong>{item.contact_email || "-"}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>전화번호</span>
                    <strong>{item.contact_phone || "-"}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>홈페이지</span>
                    <strong>{item.contact_website || "-"}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>매칭 근거</span>
                    <strong>{item.matched_by || "-"}</strong>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
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
    const detail =
      payload?.detail ||
      payload?.message ||
      `요청 실패 (${response.status})`;
    throw new Error(String(detail));
  }

  return payload;
}

function isLegacyEndpointUnavailable(message) {
  return typeof message === "string" && message.trim().toLowerCase() === "not found";
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
      if (normalized.recommendations.length > 0) {
        return normalized;
      }
      p1Issue = "P1 API는 응답했지만 추천 결과가 비었습니다.";
      p1EmptyResult = {
        ...normalized,
        hint: "P1 API는 응답했지만 현재 데이터 기준 추천 국가가 없습니다.",
      };
    } catch (error) {
      const msg = String(error.message || "");
      if (msg.includes("fetch") || msg.includes("network")) {
        p1Issue = "P1 API 서버에 연결할 수 없습니다. 터미널에서 'uvicorn main:app --reload'를 실행해 주세요.";
      } else {
        p1Issue = `P1 API 오류: ${msg}`;
      }
    }
  }

  try {
    const legacyPayload = await fetchJson(buildApiUrl("/predict", API_BASE), {
      hs_code: normalizedHs,
      exporter_country: "KOR",
      top_n: topN,
    });

    const normalizedLegacy = normalizeLegacyResponse(legacyPayload, normalizedHs, topN);
    if (normalizedLegacy.recommendations.length > 0) {
      return {
        ...normalizedLegacy,
        hint: p1Issue
          ? `${normalizedLegacy.hint} (${p1Issue})`
          : normalizedLegacy.hint,
      };
    }

    if (p1EmptyResult) {
      return p1EmptyResult;
    }

    return {
      ...normalizedLegacy,
      hint: p1Issue
        ? `두 엔진 모두 결과가 충분하지 않았습니다. (${p1Issue})`
        : "추천 결과가 비어 있습니다.",
    };
  } catch (legacyError) {
    if (p1EmptyResult) {
      const legacyUnavailable = isLegacyEndpointUnavailable(legacyError.message);
      return {
        ...p1EmptyResult,
        hint: legacyUnavailable
          ? `${p1EmptyResult.hint} 현재 연결된 서버에는 예전 실험형 엔진이 포함돼 있지 않습니다.`
          : `${p1EmptyResult.hint} 예전 실험형 엔진도 함께 확인했지만 결과를 보강하지 못했습니다.`,
      };
    }

    if (p1Issue) {
      const legacyUnavailable = isLegacyEndpointUnavailable(legacyError.message);
      throw new Error(
        legacyUnavailable
          ? `${p1Issue} 현재 연결된 서버에는 예전 실험형 엔진이 없습니다.`
          : `${p1Issue} / 예전 엔진 오류: ${legacyError.message}`
      );
    }

    throw legacyError;
  }
}

function MetricBar({ metric }) {
  return (
    <div className="analysis-metric">
      <div className="analysis-metric-head">
        <span>{metric.label}</span>
        <strong>{metric.displayValue}</strong>
      </div>
      <div className="analysis-metric-track">
        <div
          className={`analysis-metric-fill analysis-metric-fill--${metric.tone}`}
          style={{ width: `${metric.value * 100}%` }}
        />
      </div>
    </div>
  );
}

export default function AnalysisPage({ onBack }) {
  const [hsCode, setHsCode] = useState("330499");
  const [topN, setTopN] = useState(5);
  const [year, setYear] = useState(2023);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  const deferredSelectedId = useDeferredValue(selectedId);
  const selectedRecommendation =
    result?.recommendations.find((item) => item.id === deferredSelectedId) ||
    result?.recommendations[0] ||
    null;

  const handleAnalyze = async () => {
    if (!/^\d{2,6}$/.test(hsCode.trim())) {
      setError("HS 코드는 숫자 2자리에서 6자리까지 입력해야 합니다.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const analysis = await requestAnalysis(hsCode, topN, year);

      startTransition(() => {
        setResult(analysis);
        setSelectedId(analysis.recommendations[0]?.id || null);
      });
    } catch (requestError) {
      setResult(null);
      setSelectedId(null);
      setError(requestError.message || "분석 요청에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleExample = (code) => {
    setHsCode(code);
    setError("");
  };

  return (
    <div className="analysis-page">
      <header className="analysis-header">
        <div className="analysis-header-main">
          <button className="ui-button ui-button--ghost" onClick={onBack}>
            <ArrowLeft size={16} />
            첫 화면으로
          </button>
          <div>
            <p className="analysis-kicker">Export Fit Workbench</p>
            <h1>수출 유망국 분석 작업면</h1>
          </div>
        </div>
        <div className="analysis-header-status">
          <Database size={16} />
          <span>API는 다른 프로그램이 호출하는 기능 창구입니다.</span>
        </div>
      </header>

      <main className="analysis-layout">
        <section className="analysis-input-rail">
          <div className="analysis-input-card">
            <div className="analysis-input-head">
              <p className="analysis-kicker">Input</p>
              <h2>분석할 품목을 입력하세요</h2>
              <p>
                HS 코드는 국제 상품 분류 코드입니다. 6자리면 현재 P1 추천 API를 먼저
                시도하고, 아니면 예전 실험형 엔진으로 이어집니다.
              </p>
            </div>

            <div className="analysis-example-list">
              {hsExamples.map((item) => (
                <button
                  key={item.code}
                  className={`analysis-chip ${hsCode === item.code ? "is-active" : ""}`}
                  onClick={() => handleExample(item.code)}
                >
                  <span>{item.label}</span>
                  <strong>{item.code}</strong>
                </button>
              ))}
            </div>

            <label className="analysis-field">
              <span>HS 코드</span>
              <input
                type="text"
                inputMode="numeric"
                value={hsCode}
                onChange={(event) => {
                  setHsCode(event.target.value.replace(/\D/g, "").slice(0, 6));
                  setError("");
                }}
                placeholder="예: 330499"
              />
            </label>

            <div className="analysis-field-grid">
              <label className="analysis-field">
                <span>추천 국가 수</span>
                <select value={topN} onChange={(event) => setTopN(Number(event.target.value))}>
                  <option value={3}>3개</option>
                  <option value={5}>5개</option>
                  <option value={8}>8개</option>
                  <option value={10}>10개</option>
                </select>
              </label>

              <label className="analysis-field">
                <span>기준 연도</span>
                <select value={year} onChange={(event) => setYear(Number(event.target.value))}>
                  <option value={2023}>2023</option>
                  <option value={2022}>2022</option>
                  <option value={2021}>2021</option>
                </select>
              </label>
            </div>

            <button className="ui-button ui-button--solid analysis-submit" onClick={handleAnalyze} disabled={loading}>
              {loading ? <LoaderCircle size={18} className="analysis-spin" /> : <Search size={18} />}
              {loading ? "분석 중..." : "추천 국가 계산"}
            </button>

            {error ? (
              <div className="analysis-inline-alert">
                <CircleAlert size={16} />
                <span>{error}</span>
              </div>
            ) : null}
          </div>
        </section>

        <section className="analysis-stage">
          <AnimatePresence mode="wait">
            {!result && !loading ? (
              <motion.div
                key="empty"
                className="analysis-empty"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <Sparkles size={20} />
                <h2>추천 국가가 이 영역에 나타납니다.</h2>
                <p>
                  점수는 여러 지표를 한데 모아 계산한 결과입니다. 비개발자 기준으로는
                  “어느 나라가 더 유망한지 숫자로 정리한 표”라고 보면 됩니다.
                </p>
              </motion.div>
            ) : null}

            {loading ? (
              <motion.div
                key="loading"
                className="analysis-loading"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <LoaderCircle size={24} className="analysis-spin" />
                <h2>추천 국가를 계산하고 있습니다.</h2>
                <p>서버가 켜져 있으면 응답 형식에 맞춰 자동으로 결과를 정리합니다.</p>
              </motion.div>
            ) : null}

            {result && !loading ? (
              <motion.div
                key="result"
                className="analysis-result"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <div className="analysis-overview">
                  <div>
                    <p className="analysis-kicker">Overview</p>
                    <h2>
                      HS {result.request?.hsCode || hsCode} 기준 추천 결과
                    </h2>
                    <p>{result.hint}</p>
                  </div>
                  <div className="analysis-overview-badge">
                    <span>{result.engine === "p1" ? "P1 추천 엔진" : "실험형 추천 엔진"}</span>
                    <strong>{result.recommendations.length}개 국가</strong>
                  </div>
                </div>

                <DiagnosticsPanel diagnostics={result.diagnostics} />

                <div className="analysis-panels">
                  <div className="analysis-list">
                    {result.recommendations.map((item) => (
                      <button
                        key={item.id}
                        className={`analysis-card ${selectedRecommendation?.id === item.id ? "is-selected" : ""}`}
                        onClick={() => {
                          startTransition(() => {
                            setSelectedId(item.id);
                          });
                        }}
                      >
                        <div className="analysis-card-rank">{item.rank}</div>
                        <div className="analysis-card-body">
                          <div className="analysis-card-title">
                            <div>
                              <strong>
                                {item.country.flag} {item.country.name}
                              </strong>
                              <span>{item.country.region}</span>
                            </div>
                            <span className="analysis-card-badge">{item.badge}</span>
                          </div>
                          <p>{item.summary}</p>
                        </div>
                        <div className="analysis-card-score">
                          <strong>{item.score.toFixed(1)}</strong>
                          <span>점</span>
                        </div>
                      </button>
                    ))}
                  </div>

                  <div className="analysis-detail">
                    {selectedRecommendation ? (
                      <>
                        <div className="analysis-detail-head">
                          <div>
                            <p className="analysis-kicker">Selected Country</p>
                            <h3>
                              {selectedRecommendation.country.flag} {selectedRecommendation.country.name}
                            </h3>
                          </div>
                          <a
                            className="analysis-detail-link"
                            href={`https://www.google.com/search?q=${encodeURIComponent(
                              `${selectedRecommendation.country.name} market ${hsCode}`
                            )}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            추가 조사
                            <ArrowUpRight size={16} />
                          </a>
                        </div>

                        <div className="analysis-metrics">
                          {selectedRecommendation.metrics.map((metric) => (
                            <MetricBar key={metric.key} metric={metric} />
                          ))}
                        </div>

                        <div className="analysis-detail-grid">
                          {selectedRecommendation.detailRows.map((row) => (
                            <div key={row.label} className="analysis-detail-row">
                              <span>{row.label}</span>
                              <strong>{row.value}</strong>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div className="analysis-empty analysis-empty--compact">
                        <CircleAlert size={18} />
                        <h3>현재 데이터 기준으로 추천 국가가 잡히지 않았습니다.</h3>
                        <p>
                          화면 연결 문제라기보다, 지금 들어 있는 CSV 데이터로는 국가별 추천을
                          만들지 못한 상태입니다.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <BuyerShortlistPanel buyers={result.buyers} />

                {result.diagnostics ? (
                  <DiagnosticsPanel diagnostics={result.diagnostics} />
                ) : null}
              </motion.div>
            ) : null}
          </AnimatePresence>
        </section>
      </main>
    </div>
  );
}
