"""
Regression tests for require_plan: verifies that the active subscription record
in subscriptions.json is consulted, not just the plan field in users.json.

Bug: Before the fix, subscription/change wrote to subscriptions.json but
require_plan read from users.json (always "Basic"). Any Advanced-plan subscriber
received 403 on /v1/inquiry despite having paid.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from app.auth_deps import get_current_user
from app.subscription_store import change_plan, get_subscription

_BASIC_USER = {
    "user_id": "plan-test-user",
    "email": "plantest@example.com",
    "plan": "Basic",  # users.json value — never updated by subscription/change
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


@pytest.fixture()
def basic_user_client():
    """Client whose get_current_user returns a Basic-plan user (plan field only).

    Saves and restores the pre-existing override (installed by conftest.py) so
    that subsequent tests in the session continue to run with the correct mock.
    """
    _previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: _BASIC_USER
    yield TestClient(app)
    if _previous is not None:
        app.dependency_overrides[get_current_user] = _previous
    else:
        app.dependency_overrides.pop(get_current_user, None)


def test_inquiry_blocked_for_basic_user_without_subscription(basic_user_client):
    """Basic user with no subscription cannot call /v1/inquiry."""
    response = basic_user_client.post("/v1/inquiry", json=_INQUIRY_PAYLOAD)
    assert response.status_code == 403
    assert response.json()["detail"] == "requires_Advanced_plan"


def test_inquiry_allowed_after_plan_upgrade(basic_user_client):
    """After upgrading subscription to Advanced, /v1/inquiry must return 200.

    This is the core regression scenario: the user record stays plan='Basic'
    in users.json but the active subscription in subscriptions.json is Advanced.
    """
    change_plan(_BASIC_USER["user_id"], "Advanced")
    try:
        response = basic_user_client.post("/v1/inquiry", json=_INQUIRY_PAYLOAD)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "draft_ready"
    finally:
        # Downgrade back to Basic so we don't leak state to other tests
        change_plan(_BASIC_USER["user_id"], "Basic")
