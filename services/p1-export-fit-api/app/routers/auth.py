from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException
from passlib.context import CryptContext

from app.auth_store import (
    create_user, find_user_by_email,
    update_user, add_to_blacklist, consume_jti,
)
from app.auth_deps import (
    create_access_token, create_refresh_token,
    decode_refresh, decode_refresh_claims, get_current_user, get_token_payload,
    is_admin,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

LOCK_MINUTES = 15
MAX_FAIL = 5


@router.post("/register")
def register(payload: Dict[str, Any] = Body(...)):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")
    if find_user_by_email(email):
        raise HTTPException(status_code=409, detail="email_already_exists")
    user = create_user(email, pwd_ctx.hash(password))
    access = create_access_token(user["user_id"])
    return {
        "user_id": user["user_id"],
        "access_token": access,
        "refresh_token": create_refresh_token(user["user_id"]),
        # legacy 키 — 기존 클라이언트 호환
        "token": access,
    }


@router.post("/login")
def login(payload: Dict[str, Any] = Body(...)):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = find_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    locked_until = user.get("locked_until")
    if locked_until:
        if datetime.now(timezone.utc) < datetime.fromisoformat(locked_until):
            raise HTTPException(status_code=429, detail="account_locked")
        update_user(user["user_id"], {"login_fail_count": 0, "locked_until": None})
        user["login_fail_count"] = 0

    if not pwd_ctx.verify(password, user["hashed_pw"]):
        fail_count = user.get("login_fail_count", 0) + 1
        updates: dict = {"login_fail_count": fail_count}
        if fail_count >= MAX_FAIL:
            updates["locked_until"] = (
                datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)
            ).isoformat()
        update_user(user["user_id"], updates)
        if fail_count >= MAX_FAIL:
            raise HTTPException(status_code=429, detail="account_locked")
        raise HTTPException(status_code=401, detail="invalid_credentials")

    update_user(user["user_id"], {"login_fail_count": 0, "locked_until": None})
    return {
        "access_token": create_access_token(user["user_id"]),
        "refresh_token": create_refresh_token(user["user_id"]),
    }


@router.post("/refresh")
def refresh(payload: Dict[str, Any] = Body(...)):
    # Single-use refresh: atomically consume the presented jti, then rotate.
    # MUST return both tokens — client stores the new refresh_token and uses it
    # for the next rotation. Without it, the next silent refresh fails and
    # forces logout (L024).
    # decode→add_to_blacklist was racy under concurrent tabs (L025): both
    # callers passed is_blacklisted before either wrote, minting N live chains.
    # consume_jti must also hit Postgres when DATABASE_URL is set (L026).
    token = str(payload.get("refresh_token", ""))
    decoded = decode_refresh_claims(token)
    if not consume_jti(decoded.get("jti", "")):
        raise HTTPException(status_code=401, detail="token_revoked")
    user_id = decoded["sub"]
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
    }


@router.post("/logout")
def logout(
    token_payload: dict = Depends(get_token_payload),
    payload: Dict[str, Any] | None = Body(default=None),
):
    # Access jti alone is not enough — a surviving refresh_token can mint a
    # new access token after "logout" (L024).
    add_to_blacklist(token_payload.get("jti", ""))
    refresh = str((payload or {}).get("refresh_token") or "")
    if refresh:
        try:
            decoded = decode_refresh(refresh)
            add_to_blacklist(decoded.get("jti", ""))
        except HTTPException:
            # Already expired/revoked — local clear still proceeds on the client.
            pass
    return {"status": "logged_out"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "plan": user["plan"],
        # 가산 필드 — 관리자 메뉴 노출 여부 판단용 (기존 키 불변)
        "role": "admin" if is_admin(user) else "user",
    }
