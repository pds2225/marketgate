import os
from typing import Any, Dict, List

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.models import PredictRequest, PredictResponse, InquiryRequest, InquiryResponse
from app.services.buyer_shortlist import build_buyer_shortlist
from app.services.compliance import filter_blocked_results
from app.services.demo_snapshot import get_demo_snapshot, get_demo_summary, get_demo_buyers
from app.services.project_snapshot import build_project_snapshot
from app.services.scoring import recommend_countries
from app.services.inquiry_service import build_draft
from app.services.opportunity_browse import list_opportunities
from app.services.p2_status import get_p2_dropin_status
from app.utils import now_seoul_iso, new_request_id
from app.credit_store import charge, get_balance, deduct, get_history
from app.auth_deps import get_current_user, require_admin, require_plan
from app.routers import auth as auth_router
from app.routers import simulation as simulation_router
from app.routers import subscription as subscription_router
from app.routers import payment as payment_router
from app.routers import readiness as readiness_router
from app.routers import action_plan as action_plan_router
from app.routers import inquiries as inquiries_router
from app.routers import calculators as calculators_router
from app.routers import company_verification as company_verification_router

app = FastAPI(title="Export Fit Score API(P1)", version="0.0.1")
app.include_router(auth_router.router)
app.include_router(simulation_router.router)
app.include_router(subscription_router.router)
app.include_router(payment_router.router)
app.include_router(readiness_router.router)
app.include_router(action_plan_router.router)
app.include_router(inquiries_router.router)
app.include_router(calculators_router.router)
app.include_router(company_verification_router.router)
if os.getenv("APP_ENV", "").strip().lower() == "e2e":
    from app.routers import e2e as e2e_router

    app.include_router(e2e_router.router)

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
def predict(req: PredictRequest, user: dict = Depends(get_current_user)):
    request_id = new_request_id()
    results, input_echo, diagnostics = recommend_countries(req)
    results = filter_blocked_results(results)
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
def project_snapshot(user: dict = Depends(get_current_user)):
    return {
        "status": "ok",
        "timestamp": now_seoul_iso(),
        "data": build_project_snapshot(),
    }


@app.get("/v1/demo/snapshot")
def demo_snapshot(limit: int = Query(default=60, ge=1, le=200)):
    """Public (no-auth) showcase of the aggregated real buyer DB.

    Returns the aggregation shape MarketGateDemo consumes:
    {summary:{total,countryCount,byCountry[],bySource[]}, buyers:[...]}.
    Contact details are masked; no plaintext email/phone is returned.
    """
    return get_demo_snapshot(limit)


@app.get("/v1/demo/summary")
def demo_summary():
    """Public (no-auth) buyer-DB aggregation summary only."""
    return get_demo_summary()


@app.get("/v1/demo/buyers")
def demo_buyers(limit: int = Query(default=60, ge=1, le=200)):
    """Public (no-auth) masked buyer samples only."""
    return get_demo_buyers(limit)


@app.get("/v1/opportunities")
def opportunities_browse(
    q: str = Query(default=""),
    country: str = Query(default=""),
    hs: str = Query(default=""),
    signal_type: str = Query(default=""),
    source: str = Query(default=""),
    usable_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(get_current_user),
):
    """보유 opportunity_item 전체 탐색(검색·필터)."""
    return list_opportunities(
        q=q,
        country=country,
        hs=hs,
        signal_type=signal_type,
        source=source,
        usable_only=usable_only,
        limit=limit,
        offset=offset,
    )


@app.get("/v1/admin/p2-status")
def admin_p2_status(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin_required")
    return get_p2_dropin_status()


@app.get("/v1/credits/balance")
def credits_balance(user: dict = Depends(get_current_user)):
    return {"user_id": user["user_id"], "balance": get_balance(user["user_id"])}


@app.post("/v1/credits/charge")
def credits_charge(
    payload: Dict[str, Any] = Body(...),
    user: dict = Depends(require_admin),
):
    try:
        amount = int(payload.get("amount"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="amount must be > 0")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")
    return {"user_id": user["user_id"], "balance": charge(user["user_id"], amount)}


@app.post("/v1/credits/deduct")
def credits_deduct(
    payload: Dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
):
    action = str(payload.get("action", ""))
    CREDIT_MAP = {
        "buyer_fit_lite": 3,
        "buyer_fit_pro": 25,
        "contact_send": 5,
        "contact_reply": 13,
        "contact_unlock": 5,
    }
    NOTE_MAP = {
        "buyer_fit_lite": "바이어 적합성 분석 (Lite)",
        "buyer_fit_pro": "바이어 적합성 분석 (Pro)",
        "contact_send": "컨택 메시지 발송",
        "contact_reply": "컨택 답변 작성",
        "contact_unlock": "바이어 연락처 열람",
    }
    if action not in CREDIT_MAP:
        raise HTTPException(status_code=400, detail=f"unknown action: {action}")
    amount = CREDIT_MAP[action]
    note = NOTE_MAP[action]
    try:
        balance = deduct(user["user_id"], amount, action, note)
    except ValueError as e:
        if "insufficient" in str(e):
            raise HTTPException(status_code=402, detail="insufficient_credits")
        raise HTTPException(status_code=400, detail=str(e))
    return {"user_id": user["user_id"], "deducted": amount, "balance": balance}


@app.get("/v1/credits/history")
def credits_history(user: dict = Depends(get_current_user)):
    return get_history(user["user_id"])


@app.post("/v1/inquiry", response_model=InquiryResponse)
def create_inquiry(req: InquiryRequest, _: dict = Depends(require_plan("Basic"))):
    # 초안 생성은 가입(Basic)부터 허용. 실제 발송/추적은 Advanced·크레딧 경로를 유지한다.
    result = build_draft(
        buyer_name=req.buyer_name,
        contact_email=req.contact_email,
        hs_code=req.hs_code,
        sender_company=req.sender_company,
        sender_name=req.sender_name,
        message=req.message,
        sender_email=req.sender_email or "",
        country=req.country,
        match_relevance=req.match_relevance,
        recommendation_lines=req.recommendation_lines,
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
def predict_legacy(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
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
    results = filter_blocked_results(results)

    return {
        "request_id": request_id,
        "status": "ok",
        "timestamp": now_seoul_iso(),
        "data_source": "p1",
        "input": input_echo,
        "top_countries": _legacy_top_countries(results),
        "diagnostics": diagnostics,
    }
