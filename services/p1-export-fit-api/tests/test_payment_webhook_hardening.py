"""Payment webhook hardening guards (docs/LESSONS.md L014–L017).

Covers, for signed DONE webhooks:
  - concurrent redelivery fulfills exactly once (in-process lock is the gate),
  - subscription plan changes are idempotent,
  - a genuine repurchase (new orderId) still fulfills,
  - unidentifiable / mispriced payments are recorded NEEDS_REVIEW with 200,
    never a non-2xx that Toss would retry until the payment is dropped.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from app import credit_store, payment_store, subscription_store


client = TestClient(app)


def _sign(body: bytes, secret: str = "test-secret") -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _post(order_id: str, amount: int):
    body = json.dumps(
        {"status": "DONE", "orderId": order_id, "totalAmount": amount}
    ).encode()
    return client.post(
        "/v1/payment/webhook",
        content=body,
        headers={
            "TossPayments-Signature": _sign(body),
            "Content-Type": "application/json",
        },
    )


@pytest.fixture
def stores(tmp_path, monkeypatch):
    """Isolate credit / payment / subscription state per test."""
    credits_file = tmp_path / "credits.json"
    payments_file = tmp_path / "payments.json"
    subscriptions_file = tmp_path / "subscriptions.json"
    credits_file.write_text("{}")
    payments_file.write_text("[]")
    subscriptions_file.write_text("{}")
    monkeypatch.setattr(credit_store, "CREDITS_PATH", str(credits_file))
    monkeypatch.setattr(payment_store, "PAYMENTS_PATH", str(payments_file))
    monkeypatch.setattr(
        subscription_store, "SUBSCRIPTIONS_PATH", str(subscriptions_file)
    )
    monkeypatch.setenv("TOSS_WEBHOOK_SECRET", "test-secret")
    return payments_file


def _ledger(payments_file) -> list:
    return json.loads(payments_file.read_text(encoding="utf-8"))


def test_concurrent_redelivery_charges_exactly_once(stores):
    """8 parallel deliveries of the same signed webhook → one charge, one row."""
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.small.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    responses: list = []
    responses_lock = threading.Lock()
    start = threading.Event()

    def _fire():
        start.wait()
        r = _post(order_id, 20000)
        with responses_lock:
            responses.append((r.status_code, r.json()))

    threads = [threading.Thread(target=_fire) for _ in range(8)]
    for t in threads:
        t.start()
    start.set()
    for t in threads:
        t.join()

    assert len(responses) == 8
    assert all(code == 200 for code, _ in responses)
    duplicates = [payload for _, payload in responses if payload.get("duplicate")]
    assert len(duplicates) == 7, f"expected 7 duplicates, got {responses}"
    assert credit_store.get_balance(user_id) == before + 10

    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["order_id"] == order_id
    assert ledger[0]["status"] == "DONE"


def test_subscription_webhook_changes_plan_once(stores):
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.subscription.Pro.{uuid.uuid4().hex[:12]}"

    r1 = _post(order_id, 29000)
    assert r1.status_code == 200
    assert r1.json() == {"status": "ok", "duplicate": False}
    sub = subscription_store.get_subscription(user_id)
    assert sub["plan"] == "Pro"

    r2 = _post(order_id, 29000)
    assert r2.status_code == 200
    assert r2.json() == {"status": "ok", "duplicate": True}
    assert subscription_store.get_subscription(user_id) == sub
    assert len(_ledger(stores)) == 1


def test_repurchase_with_new_order_id_fulfills_again(stores):
    """Same user + same package, two checkouts → two charges."""
    user_id = str(uuid.uuid4())
    before = credit_store.get_balance(user_id)

    for _ in range(2):
        order_id = f"{user_id}.credit.small.{uuid.uuid4().hex[:12]}"
        r = _post(order_id, 20000)
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "duplicate": False}

    assert credit_store.get_balance(user_id) == before + 20
    assert len(_ledger(stores)) == 2


def test_unknown_package_records_needs_review_and_returns_200(stores):
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.enormous.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    r = _post(order_id, 20000)
    assert r.status_code == 200, "non-2xx makes Toss retry until the payment is lost"
    assert r.json()["needs_review"] is True
    assert credit_store.get_balance(user_id) == before

    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["status"] == "NEEDS_REVIEW"
    assert ledger[0]["order_id"] == order_id

    # 재전송해도 NEEDS_REVIEW 행이 늘지 않고, 뒤늦게 이행되지도 않는다.
    r2 = _post(order_id, 20000)
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True
    assert len(_ledger(stores)) == 1
    assert credit_store.get_balance(user_id) == before


def test_amount_mismatch_is_not_fulfilled(stores):
    """20,000원 결제로 160,000원 large 패키지를 받을 수 없어야 한다."""
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.large.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    r = _post(order_id, 20000)
    assert r.status_code == 200
    assert r.json()["needs_review"] is True
    assert credit_store.get_balance(user_id) == before

    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["status"] == "NEEDS_REVIEW"
    assert ledger[0]["amount"] == 20000


def test_unparseable_order_id_is_recorded_not_rejected(stores):
    r = _post("not-an-order-id-in-any-format".replace("-", "_"), 20000)
    assert r.status_code == 200
    assert r.json()["needs_review"] is True

    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["order_id"] == "not_an_order_id_in_any_format"
    assert ledger[0]["status"] == "NEEDS_REVIEW"
    assert ledger[0]["user_id"] == "unknown"


def test_ledger_lock_is_reentrant(stores):
    """apply_fn runs while the ledger lock is held — re-entry must not deadlock."""
    done = threading.Event()
    seen: list = []

    def _reenter():
        seen.append(payment_store.get_payment_history())

    def _run():
        payment_store.fulfill_payment_once(
            order_id="reentrancy-probe",
            user_id="probe",
            product_type="credit",
            package="small",
            plan=None,
            amount=20000,
            apply_fn=_reenter,
        )
        done.set()

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    assert done.wait(timeout=5), "fulfill_payment_once deadlocked on a re-entrant read"
    assert seen == [[]]


def test_subscription_amount_mismatch_leaves_plan_unchanged(stores):
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.subscription.Advanced.{uuid.uuid4().hex[:12]}"

    r = _post(order_id, 29000)  # Advanced는 79000
    assert r.status_code == 200
    assert r.json()["needs_review"] is True
    assert subscription_store.get_subscription(user_id)["plan"] == "Basic"
    assert _ledger(stores)[0]["status"] == "NEEDS_REVIEW"
