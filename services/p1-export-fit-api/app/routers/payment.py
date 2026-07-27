import json
import os
import uuid
import urllib.parse
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from app.auth_deps import get_current_user
from app.credit_store import charge
from app.payment_store import (
    CREDIT_PACKAGES, PLAN_PRICES, fulfill_payment_once, get_payment_history,
    verify_webhook_signature,
)
from app.subscription_store import change_plan

router = APIRouter(prefix="/v1/payment", tags=["payment"])

# 토스 PG — 실키 없으면 ready=false. 나중에 env만 채우면 checkout 활성화.
_TOSS_CLIENT_KEY = os.environ.get("TOSS_CLIENT_KEY", "")
_TOSS_SECRET_KEY = os.environ.get("TOSS_SECRET_KEY", "")  # 결제 승인(confirm) 후속용
_BASE_URL = os.environ.get("BASE_URL", "http://localhost:5173")


def _toss_ready() -> bool:
    key = (_TOSS_CLIENT_KEY or "").strip()
    if not key or key in ("test_ck_placeholder", "placeholder"):
        return False
    return key.startswith("test_ck_") or key.startswith("live_ck_") or len(key) > 8


def _build_order_id(user_id: str, product_type: str, item_key: str) -> str:
    """Unique per checkout. Dot separator avoids UUID hyphen ambiguity.

    Format: '{user_id}.{product_type}.{item_key}.{nonce}'
    Legacy webhook payloads may still use '{uuid}-{product_type}-{item_key}'.
    """
    nonce = uuid.uuid4().hex[:12]
    return f"{user_id}.{product_type}.{item_key}.{nonce}"


def _parse_order_id(order_id: str) -> Tuple[str, str, str]:
    """Return (user_id, product_type, item_key). Supports new + legacy formats."""
    if "." in order_id:
        parts = order_id.split(".")
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]
    # Legacy: '{uuid}-{product_type}-{item_key}' (UUID has 4 hyphens)
    parts = order_id.rsplit("-", 2)
    if len(parts) < 3:
        raise ValueError("invalid_orderId format")
    return parts[0], parts[1], parts[2]


@router.get("/provider")
def payment_provider():
    """프론트 paymentConfig / 토스 위젯 연결 시 참조 메타."""
    ready = _toss_ready()
    return {
        "provider": "toss",
        "ready": ready,
        "mode_hint": "toss" if ready else "sim",
        "client_key_configured": ready,
        "secret_configured": bool((_TOSS_SECRET_KEY or "").strip()),
        "webhook_configured": bool((os.environ.get("TOSS_WEBHOOK_SECRET") or "").strip()),
        "base_url": _BASE_URL,
        "note": "TOSS_CLIENT_KEY + TOSS_WEBHOOK_SECRET + BASE_URL 설정 후 프론트 paymentConfig.mode='toss'",
    }


@router.post("/checkout")
def checkout(
    payload: Dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
):
    product_type = str(payload.get("product_type", ""))
    package = payload.get("package")
    plan = payload.get("plan")

    if product_type == "credit":
        pkg = CREDIT_PACKAGES.get(str(package or ""))
        if not pkg:
            raise HTTPException(status_code=400, detail=f"unknown package: {package}")
        amount = pkg["price"]
        order_name = f"크레딧 {pkg['name']} ({pkg['credits']}C)"
        item_key = package
    elif product_type == "subscription":
        price = PLAN_PRICES.get(str(plan or ""))
        if not price:
            raise HTTPException(status_code=400, detail=f"unknown plan: {plan}")
        amount = price
        order_name = f"{plan} 플랜 구독"
        item_key = plan
    else:
        raise HTTPException(status_code=400, detail=f"unknown product_type: {product_type}")

    # 결제마다 고유 orderId (Toss 재결제·웹훅 재시도 대비). 레거시 하이픈 형식은 웹훅에서만 파싱.
    order_id = _build_order_id(user["user_id"], product_type, str(item_key))
    success_url = (
        f"{_BASE_URL}/payment/callback"
        f"?status=success&type={product_type}&item={item_key}"
    )
    fail_url = f"{_BASE_URL}/payment/callback?status=fail"

    ready = _toss_ready()
    client_key = _TOSS_CLIENT_KEY.strip() if ready else None

    # 토스 결제위젯/리다이렉트·SDK가 그대로 쓸 수 있는 필드
    toss_payload = {
        "clientKey": client_key or "test_ck_placeholder",
        "amount": amount,
        "orderId": order_id,
        "orderName": order_name,
        "successUrl": success_url,
        "failUrl": fail_url,
        "currency": "KRW",
    }

    checkout_url = None
    if ready:
        params = urllib.parse.urlencode({
            "clientKey": toss_payload["clientKey"],
            "amount": amount,
            "orderId": order_id,
            "orderName": order_name,
            "successUrl": success_url,
            "failUrl": fail_url,
        })
        checkout_url = f"https://pay.toss.im/v2/checkout?{params}"

    return {
        "provider": "toss",
        "ready": ready,
        "checkout_url": checkout_url,
        "order_id": order_id,
        "amount": amount,
        "order_name": order_name,
        "currency": "KRW",
        "client_key": client_key,
        "success_url": success_url,
        "fail_url": fail_url,
        "toss": toss_payload if ready else None,
        "message": None if ready else (
            "TOSS_CLIENT_KEY 미설정 — sim 충전을 쓰거나 키 설정 후 재시도하세요."
        ),
    }


@router.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("TossPayments-Signature", "")
    if not verify_webhook_signature(body, sig):
        raise HTTPException(status_code=401, detail="invalid_signature")

    try:
        data = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    status = data.get("status")
    if status != "DONE":
        return {"status": "ignored"}

    order_id = str(data.get("orderId", ""))
    try:
        user_id, product_type, item_key = _parse_order_id(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_orderId format")

    package = item_key if product_type == "credit" else None
    plan = item_key if product_type == "subscription" else None
    amount = data.get("totalAmount", 0)

    def _apply() -> None:
        if product_type == "credit":
            pkg = CREDIT_PACKAGES.get(item_key)
            if not pkg:
                raise HTTPException(status_code=400, detail=f"unknown package: {item_key}")
            charge(user_id, pkg["credits"], note=f"결제 완료 - {pkg['name']} 패키지")
        elif product_type == "subscription":
            try:
                change_plan(user_id, item_key)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=f"unknown product_type: {product_type}")

    try:
        result = fulfill_payment_once(
            order_id=order_id,
            user_id=user_id,
            product_type=product_type,
            package=package,
            plan=plan,
            amount=amount,
            apply_fn=_apply,
        )
    except HTTPException:
        raise
    return result


@router.get("/history")
def payment_history(user: dict = Depends(get_current_user)):
    return get_payment_history(user["user_id"])
