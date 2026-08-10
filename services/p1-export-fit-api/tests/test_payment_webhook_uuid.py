"""Regression test: the production orderId parser must survive UUID user_ids.

Legacy orderId format is '{uuid}-{product_type}-{item_key}'.
UUIDs contain 4 hyphens, so split('-', 2) was splitting *inside* the UUID,
producing a bogus user_id, a wrong product_type, and a wrong item_key.
The webhook handler matched neither 'credit' nor 'subscription' and returned
{"status": "ok"} without crediting the user or upgrading their plan.

Fix: rsplit('-', 2) for legacy ids, and a dot-separated format for new ones.
These tests import the real parser so they guard production, not a copy.
"""
from __future__ import annotations

import uuid

import pytest

from app.routers.payment import _build_order_id, _parse_order_id


def _legacy_order_id(user_id: str, product_type: str, item_key: str) -> str:
    return f"{user_id}-{product_type}-{item_key}"


def test_legacy_parse_preserves_uuid_user_id():
    """rsplit('-', 2) must keep the full UUID intact as the user_id."""
    user_uuid = str(uuid.uuid4())
    order_id = _legacy_order_id(user_uuid, "subscription", "Advanced")

    uid, ptype, item = _parse_order_id(order_id)
    assert uid == user_uuid, f"user_id mismatch: {uid!r} != {user_uuid!r}"
    assert ptype == "subscription"
    assert item == "Advanced"


def test_naive_split_would_break_uuid_user_id():
    """Document the old bug: split('-', 2) mangles the UUID."""
    user_uuid = "550e8400-e29b-41d4-a716-446655440000"
    order_id = _legacy_order_id(user_uuid, "subscription", "Advanced")

    parts = order_id.split("-", 2)
    assert parts[0] != user_uuid, "split('-',2) should NOT preserve the full UUID"
    assert parts[1] != "subscription", "split('-',2) should give wrong product_type"

    # 프로덕션 파서는 같은 입력을 올바르게 처리해야 한다.
    assert _parse_order_id(order_id)[0] == user_uuid


def test_legacy_parse_works_for_credit_packages():
    user_uuid = str(uuid.uuid4())
    for pkg in ("small", "medium", "large"):
        uid, ptype, item = _parse_order_id(_legacy_order_id(user_uuid, "credit", pkg))
        assert uid == user_uuid
        assert ptype == "credit"
        assert item == pkg


def test_built_order_id_round_trips_with_uuid_user_id():
    """New dot format must survive the parser even with a hyphen-rich user_id."""
    user_uuid = str(uuid.uuid4())
    for product_type, item_key in (("credit", "small"), ("subscription", "Pro")):
        order_id = _build_order_id(user_uuid, product_type, item_key)
        uid, ptype, item = _parse_order_id(order_id)
        assert uid == user_uuid
        assert ptype == product_type
        assert item == item_key


def test_built_order_ids_carry_a_unique_nonce():
    user_uuid = str(uuid.uuid4())
    ids = {_build_order_id(user_uuid, "credit", "small") for _ in range(10)}
    assert len(ids) == 10, "each checkout must produce a distinct orderId"


def test_unparseable_order_id_raises():
    for bad in ("", "garbage", "no-separator"):
        with pytest.raises(ValueError):
            _parse_order_id(bad)
