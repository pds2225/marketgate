import json
import os
import threading
import uuid
from datetime import datetime, timezone

USERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")
BLACKLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "token_blacklist.json")

_users_lock = threading.Lock()
_blacklist_lock = threading.Lock()

# Try NCP Object Storage first, fall back to file
_ncp = None


def _get_ncp():
    global _ncp
    if _ncp is not None:
        return _ncp
    try:
        from app.ncp_store import is_ncp_available
        if is_ncp_available():
            from app import ncp_store
            _ncp = ncp_store
            return _ncp
    except Exception:
        pass
    return None


def _load_users() -> dict:
    ncp = _get_ncp()
    if ncp:
        from app.ncp_store import USERS_KEY
        return ncp._s3_load(USERS_KEY, USERS_PATH)
    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_users(data: dict) -> None:
    ncp = _get_ncp()
    if ncp:
        from app.ncp_store import USERS_KEY
        ncp._s3_save(USERS_KEY, data, USERS_PATH)
        return
    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_blacklist() -> list:
    ncp = _get_ncp()
    if ncp:
        from app.ncp_store import BLACKLIST_KEY
        return ncp._s3_load(BLACKLIST_KEY, BLACKLIST_PATH)
    try:
        with open(BLACKLIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_blacklist(data: list) -> None:
    ncp = _get_ncp()
    if ncp:
        from app.ncp_store import BLACKLIST_KEY
        ncp._s3_save(BLACKLIST_KEY, data, BLACKLIST_PATH)
        return
    os.makedirs(os.path.dirname(BLACKLIST_PATH), exist_ok=True)
    with open(BLACKLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_user_by_email(email: str) -> dict | None:
    for user in _load_users().values():
        if user.get("email") == email:
            return user
    return None


def find_user_by_id(user_id: str) -> dict | None:
    return _load_users().get(user_id)


def create_user(email: str, hashed_pw: str) -> dict:
    with _users_lock:
        data = _load_users()
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
        _save_users(data)
    return user


def update_user(user_id: str, updates: dict) -> None:
    with _users_lock:
        data = _load_users()
        if user_id in data:
            data[user_id].update(updates)
            _save_users(data)


def delete_user(user_id: str, email: str) -> bool:
    with _users_lock:
        data = _load_users()
        user = data.get(user_id)
        if user is None or user.get("email") != email:
            return False
        del data[user_id]
        _save_users(data)
        return True


def add_to_blacklist(jti: str) -> None:
    if not jti:
        return
    with _blacklist_lock:
        bl = _load_blacklist()
        if jti not in bl:
            bl.append(jti)
            _save_blacklist(bl)


def is_blacklisted(jti: str) -> bool:
    return jti in _load_blacklist()
