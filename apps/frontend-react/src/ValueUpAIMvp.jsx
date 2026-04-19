import React, { useMemo, useState } from "react";
import {
  Globe,
  Loader2,
  TrendingUp,
  ShieldAlert,
  BadgeCheck,
} from "lucide-react";
import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { motion, AnimatePresence } from "framer-motion";

// 국가 코드 -> 한글 이름 매핑
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

export default function ValueUpAIMvp() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const analyze = async () => {
    setLoading(true);
    setError(null);

    try {
      // 백엔드 API 호출
      const response = await fetch("http://localhost:8000/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          hs_code: "33",
          exporter_country: "KOR",
          top_n: 3,
        }),
      });

      if (!response.ok) {
        throw new Error(`API 오류: ${response.status}`);
      }

      const data = await response.json();

      // 첫 번째 추천 국가 사용
      const topCountry = data.top_countries[0];

      // 결과 변환
      setResult({
        country: topCountry.country,
        name: COUNTRY_NAMES[topCountry.country] || topCountry.country,
        score: topCountry.score,
        expected_export_usd: topCountry.expected_export_usd,
        explanation: topCountry.explanation,
      });
    } catch (err) {
      console.error("API 호출 오류:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // explanation 필드를 레이더 차트 데이터로 변환
  const radarData = result
    ? [
        {
          axis: "중력모형 기준선",
          value: Math.abs(result.explanation.gravity_baseline) * 20,
        },
        {
          axis: "성장 잠재력",
          value: Math.abs(result.explanation.growth_potential) * 20,
        },
        {
          axis: "문화 적합성",
          value: Math.abs(result.explanation.culture_fit) * 20,
        },
        {
          axis: "규제 편의성",
          value: Math.abs(result.explanation.regulation_ease) * 20,
        },
        {
          axis: "물류 성과",
          value: Math.abs(result.explanation.logistics) * 20,
        },
        {
          axis: "관세 영향",
          value: Math.abs(result.explanation.tariff_impact) * 20,
        },
      ]
    : [];

  return (
    <div style={{ padding: 32, maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ fontSize: 32, fontWeight: "bold", marginBottom: 24 }}>
        VALUE-UP AI : 수출 유망국 추천 MVP
      </h1>

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
            <h2 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 16 }}>
              추천 국가: {result.name} ({result.country})
            </h2>

            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 14, color: "#666", marginBottom: 8 }}>
                <strong>종합 점수:</strong>{" "}
                {(result.score * 100).toFixed(1)} / 100
              </div>
              <div style={{ fontSize: 14, color: "#666" }}>
                <strong>예상 수출액:</strong> $
                {result.expected_export_usd.toLocaleString("en-US", {
                  maximumFractionDigits: 0,
                })}
              </div>
            </div>

            <h3 style={{ fontSize: 18, fontWeight: "bold", marginBottom: 16 }}>
              AI 분석 근거 (SHAP 기반)
            </h3>

            <div style={{ width: "100%", height: 400 }}>
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
                주요 요인 분석
              </h4>
              <ul style={{ fontSize: 14, lineHeight: 1.8 }}>
                <li>
                  <strong>중력모형 기준선:</strong>{" "}
                  {result.explanation.gravity_baseline > 0 ? "+" : ""}
                  {result.explanation.gravity_baseline.toFixed(3)} (경제 규모 및 거리 기반)
                </li>
                <li>
                  <strong>성장 잠재력:</strong>{" "}
                  {result.explanation.growth_potential > 0 ? "+" : ""}
                  {result.explanation.growth_potential.toFixed(3)} (GDP 성장률 반영)
                </li>
                <li>
                  <strong>문화 적합성:</strong>{" "}
                  {result.explanation.culture_fit > 0 ? "+" : ""}
                  {result.explanation.culture_fit.toFixed(3)} (문화적 유사성)
                </li>
                <li>
                  <strong>관세 영향:</strong>{" "}
                  {result.explanation.tariff_impact > 0 ? "+" : ""}
                  {result.explanation.tariff_impact.toFixed(3)} (관세율 영향)
                </li>
              </ul>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
