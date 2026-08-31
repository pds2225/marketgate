"""Authenticated contact-ownership challenge API (MG-006).

No delivery provider is called here. A preview token is exposed only when an
explicit non-production dry-run flag is enabled. Raw recipients and raw tokens
are never returned by status reads or stored in the challenge registry.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth_deps import get_current_user

router = APIRouter(prefix="/v1/contact-verifications", tags=["contact-verification"])

_CHALLENGES: dict[str, dict] = {}
_LOCK = threading.RLock()
_TTL_MINUTES = 15
_MAX_ATTEMPTS = 5
_MAX_PENDING_PER_USER = 10
_TRUTHY = {"1", "true", "yes", "on"}
_PRODUCTION_ENVS = {"prod", "production"}


class ChallengeRequest(BaseModel):
    channel: Literal["email", "sms"]
    recipient: str = Field(min_length=3, max_length=254)


class ChallengeConfirmation(BaseModel):
    token: str = Field(min_length=8, max_length=256)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dry_run_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env in _PRODUCTION_ENVS or os.getenv("RENDER"):
        return False
    return os.getenv("CONTACT_VERIFICATION_DRY_RUN", "").strip().lower() in _TRUTHY


def _normalise_recipient(channel: str, recipient: str) -> str:
    value = recipient.strip()
    if channel == "email":
        value = value.lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise HTTPException(status_code=422, detail="invalid_email")
        return value
    digits = re.sub(r"\D", "", value)
    if not 8 <= len(digits) <= 15:
        raise HTTPException(status_code=422, detail="invalid_phone")
    return digits


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _owned_record(challenge_id: str, user_id: str) -> dict:
    record = _CHALLENGES.get(challenge_id)
    if record is None or record["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="contact_verification_not_found")
    return record


def _public(record: dict, *, preview_token: str | None = None) -> dict:
    body = {
        "challenge_id": record["challenge_id"],
        "state": record["state"],
        "previous_state": record["previous_state"],
        "method": record["method"],
        "recipient_fingerprint": record["recipient_fingerprint"],
        "delivery_status": record["delivery_status"],
        "attempts": record["attempts"],
        "expires_at": record["expires_at"].isoformat(),
        "verified_at": record["verified_at"],
    }
    if preview_token is not None:
        body["preview_token"] = preview_token
    return body


@router.post("")
def request_contact_verification(
    payload: ChallengeRequest,
    user: dict = Depends(get_current_user),
):
    normalised = _normalise_recipient(payload.channel, payload.recipient)
    now = _now()
    user_id = user["user_id"]
    challenge_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(24)
    dry_run = _dry_run_enabled()
    record = {
        "challenge_id": challenge_id,
        "user_id": user_id,
        "state": "pending",
        "previous_state": "not_requested",
        "method": "email_link" if payload.channel == "email" else "sms_otp",
        "recipient_fingerprint": f"sha256:{_digest(f'{payload.channel}:{normalised}')}",
        "token_hash": _digest(token),
        "delivery_status": "dry_run_preview" if dry_run else "provider_required",
        "attempts": 0,
        "expires_at": now + timedelta(minutes=_TTL_MINUTES),
        "verified_at": None,
    }
    with _LOCK:
        pending_count = 0
        for existing in _CHALLENGES.values():
            if existing["state"] == "pending" and now >= existing["expires_at"]:
                existing["previous_state"] = "pending"
                existing["state"] = "expired"
            if existing["user_id"] == user_id and existing["state"] == "pending":
                pending_count += 1
        if pending_count >= _MAX_PENDING_PER_USER:
            raise HTTPException(status_code=429, detail="too_many_pending_verifications")
        _CHALLENGES[challenge_id] = record
    return _public(record, preview_token=token if dry_run else None)


@router.get("/{challenge_id}")
def get_contact_verification(
    challenge_id: str,
    user: dict = Depends(get_current_user),
):
    with _LOCK:
        return _public(_owned_record(challenge_id, user["user_id"]))


@router.post("/{challenge_id}/confirm")
def confirm_contact_verification(
    challenge_id: str,
    payload: ChallengeConfirmation,
    user: dict = Depends(get_current_user),
):
    with _LOCK:
        record = _owned_record(challenge_id, user["user_id"])
        if record["state"] == "ownership_verified":
            raise HTTPException(status_code=409, detail="contact_already_verified")
        if record["state"] != "pending":
            raise HTTPException(status_code=409, detail=f"contact_verification_{record['state']}")
        if _now() >= record["expires_at"]:
            record["previous_state"] = "pending"
            record["state"] = "expired"
            raise HTTPException(status_code=410, detail="contact_verification_expired")
        if record["attempts"] >= _MAX_ATTEMPTS:
            record["previous_state"] = "pending"
            record["state"] = "failed"
            raise HTTPException(status_code=429, detail="contact_verification_attempts_exceeded")
        if not hmac.compare_digest(_digest(payload.token), record["token_hash"]):
            record["attempts"] += 1
            if record["attempts"] >= _MAX_ATTEMPTS:
                record["previous_state"] = "pending"
                record["state"] = "failed"
            raise HTTPException(status_code=400, detail="invalid_verification_token")
        record["previous_state"] = "pending"
        record["state"] = "ownership_verified"
        record["verified_at"] = _now().isoformat()
        record["token_hash"] = ""
        return _public(record)


@router.post("/{challenge_id}/revoke")
def revoke_contact_verification(
    challenge_id: str,
    user: dict = Depends(get_current_user),
):
    with _LOCK:
        record = _owned_record(challenge_id, user["user_id"])
        if record["state"] != "ownership_verified":
            raise HTTPException(status_code=409, detail="contact_not_verified")
        record["previous_state"] = "ownership_verified"
        record["state"] = "revoked"
        return _public(record)


def _reset_for_tests() -> None:
    with _LOCK:
        _CHALLENGES.clear()
