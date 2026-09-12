"""Inquiry delivery boundary for MG-007.

Only a non-production dry-run adapter is implemented. It performs no network
I/O and never logs or returns the recipient or message body. A real provider
must implement the same result contract in a later, explicitly authorised task.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY = {"1", "true", "yes", "on"}
_PRODUCTION_ENVS = {"prod", "production"}


class DeliveryUnavailable(RuntimeError):
    pass


class DeliveryRejected(ValueError):
    pass


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    provider_message_id: str
    accepted: bool


def dry_run_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env in _PRODUCTION_ENVS or os.getenv("RENDER"):
        return False
    return os.getenv("INQUIRY_DELIVERY_DRY_RUN", "").strip().lower() in _TRUTHY


def deliver_inquiry(record: dict) -> DeliveryResult:
    """Accept one queued inquiry without external I/O in explicit dry-run mode."""
    if not dry_run_enabled():
        raise DeliveryUnavailable("inquiry_delivery_provider_unavailable")
    if record.get("status") != "queued":
        raise DeliveryRejected("inquiry_not_queued")
    recipient = str(record.get("recipient_email") or "").strip()
    if not recipient or "@" not in recipient:
        raise DeliveryRejected("contact_missing")
    inquiry_id = str(record.get("inquiry_id") or "").strip()
    if not inquiry_id:
        raise DeliveryRejected("inquiry_id_missing")
    return DeliveryResult(
        provider="dry_run",
        # Deterministic per inquiry so provider retries have one idempotency key.
        provider_message_id=f"dryrun:{inquiry_id}",
        accepted=True,
    )
