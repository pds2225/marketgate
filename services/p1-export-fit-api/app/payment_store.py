import hashlib
import hmac
import json
import os
import threading
from datetime import datetime, timezone

PAYMENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "payments.json")
_lock = threading.Lock()

CREDIT_PACKAGES = {
    "small":  {"credits": 10,  "price": 20000,  "name": "소형"},
    "medium": {"credits": 30,  "price": 54000,  "name": "중형"},
    "large":  {"credits": 100, "price": 160000, "name": "대형"},
}

PLAN_PRICES = {
    "Pro":      29000,
    "Advanced": 79000,
}


def verify_webhook_signature(payload_bytes: bytes, signature: str) -> bool:
    # fail-closed: 시크릿 미설정 시 어떤 웹훅도 신뢰하지 않는다
    secret = os.environ.get("TOSS_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _load() -> list:
    try:
        with open(PAYMENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(data: list) -> None:
    os.makedirs(os.path.dirname(PAYMENTS_PATH), exist_ok=True)
    with open(PAYMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_payment(
    user_id: str,
    product_type: str,
    package: str = None,
    plan: str = None,
    amount: int = 0,
    status: str = "DONE",
) -> dict:
    with _lock:
        data = _load()
        record = {
            "user_id": user_id,
            "product_type": product_type,
            "package": package,
            "plan": plan,
            "amount": amount,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data.append(record)
        _save(data)
        return record


def get_payment_history(user_id: str | None = None) -> list:
    with _lock:
        data = _load()
    if user_id is None:
        return data
    return [r for r in data if r.get("user_id") == user_id]
