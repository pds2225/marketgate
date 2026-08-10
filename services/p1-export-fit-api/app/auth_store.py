import json
import os
import threading
import uuid
from datetime import datetime, timezone

from app.db_conn import get_conn, put_conn, is_available

USERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")
BLACKLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "token_blacklist.json")

_users_lock = threading.Lock()
_blacklist_lock = threading.Lock()


# ── file-based fallback (ephemeral on Render free plan) ──

def _load_users_file() -> dict:
    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_users_file(data: dict) -> None:
    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_blacklist_file() -> list:
    try:
        with open(BLACKLIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_blacklist_file(data: list) -> None:
    # Atomic replace — a torn in-place write can make concurrent readers hit
    # JSONDecodeError and fail-open to an empty blacklist (L016/L025).
    os.makedirs(os.path.dirname(BLACKLIST_PATH), exist_ok=True)
    tmp_path = f"{BLACKLIST_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, BLACKLIST_PATH)


# ── PostgreSQL operations ──

def _db_find_user_by_email(email: str) -> dict | None:
    conn = get_conn()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, email, hashed_pw, role, plan, login_fail_count, locked_until "
                "FROM auth_users WHERE email = %s", (email,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "user_id": row[0], "email": row[1], "hashed_pw": row[2],
                "role": row[3], "plan": row[4],
                "login_fail_count": row[5],
                "locked_until": row[6].isoformat() if row[6] else None,
            }
    finally:
        put_conn(conn)


def _db_find_user_by_id(user_id: str) -> dict | None:
    conn = get_conn()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, email, hashed_pw, role, plan, login_fail_count, locked_until "
                "FROM auth_users WHERE user_id = %s", (user_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "user_id": row[0], "email": row[1], "hashed_pw": row[2],
                "role": row[3], "plan": row[4],
                "login_fail_count": row[5],
                "locked_until": row[6].isoformat() if row[6] else None,
            }
    finally:
        put_conn(conn)


def _db_create_user(email: str, hashed_pw: str) -> dict:
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    conn = get_conn()
    if conn is None:
        raise RuntimeError("PostgreSQL unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_users (user_id, email, hashed_pw, role, plan, login_fail_count, created_at, updated_at) "
                "VALUES (%s, %s, %s, 'user', 'Basic', 0, %s, %s)",
                (user_id, email, hashed_pw, now, now)
            )
        conn.commit()
        return {
            "user_id": user_id, "email": email, "hashed_pw": hashed_pw,
            "plan": "Basic", "created_at": now.isoformat(),
            "login_fail_count": 0, "locked_until": None,
        }
    finally:
        put_conn(conn)


def _db_update_user(user_id: str, updates: dict) -> None:
    conn = get_conn()
    if conn is None:
        return
    try:
        sets = []
        vals = []
        for k, v in updates.items():
            sets.append(f"{k} = %s")
            vals.append(v)
        sets.append("updated_at = %s")
        vals.append(datetime.now(timezone.utc))
        vals.append(user_id)
        with conn.cursor() as cur:
            cur.execute(f"UPDATE auth_users SET {', '.join(sets)} WHERE user_id = %s", vals)
        conn.commit()
    finally:
        put_conn(conn)


def _db_delete_user(user_id: str, email: str) -> bool:
    conn = get_conn()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM auth_users WHERE user_id = %s AND email = %s",
                (user_id, email)
            )
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        put_conn(conn)


def _db_add_to_blacklist(jti: str) -> None:
    if not jti:
        return
    conn = get_conn()
    if conn is None:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_token_blacklist (jti) VALUES (%s) ON CONFLICT DO NOTHING",
                (jti,)
            )
        conn.commit()
    finally:
        put_conn(conn)


def _db_is_blacklisted(jti: str) -> bool:
    conn = get_conn()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM auth_token_blacklist WHERE jti = %s", (jti,))
            return cur.fetchone() is not None
    finally:
        put_conn(conn)


def _db_consume_jti(jti: str) -> bool:
    """Atomically insert jti into Postgres blacklist. True = first consumer.

    Fail closed if the pool cannot hand out a connection: returning True here
    would mint a rotated refresh without a durable revoke record (L026).
    """
    conn = get_conn()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_token_blacklist (jti) VALUES (%s) "
                "ON CONFLICT DO NOTHING RETURNING jti",
                (jti,),
            )
            row = cur.fetchone()
        conn.commit()
        return row is not None
    finally:
        put_conn(conn)


# ── public API (PostgreSQL优先, file fallback) ──

def find_user_by_email(email: str) -> dict | None:
    if is_available():
        return _db_find_user_by_email(email)
    for user in _load_users_file().values():
        if user.get("email") == email:
            return user
    return None


def find_user_by_id(user_id: str) -> dict | None:
    if is_available():
        return _db_find_user_by_id(user_id)
    return _load_users_file().get(user_id)


def create_user(email: str, hashed_pw: str) -> dict:
    if is_available():
        return _db_create_user(email, hashed_pw)
    with _users_lock:
        data = _load_users_file()
        user_id = str(uuid.uuid4())
        user = {
            "user_id": user_id,
            "email": email,
            "hashed_pw": hashed_pw,
            "plan": "Basic",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "login_fail_count": 0,
            "locked_until": None,
        }
        data[user_id] = user
        _save_users_file(data)
    return user


def update_user(user_id: str, updates: dict) -> None:
    if is_available():
        return _db_update_user(user_id, updates)
    with _users_lock:
        data = _load_users_file()
        if user_id in data:
            data[user_id].update(updates)
            _save_users_file(data)


def delete_user(user_id: str, email: str) -> bool:
    if is_available():
        return _db_delete_user(user_id, email)
    with _users_lock:
        data = _load_users_file()
        user = data.get(user_id)
        if user is None or user.get("email") != email:
            return False
        del data[user_id]
        _save_users_file(data)
        return True


def add_to_blacklist(jti: str) -> None:
    if is_available():
        return _db_add_to_blacklist(jti)
    if not jti:
        return
    with _blacklist_lock:
        bl = _load_blacklist_file()
        if jti not in bl:
            bl.append(jti)
            _save_blacklist_file(bl)


def consume_jti(jti: str) -> bool:
    """Atomically blacklist a jti. True = first consumer; False = already used.

    Refresh rotation must use this instead of is_blacklisted()+add_to_blacklist()
    so concurrent /refresh calls cannot mint multiple live refresh chains (L025).

    When Postgres is configured, must write the same durable blacklist that
    is_blacklisted()/add_to_blacklist() use — file-only consume is wiped on
    Render ephemeral disk / multi-instance and allows refresh reuse (L026).
    """
    if not jti:
        return False
    if is_available():
        return _db_consume_jti(jti)
    with _blacklist_lock:
        bl = _load_blacklist_file()
        if jti in bl:
            return False
        bl.append(jti)
        _save_blacklist_file(bl)
        return True


def is_blacklisted(jti: str) -> bool:
    if is_available():
        return _db_is_blacklisted(jti)
    with _blacklist_lock:
        return jti in _load_blacklist_file()
