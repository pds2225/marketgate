import json
import os
import tempfile
import threading
from datetime import datetime, timezone, timedelta

from app.db_conn import get_conn, put_conn, is_available, in_transaction

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


def _sub_dict(plan: str, started_at, expires_at) -> dict:
    return {
        "plan": plan,
        "started_at": started_at.isoformat() if hasattr(started_at, "isoformat") and started_at else started_at,
        "expires_at": expires_at.isoformat() if hasattr(expires_at, "isoformat") and expires_at else expires_at,
    }


def _db_get_subscription(user_id: str) -> dict:
    conn = get_conn()
    if conn is None:
        raise RuntimeError("postgres_unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT plan, started_at, expires_at FROM subscriptions "
                "WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                result = {"plan": "Basic", "started_at": None, "expires_at": None}
            else:
                plan, started_at, expires_at = row
                if expires_at is not None:
                    expires = expires_at
                    if expires.tzinfo is None:
                        expires = expires.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) > expires:
                        cur.execute(
                            "UPDATE subscriptions SET plan=%s, started_at=NULL, "
                            "expires_at=NULL, updated_at=%s WHERE user_id=%s",
                            ("Basic", datetime.now(timezone.utc), user_id),
                        )
                        result = {"plan": "Basic", "started_at": None, "expires_at": None}
                    else:
                        result = _sub_dict(plan, started_at, expires_at)
                else:
                    result = _sub_dict(plan, started_at, expires_at)
            # FOR UPDATE holds the row lock until commit/rollback. Returning the
            # connection to the pool (maxconn=4 on Render) without ending the
            # transaction leaves paid users' subscription rows locked and can
            # block change_plan / require_plan until process restart.
            if not in_transaction():
                conn.commit()
            return result
    except Exception:
        if not in_transaction():
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        put_conn(conn)


def get_subscription(user_id: str) -> dict:
    if is_available():
        return _db_get_subscription(user_id)
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


def delete_user(user_id: str) -> bool:
    """Remove an isolated user's subscription during E2E cleanup."""
    if is_available():
        conn = get_conn()
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM subscriptions WHERE user_id = %s", (user_id,))
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        finally:
            put_conn(conn)
    with _lock:
        data = _load()
        if user_id not in data:
            return False
        del data[user_id]
        _save(data)
        return True


def change_plan(user_id: str, plan: str) -> dict:
    if plan not in PLANS:
        raise ValueError(f"invalid plan: {plan}")
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=30)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
    if is_available():
        conn = get_conn()
        if conn is None:
            raise RuntimeError("postgres_unavailable")
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO subscriptions "
                    "(user_id, plan, started_at, expires_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (user_id) DO UPDATE SET "
                    "plan = EXCLUDED.plan, started_at = EXCLUDED.started_at, "
                    "expires_at = EXCLUDED.expires_at, updated_at = EXCLUDED.updated_at",
                    (user_id, plan, now, expires, now),
                )
            if not in_transaction():
                conn.commit()
            return _sub_dict(plan, now, expires)
        finally:
            put_conn(conn)
    with _lock:
        data = _load()
        data[user_id] = {
            "plan": plan,
            "started_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }
        _save(data)
        return data[user_id]
