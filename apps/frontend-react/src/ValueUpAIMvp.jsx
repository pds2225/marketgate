import React, { useMemo, useState } from "react";
import { Globe, ShieldAlert } from "lucide-react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import { ENDPOINTS } from "./config";

const COUNTRY_NAMES = {
  VNM: "베트남",
  USA: "미국",
  CHN: "중국",
  JPN: "일본",
  SGP: "싱가포르",
  THA: "태국",
  MYS: "말레이시아",
  IDN: "인도네시아",
  DEU: "독일",
  GBR: "영국",
};

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

function formatDiagnostics(items) {
  const values = (items || []).map((item) => diagnosticLabels[item] || item).filter(Boolean);
  return values.length > 0 ? values.join(" · ") : "없음";
}

function renderStatusTone(snapshot) {
  if (!snapshot) return "대기 중";
  if (!snapshot.is_git_repo) return "Git 아님";
  if (snapshot.status_key === "dirty") return "변경 있음";
  if (snapshot.status_key === "remote-missing") return "remote 없음";
  return "정상";
}

export default function ValueUpAIMvp() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const analyze = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(ENDPOINTS.predict, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          hs_code: "330499",
          exporter_country_iso3: "KOR",
          top_n: 3,
          year: 2023,
        }),
      });

      if (!response.ok) {
        throw new Error(`API 오류: ${response.status}`);
      }

      const data = await response.json();
      const topCountry = data?.data?.results?.[0];

      if (!topCountry) {
        setResult({
          empty: true,
          diagnostics: data?.data?.diagnostics || null,
        });
        return;
      }

      setResult({
        country: topCountry.partner_country_iso3,
        name: COUNTRY_NAMES[topCountry.partner_country_iso3] || topCountry.partner_country_iso3,
        fit_score: topCountry.fit_score,
        score_components: topCountry.score_components || {},
        explanation: topCountry.explanation || {},
        diagnostics: data?.data?.diagnostics || null,
      });
    } catch (err) {
      console.error("API 호출 오류:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const radarData = useMemo(() => {
    if (!result?.score_components) return [];

    const components = result.score_components;
    const softAdjustment = Number(components.soft_adjustment ?? 0);

    return [
      { axis: "무역 실적", value: Math.round(Number(components.trade_volume_score ?? 0) * 100) },
      { axis: "성장률", value: Math.round(Number(components.growth_score ?? 0) * 100) },
      { axis: "GDP 규모", value: Math.round(Number(components.gdp_score ?? 0) * 100) },
      { axis: "거리 이점", value: Math.round(Number(components.distance_score ?? 0) * 100) },
      { axis: "보정 점수", value: Math.max(0, Math.min(100, Math.round(100 + softAdjustment * 5))) },
    ];
  }, [result]);

  return (
    <div style={{ padding: 32, maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ fontSize: 32, fontWeight: "bold", marginBottom: 12 }}>
        VALUE-UP AI : 수출 유망국 추천 MVP
      </h1>
      <p style={{ color: "#6b7280", marginBottom: 24 }}>
        현재 화면은 `/v1/predict`와 공통 API 베이스 URL 규칙을 사용합니다.
      </p>

      <button
        onClick={analyze}
        disabled={loading}
        style={{
          padding: "12px 24px",
          fontSize: 16,
          backgroundColor: loading ? "#ccc" : "#2563eb",
          color: "white",
          border: "none",
          borderRadius: 8,
          cursor: loading ? "not-allowed" : "pointer",
          marginBottom: 24,
        }}
      >
        {loading ? "분석 중..." : "분석하기"}
      </button>

      {error && (
        <div
          style={{
            padding: 16,
            backgroundColor: "#fee",
            color: "#c00",
            borderRadius: 8,
            marginBottom: 24,
          }}
        >
          <strong>오류 발생:</strong> {error}
          <br />
          <small>백엔드 API 서버가 실행 중인지 확인하세요.</small>
        </div>
      )}

      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            style={{
              backgroundColor: "#f9fafb",
              padding: 24,
              borderRadius: 12,
              border: "1px solid #e5e7eb",
            }}
          >
            {result.empty ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: 16,
                  backgroundColor: "#fff7ed",
                  border: "1px solid #fdba74",
                  borderRadius: 8,
                }}
              >
                <ShieldAlert size={24} color="#c2410c" />
                <div>
                  <strong>추천 결과가 비어 있습니다.</strong>
                  <div style={{ color: "#7c2d12", marginTop: 4 }}>
                    {formatDiagnostics(result.diagnostics?.zero_result_reasons || [])}
                  </div>
                </div>
              </div>
            ) : (
              <>
                <h2 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 16 }}>
                  추천 국가: {result.name} ({result.country})
                </h2>

                <div style={{ marginBottom: 24 }}>
                  <div style={{ fontSize: 14, color: "#666", marginBottom: 8 }}>
                    <strong>종합 점수:</strong> {Number(result.fit_score || 0).toFixed(1)} / 100
                  </div>
                </div>

                <h3 style={{ fontSize: 18, fontWeight: "bold", marginBottom: 16 }}>
                  P1 점수 분해
                </h3>

                <div style={{ width: "100%", height: 360 }}>
                  <ResponsiveContainer>
                    <RadarChart data={radarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="axis" style={{ fontSize: 12 }} />
                      <PolarRadiusAxis domain={[0, 100]} />
                      <Radar
                        name="특성 기여도"
                        dataKey="value"
                        stroke="#2563eb"
                        fill="#2563eb"
                        fillOpacity={0.4}
                      />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>

                <div
                  style={{
                    marginTop: 24,
                    padding: 16,
                    backgroundColor: "#fff",
                    borderRadius: 8,
                  }}
                >
                  <h4 style={{ fontSize: 16, fontWeight: "bold", marginBottom: 12 }}>
                    주요 요인
                  </h4>
                  <ul style={{ fontSize: 14, lineHeight: 1.8 }}>
                    <li>
                      <strong>무역 실적:</strong>{" "}
                      {Number(result.score_components.trade_volume_score ?? 0).toFixed(3)}
                    </li>
                    <li>
                      <strong>성장률:</strong>{" "}
                      {Number(result.score_components.growth_score ?? 0).toFixed(3)}
                    </li>
                    <li>
                      <strong>GDP 규모:</strong>{" "}
                      {Number(result.score_components.gdp_score ?? 0).toFixed(3)}
                    </li>
                    <li>
                      <strong>거리 이점:</strong>{" "}
                      {Number(result.score_components.distance_score ?? 0).toFixed(3)}
                    </li>
                    <li>
                      <strong>보정 점수:</strong>{" "}
                      {Number(result.score_components.soft_adjustment ?? 0).toFixed(1)}
                    </li>
                  </ul>
                </div>

                {result.diagnostics && (
                  <div
                    style={{
                      marginTop: 24,
                      padding: 16,
                      backgroundColor: "#eff6ff",
                      border: "1px solid #bfdbfe",
                      borderRadius: 8,
                    }}
                  >
                    <h4 style={{ fontSize: 16, fontWeight: "bold", marginBottom: 12 }}>
                      진단 정보
                    </h4>
                    <div style={{ fontSize: 14, lineHeight: 1.8 }}>
                      <div>
                        <strong>후보 수:</strong> {result.diagnostics.candidate_count ?? "-"}
                      </div>
                      <div>
                        <strong>조건 충족:</strong> {result.diagnostics.eligible_count ?? "-"}
                      </div>
                      <div>
                        <strong>반환 수:</strong> {result.diagnostics.returned_count ?? "-"}
                      </div>
                      <div>
                        <strong>경고:</strong> {formatDiagnostics(result.diagnostics.quality_warnings)}
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div
        style={{
          marginTop: 24,
          padding: 16,
          borderRadius: 12,
          backgroundColor: "#f8fafc",
          border: "1px solid #e2e8f0",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <Globe size={18} />
          <strong>프로젝트 상태 예시</strong>
        </div>
        <div style={{ fontSize: 14, color: "#475569" }}>
          이 화면은 브라우저에 직접 Git 정보를 읽지 않고, 같은 상태 문구 규칙을 다른 화면과 공유합니다.
        </div>
        <div style={{ marginTop: 8, fontSize: 13, color: "#64748b" }}>
          상태 문구: {renderStatusTone(null)} · 대표 결과 수: {joinList([String(result?.fit_score ?? "")], "-")}
        </div>
      </div>
    </div>
  );
}
