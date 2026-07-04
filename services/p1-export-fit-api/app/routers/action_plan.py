"""B7 — Export Action Plan 30/60/90 라우터.

readiness 결과(readiness_score + 선택적 dimensions) + top_buyer_name + buyer_signal 을 POST 받아
결정론적 3구간 액션 플랜을 반환한다. 계산은 순수함수 app.services.action_plan 에 위임한다.
"""
from fastapi import APIRouter, Depends

from app.auth_deps import get_current_user
from app.models import ActionPlanRequest, ActionPlanResponse
from app.services.action_plan import build_action_plan

router = APIRouter(prefix="/v1", tags=["action-plan"])


@router.post("/action-plan", response_model=ActionPlanResponse)
def action_plan(req: ActionPlanRequest, user: dict = Depends(get_current_user)):
    return build_action_plan(
        readiness_score=req.readiness_score,
        top_buyer_name=req.top_buyer_name,
        buyer_signal=req.buyer_signal or "none",
        dimensions=req.dimensions,
    )
