import json
import os
import tempfile
import threading
from datetime import datetime, timezone

from app.db_conn import get_conn, put_conn, is_available, in_transaction

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


def _db_get_or_create(cur, user_id: str) -> tuple[int, list]:
    cur.execute(
        "SELECT balance, history FROM credit_accounts WHERE user_id = %s FOR UPDATE",
        (user_id,),
    )
    row = cur.fetchone()
    if row:
        history = row[1] if isinstance(row[1], list) else json.loads(row[1] or "[]")
        return int(row[0]), history
    cur.execute(
        "INSERT INTO credit_accounts (user_id, balance, history, updated_at) "
        "VALUES (%s, %s, %s::jsonb, %s) "
        "ON CONFLICT (user_id) DO NOTHING",
        (user_id, DEFAULT_BALANCE, json.dumps([]), datetime.now(timezone.utc)),
    )
    cur.execute(
        "SELECT balance, history FROM credit_accounts WHERE user_id = %s FOR UPDATE",
        (user_id,),
    )
    row = cur.fetchone()
    history = row[1] if isinstance(row[1], list) else json.loads(row[1] or "[]")
    return int(row[0]), history


def _db_write_balance(cur, user_id: str, balance: int, history: list) -> None:
    cur.execute(
        "INSERT INTO credit_accounts (user_id, balance, history, updated_at) "
        "VALUES (%s, %s, %s::jsonb, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET "
        "balance = EXCLUDED.balance, history = EXCLUDED.history, "
        "updated_at = EXCLUDED.updated_at",
        (
            user_id,
            balance,
            json.dumps(history, ensure_ascii=False),
            datetime.now(timezone.utc),
        ),
    )


def get_balance(user_id: str = "default") -> int:
    if is_available():
        conn = get_conn()
        if conn is None:
            raise RuntimeError("postgres_unavailable")
        try:
            with conn.cursor() as cur:
                balance, _ = _db_get_or_create(cur, user_id)
            if not in_transaction():
                conn.commit()
            return balance
        finally:
            put_conn(conn)
    data = _load()
    data = _ensure_user(data, user_id)
    return data[user_id]["balance"]


def charge(user_id: str = "default", amount: int = 0, note: str = "") -> int:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    if is_available():
        conn = get_conn()
        if conn is None:
            raise RuntimeError("postgres_unavailable")
        try:
            with conn.cursor() as cur:
                balance, history = _db_get_or_create(cur, user_id)
                balance += amount
                history.append({
                    "action": "charge",
                    "amount": amount,
                    "balance": balance,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "note": note,
                })
                _db_write_balance(cur, user_id, balance, history)
            if not in_transaction():
                conn.commit()
            return balance
        finally:
            put_conn(conn)
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
    if is_available():
        conn = get_conn()
        if conn is None:
            raise RuntimeError("postgres_unavailable")
        try:
            with conn.cursor() as cur:
                _, history = _db_get_or_create(cur, user_id)
            if not in_transaction():
                conn.commit()
            return history
        finally:
            put_conn(conn)
    data = _load()
    data = _ensure_user(data, user_id)
    return data[user_id]["history"]


def delete_user(user_id: str) -> bool:
    """Remove an isolated user's ledger during E2E cleanup."""
    if is_available():
        conn = get_conn()
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM credit_accounts WHERE user_id = %s", (user_id,)
                )
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


def deduct(user_id: str = "default", amount: int = 0, action: str = "", note: str = "") -> int:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    if is_available():
        conn = get_conn()
        if conn is None:
            raise RuntimeError("postgres_unavailable")
        try:
            with conn.cursor() as cur:
                balance, history = _db_get_or_create(cur, user_id)
                if balance < amount:
                    raise ValueError("insufficient_credits")
                balance -= amount
                history.append({
                    "action": action or "deduct",
                    "amount": -amount,
                    "balance": balance,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "note": note,
                })
                _db_write_balance(cur, user_id, balance, history)
            if not in_transaction():
                conn.commit()
            return balance
        finally:
            put_conn(conn)
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
