"""Regression test: payment webhook must parse UUID user_id correctly.

order_id format is '{uuid}-{product_type}-{item_key}'.
UUIDs contain 4 hyphens, so split('-', 2) was splitting *inside* the UUID,
producing a bogus user_id, a wrong product_type, and a wrong item_key.
The webhook handler matched neither 'credit' nor 'subscription' and returned
{"status": "ok"} without crediting the user or upgrading their plan.

Fix: use rsplit('-', 2) so the split happens from the right.
"""
from __future__ import annotations

import json
import uuid


def _build_order_id(user_id: str, product_type: str, item_key: str) -> str:
    return f"{user_id}-{product_type}-{item_key}"


def test_rsplit_preserves_uuid_user_id():
    """rsplit('-', 2) must keep the full UUID intact as parts[0]."""
    user_uuid = str(uuid.uuid4())
    order_id = _build_order_id(user_uuid, "subscription", "Advanced")

    parts = order_id.rsplit("-", 2)
    assert len(parts) == 3, "rsplit('-', 2) must yield exactly 3 parts"
    assert parts[0] == user_uuid, f"user_id mismatch: {parts[0]!r} != {user_uuid!r}"
    assert parts[1] == "subscription"
    assert parts[2] == "Advanced"


def test_old_split_breaks_uuid_user_id():
    """Confirm split('-', 2) produces wrong results (documents the old bug)."""
    user_uuid = "550e8400-e29b-41d4-a716-446655440000"
    order_id = _build_order_id(user_uuid, "subscription", "Advanced")

    parts = order_id.split("-", 2)
    # The first part should be wrong (only the first UUID segment)
    assert parts[0] != user_uuid, "split('-',2) should NOT preserve the full UUID"
    assert parts[1] != "subscription", "split('-',2) should give wrong product_type"


def test_rsplit_works_for_credit_packages():
    """rsplit('-', 2) must also parse credit package order_ids correctly."""
    user_uuid = str(uuid.uuid4())
    for pkg in ("small", "medium", "large"):
        order_id = _build_order_id(user_uuid, "credit", pkg)
        parts = order_id.rsplit("-", 2)
        assert parts[0] == user_uuid
        assert parts[1] == "credit"
        assert parts[2] == pkg
