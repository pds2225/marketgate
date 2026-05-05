from typing import Any, Dict, List

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.models import PredictRequest, PredictResponse, InquiryRequest, InquiryResponse
from app.services.buyer_shortlist import build_buyer_shortlist
from app.services.project_snapshot import build_project_snapshot
from app.services.scoring import recommend_countries
from app.services.inquiry_service import build_draft
from app.utils import now_seoul_iso, new_request_id

app = FastAPI(title="Export Fit Score API(P1)", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
                "https://marketgate.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return """
    <html><head><title>Export Fit Score API</title></head>
    <body style="font-family:sans-serif;padding:40px;background:#0d1117;color:#e6edf3;">
        <h2>🚀 Export Fit Score API (P1)</h2>
        <p style="color:#7d8590;">수출 대상 국가 추천 시스템 — 정상 운영 중</p>
        <hr style="border-color:#30363d;">
        <ul>
            <li><a href="/docs" style="color:#58a6ff;">📄 Swagger UI (API 테스트)</a></li>
            <li><a href="/redoc" style="color:#58a6ff;">📘 ReDoc (API 문서)</a></li>
            <li><a href="/v1/health" style="color:#58a6ff;">❤️ Health Check</a></li>
        </ul>
        <h4>빠른 테스트 예시 (POST /v1/predict)</h4>
        <pre style="background:#161b22;padding:16px;border-radius:6px;color:#79c0ff;">
{
  "hs_code": "330499",
  "exporter_country_iso3": "KOR",
  "top_n": 5,
  "year": 2023
}</pre>
    </body></html>
    """


@app.get("/v1/health")
def health():
    return {"status": "ok", "timestamp": now_seoul_iso()}


@app.get("/health")
def health_legacy():
    return health()


@app.post("/v1/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    request_id = new_request_id()
    results, input_echo, diagnostics = recommend_countries(req)
    buyers = build_buyer_shortlist(req, results)

    return {
        "request_id": request_id,
        "status": "ok",
        "timestamp": now_seoul_iso(),
        "data": {
            "input": input_echo,
            "results": results,
            "diagnostics": diagnostics,
            "buyers": buyers,
        },
    }


@app.get("/v1/snapshot")
def project_snapshot():
    return {
        "status": "ok",
        "timestamp": now_seoul_iso(),
        "data": build_project_snapshot(),
    }


@app.post("/v1/inquiry", response_model=InquiryResponse)
def create_inquiry(req: InquiryRequest):
    result = build_draft(
        buyer_name=req.buyer_name,
        contact_email=req.contact_email,
        hs_code=req.hs_code,
        sender_company=req.sender_company,
        sender_name=req.sender_name,
        message=req.message,
    )
    return result


def _legacy_explanation_from_p1(result: Dict[str, Any]) -> Dict[str, Any]:
    score_components = result.get("score_components") or {}
    explanation = result.get("explanation") or {}

    trade_score = float(score_components.get("trade_volume_score") or 0.0)
    growth_score = float(score_components.get("growth_score") or 0.0)
    gdp_score = float(score_components.get("gdp_score") or 0.0)
    distance_score = float(score_components.get("distance_score") or 0.0)
    soft_adjustment = float(score_components.get("soft_adjustment") or 0.0)

    return {
        "gravity_baseline": round(gdp_score * 2.0 - 1.0, 4),
        "growth_potential": round(growth_score * 2.0 - 1.0, 4),
        "culture_fit": round(trade_score * 2.0 - 1.0, 4),
        "regulation_ease": round(max(-1.0, min(1.0, 1.0 - abs(soft_adjustment) / 15.0)), 4),
        "logistics": round(distance_score * 2.0 - 1.0, 4),
        "tariff_impact": round(trade_score * 2.0 - 1.0, 4),
        "top_factors": explanation.get("top_factors") or [],
        "data_sources": explanation.get("data_sources") or [],
        "filters_applied": explanation.get("filters_applied") or [],
        "trade_signal_source": explanation.get("trade_signal_source"),
        "kotra_weight_score": explanation.get("kotra_weight_score"),
        "missing_indicators": explanation.get("missing_indicators") or {},
        "p1_score_components": score_components,
    }


def _legacy_top_countries(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    legacy_results: List[Dict[str, Any]] = []
    for result in results:
        fit_score = float(result.get("fit_score") or 0.0)
        legacy_results.append(
            {
                "country": result.get("partner_country_iso3"),
                "score": round(fit_score / 100.0, 4),
                "expected_export_usd": None,
                "explanation": _legacy_explanation_from_p1(result),
                "fit_score": fit_score,
                "rank": result.get("rank"),
            }
        )
    return legacy_results


@app.post("/predict")
def predict_legacy(payload: Dict[str, Any] = Body(...)):
    request_id = new_request_id()
    normalized_payload = dict(payload or {})
    normalized_payload["hs_code"] = normalized_payload.get("hs_code", "").strip()
    normalized_payload["exporter_country_iso3"] = (
        normalized_payload.get("exporter_country_iso3")
        or normalized_payload.get("exporter_country")
        or "KOR"
    )
    normalized_payload["top_n"] = normalized_payload.get("top_n", 10)
    normalized_payload["year"] = normalized_payload.get("year", 2023)

    req = PredictRequest(**normalized_payload)
    results, input_echo, diagnostics = recommend_countries(req)

    return {
        "request_id": request_id,
        "status": "ok",
        "timestamp": now_seoul_iso(),
        "data_source": "p1",
        "input": input_echo,
        "top_countries": _legacy_top_countries(results),
        "diagnostics": diagnostics,
    }
