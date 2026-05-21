"""
Tests for payment webhook order_id parsing and require_plan subscription check.
"""
from __future__ import annotations

import json
import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Bug 1: payment webhook order_id parser broken for UUID user_ids
# ---------------------------------------------------------------------------

class TestWebhookOrderIdParsing:
    """
    Regression tests for the bug where order_id.split('-', 2) misidentified
    UUID segments as product_type/item_key.
    """

    def _webhook_payload(self, user_id: str, product_type: str, item_key: str) -> bytes:
        order_id = f"{user_id}-{product_type}-{item_key}"
        return json.dumps({"status": "DONE", "orderId": order_id, "totalAmount": 29000}).encode()

    def test_uuid_user_id_credit_package_is_parsed_correctly(self):
        """
        order_id = "<full-uuid>-credit-small" must not be split at UUID hyphens.
        """
        test_uuid = "550e8400-e29b-41d4-a716-446655440000"
        payload = self._webhook_payload(test_uuid, "credit", "small")

        with patch("app.routers.payment.verify_webhook_signature", return_value=True), \
             patch("app.routers.payment.charge") as mock_charge, \
             patch("app.routers.payment.record_payment") as mock_record:
            response = client.post("/v1/payment/webhook", content=payload,
                                   headers={"content-type": "application/json"})

        assert response.status_code == 200
        # charge must be called with the FULL uuid, not the first UUID segment
        mock_charge.assert_called_once()
        called_user_id = mock_charge.call_args[0][0]
        assert called_user_id == test_uuid, (
            f"Expected full UUID '{test_uuid}', got '{called_user_id}' — "
            "UUID hyphens are being mis-split"
        )

    def test_uuid_user_id_subscription_plan_is_parsed_correctly(self):
        """
        order_id = "<full-uuid>-subscription-Advanced" must resolve to
        product_type='subscription', item_key='Advanced', user_id=full UUID.
        """
        test_uuid = str(uuid.uuid4())
        payload = self._webhook_payload(test_uuid, "subscription", "Advanced")

        with patch("app.routers.payment.verify_webhook_signature", return_value=True), \
             patch("app.routers.payment.change_plan") as mock_change, \
             patch("app.routers.payment.record_payment"):
            response = client.post("/v1/payment/webhook", content=payload,
                                   headers={"content-type": "application/json"})

        assert response.status_code == 200
        mock_change.assert_called_once_with(test_uuid, "Advanced")

    def test_invalid_order_id_too_short_returns_400(self):
        """An order_id without enough segments should return 400."""
        payload = json.dumps({"status": "DONE", "orderId": "bad-id", "totalAmount": 0}).encode()
        with patch("app.routers.payment.verify_webhook_signature", return_value=True):
            response = client.post("/v1/payment/webhook", content=payload,
                                   headers={"content-type": "application/json"})
        assert response.status_code == 400

    def test_non_done_status_is_ignored(self):
        """Webhook events with status != DONE must be silently ignored."""
        test_uuid = str(uuid.uuid4())
        payload = self._webhook_payload(test_uuid, "subscription", "Advanced")
        data = json.loads(payload)
        data["status"] = "WAITING"
        payload = json.dumps(data).encode()

        with patch("app.routers.payment.verify_webhook_signature", return_value=True), \
             patch("app.routers.payment.change_plan") as mock_change:
            response = client.post("/v1/payment/webhook", content=payload,
                                   headers={"content-type": "application/json"})

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        mock_change.assert_not_called()


# ---------------------------------------------------------------------------
# Bug 2: require_plan must consult subscription_store, not auth_store "plan"
# ---------------------------------------------------------------------------

class TestRequirePlanUsesSubscriptionStore:
    """
    require_plan() must gate access based on the live subscription record,
    not the static 'plan' field in auth_store (which is always 'Basic').
    """

    def test_inquiry_allowed_when_subscription_is_advanced(self):
        """
        The conftest patches get_subscription to return Advanced for 'test-user'.
        /v1/inquiry must return 200, not 403.
        """
        response = client.post(
            "/v1/inquiry",
            json={
                "buyer_name": "Acme Corp",
                "contact_email": "buyer@acme.com",
                "hs_code": "330499",
                "sender_company": "MarketGate",
                "sender_name": "Kim",
                "message": "Test",
            },
        )
        assert response.status_code == 200, (
            "Advanced-plan users must be allowed — check that require_plan "
            "reads subscription_store, not auth_store"
        )

    def test_inquiry_blocked_for_basic_plan(self):
        """
        A Basic-plan subscriber must be denied access to /v1/inquiry (403).
        """
        import app.auth_deps as _auth_deps_module
        original = _auth_deps_module.get_subscription
        _auth_deps_module.get_subscription = lambda uid: {"plan": "Basic", "started_at": None, "expires_at": None}
        try:
            response = client.post(
                "/v1/inquiry",
                json={
                    "buyer_name": "Acme Corp",
                    "contact_email": "buyer@acme.com",
                    "hs_code": "330499",
                    "sender_company": "MarketGate",
                    "sender_name": "Kim",
                },
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "requires_Advanced_plan"
        finally:
            _auth_deps_module.get_subscription = original
