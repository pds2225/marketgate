import json
import os
import tempfile
import threading
from datetime import datetime, timezone, timedelta

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
    """구독 읽기. 파일 없음은 부트스트랩, 손상은 실패 처리한다.

    손상을 빈 구독으로 취급하면 유료 플랜이 조용히 Basic으로 강등된다
    (docs/LESSONS.md L016).
    """
    try:
        with open(SUBSCRIPTIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"subscriptions ledger is not an object: {type(data).__name__}")
    return data


def _save(data: dict) -> None:
    # 원자적 + 내구성 있는 교체 (docs/LESSONS.md L016).
    directory = os.path.dirname(SUBSCRIPTIONS_PATH)
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=directory, prefix=".subscriptions-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, SUBSCRIPTIONS_PATH)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


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
        return data[user_id]
