"""
Regression test for the require_plan / subscription store desync bug.

Root cause: require_plan() previously read user.get("plan") from users.json,
which is always "Basic" (set at registration, never updated). change_plan()
only writes to subscriptions.json, so Advanced-plan users were always blocked
with HTTP 403 on plan-gated endpoints.

Fix: require_plan() now calls subscription_store.get_subscription() which is
the authoritative source and also handles subscription expiry.
"""
from __future__ import annotations

import json
import sys
import unittest.mock
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi import HTTPException

import app.subscription_store as _ss
from app.auth_deps import require_plan


def _user(user_id: str = "u-test") -> dict:
    """Simulate the user dict loaded from users.json — plan field is always 'Basic'."""
    return {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "plan": "Basic",  # production users.json never updates this field
        "login_fail_count": 0,
        "locked_until": None,
    }


def _sub_record(plan: str, days_remaining: int = 29) -> dict:
    if days_remaining <= 0:
        expires = (datetime.now(timezone.utc) + timedelta(days=days_remaining)).isoformat()
    else:
        expires = (datetime.now(timezone.utc) + timedelta(days=days_remaining)).isoformat()
    return {
        "plan": plan,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires,
    }


def _call_require_plan(min_plan: str, user: dict, subs_data: dict) -> dict:
    """
    Call the inner _check closure of require_plan() directly, patching
    subscription_store.SUBSCRIPTIONS_PATH to point at a temp file.
    """
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(subs_data, f)
        tmp_path = f.name
    try:
        with unittest.mock.patch.object(_ss, "SUBSCRIPTIONS_PATH", tmp_path):
            checker = require_plan(min_plan)
            return checker(user=user)
    finally:
        os.unlink(tmp_path)


class TestRequirePlanConsultsSubscriptionStore:
    """
    require_plan() must consult subscription_store.get_subscription() for the
    effective plan — not user.get("plan") which is always "Basic" in users.json.
    """

    def test_no_subscription_blocks_advanced_endpoint(self):
        """Basic user (no subscription record) is denied Advanced access."""
        with pytest.raises(HTTPException) as exc:
            _call_require_plan("Advanced", _user("u-none"), {})
        assert exc.value.status_code == 403
        assert exc.value.detail == "requires_Advanced_plan"

    def test_active_advanced_subscription_allows_access(self):
        """User with active Advanced sub passes even though users.json says Basic."""
        subs = {"u-adv": _sub_record("Advanced", days_remaining=29)}
        result = _call_require_plan("Advanced", _user("u-adv"), subs)
        assert result["user_id"] == "u-adv"

    def test_expired_advanced_subscription_is_blocked(self):
        """Expired Advanced subscription downgrades to Basic — access denied."""
        subs = {"u-exp": _sub_record("Advanced", days_remaining=-1)}
        with pytest.raises(HTTPException) as exc:
            _call_require_plan("Advanced", _user("u-exp"), subs)
        assert exc.value.status_code == 403

    def test_pro_blocked_from_advanced_endpoint(self):
        """Pro subscriber cannot access Advanced-minimum endpoint."""
        subs = {"u-pro": _sub_record("Pro", days_remaining=29)}
        with pytest.raises(HTTPException) as exc:
            _call_require_plan("Advanced", _user("u-pro"), subs)
        assert exc.value.status_code == 403

    def test_pro_allowed_on_pro_endpoint(self):
        """Pro subscriber passes a Pro-minimum gate."""
        subs = {"u-pro2": _sub_record("Pro", days_remaining=29)}
        result = _call_require_plan("Pro", _user("u-pro2"), subs)
        assert result["user_id"] == "u-pro2"

    def test_advanced_allowed_on_pro_endpoint(self):
        """Advanced subscriber also passes a Pro-minimum gate."""
        subs = {"u-adv2": _sub_record("Advanced", days_remaining=15)}
        result = _call_require_plan("Pro", _user("u-adv2"), subs)
        assert result["user_id"] == "u-adv2"
