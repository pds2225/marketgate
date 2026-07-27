import json
import os
import threading
from datetime import datetime, timezone

CREDITS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "credits.json")
DEFAULT_BALANCE = 100
_lock = threading.Lock()


def _load() -> dict:
    try:
        with open(CREDITS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("invalid format")
        return data
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {}


def _save(data: dict) -> None:
    # 원자적 교체 — 찢어진 쓰기는 _load에서 빈 잔액으로 취급된다 (docs/LESSONS.md L016).
    os.makedirs(os.path.dirname(CREDITS_PATH), exist_ok=True)
    tmp_path = f"{CREDITS_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CREDITS_PATH)


def _ensure_user(data: dict, user_id: str) -> dict:
    if user_id not in data:
        data[user_id] = {"balance": DEFAULT_BALANCE, "history": []}
    return data


def get_balance(user_id: str = "default") -> int:
    data = _load()
    data = _ensure_user(data, user_id)
    return data[user_id]["balance"]


def charge(user_id: str = "default", amount: int = 0, note: str = "") -> int:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    with _lock:
        data = _load()
        data = _ensure_user(data, user_id)
        data[user_id]["balance"] += amount
        data[user_id]["history"].append({
            "action": "charge",
            "amount": amount,
            "balance": data[user_id]["balance"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": note,
        })
        _save(data)
        return data[user_id]["balance"]


def get_history(user_id: str = "default") -> list:
    data = _load()
    data = _ensure_user(data, user_id)
    return data[user_id]["history"]


def deduct(user_id: str = "default", amount: int = 0, action: str = "", note: str = "") -> int:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    with _lock:
        data = _load()
        data = _ensure_user(data, user_id)
        if data[user_id]["balance"] < amount:
            raise ValueError("insufficient_credits")
        data[user_id]["balance"] -= amount
        data[user_id]["history"].append({
            "action": action or "deduct",
            "amount": -amount,
            "balance": data[user_id]["balance"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": note,
        })
        _save(data)
        return data[user_id]["balance"]
