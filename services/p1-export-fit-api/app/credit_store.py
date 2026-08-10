import json
import os
import tempfile
import threading
from datetime import datetime, timezone

CREDITS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "credits.json")
DEFAULT_BALANCE = 100
_lock = threading.Lock()


def _load() -> dict:
    """잔액 읽기. 파일 없음은 부트스트랩, 손상은 실패 처리한다.

    손상을 빈 잔액으로 취급하면 전 사용자 잔액이 조용히 초기화된다
    (docs/LESSONS.md L016).
    """
    try:
        with open(CREDITS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"credits ledger is not an object: {type(data).__name__}")
    return data


def _save(data: dict) -> None:
    # 원자적 + 내구성 있는 교체 (docs/LESSONS.md L016).
    directory = os.path.dirname(CREDITS_PATH)
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".credits-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, CREDITS_PATH)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


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


def delete_user(user_id: str) -> bool:
    """Remove an isolated user's ledger during E2E cleanup."""
    with _lock:
        data = _load()
        if user_id not in data:
            return False
        del data[user_id]
        _save(data)
        return True


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
