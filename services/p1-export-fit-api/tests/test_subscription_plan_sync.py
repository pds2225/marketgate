"""
Tests that verify plan upgrades and downgrades are synced to users.json
so that require_plan() enforces the correct tier.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from app.subscription_store import change_plan, get_subscription
from app.auth_store import create_user, find_user_by_id


def _make_user(plan: str = "Basic") -> dict:
    """Create a throwaway user and return it."""
    uid = str(uuid.uuid4())
    email = f"{uid}@test.invalid"
    user = create_user(email, "hashed_pw_placeholder")
    return user


def test_change_plan_syncs_to_users_json(tmp_path, monkeypatch):
    """After change_plan the user's plan field in users.json must reflect the new tier."""
    import app.subscription_store as sub_store
    import app.auth_store as auth_store_mod

    # Redirect file paths to tmp directories so tests don't pollute shared state.
    users_file = tmp_path / "users.json"
    subs_file = tmp_path / "subscriptions.json"
    monkeypatch.setattr(auth_store_mod, "USERS_PATH", str(users_file))
    monkeypatch.setattr(sub_store, "SUBSCRIPTIONS_PATH", str(subs_file))

    user = _make_user()
    user_id = user["user_id"]

    # Sanity: newly created user starts on Basic.
    assert find_user_by_id(user_id)["plan"] == "Basic"

    change_plan(user_id, "Advanced")

    updated = find_user_by_id(user_id)
    assert updated is not None
    assert updated["plan"] == "Advanced", (
        "users.json plan field must be updated by change_plan so require_plan() passes"
    )


def test_get_subscription_downgrades_users_json_on_expiry(tmp_path, monkeypatch):
    """When a subscription expires get_subscription must reset users.json plan to Basic."""
    import app.subscription_store as sub_store
    import app.auth_store as auth_store_mod

    users_file = tmp_path / "users.json"
    subs_file = tmp_path / "subscriptions.json"
    monkeypatch.setattr(auth_store_mod, "USERS_PATH", str(users_file))
    monkeypatch.setattr(sub_store, "SUBSCRIPTIONS_PATH", str(subs_file))

    user = _make_user()
    user_id = user["user_id"]

    # Upgrade to Advanced.
    change_plan(user_id, "Advanced")
    assert find_user_by_id(user_id)["plan"] == "Advanced"

    # Manually backdating the expiry in subscriptions.json.
    import json
    expired_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    subs = {user_id: {"plan": "Advanced", "started_at": expired_at, "expires_at": expired_at}}
    subs_file.write_text(json.dumps(subs))

    result = get_subscription(user_id)
    assert result["plan"] == "Basic"

    downgraded = find_user_by_id(user_id)
    assert downgraded is not None
    assert downgraded["plan"] == "Basic", (
        "users.json plan must be reset to Basic when subscription expires"
    )
