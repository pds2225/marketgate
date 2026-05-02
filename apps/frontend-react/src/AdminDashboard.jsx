import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle,
  Database,
  GitBranch,
  PlayCircle,
  RefreshCw,
  Server,
  Settings,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { API_BASE, ENDPOINTS } from "./config";

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

function projectStatusTone(snapshot) {
  if (!snapshot) return undefined;
  if (!snapshot.is_git_repo) return false;
  if (snapshot.status_key === "clean") return true;
  if (snapshot.status_key === "non-git") return false;
  return undefined;
}

function getResultsFromTest(testResult) {
  if (!testResult) return [];
  if (testResult.mode === "p1") {
    return testResult.payload?.data?.results || [];
  }
  return testResult.payload?.top_countries || [];
}

function getDiagnosticsFromTest(testResult) {
  if (!testResult) return null;
  if (testResult.mode === "p1") {
    return testResult.payload?.data?.diagnostics || null;
  }
  return testResult.payload?.diagnostics || null;
}

export default function AdminDashboard() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [logs, setLogs] = useState([]);

  const pushLog = (msg, type = "info") => {
    setLogs((prev) => [...prev, { time: new Date().toLocaleTimeString(), msg, type }]);
  };

  const checkSystemStatus = async () => {
    setLoading(true);
    try {
      pushLog("백엔드와 프로젝트 상태를 확인 중...", "info");

      const [healthRes, snapshotRes] = await Promise.all([
        fetch(ENDPOINTS.health),
        fetch(ENDPOINTS.snapshot),
      ]);

      const healthData = await healthRes.json();
      const snapshotData = await snapshotRes.json();

      setSystemStatus({
        backend: healthRes.ok,
        backendTimestamp: healthData.timestamp ?? null,
        projectSnapshot: snapshotData?.data ?? null,
        apiBase: API_BASE,
      });

      pushLog("✓ 시스템 정상", "success");
    } catch (err) {
      setSystemStatus({ backend: false, projectSnapshot: null, apiBase: API_BASE });
      pushLog(`✗ 오류: ${err?.message || String(err)}`, "error");
    } finally {
      setLoading(false);
    }
  };

  const testP1API = async () => {
    setLoading(true);
    try {
      pushLog("P1 스모크 테스트 시작...", "info");

      const response = await fetch(ENDPOINTS.predict, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hs_code: "330499",
          exporter_country_iso3: "KOR",
          top_n: 5,
          year: 2023,
        }),
      });

      const data = await response.json();
      setTestResult({ mode: "p1", payload: data });

      const n = data?.data?.results?.length ?? 0;
      const diag = data?.data?.diagnostics;
      const warn = diag?.quality_warnings?.length ? ` (경고 ${diag.quality_warnings.length}건)` : "";
      pushLog(`✓ P1 테스트 성공: ${n}개 국가 추천${warn}`, "success");
    } catch (err) {
      pushLog(`✗ P1 테스트 실패: ${err?.message || String(err)}`, "error");
    } finally {
      setLoading(false);
    }
  };

  const testLegacyAPI = async () => {
    setLoading(true);
    try {
      pushLog("호환성 테스트 시작...", "info");

      const response = await fetch(ENDPOINTS.legacyPredict, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hs_code: "330499",
          exporter_country: "KOR",
          top_n: 5,
          year: 2023,
        }),
      });

      const data = await response.json();
      setTestResult({ mode: "legacy", payload: data });

      const n = data?.top_countries?.length ?? 0;
      pushLog(`✓ 호환성 테스트 성공: ${n}개 국가 추천`, "success");
    } catch (err) {
      pushLog(`✗ 호환성 테스트 실패: ${err?.message || String(err)}`, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkSystemStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const diagnostics = getDiagnosticsFromTest(testResult);
  const results = getResultsFromTest(testResult);

  return (
    <div style={{ padding: 32, maxWidth: 1400, margin: "0 auto", fontFamily: "sans-serif" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 32, fontWeight: "bold", marginBottom: 8 }}>
          <Settings style={{ display: "inline", marginRight: 12 }} />
          MarketGate 관리자 대시보드
        </h1>
        <p style={{ color: "#666" }}>시스템 상태 모니터링 및 P1 계약 점검</p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
          marginBottom: 32,
        }}
      >
        <StatusCard title="백엔드 서버" icon={<Server />} status={systemStatus?.backend} details="FastAPI /v1/health" />
        <StatusCard
          title="프로젝트 상태"
          icon={<GitBranch />}
          status={projectStatusTone(systemStatus?.projectSnapshot)}
          details={systemStatus?.projectSnapshot?.status_text || "Git 상태 확인 중"}
        />
        <StatusCard title="P1 추천 API" icon={<TrendingUp />} status={!!(results.length > 0)} details="POST /v1/predict" />
        <StatusCard
          title="호환성 계약"
          icon={<Database />}
          status={testResult?.mode === "legacy" ? results.length > 0 : undefined}
          details="POST /predict"
        />
      </div>

      <div
        style={{
          backgroundColor: "#f9fafb",
          padding: 24,
          borderRadius: 12,
          marginBottom: 32,
          border: "1px solid #e5e7eb",
        }}
      >
        <h2 style={{ fontSize: 20, fontWeight: "bold", marginBottom: 16 }}>
          <Settings style={{ display: "inline", marginRight: 8, width: 20, height: 20 }} />
          현재 설정
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
          <ConfigItem label="API Base URL" value={systemStatus?.apiBase || API_BASE} />
          <ConfigItem label="브랜치" value={systemStatus?.projectSnapshot?.branch || "non-git"} />
          <ConfigItem label="HEAD" value={systemStatus?.projectSnapshot?.head || "-"} />
          <ConfigItem label="remote" value={systemStatus?.projectSnapshot?.remote || "없음"} />
        </div>

        <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
          <ConfigItem
            label="dirty"
            value={systemStatus?.projectSnapshot?.dirty === null || systemStatus?.projectSnapshot?.dirty === undefined ? "-" : systemStatus.projectSnapshot.dirty ? "예" : "아니오"}
          />
          <ConfigItem label="상태 문구" value={systemStatus?.projectSnapshot?.status_text || "Git 저장소가 아닙니다."} />
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 32, flexWrap: "wrap" }}>
        <Button onClick={checkSystemStatus} disabled={loading} icon={<RefreshCw />} variant="primary">
          상태 새로고침
        </Button>
        <Button onClick={testP1API} disabled={loading} icon={<PlayCircle />} variant="success">
          P1 스모크 테스트
        </Button>
        <Button onClick={testLegacyAPI} disabled={loading} icon={<Activity />} variant="warning">
          호환성 테스트
        </Button>
      </div>

      {testResult && (
        <div
          style={{
            backgroundColor: "#f0f9ff",
            padding: 24,
            borderRadius: 12,
            marginBottom: 32,
            border: "1px solid #0284c7",
          }}
        >
          <h2 style={{ fontSize: 20, fontWeight: "bold", marginBottom: 16 }}>
            <BarChart3 style={{ display: "inline", marginRight: 8, width: 20, height: 20 }} />
            최근 API 테스트 결과
          </h2>

          <div style={{ fontSize: 14 }}>
            <div style={{ marginBottom: 12 }}>
              <strong>데이터 소스:</strong> {testResult.mode === "p1" ? "P1 /v1/predict" : "/predict 호환"}
            </div>

            {diagnostics && (
              <div
                style={{
                  marginBottom: 16,
                  padding: 16,
                  borderRadius: 8,
                  backgroundColor: "#fff",
                  border: "1px solid #bae6fd",
                }}
              >
                <h3 style={{ fontSize: 16, fontWeight: "600", marginBottom: 12 }}>진단 정보</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
                  <Stat label="후보 수" value={diagnostics.candidate_count} />
                  <Stat label="조건 충족" value={diagnostics.eligible_count} />
                  <Stat label="반환 수" value={diagnostics.returned_count} />
                  <Stat label="무역 신호" value={joinList(Object.entries(diagnostics.trade_signal_counts || {}).map(([key, value]) => `${key}: ${value}`))} />
                </div>
                <div style={{ marginTop: 12 }}>
                  <strong>0건 사유:</strong> {formatDiagnostics(diagnostics.zero_result_reasons)}
                </div>
                <div style={{ marginTop: 8 }}>
                  <strong>경고:</strong> {formatDiagnostics(diagnostics.quality_warnings)}
                </div>
              </div>
            )}

            <div>
              <strong>추천 국가:</strong>
            </div>

            <table style={{ width: "100%", marginTop: 12, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ backgroundColor: "#e0f2fe", textAlign: "left" }}>
                  <th style={{ padding: 8, border: "1px solid #bae6fd" }}>순위</th>
                  <th style={{ padding: 8, border: "1px solid #bae6fd" }}>국가</th>
                  <th style={{ padding: 8, border: "1px solid #bae6fd" }}>점수</th>
                  <th style={{ padding: 8, border: "1px solid #bae6fd" }}>예상 수출액(USD)</th>
                  <th style={{ padding: 8, border: "1px solid #bae6fd" }}>주요 요인(일부)</th>
                </tr>
              </thead>

              <tbody>
                {results.map((item, idx) => {
                  const country = testResult.mode === "p1" ? item : item;
                  const score = testResult.mode === "p1" ? country.fit_score : Number(country.score || 0) * 100;
                  const explanation = country.explanation || {};
                  return (
                    <tr key={`${country?.country || country?.partner_country_iso3 || idx}`} style={{ backgroundColor: idx % 2 === 0 ? "#fff" : "#f0f9ff" }}>
                      <td style={{ padding: 8, border: "1px solid #bae6fd" }}>{idx + 1}</td>
                      <td style={{ padding: 8, border: "1px solid #bae6fd" }}>
                        <strong>{country?.country || country?.partner_country_iso3 || "-"}</strong>
                      </td>
                      <td style={{ padding: 8, border: "1px solid #bae6fd" }}>
                        {typeof score === "number" ? score.toFixed(1) : "-"}
                      </td>
                      <td style={{ padding: 8, border: "1px solid #bae6fd" }}>
                        {typeof country?.expected_export_usd === "number"
                          ? `$${Math.round(country.expected_export_usd).toLocaleString()}`
                          : "-"}
                      </td>
                      <td style={{ padding: 8, border: "1px solid #bae6fd", fontSize: 12 }}>
                        {testResult.mode === "p1"
                          ? `무역: ${Number(country?.score_components?.trade_volume_score ?? 0).toFixed(2)}, 성장: ${Number(country?.score_components?.growth_score ?? 0).toFixed(2)}`
                          : `중력: ${Number(explanation.gravity_baseline ?? 0).toFixed(2)}, 성장: ${Number(explanation.growth_potential ?? 0).toFixed(2)}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div style={{ backgroundColor: "#1f2937", color: "#fff", padding: 24, borderRadius: 12, maxHeight: 400, overflowY: "auto" }}>
        <h2 style={{ fontSize: 20, fontWeight: "bold", marginBottom: 16 }}>
          <Activity style={{ display: "inline", marginRight: 8, width: 20, height: 20 }} />
          시스템 로그
        </h2>

        {logs.length === 0 ? (
          <div style={{ color: "#9ca3af" }}>로그가 없습니다.</div>
        ) : (
          <div style={{ fontFamily: "monospace", fontSize: 13 }}>
            {logs.map((log, idx) => (
              <div
                key={idx}
                style={{
                  marginBottom: 8,
                  color: log.type === "error" ? "#ef4444" : log.type === "success" ? "#10b981" : "#60a5fa",
                }}
              >
                [{log.time}] {log.msg}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: 32, padding: 24, backgroundColor: "#fffbeb", borderRadius: 12, border: "1px solid #fbbf24" }}>
        <h3 style={{ fontSize: 18, fontWeight: "bold", marginBottom: 12 }}>
          <AlertCircle style={{ display: "inline", marginRight: 8, width: 20, height: 20 }} />
          빠른 가이드
        </h3>
        <ul style={{ fontSize: 14, lineHeight: 2, color: "#78716c" }}>
          <li>
            <strong>상태 새로고침:</strong> 백엔드와 Git 상태를 다시 읽습니다.
          </li>
          <li>
            <strong>P1 스모크 테스트:</strong> HS 코드 330499 기준으로 `/v1/predict`를 확인합니다.
          </li>
          <li>
            <strong>호환성 테스트:</strong> `/predict` legacy 응답 규격을 확인합니다.
          </li>
          <li>
            <strong>프로젝트 상태:</strong> branch / HEAD / remote / dirty / non-git 문구를 같은 방식으로 보여줍니다.
          </li>
        </ul>
      </div>
    </div>
  );
}

function StatusCard({ title, icon, status, details }) {
  return (
    <div
      style={{
        padding: 20,
        backgroundColor: status ? "#f0fdf4" : status === false ? "#fef2f2" : "#f9fafb",
        border: `2px solid ${status ? "#10b981" : status === false ? "#ef4444" : "#e5e7eb"}`,
        borderRadius: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
        <div style={{ color: status ? "#10b981" : status === false ? "#ef4444" : "#9ca3af", marginRight: 12 }}>
          {React.cloneElement(icon, { size: 24 })}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: "bold", fontSize: 16 }}>{title}</div>
          <div style={{ fontSize: 12, color: "#666" }}>{details}</div>
        </div>
        <div>
          {status ? (
            <CheckCircle style={{ color: "#10b981" }} size={28} />
          ) : status === false ? (
            <XCircle style={{ color: "#ef4444" }} size={28} />
          ) : (
            <AlertCircle style={{ color: "#9ca3af" }} size={28} />
          )}
        </div>
      </div>
    </div>
  );
}

function ConfigItem({ label, value, status }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: "bold", color: status === false ? "#ef4444" : "#1f2937" }}>{value}</div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "#666" }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: "bold", color: "#111827" }}>{value ?? "-"}</div>
    </div>
  );
}

function Button({ children, onClick, disabled, icon, variant = "primary" }) {
  const colors = {
    primary: { bg: "#2563eb", hover: "#1d4ed8" },
    success: { bg: "#10b981", hover: "#059669" },
    warning: { bg: "#f59e0b", hover: "#d97706" },
  };

  const safe = colors[variant] || colors.primary;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "12px 20px",
        fontSize: 14,
        backgroundColor: disabled ? "#ccc" : safe.bg,
        color: "white",
        border: "none",
        borderRadius: 8,
        cursor: disabled ? "not-allowed" : "pointer",
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontWeight: "bold",
        transition: "background-color 0.2s",
      }}
      onMouseOver={(e) => {
        if (!disabled) e.currentTarget.style.backgroundColor = safe.hover;
      }}
      onMouseOut={(e) => {
        if (!disabled) e.currentTarget.style.backgroundColor = safe.bg;
      }}
    >
      {icon && React.cloneElement(icon, { size: 18 })}
      {children}
    </button>
  );
}
