from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException

from app.auth_deps import get_current_user
from app.subscription_store import PLANS, change_plan, get_subscription

router = APIRouter(prefix="/v1/subscription", tags=["subscription"])


@router.get("/me")
def subscription_me(user: dict = Depends(get_current_user)):
    return get_subscription(user["user_id"])


@router.post("/change")
def subscription_change(
    payload: Dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
):
    plan = str(payload.get("plan", ""))
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"invalid plan. must be one of {PLANS}")
    return change_plan(user["user_id"], plan)
