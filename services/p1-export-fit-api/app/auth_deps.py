import json
import os
import threading
import uuid
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth_store import find_user_by_id, is_blacklisted
from app.subscription_store import get_subscription

def _resolve_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if secret:
        return secret
    # Render 런타임은 APP_ENV 설정 여부와 무관하게 fail-closed.
    if os.environ.get("RENDER"):
        raise RuntimeError(
            "JWT_SECRET must be set in the Render dashboard before deploy "
            "(see docs/LESSONS.md L019-class hole: dev fallback signs forgeable tokens)"
        )
    if os.environ.get("APP_ENV", "").lower() in ("prod", "production"):
        raise RuntimeError("JWT_SECRET must be set when APP_ENV=production")
    return "dev-secret-change-in-prod"


JWT_SECRET = _resolve_jwt_secret()
JWT_ALGORITHM = "HS256"
ACCESS_EXPIRE_MIN = 30
REFRESH_EXPIRE_DAYS = 7

security = HTTPBearer()

PLAN_ORDER = {"Basic": 0, "Pro": 1, "Advanced": 2}


def create_access_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "type": "access",
            "jti": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_EXPIRE_MIN),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "type": "refresh",
            "jti": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def _decode_token(token: str, expected_type: str, *, check_blacklist: bool = True) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid_token")

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="invalid_token")
    if check_blacklist and is_blacklisted(payload.get("jti", "")):
        raise HTTPException(status_code=401, detail="token_revoked")
    return payload


def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    return _decode_token(credentials.credentials, "access")


def get_current_user(payload: dict = Depends(get_token_payload)) -> dict:
    user = find_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")
    return user


def decode_refresh(token: str) -> dict:
    return _decode_token(token, "refresh")


def decode_refresh_claims(token: str) -> dict:
    """Validate signature/exp/type only — caller must consume_jti atomically."""
    return _decode_token(token, "refresh", check_blacklist=False)


ADMIN_ACCESS_LOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "admin_access_log.json"
)
_admin_log_lock = threading.Lock()


def _admin_emails() -> set[str]:
    # 매 호출마다 env를 읽어 테스트에서 monkeypatch 가능하게 한다.
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def is_admin(user: dict) -> bool:
    if str(user.get("role", "")).lower() == "admin":
        return True
    return str(user.get("email", "")).lower() in _admin_emails()


def log_admin_access(user: dict, path: str, allowed: bool) -> None:
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "user_id": user.get("user_id"),
        "email": user.get("email"),
        "path": path,
        "allowed": allowed,
    }
    with _admin_log_lock:
        try:
            with open(ADMIN_ACCESS_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                data = []
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
        data.append(entry)
        os.makedirs(os.path.dirname(ADMIN_ACCESS_LOG_PATH), exist_ok=True)
        with open(ADMIN_ACCESS_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def require_admin(request: Request, user: dict = Depends(get_current_user)) -> dict:
    """관리자 전용 엔드포인트 가드. 비관리자는 403 + 접근 로그 저장."""
    allowed = is_admin(user)
    log_admin_access(user, request.url.path, allowed)
    if not allowed:
        raise HTTPException(status_code=403, detail="admin_required")
    return user


def require_plan(min_plan: str):
    def _check(user: dict = Depends(get_current_user)) -> dict:
        # subscriptions.json is the authoritative source for plan; users.json is
        # only a fallback for legacy records and test mocks that never go through
        # the payment/subscription flow.
        sub = get_subscription(user["user_id"])
        if sub.get("started_at") is not None:
            effective_plan = sub.get("plan", "Basic")
        else:
            effective_plan = user.get("plan", "Basic")
        if PLAN_ORDER.get(effective_plan, 0) < PLAN_ORDER.get(min_plan, 0):
            raise HTTPException(status_code=403, detail=f"requires_{min_plan}_plan")
        return user
    return _check
