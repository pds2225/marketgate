import os
import uuid
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth_store import find_user_by_id, is_blacklisted
from app.subscription_store import get_subscription

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
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


def _decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid_token")

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="invalid_token")
    if is_blacklisted(payload.get("jti", "")):
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
