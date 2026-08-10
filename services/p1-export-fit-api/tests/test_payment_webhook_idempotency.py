"""Payment webhook must not double-fulfill on Toss retries.

Concrete trigger: signed DONE webhook for the same orderId delivered twice
(network retry / Toss redelivery) previously charged credits twice.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from fastapi.testclient import TestClient

from main import app
from app import credit_store, payment_store
from app.routers import payment as payment_router


client = TestClient(app)


def _sign(body: bytes, secret: str = "test-secret") -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _stub_known_user(monkeypatch) -> None:
    """합성 user_id를 실계정으로 취급한다 (미등록 사용자 가드는 별도 테스트)."""
    monkeypatch.setattr(
        payment_router, "find_user_by_id", lambda uid: {"user_id": uid}
    )


def test_webhook_retry_does_not_double_charge(tmp_path, monkeypatch):
    credits_file = tmp_path / "credits.json"
    payments_file = tmp_path / "payments.json"
    credits_file.write_text("{}")
    payments_file.write_text("[]")
    monkeypatch.setattr(credit_store, "CREDITS_PATH", str(credits_file))
    monkeypatch.setattr(payment_store, "PAYMENTS_PATH", str(payments_file))
    monkeypatch.setenv("TOSS_WEBHOOK_SECRET", "test-secret")
    _stub_known_user(monkeypatch)

    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.small.{uuid.uuid4().hex[:12]}"
    body = json.dumps(
        {"status": "DONE", "orderId": order_id, "totalAmount": 20000}
    ).encode()
    headers = {
        "TossPayments-Signature": _sign(body),
        "Content-Type": "application/json",
    }

    before = credit_store.get_balance(user_id)
    r1 = client.post("/v1/payment/webhook", content=body, headers=headers)
    mid = credit_store.get_balance(user_id)
    r2 = client.post("/v1/payment/webhook", content=body, headers=headers)
    after = credit_store.get_balance(user_id)

    assert r1.status_code == 200
    assert r1.json() == {"status": "ok", "duplicate": False}
    assert mid == before + 10
    assert r2.status_code == 200
    assert r2.json() == {"status": "ok", "duplicate": True}
    assert after == mid
    payments = json.loads(payments_file.read_text())
    assert len(payments) == 1
    assert payments[0]["order_id"] == order_id


def test_checkout_order_ids_are_unique_per_request():
    r1 = client.post(
        "/v1/payment/checkout",
        json={"product_type": "credit", "package": "small"},
    )
    r2 = client.post(
        "/v1/payment/checkout",
        json={"product_type": "credit", "package": "small"},
    )

    assert r1.status_code == 200 and r2.status_code == 200
    o1, o2 = r1.json()["order_id"], r2.json()["order_id"]
    assert o1 != o2
    for order_id in (o1, o2):
        uid, ptype, item = payment_router._parse_order_id(order_id)
        assert uid == "test-user"
        assert ptype == "credit"
        assert item == "small"


def test_parse_order_id_supports_legacy_hyphen_format():
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    order_id = f"{user_id}-credit-medium"
    uid, ptype, item = payment_router._parse_order_id(order_id)
    assert uid == user_id
    assert ptype == "credit"
    assert item == "medium"


def test_legacy_order_id_webhook_still_fulfills_once(tmp_path, monkeypatch):
    credits_file = tmp_path / "credits.json"
    payments_file = tmp_path / "payments.json"
    credits_file.write_text("{}")
    payments_file.write_text("[]")
    monkeypatch.setattr(credit_store, "CREDITS_PATH", str(credits_file))
    monkeypatch.setattr(payment_store, "PAYMENTS_PATH", str(payments_file))
    monkeypatch.setenv("TOSS_WEBHOOK_SECRET", "test-secret")
    _stub_known_user(monkeypatch)

    user_id = "550e8400-e29b-41d4-a716-446655440000"
    order_id = f"{user_id}-credit-small"
    body = json.dumps(
        {"status": "DONE", "orderId": order_id, "totalAmount": 20000}
    ).encode()
    headers = {
        "TossPayments-Signature": _sign(body),
        "Content-Type": "application/json",
    }
    before = credit_store.get_balance(user_id)
    assert client.post("/v1/payment/webhook", content=body, headers=headers).status_code == 200
    assert credit_store.get_balance(user_id) == before + 10
    assert client.post("/v1/payment/webhook", content=body, headers=headers).json()[
        "duplicate"
    ] is True
    assert credit_store.get_balance(user_id) == before + 10
