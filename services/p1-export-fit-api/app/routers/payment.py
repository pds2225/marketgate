import json
import os
import urllib.parse
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from app.auth_deps import get_current_user
from app.credit_store import charge
from app.payment_store import (
    CREDIT_PACKAGES, PLAN_PRICES, get_payment_history,
    record_payment, verify_webhook_signature,
)
from app.subscription_store import change_plan

router = APIRouter(prefix="/v1/payment", tags=["payment"])

_TOSS_CLIENT_KEY = os.environ.get("TOSS_CLIENT_KEY", "test_ck_placeholder")
_BASE_URL = os.environ.get("BASE_URL", "http://localhost:5173")


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

    order_id = f"{user['user_id']}-{product_type}-{item_key}"
    success_url = (
        f"{_BASE_URL}/payment/callback"
        f"?status=success&type={product_type}&item={item_key}"
    )
    fail_url = f"{_BASE_URL}/payment/callback?status=fail"

    params = urllib.parse.urlencode({
        "clientKey": _TOSS_CLIENT_KEY,
        "amount": amount,
        "orderId": order_id,
        "orderName": order_name,
        "successUrl": success_url,
        "failUrl": fail_url,
    })
    checkout_url = f"https://pay.toss.im/v2/checkout?{params}"
    return {"checkout_url": checkout_url, "order_id": order_id, "amount": amount}


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
    # order_id format: "{uuid}-{product_type}-{item_key}"
    # UUIDs contain 4 hyphens, so split from the right to keep the UUID intact.
    parts = order_id.rsplit("-", 2)
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="invalid_orderId format")

    user_id, product_type, item_key = parts[0], parts[1], parts[2]

    if product_type == "credit":
        pkg = CREDIT_PACKAGES.get(item_key)
        if pkg:
            charge(user_id, pkg["credits"], note=f"결제 완료 - {pkg['name']} 패키지")
    elif product_type == "subscription":
        try:
            change_plan(user_id, item_key)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    record_payment(
        user_id=user_id,
        product_type=product_type,
        package=item_key if product_type == "credit" else None,
        plan=item_key if product_type == "subscription" else None,
        amount=data.get("totalAmount", 0),
        status="DONE",
    )
    return {"status": "ok"}


@router.get("/history")
def payment_history(user: dict = Depends(get_current_user)):
    return get_payment_history(user["user_id"])
