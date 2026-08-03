import { startTransition, useDeferredValue, useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  CircleAlert,
  Database,
  LoaderCircle,
  Mail,
  Search,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { buildP1Url, ENDPOINTS } from "./config";
import { displayPhone } from "./lib/phone";
import api from "./lib/api";
import { saveCompareSnapshot } from "./ComparePage";

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

      {diagnostics.coverage_status && diagnostics.coverage_status !== "OK" ? (
        <div
          style={{
            marginTop: 14,
            padding: "12px 14px",
            borderRadius: 12,
            border: "1px solid rgba(251, 191, 36, 0.45)",
            background: "rgba(120, 53, 15, 0.25)",
            display: "flex",
            gap: 10,
            alignItems: "flex-start",
          }}
        >
          <span aria-hidden="true">ℹ️</span>
          <div>
            <strong style={{ color: "#fde68a", fontSize: 13 }}>
              {diagnostics.coverage_status === "NO_BUYERS"
                ? "추천 없음"
                : "데이터 미지원 품목"}
            </strong>
            <div style={{ fontSize: 13, color: "#fef3c7", marginTop: 4 }}>
              {diagnostics.coverage_message ||
                "이 품목은 아직 추천 데이터가 준비되지 않았습니다."}
            </div>
          </div>
        </div>
      ) : null}

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

// P1 점수 항목별로, 그 점수를 만들 때 쓰인 원본 데이터가 비어 있는지 알려주는 키 매핑.
// 백엔드는 결측 시 0으로 대체하므로, 결측 여부를 함께 알아야 "진짜 0점"과 "데이터 없음"을 구분할 수 있다.
const p1MetricMissingKey = {
  gdp_score: "gdp_missing",
  growth_score: "growth_missing",
};

function buildP1Recommendation(entry) {
  const meta = getCountryMeta(entry.partner_country_iso3);
  const components = entry.score_components || {};
  const explanation = entry.explanation || {};
  const missingIndicators = explanation.missing_indicators || {};
  const dataCoverage = entry.data_coverage || null;
  const warnings = Array.isArray(entry.warnings) ? entry.warnings : [];
  const rawTopFactors = Array.isArray(explanation.top_factors) ? explanation.top_factors : [];
  const topFactors = rawTopFactors
    .map((item) => factorNames[item.factor] || item.factor)
    .filter(Boolean);

  const metrics = Object.entries(p1MetricMeta).map(([key, metaInfo]) => {
    const missingKey = p1MetricMissingKey[key];
    const missing = Boolean(missingKey && missingIndicators[missingKey]);
    return {
      key,
      label: metaInfo.label,
      tone: metaInfo.tone,
      missing,
      value: missing ? 0 : clampMetric(key, components[key]),
      displayValue: missing ? "자료 내 확인 불가" : formatMetricValue(key, components[key]),
    };
  });

  const tradeSourceLabels = {
    partner_observed: "상대국 관측 무역 실적",
    world_total_allocated: "세계 합계 배분(폴백)",
  };
  const tradeSource = explanation.trade_signal_source;
  const evidence = [];
  rawTopFactors.forEach((item, index) => {
    const label = factorNames[item.factor] || item.factor;
    if (!label) return;
    evidence.push({
      id: `factor-${index}`,
      label: `${index + 1}순위 기여 요인`,
      value: label,
      note: item.direction === "positive" ? "점수에 양의 기여" : item.direction || "",
    });
  });
  metrics.forEach((metric) => {
    evidence.push({
      id: `metric-${metric.key}`,
      label: metric.label,
      value: metric.displayValue,
      note: metric.missing ? "결측 — 점수에 반영하지 않음" : "정규화 지표",
    });
  });
  if (components.soft_adjustment != null && Number(components.soft_adjustment) !== 0) {
    evidence.push({
      id: "soft",
      label: "소프트 보정",
      value: `${Number(components.soft_adjustment) > 0 ? "+" : ""}${Number(components.soft_adjustment).toFixed(1)}점`,
      note: "규제·리스크 등 보정",
    });
  }
  if (components.compliance_penalty != null && Number(components.compliance_penalty) !== 0) {
    evidence.push({
      id: "compliance",
      label: "수출제한 페널티",
      value: `${Number(components.compliance_penalty).toFixed(1)}점`,
      note: "제한 국가 반영",
    });
  }
  if (tradeSource) {
    evidence.push({
      id: "trade-source",
      label: "무역 신호 출처",
      value: tradeSourceLabels[tradeSource] || tradeSource,
      note: "",
    });
  }
  if (explanation.kotra_weight_score != null) {
    evidence.push({
      id: "kotra",
      label: "KOTRA 가중 신호",
      value: String(explanation.kotra_weight_score),
      note: "원본 가중치",
    });
  }
  const sources = explanation.data_sources || [];
  if (sources.length) {
    evidence.push({
      id: "sources",
      label: "데이터 출처",
      value: sources.join(" · "),
      note: "",
    });
  }

  return {
    id: `${meta.iso3}-${entry.rank}`,
    country: meta,
    rank: entry.rank,
    score: Number(entry.fit_score || 0),
    badge: "P1 API",
    dataCoverage,
    warnings,
    evidence,
    summary:
      topFactors.length > 0
        ? `근거: ${topFactors.join(" · ")}`
        : "표시 가능한 상위 기여 요인이 응답에 없습니다.",
    metrics,
    detailRows: [
      { label: "주요 근거", value: topFactors.join(", ") || "표시 가능한 상위 요인 없음" },
      {
        label: "적용 필터",
        value: (explanation.filters_applied || []).join(", ") || "없음",
      },
      {
        label: "데이터 출처",
        value: sources.join(", ") || "CSV 파일 기준",
      },
      {
        label: "무역 신호",
        value: tradeSource ? (tradeSourceLabels[tradeSource] || tradeSource) : "자료 내 확인 불가",
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
    hint: "적합도 점수와 함께 기여 요인·출처·결측 근거를 표시합니다.",
    request: { hsCode: input.hs_code, topN: input.top_n, year: input.year },
    recommendations: results.map((entry) => buildP1Recommendation(entry)),
    diagnostics,
    buyers,
  };
}

function persistCompareFromAnalysis(analysis) {
  if (!analysis?.recommendations?.length) return;
  const hs = analysis.request?.hsCode || "";
  const buyerItems =
    analysis.buyers?.items || analysis.buyers?.buyers || analysis.buyers?.candidates || [];
  saveCompareSnapshot({
    hs_code: hs,
    generated_at: new Date().toISOString(),
    countries: analysis.recommendations.map((r, i) => ({
      rank: i + 1,
      iso3: r.iso3 || r.countryIso3 || r.id,
      name: r.name || r.countryName || r.title,
      score: r.score ?? r.finalScore,
      trade: r.metrics?.find?.((m) => /무역|trade/i.test(m.label))?.value,
      growth: r.metrics?.find?.((m) => /성장|growth/i.test(m.label))?.value,
      gdp: r.metrics?.find?.((m) => /gdp|GDP/i.test(m.label))?.value,
      distance: r.metrics?.find?.((m) => /거리|distance|물류/i.test(m.label))?.value,
    })),
    buyers: (Array.isArray(buyerItems) ? buyerItems : []).slice(0, 20).map((b, i) => ({
      rank: i + 1,
      name: b.buyer_name || b.name,
      country: b.country_norm || b.source_target_country_name || "",
      score: b.final_score ?? b.score,
      has_contact: !!b.has_contact,
      source: b.source_dataset || "",
      hs: b.hs_code_norm || hs,
      matched_by: b.matched_by || "",
    })),
  });
}

function buildOpportunitySignals(meta) {
  if (!meta || typeof meta !== "object") return [];

  const mapEntry = (entry) => ({
    title: String(entry.opportunity_title || entry.title || "").trim(),
    countryIso3: String(entry.country_iso3 || entry.opportunity_country_iso3 || "")
      .trim()
      .toUpperCase(),
    countryName: String(entry.opportunity_country_norm || "").trim(),
    signalType: String(entry.opportunity_signal_type || "").trim(),
    hsCode: String(entry.opportunity_hs_code_norm || "").trim(),
    keywords: String(entry.opportunity_keywords_norm || "").trim(),
    productName: String(entry.opportunity_product_name || "").trim(),
    validUntil: String(entry.opportunity_valid_until || "").trim(),
    sourceDataset: String(entry.opportunity_source_dataset || "").trim(),
    sourceFile: String(entry.opportunity_source_file || "").trim(),
    sourceRowNo: String(entry.opportunity_source_row_no || "").trim(),
    hasContact: Boolean(entry.opportunity_has_contact),
    contactName: String(entry.opportunity_contact_name || "").trim(),
    contactEmail: String(entry.opportunity_contact_email || "").trim(),
    contactPhone: String(entry.opportunity_contact_phone || "").trim(),
    contactWebsite: String(entry.opportunity_contact_website || "").trim(),
    signalUsable: Boolean(entry.opportunity_signal_usable),
    snapshotDate: String(entry.opportunity_snapshot_date || "").trim(),
    scoringApplied: Boolean(entry.scoring_opportunity_applied),
    matchScore:
      entry.match_score == null || entry.match_score === ""
        ? null
        : Number(entry.match_score),
  });

  const rich = Array.isArray(meta.opportunity_signals)
    ? meta.opportunity_signals
    : Array.isArray(meta.matched_opportunity_signals)
      ? meta.matched_opportunity_signals
      : [];
  if (rich.length > 0) {
    return rich.map(mapEntry).filter((row) => row.title);
  }

  const scores = Array.isArray(meta.selected_opportunity_match_scores)
    ? meta.selected_opportunity_match_scores
    : [];
  if (scores.length > 0) {
    return scores.map(mapEntry).filter((row) => row.title);
  }
  const titles = Array.isArray(meta.selected_opportunity_titles)
    ? meta.selected_opportunity_titles
    : [];
  const countries = Array.isArray(meta.selected_opportunity_countries)
    ? meta.selected_opportunity_countries
    : [];
  const types = Array.isArray(meta.selected_opportunity_signal_types)
    ? meta.selected_opportunity_signal_types
    : [];
  return titles
    .map((title, index) =>
      mapEntry({
        opportunity_title: title,
        opportunity_country_norm: countries[index] || "",
        opportunity_signal_type: types[index] || "",
      })
    )
    .filter((row) => row.title);
}

function signalTypeLabel(type) {
  const key = String(type || "").toLowerCase();
  if (key === "inquiry" || key.includes("inqu")) return "인콰이어리";
  if (key === "consultation" || key.includes("consult")) return "상담 요청";
  if (key === "offer" || key.includes("offer") || key.includes("구매")) return "구매 오퍼";
  if (!key) return "구매 신호";
  return type;
}

function formatKeywords(raw) {
  return String(raw || "")
    .split("|")
    .map((part) => part.trim())
    .filter((part) => part && part.toLowerCase() !== "none");
}

function FactLine({ label, value }) {
  const display = value == null || String(value).trim() === "" ? "자료 내 확인 불가" : String(value);
  return (
    <div style={{ display: "grid", gridTemplateColumns: "88px 1fr", gap: 8, fontSize: 12 }}>
      <span style={{ color: "#a8a29e" }}>{label}</span>
      <strong style={{ color: "#e7e5e4", fontWeight: 500 }}>{display}</strong>
    </div>
  );
}

/** 구매 신호(수요 인콰이어리 등) — 바이어 연락처가 아닐 수 있음. predict meta만 사용. */
function OpportunitySignalsPanel({ meta }) {
  const signals = buildOpportunitySignals(meta);
  return (
    <div
      style={{
        marginTop: 20,
        padding: 18,
        borderRadius: 20,
        border: "1px solid rgba(245, 158, 11, 0.28)",
        background: "rgba(41, 37, 36, 0.55)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div>
          <p className="analysis-kicker">Purchase Signals</p>
          <h3 style={{ margin: "6px 0 0", fontSize: 20 }}>구매 신호</h3>
          <p style={{ margin: "8px 0 0", color: "#a8a29e", fontSize: 13, lineHeight: 1.5 }}>
            buyKOREA 인콰이어리 등 <strong style={{ color: "#e7e5e4" }}>수요 신호</strong>입니다.
            연락 가능한 바이어 명단이 아니며, 원본에 있는 필드만 표시합니다.
          </p>
        </div>
        <strong style={{ color: "#fbbf24", whiteSpace: "nowrap" }}>{signals.length}건</strong>
      </div>

      {signals.length === 0 ? (
        <div className="analysis-empty analysis-empty--compact" style={{ marginTop: 14 }}>
          <CircleAlert size={18} />
          <h3>연결된 구매 신호 없음</h3>
          <p>현재 HS·추천국 조건으로 매칭된 인콰이어리/오퍼가 자료에 없거나 선택되지 않았습니다.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
          {signals.map((signal, index) => {
            const metaCountry = signal.countryIso3
              ? countryInfo[signal.countryIso3]
              : null;
            const countryLabel =
              metaCountry?.name ||
              signal.countryName ||
              signal.countryIso3 ||
              "국가 미상";
            const flag = metaCountry?.flag || "";
            const keywords = formatKeywords(signal.keywords);
            return (
              <div
                key={`${signal.title}-${index}`}
                style={{
                  padding: "12px 14px",
                  borderRadius: 12,
                  border: "1px solid rgba(168, 162, 158, 0.25)",
                  background: "rgba(12, 10, 9, 0.45)",
                  textAlign: "left",
                }}
              >
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 8 }}>
                  <span style={badgeStyle("#78350f", "#fcd34d")}>{signalTypeLabel(signal.signalType)}</span>
                  <span style={{ fontSize: 13, color: "#d6d3d1" }}>
                    {flag} {countryLabel}
                  </span>
                  {signal.scoringApplied ? (
                    <span style={badgeStyle("#1e3a8a", "#93c5fd")}>점수 반영됨</span>
                  ) : null}
                </div>
                <strong style={{ color: "#fafaf9", fontSize: 15, lineHeight: 1.4 }}>{signal.title}</strong>
                <div style={{ display: "grid", gap: 6, marginTop: 10 }}>
                  <FactLine label="품명" value={signal.productName} />
                  <FactLine label="HS" value={signal.hsCode} />
                  <FactLine
                    label="키워드"
                    value={keywords.length ? keywords.join(" · ") : ""}
                  />
                  <FactLine label="유효기한" value={signal.validUntil} />
                  <FactLine label="수집일" value={signal.snapshotDate} />
                  <FactLine label="출처" value={signal.sourceDataset} />
                  <FactLine
                    label="연락처"
                    value={
                      signal.hasContact
                        ? [signal.contactName, signal.contactEmail, signal.contactPhone, signal.contactWebsite]
                            .filter(Boolean)
                            .join(" · ")
                        : ""
                    }
                  />
                  <FactLine
                    label="매칭"
                    value={
                      signal.matchScore == null || Number.isNaN(signal.matchScore)
                        ? ""
                        : `${signal.matchScore} (엔진 참고)`
                    }
                  />
                  <FactLine
                    label="사용가능"
                    value={signal.signalUsable ? "예" : "자료 기준 미확인/불가"}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function BuyerShortlistPanel({ buyers, onInquiry }) {
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

      {buyers.meta?.buyer_country_mismatch ? (
        <div
          style={{
            marginTop: 14,
            padding: "12px 14px",
            borderRadius: 12,
            border: "1px solid rgba(248, 113, 113, 0.45)",
            background: "rgba(127, 29, 29, 0.28)",
            display: "flex",
            gap: 10,
            alignItems: "flex-start",
          }}
        >
          <CircleAlert size={16} style={{ color: "#fca5a5", flexShrink: 0, marginTop: 2 }} />
          <div>
            <strong style={{ color: "#fecaca", fontSize: 13 }}>추천국 ≠ 바이어국</strong>
            <div style={{ fontSize: 13, color: "#fee2e2", marginTop: 4 }}>
              {buyers.meta.buyer_country_mismatch.message}
            </div>
          </div>
        </div>
      ) : null}

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
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                      {item.source_verification === "verified" ? (
                        <span style={badgeStyle("#065f46", "#6ee7b7")}>출처 검증됨</span>
                      ) : item.source_verification === "unverified" ? (
                        <span style={badgeStyle("#78350f", "#fcd34d")}>출처 미검증(SNS)</span>
                      ) : (
                        <span style={badgeStyle("#334155", "#cbd5e1")}>출처 미상</span>
                      )}
                      {item.contact_email_estimated ? (
                        <span style={badgeStyle("#78350f", "#fcd34d")}>추정 연락처</span>
                      ) : null}
                    </div>
                  </div>
                  <span className="analysis-card-badge">
                    {item.final_score != null
                      ? `${Number(item.final_score).toFixed?.(1) ?? item.final_score}점`
                      : "점수 없음"}
                  </span>
                </div>
                <p>
                  <strong style={{ color: "#e7e5e4" }}>근거 </strong>
                  {(item.explanation_reasons || item.recommendation_lines || []).join(" · ") ||
                    "근거 문장 없음"}
                </p>
                <div className="analysis-detail-grid" style={{ marginTop: 12 }}>
                  <div className="analysis-detail-row">
                    <span>추천 국가</span>
                    <strong>
                      {item.source_target_country_name || item.source_target_country_iso3 || "-"}
                    </strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>바이어 HS</span>
                    <strong>{item.hs_code_norm || "자료 내 확인 불가"}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>키워드</span>
                    <strong>{item.keywords_norm || (item.matched_terms || []).join(", ") || "자료 내 확인 불가"}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>매칭</span>
                    <strong>{item.matched_by || "자료 내 확인 불가"}{item.decision ? ` · ${item.decision}` : ""}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>이메일</span>
                    <strong>{item.contact_email || "-"}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>전화번호</span>
                    <strong>{displayPhone(item.contact_phone)}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>홈페이지</span>
                    <strong>{item.contact_website || "-"}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>담당자</span>
                    <strong>{item.contact_name || "-"}</strong>
                  </div>
                  <div className="analysis-detail-row">
                    <span>출처</span>
                    <strong>{item.source_dataset || "자료 내 확인 불가"}</strong>
                  </div>
                </div>
                {onInquiry ? (
                  <div style={{ marginTop: 12 }}>
                    <button
                      className="ui-button ui-button--ghost"
                      style={{ fontSize: 13, padding: "8px 12px" }}
                      onClick={() => onInquiry(item)}
                    >
                      <Mail size={14} />
                      인콰이어리 작성
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

async function fetchJson(url, body) {
  const token = localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const response = await fetch(url, {
    method: "POST",
    headers,
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
        p1Issue = "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.";
      } else {
        p1Issue = `P1 API 오류: ${msg}`;
      }
    }
  }

  try {
    const legacyPayload = await fetchJson(buildP1Url("/predict"), {
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
    <div className={`analysis-metric ${metric.missing ? "analysis-metric--missing" : ""}`}>
      <div className="analysis-metric-head">
        <span>{metric.label}</span>
        <strong>{metric.displayValue}</strong>
      </div>
      <div className="analysis-metric-track">
        {metric.missing ? (
          <div className="analysis-metric-empty">자료 내 확인 불가</div>
        ) : (
          <div
            className={`analysis-metric-fill analysis-metric-fill--${metric.tone}`}
            style={{ width: `${metric.value * 100}%` }}
          />
        )}
      </div>
    </div>
  );
}

function levelLabel(level) {
  if (level === "high") return "높음";
  if (level === "medium") return "보통";
  if (level === "low") return "낮음";
  if (level === "very_low") return "매우 낮음";
  return level || "-";
}

function badgeStyle(bg, fg) {
  return {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 600,
    background: bg,
    color: fg,
    lineHeight: 1.6,
  };
}

function ConfidenceNotice({ recommendation }) {
  const coverage = recommendation?.dataCoverage;
  const warnings = recommendation?.warnings || [];
  const lowConfidence =
    coverage && (coverage.confidence_level === "low" || coverage.confidence_level === "very_low");
  // 가산 (matchA): 리스크 미평가 상태면 'high'가 아니라 정직한 display 라벨로 안내한다.
  const riskUnassessed = coverage && coverage.risk_assessed === false;
  const displayLevel = coverage?.display_confidence_level || coverage?.confidence_level;

  if (!lowConfidence && !riskUnassessed && warnings.length === 0) {
    return null;
  }

  const missingFieldLabels = {
    export_score: "수출 행동 점수",
    gdp: "GDP 규모",
    growth_rate: "GDP 성장률",
    market_size: "시장 규모",
    news_risk: "뉴스 리스크",
  };
  const missingFields = (coverage?.missing_fields || [])
    .map((field) => missingFieldLabels[field] || field)
    .filter(Boolean);

  return (
    <div
      className="analysis-inline-alert"
      style={{ marginBottom: 16, alignItems: "flex-start" }}
      role="status"
    >
      <CircleAlert size={16} style={{ marginTop: 2, flexShrink: 0 }} />
      <div>
        {lowConfidence ? (
          <div>
            데이터 신뢰도 <strong>{levelLabel(displayLevel)}</strong>
            {coverage.confidence != null ? ` (${Math.round(coverage.confidence * 100)}%)` : ""}
            {missingFields.length > 0 ? ` · 결측: ${missingFields.join(" · ")}` : ""}. 일부 점수가
            0으로 보일 수 있으나 이는 데이터가 비어 있어서이며 실제 0점이 아닙니다.
          </div>
        ) : null}
        {!lowConfidence && riskUnassessed ? (
          <div>
            데이터 신뢰도 <strong>{levelLabel(displayLevel)}</strong>
            {coverage.confidence != null ? ` (${Math.round(coverage.confidence * 100)}%)` : ""} · 리스크(뉴스·제재
            동향) 미평가로 '높음' 표시는 제한됩니다.
          </div>
        ) : null}
        {warnings
          .filter(
            (item) =>
              item &&
              item.code !== "LOW_CONFIDENCE" &&
              !(item.code === "RISK_NOT_ASSESSED" && riskUnassessed)
          )
          .map((item, index) => (
            <div key={`${item.code}-${index}`} style={{ marginTop: lowConfidence || index > 0 ? 6 : 0 }}>
              {item.message || item.code}
            </div>
          ))}
      </div>
    </div>
  );
}

export default function AnalysisPage({ onBack, preset, onBalanceRefresh }) {
  const [hsCode, setHsCode] = useState("330499");
  const [topN, setTopN] = useState(5);
  const [year, setYear] = useState(2023);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  const [inquiryBuyer, setInquiryBuyer] = useState(null);
  const [showInquiryModal, setShowInquiryModal] = useState(false);
  const [inquiryForm, setInquiryForm] = useState({ sender_company: "", sender_name: "", message: "" });
  const [inquiryLoading, setInquiryLoading] = useState(false);
  const [inquiryResult, setInquiryResult] = useState(null);
  const [inquiryError, setInquiryError] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const [queueRecord, setQueueRecord] = useState(null);
  const [queueSubmitted, setQueueSubmitted] = useState(false);
  const [draftPlanBlocked, setDraftPlanBlocked] = useState(false);

  const deferredSelectedId = useDeferredValue(selectedId);
  const selectedRecommendation =
    result?.recommendations.find((item) => item.id === deferredSelectedId) ||
    result?.recommendations[0] ||
    null;

  useEffect(() => {
    if (!preset?.hsCode) return;
    const code = String(preset.hsCode).replace(/\D/g, "").slice(0, 6);
    if (!code) return;
    setHsCode(code);
    setError("");

    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const analysis = await requestAnalysis(code, topN, year);
        if (cancelled) return;
        persistCompareFromAnalysis(analysis);
        startTransition(() => {
          setResult(analysis);
          setSelectedId(analysis.recommendations[0]?.id || null);
        });
      } catch (requestError) {
        if (cancelled) return;
        setResult(null);
        setSelectedId(null);
        setError(requestError.message || "분석 요청에 실패했습니다.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
    // 랜딩에서 넘긴 HS만 1회 자동 분석 — topN/year 변경으로 재실행하지 않음
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preset]);

  const handleAnalyze = async () => {
    if (!/^\d{2,6}$/.test(hsCode.trim())) {
      setError("HS 코드는 숫자 2자리에서 6자리까지 입력해야 합니다.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const analysis = await requestAnalysis(hsCode, topN, year);
      persistCompareFromAnalysis(analysis);

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

  const handleOpenInquiry = (buyer) => {
    setInquiryBuyer(buyer);
    setInquiryForm({ sender_company: "", sender_name: "", message: "" });
    setInquiryResult(null);
    setInquiryError("");
    setCopyStatus("");
    setDraftPlanBlocked(false);
    setShowInquiryModal(true);
  };

  const handleCloseInquiry = () => {
    setShowInquiryModal(false);
    setInquiryBuyer(null);
    setInquiryResult(null);
    setInquiryError("");
    setCopyStatus("");
    setQueueRecord(null);
    setQueueSubmitted(false);
    setDraftPlanBlocked(false);
  };

  const handleCopyDraft = async (text, label) => {
    const value = String(text || "");
    if (!value) {
      setCopyStatus("복사할 내용이 없습니다.");
      return;
    }
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        throw new Error("clipboard unavailable");
      }
      setCopyStatus(`${label} 초안을 복사했습니다.`);
    } catch {
      setCopyStatus("자동 복사가 막혀 있어요. 초안을 길게 눌러(드래그) 직접 복사해 주세요.");
    }
  };

  const handleInquirySubmit = async () => {
    if (!inquiryForm.sender_company.trim() || !inquiryForm.sender_name.trim()) {
      setInquiryError("회사명과 담당자 이름을 입력해 주세요.");
      return;
    }
    setInquiryLoading(true);
    setInquiryError("");
    try {
      const inquiryToken = localStorage.getItem("access_token");
      const inquiryHeaders = { "Content-Type": "application/json" };
      if (inquiryToken) inquiryHeaders["Authorization"] = `Bearer ${inquiryToken}`;
      const res = await fetch(buildP1Url("/v1/inquiry"), {
        method: "POST",
        headers: inquiryHeaders,
        body: JSON.stringify({
          buyer_name: inquiryBuyer.buyer_name || "Unknown",
          contact_email: inquiryBuyer.contact_email || "",
          hs_code: inquiryBuyer.hs_code_norm || hsCode || "",
          sender_company: inquiryForm.sender_company,
          sender_name: inquiryForm.sender_name,
          message: inquiryForm.message,
        }),
      });
      let data = null;
      try {
        data = await res.json();
      } catch {
        data = null;
      }
      if (!res.ok) {
        const detail = data?.detail || data?.message || "";
        if (res.status === 403 || /requires_.*_plan/i.test(String(detail))) {
          setDraftPlanBlocked(true);
          return;
        }
        let message;
        if (res.status === 401) {
          message = "로그인이 필요합니다. 다시 로그인한 뒤 시도해 주세요.";
        } else {
          message = detail || `인콰이어리 생성에 실패했습니다 (${res.status}).`;
        }
        throw new Error(message);
      }
      setInquiryResult(data);
    } catch (err) {
      setInquiryError(err.message || "잠시 후 다시 시도해 주세요.");
    } finally {
      setInquiryLoading(false);
    }
  };

  const handleQueueSubmit = async () => {
    if (!inquiryBuyer?.contact_email || !String(inquiryBuyer.contact_email).includes("@")) {
      setInquiryError("이메일이 있는 바이어만 발송 검토 요청을 할 수 있습니다.");
      return;
    }
    if (!inquiryForm.sender_company.trim() || !inquiryForm.sender_name.trim()) {
      setInquiryError("회사명과 담당자 이름을 입력해 주세요.");
      return;
    }
    setInquiryLoading(true);
    setInquiryError("");
    try {
      let record = queueRecord;
      if (!record) {
        const created = await api.post("/v1/inquiries", {
          buyer_name: inquiryBuyer.buyer_name || "Unknown",
          buyer_id: inquiryBuyer.buyer_name || "unknown",
          recipient_email: inquiryBuyer.contact_email,
          hs_code: inquiryBuyer.hs_code_norm || hsCode || "",
          sender_company: inquiryForm.sender_company.trim(),
          sender_name: inquiryForm.sender_name.trim(),
          message: inquiryForm.message.trim(),
          country: inquiryBuyer.source_target_country_name || inquiryBuyer.country_norm || "",
          match_relevance: inquiryBuyer.match_relevance,
          recommendation_lines: inquiryBuyer.recommendation_lines,
        });
        record = created.data;
        setQueueRecord(record);
        if (!inquiryResult && record.draft_ko) {
          setInquiryResult({ draft_ko: record.draft_ko, draft_en: record.draft_en });
        }
      }
      const submitted = await api.post(`/v1/inquiries/${record.inquiry_id}/submit`);
      setQueueRecord(submitted.data);
      setQueueSubmitted(true);
      setCopyStatus("발송 검토 요청이 접수되었습니다. 관리자 승인 후 발송됩니다.");
      try {
        await api.post("/v1/credits/deduct", { action: "contact_send" });
        if (onBalanceRefresh) await onBalanceRefresh();
      } catch {
        /* 잔액 부족이어도 큐 접수는 유지 */
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setInquiryError(
        detail === "contact_missing"
          ? "연락처(이메일)가 없는 바이어는 발송 요청을 만들 수 없습니다."
          : detail || err.message || "발송 검토 요청에 실패했습니다."
      );
    } finally {
      setInquiryLoading(false);
    }
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

            <div className="analysis-next-steps" aria-label="분석 진행 순서">
              <div>
                <span>1</span>
                <strong>품목 선택</strong>
                <p>예시를 누르거나 HS 코드를 입력합니다.</p>
              </div>
              <div>
                <span>2</span>
                <strong>조건 확인</strong>
                <p>추천 국가 수와 기준 연도를 맞춥니다.</p>
              </div>
              <div>
                <span>3</span>
                <strong>결과 검토</strong>
                <p>국가 점수와 그 근거(요인·출처·결측)를 함께 봅니다.</p>
              </div>
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
                <div className="analysis-empty-steps">
                  <div className="analysis-empty-step">
                    <span className="analysis-empty-step-num">1</span>
                    <div>
                      <strong>HS 코드 입력</strong>
                      <span>왼쪽 패널에서 품목 코드를 입력하거나 예시를 클릭하세요.</span>
                    </div>
                  </div>
                  <div className="analysis-empty-step">
                    <span className="analysis-empty-step-num">2</span>
                    <div>
                      <strong>추천 국가 계산</strong>
                      <span>버튼을 누르면 데이터 기반 유망 시장을 자동 분석합니다.</span>
                    </div>
                  </div>
                  <div className="analysis-empty-step">
                    <span className="analysis-empty-step-num">3</span>
                    <div>
                      <strong>결과 확인 및 바이어 탐색</strong>
                      <span>점수·근거·바이어 후보·구매 신호까지 한 화면에 정리됩니다.</span>
                    </div>
                  </div>
                </div>
                <p className="analysis-empty-hint">
                  왼쪽 입력 패널에서 <strong>추천 국가 계산</strong> 버튼을 눌러 시작하세요.
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

                        <ConfidenceNotice recommendation={selectedRecommendation} />

                        <div
                          style={{
                            marginBottom: 16,
                            padding: "14px 16px",
                            borderRadius: 14,
                            border: "1px solid rgba(245, 158, 11, 0.3)",
                            background: "rgba(41, 37, 36, 0.55)",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
                            <div>
                              <p className="analysis-kicker">Score Evidence</p>
                              <h4 style={{ margin: "4px 0 0", fontSize: 16, color: "#fafaf9" }}>
                                이 순위·점수의 근거
                              </h4>
                            </div>
                            <strong style={{ color: "#fbbf24", fontSize: 20 }}>
                              {selectedRecommendation.score.toFixed(1)}
                              <span style={{ fontSize: 12, marginLeft: 4 }}>점</span>
                            </strong>
                          </div>
                          {(selectedRecommendation.evidence || []).length === 0 ? (
                            <p style={{ margin: "12px 0 0", fontSize: 13, color: "#a8a29e" }}>
                              응답에 표시 가능한 근거 항목이 없습니다.
                            </p>
                          ) : (
                            <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                              {selectedRecommendation.evidence.map((row) => (
                                <div
                                  key={row.id}
                                  style={{
                                    display: "grid",
                                    gridTemplateColumns: "minmax(96px, 140px) 1fr",
                                    gap: 10,
                                    padding: "8px 10px",
                                    borderRadius: 10,
                                    background: "rgba(12, 10, 9, 0.45)",
                                    border: "1px solid rgba(168, 162, 158, 0.2)",
                                  }}
                                >
                                  <span style={{ fontSize: 12, color: "#a8a29e" }}>{row.label}</span>
                                  <div>
                                    <strong style={{ fontSize: 13, color: "#f5f5f4", fontWeight: 600 }}>{row.value}</strong>
                                    {row.note ? (
                                      <div style={{ fontSize: 11, color: "#78716c", marginTop: 2 }}>{row.note}</div>
                                    ) : null}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
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
                          현재 조건으로는 국가별 추천을 만들지 못했습니다. HS 코드나 연도를 바꿔 다시 시도해 주세요.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <OpportunitySignalsPanel meta={result.buyers?.meta} />
                <BuyerShortlistPanel buyers={result.buyers} onInquiry={handleOpenInquiry} />
              </motion.div>
            ) : null}
          </AnimatePresence>

          {/* 인콰이어리 모달 */}
          <AnimatePresence>
            {showInquiryModal && inquiryBuyer && (
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
                onClick={handleCloseInquiry}
              >
                <motion.div
                  style={{
                    width: "100%",
                    maxWidth: 520,
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
                    <h3 style={{ margin: 0, fontSize: 18 }}>✉️ 인콰이어리 작성</h3>
                    <button className="ui-button ui-button--ghost" onClick={handleCloseInquiry} style={{ padding: 6 }}>
                      <X size={18} />
                    </button>
                  </div>

                  <div style={{ marginBottom: 14, fontSize: 14, color: "#94a3b8" }}>
                    <strong style={{ color: "#e2e8f0" }}>{inquiryBuyer.buyer_name}</strong> · {" "}
                    {inquiryBuyer.contact_email || "연락처 미제공"}
                  </div>

                  {!inquiryResult ? (
                    <>
                      <label className="analysis-field" style={{ marginBottom: 12 }}>
                        <span>회사명 (sender_company)</span>
                        <input
                          type="text"
                          value={inquiryForm.sender_company}
                          onChange={(e) => setInquiryForm((prev) => ({ ...prev, sender_company: e.target.value }))}
                          placeholder="예: 주식회사 샘플"
                        />
                      </label>
                      <label className="analysis-field" style={{ marginBottom: 12 }}>
                        <span>담당자 이름 (sender_name)</span>
                        <input
                          type="text"
                          value={inquiryForm.sender_name}
                          onChange={(e) => setInquiryForm((prev) => ({ ...prev, sender_name: e.target.value }))}
                          placeholder="예: 김철수"
                        />
                      </label>
                      <label className="analysis-field" style={{ marginBottom: 12 }}>
                        <span>추가 메시지 (선택)</span>
                        <textarea
                          rows={3}
                          value={inquiryForm.message}
                          onChange={(e) => setInquiryForm((prev) => ({ ...prev, message: e.target.value }))}
                          placeholder="전달하고 싶은 내용을 입력하세요."
                          style={{ resize: "vertical" }}
                        />
                      </label>

                      {inquiryError ? (
                        <div className="analysis-inline-alert" style={{ marginBottom: 12 }}>
                          <CircleAlert size={16} />
                          <span>{inquiryError}</span>
                        </div>
                      ) : null}

                      {draftPlanBlocked ? (
                        <div className="analysis-inline-alert" style={{ marginBottom: 12 }}>
                          <CircleAlert size={16} />
                          <span>AI 초안 작성은 Advanced 플랜 기능입니다. 발송 검토 요청은 바로 이용하실 수 있습니다.</span>
                        </div>
                      ) : null}

                      <button
                        className="ui-button ui-button--solid"
                        onClick={handleInquirySubmit}
                        disabled={inquiryLoading || draftPlanBlocked}
                        style={{ width: "100%" }}
                      >
                        {inquiryLoading ? <LoaderCircle size={18} className="analysis-spin" /> : <Mail size={18} />}
                        {inquiryLoading ? "생성 중..." : "인콰이어리 초안 생성"}
                      </button>

                      {!queueSubmitted ? (
                        <button
                          className="ui-button ui-button--ghost"
                          onClick={handleQueueSubmit}
                          disabled={inquiryLoading || !inquiryBuyer?.contact_email}
                          title={!inquiryBuyer?.contact_email ? "이메일 필요" : "관리자 검토 큐에 제출"}
                          style={{ width: "100%", marginTop: 8 }}
                        >
                          {inquiryLoading ? "제출 중…" : "발송 검토 요청"}
                        </button>
                      ) : (
                        <p style={{ marginTop: 10, marginBottom: 0, fontSize: 13, color: "#86efac" }}>
                          검토 대기 ({queueRecord?.status || "review_required"})
                        </p>
                      )}

                      {copyStatus ? (
                        <p role="status" style={{ marginTop: 10, marginBottom: 0, fontSize: 13, color: "#94a3b8" }}>
                          {copyStatus}
                        </p>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <div style={{ marginBottom: 12 }}>
                        <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>영문 초안</p>
                        <div
                          style={{
                            background: "rgba(15,23,42,0.8)",
                            border: "1px solid rgba(148,163,184,0.2)",
                            borderRadius: 12,
                            padding: 14,
                            fontSize: 14,
                            lineHeight: 1.6,
                            whiteSpace: "pre-wrap",
                          }}
                        >
                          {inquiryResult.draft_en}
                        </div>
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>한국어 초안</p>
                        <div
                          style={{
                            background: "rgba(15,23,42,0.8)",
                            border: "1px solid rgba(148,163,184,0.2)",
                            borderRadius: 12,
                            padding: 14,
                            fontSize: 14,
                            lineHeight: 1.6,
                            whiteSpace: "pre-wrap",
                          }}
                        >
                          {inquiryResult.draft_ko}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <button className="ui-button ui-button--solid" style={{ flex: 1, minWidth: 120 }} onClick={() => handleCopyDraft(inquiryResult.draft_ko, "한국어")}>
                          한국어 복사
                        </button>
                        <button className="ui-button ui-button--solid" style={{ flex: 1, minWidth: 120 }} onClick={() => handleCopyDraft(inquiryResult.draft_en, "영문")}>
                          영문 복사
                        </button>
                        {!queueSubmitted ? (
                          <button
                            className="ui-button ui-button--solid"
                            style={{ flex: 1, minWidth: 140 }}
                            onClick={handleQueueSubmit}
                            disabled={inquiryLoading || !inquiryBuyer?.contact_email}
                            title={!inquiryBuyer?.contact_email ? "이메일 필요" : "관리자 검토 큐에 제출"}
                          >
                            {inquiryLoading ? "제출 중…" : "발송 검토 요청"}
                          </button>
                        ) : (
                          <span style={{ flex: 1, minWidth: 140, fontSize: 12, color: "#86efac", alignSelf: "center" }}>
                            검토 대기 ({queueRecord?.status || "review_required"})
                          </span>
                        )}
                        <button className="ui-button ui-button--ghost" style={{ flex: 1, minWidth: 120 }} onClick={handleCloseInquiry}>
                          닫기
                        </button>
                      </div>
                      {copyStatus ? (
                        <p role="status" style={{ marginTop: 10, marginBottom: 0, fontSize: 13, color: "#94a3b8" }}>
                          {copyStatus}
                        </p>
                      ) : null}
                    </>
                  )}
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </main>
    </div>
  );
}
