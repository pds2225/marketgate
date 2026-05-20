"""Regression test for the webhook order_id UUID-parsing bug.

Before the fix, `order_id.split("-", 2)` would shred the UUID user_id because
UUIDs contain 4 hyphens.  The fix uses `rsplit("-", 2)` so the UUID is kept
intact as the first element.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient


def _make_body(user_id: str, product_type: str, item_key: str, amount: int = 20000) -> bytes:
    order_id = f"{user_id}-{product_type}-{item_key}"
    return json.dumps(
        {"status": "DONE", "orderId": order_id, "totalAmount": amount}
    ).encode()


def test_webhook_parses_uuid_user_id_for_credit(tmp_path):
    """A UUID user_id must survive order_id parsing so credits are charged."""
    from main import app

    user_id = str(uuid.uuid4())  # e.g. 550e8400-e29b-41d4-a716-446655440000

    body = _make_body(user_id, "credit", "small")

    with (
        patch("app.routers.payment.verify_webhook_signature", return_value=True),
        patch("app.routers.payment.charge") as mock_charge,
        patch("app.routers.payment.record_payment") as mock_record,
    ):
        client = TestClient(app)
        response = client.post(
            "/v1/payment/webhook",
            content=body,
            headers={"content-type": "application/json", "TossPayments-Signature": ""},
        )

    assert response.status_code == 200, response.text
    mock_charge.assert_called_once()
    call_args = mock_charge.call_args
    assert call_args[0][0] == user_id, (
        f"charge() received wrong user_id={call_args[0][0]!r}, expected {user_id!r}. "
        "order_id parsing is still broken."
    )


def test_webhook_parses_uuid_user_id_for_subscription(tmp_path):
    """A UUID user_id must survive order_id parsing so the plan is upgraded."""
    from main import app

    user_id = str(uuid.uuid4())

    body = _make_body(user_id, "subscription", "Advanced", amount=79000)

    with (
        patch("app.routers.payment.verify_webhook_signature", return_value=True),
        patch("app.routers.payment.change_plan") as mock_change_plan,
        patch("app.routers.payment.record_payment") as mock_record,
    ):
        client = TestClient(app)
        response = client.post(
            "/v1/payment/webhook",
            content=body,
            headers={"content-type": "application/json", "TossPayments-Signature": ""},
        )

    assert response.status_code == 200, response.text
    mock_change_plan.assert_called_once()
    call_args = mock_change_plan.call_args
    assert call_args[0][0] == user_id, (
        f"change_plan() received wrong user_id={call_args[0][0]!r}, expected {user_id!r}. "
        "order_id parsing is still broken."
    )
    assert call_args[0][1] == "Advanced"
