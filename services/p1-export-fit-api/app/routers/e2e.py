"""Fail-closed helpers for deployed E2E staging only.

This router is conditionally registered by ``main.py`` only when
``APP_ENV=e2e``. Cleanup is additionally protected by a high-entropy token and
can delete only generated ``e2e-...@example.com`` accounts.
"""

from __future__ import annotations

import hmac
import os
import re
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException

from app import auth_store, credit_store, inquiry_store, subscription_store


router = APIRouter(prefix="/v1/e2e", tags=["e2e"])
_E2E_EMAIL = re.compile(r"^e2e-[a-z0-9-]+@example\.com$")


def _require_e2e_environment() -> None:
    if os.getenv("APP_ENV", "").strip().lower() != "e2e":
        raise HTTPException(status_code=404, detail="not_found")


def _require_admin_token(provided: str | None) -> None:
    expected = os.getenv("E2E_ADMIN_TOKEN", "")
    if len(expected) < 32:
        raise HTTPException(status_code=503, detail="e2e_cleanup_not_configured")
    if not hmac.compare_digest(provided or "", expected):
        raise HTTPException(status_code=401, detail="invalid_e2e_admin_token")


@router.get("/identity")
def identity() -> dict[str, str]:
    """Prove that a preview is wired to the isolated E2E backend."""
    _require_e2e_environment()
    return {"environment": "e2e"}


@router.post("/cleanup")
def cleanup(
    payload: dict[str, Any] = Body(...),
    x_e2e_admin_token: str | None = Header(
        default=None, alias="X-E2E-Admin-Token"
    ),
) -> dict[str, Any]:
    """Idempotently remove one generated E2E user's persisted staging data."""
    _require_e2e_environment()
    _require_admin_token(x_e2e_admin_token)

    email = str(payload.get("email", "")).strip().lower()
    requested_user_id = str(payload.get("user_id", "")).strip()
    if not _E2E_EMAIL.fullmatch(email):
        raise HTTPException(status_code=400, detail="invalid_e2e_email")

    user = auth_store.find_user_by_email(email)
    if user is None:
        return {
            "deleted": False,
            "email": email,
            "inquiries_deleted": 0,
            "credit_deleted": False,
            "subscription_deleted": False,
        }

    user_id = str(user.get("user_id", ""))
    if requested_user_id and requested_user_id != user_id:
        raise HTTPException(status_code=409, detail="e2e_user_mismatch")

    inquiries_deleted = inquiry_store.delete_user_inquiries(user_id)
    credit_deleted = credit_store.delete_user(user_id)
    subscription_deleted = subscription_store.delete_user(user_id)
    user_deleted = auth_store.delete_user(user_id, email)

    return {
        "deleted": user_deleted,
        "email": email,
        "inquiries_deleted": inquiries_deleted,
        "credit_deleted": credit_deleted,
        "subscription_deleted": subscription_deleted,
    }
