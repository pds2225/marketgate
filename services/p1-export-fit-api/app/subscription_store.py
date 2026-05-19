import json
import os
import threading
from datetime import datetime, timezone, timedelta

from app.auth_store import update_user

SUBSCRIPTIONS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "subscriptions.json")
_lock = threading.Lock()

PLANS = ["Basic", "Pro", "Advanced"]

PLAN_FEATURES = {
    "Basic":    ["export_search", "bep_calc"],
    "Pro":      ["export_search", "bep_calc", "buyer_detail", "profit_analysis"],
    "Advanced": ["export_search", "bep_calc", "buyer_detail", "profit_analysis",
                 "buyer_credit_report", "buyer_contact", "ksure_db"],
}


def _load() -> dict:
    try:
        with open(SUBSCRIPTIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(SUBSCRIPTIONS_PATH), exist_ok=True)
    with open(SUBSCRIPTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_subscription(user_id: str) -> dict:
    with _lock:
        data = _load()
        if user_id not in data:
            return {"plan": "Basic", "started_at": None, "expires_at": None}
        sub = dict(data[user_id])
        if sub.get("expires_at"):
            expires = datetime.fromisoformat(sub["expires_at"])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:
                sub = {"plan": "Basic", "started_at": None, "expires_at": None}
                data[user_id] = sub
                _save(data)
                update_user(user_id, {"plan": "Basic"})
        return sub


def change_plan(user_id: str, plan: str) -> dict:
    if plan not in PLANS:
        raise ValueError(f"invalid plan: {plan}")
    with _lock:
        data = _load()
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=30)).replace(hour=23, minute=59, second=59, microsecond=0)
        data[user_id] = {
            "plan": plan,
            "started_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }
        _save(data)
    update_user(user_id, {"plan": plan})
    return data[user_id]
