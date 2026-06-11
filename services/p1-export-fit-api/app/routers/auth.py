from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException
from passlib.context import CryptContext

from app.auth_store import (
    create_user, find_user_by_email,
    update_user, add_to_blacklist,
)
from app.auth_deps import (
    create_access_token, create_refresh_token,
    decode_refresh, get_current_user, get_token_payload,
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
    token = str(payload.get("refresh_token", ""))
    decoded = decode_refresh(token)
    add_to_blacklist(decoded["jti"])
    return {"access_token": create_access_token(decoded["sub"])}


@router.post("/logout")
def logout(token_payload: dict = Depends(get_token_payload)):
    add_to_blacklist(token_payload.get("jti", ""))
    return {"status": "logged_out"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"user_id": user["user_id"], "email": user["email"], "plan": user["plan"]}
