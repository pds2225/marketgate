"""Tests that require_plan reads the plan kept in sync by change_plan.

The bug: change_plan() wrote only to subscriptions.json, while
require_plan() read user["plan"] from users.json (via get_current_user).
These two stores were never synced, so require_plan("Advanced") always
returned 403 even for legitimately-upgraded users.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from app.auth_deps import get_current_user
from app.subscription_store import change_plan
from app.auth_store import find_user_by_id, create_user, update_user

client = TestClient(app)

_BASIC_USER = {
    "user_id": "plan-test-user",
    "email": "plantest@example.com",
    "plan": "Basic",
    "login_fail_count": 0,
    "locked_until": None,
}

_INQUIRY_PAYLOAD = {
    "buyer_name": "Test Buyer",
    "contact_email": "buyer@example.com",
    "hs_code": "330499",
    "sender_company": "TestCo",
    "sender_name": "Kim",
}


def test_basic_plan_user_cannot_access_inquiry():
    """A Basic plan user must receive 403 on /v1/inquiry."""
    basic_user = dict(_BASIC_USER, plan="Basic")
    _prior = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: basic_user
    try:
        resp = client.post("/v1/inquiry", json=_INQUIRY_PAYLOAD)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "requires_Advanced_plan"
    finally:
        if _prior is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = _prior


def test_advanced_plan_user_can_access_inquiry():
    """An Advanced plan user must receive 200 on /v1/inquiry."""
    advanced_user = dict(_BASIC_USER, plan="Advanced")
    _prior = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: advanced_user
    try:
        resp = client.post("/v1/inquiry", json=_INQUIRY_PAYLOAD)
        assert resp.status_code == 200
    finally:
        if _prior is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = _prior


def test_change_plan_syncs_to_users_json(tmp_path, monkeypatch):
    """change_plan() must update users.json so that require_plan reflects the new plan."""
    import json

    users_file = tmp_path / "users.json"
    subs_file = tmp_path / "subscriptions.json"

    user_id = "sync-test-user"
    users_file.write_text(
        json.dumps({user_id: {
            "user_id": user_id,
            "email": "sync@example.com",
            "plan": "Basic",
            "login_fail_count": 0,
            "locked_until": None,
        }}),
        encoding="utf-8",
    )
    subs_file.write_text("{}", encoding="utf-8")

    import app.auth_store as auth_store_mod
    import app.subscription_store as sub_store_mod

    monkeypatch.setattr(auth_store_mod, "USERS_PATH", str(users_file))
    monkeypatch.setattr(sub_store_mod, "SUBSCRIPTIONS_PATH", str(subs_file))

    change_plan(user_id, "Advanced")

    updated = json.loads(users_file.read_text(encoding="utf-8"))
    assert updated[user_id]["plan"] == "Advanced", (
        "users.json plan must be updated to 'Advanced' after change_plan()"
    )

    subs = json.loads(subs_file.read_text(encoding="utf-8"))
    assert subs[user_id]["plan"] == "Advanced"
