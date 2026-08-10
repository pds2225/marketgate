"""B5 — Export Readiness Check 라우터.

클라이언트가 predict 결과의 핵심필드 DTO 를 POST /v1/readiness 로 보낸다.
서버는 predict/recommend_countries 를 *재호출하지 않고* DTO 만 소비한다(이중 스코어링·36k CSV 재읽기 회피).
계산은 순수함수 app.services.readiness 에 위임한다.
"""
from fastapi import APIRouter, Depends

from app.auth_deps import get_current_user
from app.models import ReadinessRequest, ReadinessResponse
from app.services.readiness import aggregate_buyer_signal, compute_readiness

router = APIRouter(prefix="/v1", tags=["readiness"])


@router.post("/readiness", response_model=ReadinessResponse)
def readiness(req: ReadinessRequest, user: dict = Depends(get_current_user)):
    # raw buyers.items 를 받으면 서버가 shortlist 중 max match_relevance 로 집계 (M-A 경로)
    buyer_signal = req.buyer_signal
    if req.buyers_items is not None:
        buyer_signal = aggregate_buyer_signal(req.buyers_items)

    return compute_readiness(
        country_fit_score=req.country_fit_score,
        compliance=req.compliance,
        buyer_signal=buyer_signal or "none",
        margin_grade=req.margin_grade,
        top_buyer_name=req.top_buyer_name,
    )
