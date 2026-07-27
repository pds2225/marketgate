import hashlib
import json
import logging
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

logger = logging.getLogger(__name__)

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


def _record_needs_review(
    *,
    order_id: str,
    reason: str,
    amount: Any = 0,
    user_id: str = "unknown",
    product_type: str = "unknown",
    package: str | None = None,
    plan: str | None = None,
) -> Dict[str, Any]:
    """재시도로 고칠 수 없는 상태 — 원장에 남기고 200을 준다.

    비-2xx를 주면 Toss가 재전송 예산을 소진한 뒤 결제를 영구 폐기해
    돈은 빠졌는데 기록이 0인 상태가 된다 (docs/LESSONS.md L015).
    """
    logger.warning(
        f"[payment] NEEDS_REVIEW order_id={order_id!r} amount={amount!r} reason={reason}"
    )
    result = fulfill_payment_once(
        order_id=order_id,
        user_id=user_id,
        product_type=product_type,
        package=package,
        plan=plan,
        amount=amount,
        status="NEEDS_REVIEW",
        apply_fn=lambda: None,
    )
    payload = {"status": "ok", "needs_review": True, "duplicate": result["duplicate"]}
    if result.get("blocked_by"):
        payload["blocked_by"] = result["blocked_by"]
    return payload


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
        if not isinstance(data, dict):
            raise ValueError(f"payload is not an object: {type(data).__name__}")
    except ValueError as e:  # JSONDecodeError·UnicodeDecodeError 모두 ValueError
        # 서명이 이미 Toss 발신을 증명했다 — 400은 재전송 예산만 태우고
        # 원장에는 아무 흔적도 남기지 않는다. 본문 해시를 키로 기록한다.
        return _record_needs_review(
            order_id=f"invalid-json:{hashlib.sha256(body).hexdigest()[:16]}",
            reason=f"invalid_json:{e}",
        )

    # Toss PAYMENT_STATUS_CHANGED 본문은 {eventType, createdAt, data:{Payment}} 래핑이다.
    # 루트에서 status/orderId를 읽으면 실제 웹훅이 전량 무시된다 (docs/LESSONS.md L018).
    # 래퍼가 없으면 본문 자체를 Payment 객체로 본다(레거시·합성 발신자 호환).
    event_type = data.get("eventType")
    if event_type and isinstance(data.get("data"), dict):
        if event_type != "PAYMENT_STATUS_CHANGED":
            logger.info(f"[payment] webhook ignored event_type={event_type!r}")
            return {"status": "ignored", "event_type": event_type}
        data = data["data"]

    status = data.get("status")
    if status != "DONE":
        return {"status": "ignored"}

    order_id = str(data.get("orderId", ""))
    amount = data.get("totalAmount", 0)
    payment_key = str(data.get("paymentKey", "") or "")
    if order_id:
        review_order_id = order_id
    elif payment_key:
        review_order_id = f"missing-orderId:{payment_key}"
    else:
        # 멱등 키가 하나도 없다 — 배달마다 별도 행으로 남긴다. 어차피 중복
        # 판별이 불가능하므로, 검토 큐에 중복 행이 생기는 편이 결제가
        # 조용히 하나로 합쳐져 유실되는 것보다 낫다.
        review_order_id = f"missing-orderId:{uuid.uuid4().hex}"

    def _needs_review(reason: str, **fields: Any) -> Dict[str, Any]:
        return _record_needs_review(
            order_id=review_order_id, reason=reason, amount=amount, **fields
        )

    try:
        user_id, product_type, item_key = _parse_order_id(order_id)
    except ValueError:
        return _needs_review("unparseable_orderId")

    package = item_key if product_type == "credit" else None
    plan = item_key if product_type == "subscription" else None
    review_ctx = {
        "user_id": user_id,
        "product_type": product_type,
        "package": package,
        "plan": plan,
    }

    def _amount_matches(expected: int) -> bool:
        # 서명은 발신자만 증명한다 — 금액은 별도로 대조해야 한다 (docs/LESSONS.md L017).
        try:
            return int(amount) == int(expected)
        except (TypeError, ValueError):
            return False

    if product_type == "credit":
        pkg = CREDIT_PACKAGES.get(item_key)
        if not pkg:
            return _needs_review(f"unknown_package:{item_key}", **review_ctx)
        if not _amount_matches(pkg["price"]):
            return _needs_review(
                f"amount_mismatch expected={pkg['price']}", **review_ctx
            )

        def _apply() -> None:
            charge(user_id, pkg["credits"], note=f"결제 완료 - {pkg['name']} 패키지")

    elif product_type == "subscription":
        price = PLAN_PRICES.get(item_key)
        if price is None:
            return _needs_review(f"unknown_plan:{item_key}", **review_ctx)
        if not _amount_matches(price):
            return _needs_review(f"amount_mismatch expected={price}", **review_ctx)

        def _apply() -> None:
            change_plan(user_id, item_key)

    else:
        return _needs_review(f"unknown_product_type:{product_type}", **review_ctx)

    # apply 콜백이 거부한 경우만 NEEDS_REVIEW로 흡수한다. 원장 손상도
    # ValueError로 올라오는데(JSONDecodeError), 그건 200으로 삼키면 안 되고
    # 5xx로 실패해야 Toss가 재전송한다 (docs/LESSONS.md L016).
    apply_rejected: list[str] = []

    def _guarded_apply() -> None:
        try:
            _apply()
        except ValueError as e:
            apply_rejected.append(str(e))
            raise

    try:
        return fulfill_payment_once(
            order_id=order_id,
            user_id=user_id,
            product_type=product_type,
            package=package,
            plan=plan,
            amount=amount,
            apply_fn=_guarded_apply,
        )
    except ValueError:
        if not apply_rejected:
            raise
        return _needs_review(f"apply_rejected:{apply_rejected[0]}", **review_ctx)


@router.get("/history")
def payment_history(user: dict = Depends(get_current_user)):
    return get_payment_history(user["user_id"])
