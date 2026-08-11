"""Regression test: require_plan() must use the live subscription plan.

users.json always starts with plan="Basic" at registration and is never updated
by the payment/subscription flow. subscriptions.json is the authoritative store.
Before the fix, require_plan() read user["plan"] from users.json, so a user who
successfully upgraded to Advanced still got 403 on protected endpoints.

Fix: require_plan() now calls get_subscription(user_id) from subscription_store
and uses that plan when an active subscription record exists.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth_deps import require_plan  # noqa: E402


def _make_user(plan: str = "Basic") -> dict:
    return {
        "user_id": "test-user-abc",
        "email": "test@example.com",
        "plan": plan,
        "login_fail_count": 0,
        "locked_until": None,
    }


def test_require_plan_allows_when_subscription_upgraded():
    """A user whose users.json plan is Basic but subscription is Advanced must pass."""
    user = _make_user("Basic")
    active_sub = {
        "plan": "Advanced",
        "started_at": "2026-05-01T00:00:00+00:00",
        "expires_at": "2099-12-31T23:59:59+00:00",
    }

    with patch("app.auth_deps.get_subscription", return_value=active_sub):
        # require_plan returns _check; call it directly with the user dict
        check = require_plan("Advanced")
        result = check(user)
        assert result == user


def test_require_plan_blocks_when_no_subscription():
    """A user with plan=Basic in users.json and no active subscription must be blocked."""
    from fastapi import HTTPException

    user = _make_user("Basic")
    no_sub = {"plan": "Basic", "started_at": None, "expires_at": None}

    with patch("app.auth_deps.get_subscription", return_value=no_sub):
        check = require_plan("Advanced")
        try:
            check(user)
            assert False, "Expected HTTPException 403"
        except HTTPException as e:
            assert e.status_code == 403


def test_require_plan_blocks_when_subscription_expired():
    """An expired subscription must not grant access (subscription_store resets plan to Basic)."""
    from fastapi import HTTPException

    user = _make_user("Basic")
    # get_subscription returns Basic + None timestamps when subscription has expired
    expired_sub = {"plan": "Basic", "started_at": None, "expires_at": None}

    with patch("app.auth_deps.get_subscription", return_value=expired_sub):
        check = require_plan("Advanced")
        try:
            check(user)
            assert False, "Expected HTTPException 403"
        except HTTPException as e:
            assert e.status_code == 403


def test_require_plan_fallback_to_users_json_when_no_sub_record():
    """Without an active subscription, user['plan'] from users.json is used as fallback."""
    user = _make_user("Advanced")
    no_sub = {"plan": "Basic", "started_at": None, "expires_at": None}

    with patch("app.auth_deps.get_subscription", return_value=no_sub):
        check = require_plan("Advanced")
        result = check(user)
        assert result == user
