import React, { useEffect, useState } from "react";
import {
  Server,
  Database,
  Activity,
  Settings,
  PlayCircle,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  TrendingUp,
  Globe,
  BarChart3,
} from "lucide-react";

export default function AdminDashboard() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [logs, setLogs] = useState([]);

  const pushLog = (msg, type = "info") => {
    setLogs((prev) => [...prev, { time: new Date().toLocaleTimeString(), msg, type }]);
  };

  // 시스템 상태 확인
  const checkSystemStatus = async () => {
    setLoading(true);
    try {
      pushLog("백엔드 서버 확인 중...", "info");

      const healthRes = await fetch("http://localhost:8000/health");
      const healthData = await healthRes.json();

      const configRes = await fetch("http://localhost:8000/config");
      const configData = await configRes.json();

      // 캐시 통계(선택)
      let cacheStats = null;
      if (configData.cache_enabled) {
        try {
          const cacheRes = await fetch("http://localhost:8000/cache/stats");
          cacheStats = await cacheRes.json();
        } catch {
          // 캐시 stats 엔드포인트가 없을 수 있으니 조용히 무시
        }
      }

      setSystemStatus({
        backend: healthRes.ok,
        gravityModel: !!healthData.gravity_model,
        xgbModel: !!healthData.xgb_model,
        dataCollector: !!healthData.data_collector,
        useRealData: !!configData.use_real_data,
        comtradeConfigured: !!configData.comtrade_api_configured,
        cacheEnabled: !!configData.cache_enabled,
        modelVersion: configData.model_version || healthData.model_version || "unknown",
        cacheStats,
      });

      pushLog("✓ 시스템 정상", "success");
    } catch (err) {
      setSystemStatus({ backend: false });
      pushLog(`✗ 오류: ${err?.message || String(err)}`, "error");
    } finally {
      setLoading(false);
    }
  };

  // API 테스트
  const testAPI = async () => {
    setLoading(true);
    try {
      pushLog("API 테스트 시작...", "info");

      const response = await fetch("http://localhost:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hs_code: "33", exporter_country: "KOR", top_n: 5 }),
      });

      const data = await response.json();
      setTestResult(data);

      const n = Array.isArray(data?.top_countries) ? data.top_countries.length : 0;
      pushLog(`✓ API 테스트 성공: ${n}개 국가 추천`, "success");
    } catch (err) {
      pushLog(`✗ API 테스트 실패: ${err?.message || String(err)}`, "error");
    } finally {
      setLoading(false);
    }
  };

  // 모델 재학습
  const retrainModels = async () => {
    const ok = window.confirm("모델을 재학습하시겠습니까? (시간이 소요될 수 있습니다)");
    if (!ok) return;

    setLoading(true);
    try {
      pushLog("모델 재학습 시작...", "info");

      const response = await fetch("http://localhost:8000/retrain", { method: "POST" });
      const data = await response.json();

      const samples = data?.training_samples ?? data?.samples ?? "unknown";
      pushLog(`✓ 재학습 완료: ${samples}개 샘플 사용`, "success");

      // 재학습 후 상태 갱신
      await checkSystemStatus();
    } catch (err) {
      pushLog(`✗ 재학습 실패: ${err?.message || String(err)}`, "error");
    } finally {
      setLoading(false);
    }
  };

  // 초기 로드
  useEffect(() => {
    checkSystemStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ padding: 32, maxWidth: 1400, margin: "0 auto", fontFamily: "sans-serif" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 32, fontWeight: "bold", marginBottom: 8 }}>
          <Settings style={{ display: "inline", marginRight: 12 }} />
          VALUE-UP AI 관리자 대시보드
        </h1>
        <p style={{ color: "#666" }}>시스템 상태 모니터링 및 제어</p>
      </div>

      {/* 시스템 상태 카드 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
          marginBottom: 32,
        }}
      >
        <StatusCard title="백엔드 서버" icon={<Server />} status={systemStatus?.backend} details="FastAPI (port 8001)" />
        <StatusCard title="중력모형" icon={<Globe />} status={systemStatus?.gravityModel} details="Gravity Model (베이스라인)" />
        <StatusCard title="XGBoost 모델" icon={<TrendingUp />} status={systemStatus?.xgbModel} details="보정 모델 (SHAP 확장)" />
        <StatusCard
          title="데이터 수집기"
          icon={<Database />}
          status={systemStatus?.dataCollector}
          details={systemStatus?.useRealData ? "실데이터 모드" : "더미 데이터 모드"}
        />
      </div>

      {/* 설정 정보 */}
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
          <ConfigItem label="데이터 소스" value={systemStatus?.useRealData ? "실데이터" : "더미 데이터"} />
          <ConfigItem
            label="UN Comtrade API"
            value={systemStatus?.comtradeConfigured ? "설정됨" : "미설정"}
            status={systemStatus?.comtradeConfigured}
          />
          <ConfigItem label="캐시" value={systemStatus?.cacheEnabled ? "활성화" : "비활성화"} />
          <ConfigItem label="모델 버전" value={systemStatus?.modelVersion || "미상"} />
        </div>

        {systemStatus?.cacheStats && (
          <div
            style={{
              marginTop: 16,
              padding: 16,
              backgroundColor: "#fff",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
            }}
          >
            <h3 style={{ fontSize: 16, fontWeight: "600", marginBottom: 12 }}>캐시 통계</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
              <Stat label="총 항목" value={systemStatus.cacheStats.total_entries} />
              <Stat label="캐시 히트" value={systemStatus.cacheStats.hits} accent="#10b981" />
              <Stat label="캐시 미스" value={systemStatus.cacheStats.misses} accent="#f59e0b" />
              <Stat label="히트율" value={`${systemStatus.cacheStats.hit_rate_percent}%`} accent="#3b82f6" />
            </div>
          </div>
        )}
      </div>

      {/* 제어 버튼 */}
      <div style={{ display: "flex", gap: 12, marginBottom: 32, flexWrap: "wrap" }}>
        <Button onClick={checkSystemStatus} disabled={loading} icon={<RefreshCw />} variant="primary">
          시스템 상태 새로고침
        </Button>
        <Button onClick={testAPI} disabled={loading} icon={<PlayCircle />} variant="success">
          API 테스트 실행
        </Button>
        <Button onClick={retrainModels} disabled={loading} icon={<Activity />} variant="warning">
          모델 재학습
        </Button>
      </div>

      {/* API 테스트 결과 */}
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
              <strong>데이터 소스:</strong> {testResult?.data_source ?? "unknown"}
            </div>

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
                {(testResult?.top_countries ?? []).map((country, idx) => (
                  <tr key={idx} style={{ backgroundColor: idx % 2 === 0 ? "#fff" : "#f0f9ff" }}>
                    <td style={{ padding: 8, border: "1px solid #bae6fd" }}>{idx + 1}</td>
                    <td style={{ padding: 8, border: "1px solid #bae6fd" }}>
                      <strong>{country?.country ?? "-"}</strong>
                    </td>
                    <td style={{ padding: 8, border: "1px solid #bae6fd" }}>
                      {typeof country?.score === "number" ? (country.score * 100).toFixed(1) : "-"}
                    </td>
                    <td style={{ padding: 8, border: "1px solid #bae6fd" }}>
                      {typeof country?.expected_export_usd === "number"
                        ? `$${Math.round(country.expected_export_usd).toLocaleString()}`
                        : "-"}
                    </td>
                    <td style={{ padding: 8, border: "1px solid #bae6fd", fontSize: 12 }}>
                      중력: {Number(country?.explanation?.gravity_baseline ?? 0).toFixed(2)}, 성장:{" "}
                      {Number(country?.explanation?.growth_potential ?? 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 로그 */}
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

      {/* 도움말 */}
      <div style={{ marginTop: 32, padding: 24, backgroundColor: "#fffbeb", borderRadius: 12, border: "1px solid #fbbf24" }}>
        <h3 style={{ fontSize: 18, fontWeight: "bold", marginBottom: 12 }}>
          <AlertCircle style={{ display: "inline", marginRight: 8, width: 20, height: 20 }} />
          빠른 가이드
        </h3>
        <ul style={{ fontSize: 14, lineHeight: 2, color: "#78716c" }}>
          <li>
            <strong>시스템 상태 새로고침:</strong> 백엔드 서버와 모델 상태를 확인합니다.
          </li>
          <li>
            <strong>API 테스트 실행:</strong> HS 코드 33(화장품) 기준으로 상위 5개 국가를 추천받습니다.
          </li>
          <li>
            <strong>모델 재학습:</strong> 새로운 데이터로 중력모형과 XGBoost를 다시 학습합니다.
          </li>
          <li>
            <strong>데이터 소스:</strong> .env 파일의 USE_REAL_DATA로 실데이터/더미 전환이 가능합니다.
          </li>
        </ul>
      </div>
    </div>
  );
}

// 상태 카드
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

// 설정 아이템
function ConfigItem({ label, value, status }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: "bold", color: status === false ? "#ef4444" : "#1f2937" }}>{value}</div>
    </div>
  );
}

// 통계 표시
function Stat({ label, value, accent }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "#666" }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: "bold", color: accent || "#111827" }}>{value ?? "-"}</div>
    </div>
  );
}

// 버튼
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
