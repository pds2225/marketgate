"""결제 승인(confirm) — 승인하지 않으면 결제가 매입되지 않고 EXPIRE된다.

토스 API는 전부 목으로 대체한다(네트워크 호출 없음). 검증 포인트:
  - 승인 요청에 실리는 금액은 클라이언트가 보낸 값이 아니라 주문서 정가다
  - 소유자·금액·상품 검증은 네트워크 호출 **이전**에 끝난다
  - confirm과 웹훅은 같은 order_id를 공유하므로 순서와 무관하게 1회만 적용된다
  - 토스가 거절하거나 닿지 않으면 원장에 아무것도 남기지 않는다(재시도 가능)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import urllib.error
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from app import credit_store, payment_store, subscription_store
from app.routers import payment as payment_router


client = TestClient(app)

# conftest가 get_current_user를 이 사용자로 덮어쓴다.
USER_ID = "test-user"
SECRET = "test_sk_confirm"


@pytest.fixture
def stores(tmp_path, monkeypatch):
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
    monkeypatch.setattr(payment_router, "_TOSS_SECRET_KEY", SECRET)
    # 웹훅 상호작용 테스트용 — 합성 user_id를 실계정으로 취급한다.
    monkeypatch.setattr(
        payment_router, "find_user_by_id", lambda uid: {"user_id": uid}
    )
    monkeypatch.setenv("TOSS_WEBHOOK_SECRET", "test-secret")
    return payments_file


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _mock_toss(monkeypatch, *, payload=None, error=None):
    """urlopen을 가로채고, 실제로 나간 요청을 기록해 돌려준다."""
    calls: list[dict] = []

    def _fake_urlopen(request, timeout=None):
        calls.append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "headers": {k.lower(): v for k, v in request.headers.items()},
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        if error is not None:
            raise error
        return _FakeResponse(payload or {"status": "DONE"})

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    return calls


def _order_id(product_type: str, item_key: str, user_id: str = USER_ID) -> str:
    return f"{user_id}.{product_type}.{item_key}.{uuid.uuid4().hex[:12]}"


def _confirm(order_id: str, amount: int, payment_key: str = "pk_test_1"):
    return client.post(
        "/v1/payment/confirm",
        json={"paymentKey": payment_key, "orderId": order_id, "amount": amount},
    )


def _webhook(order_id: str, amount: int):
    body = json.dumps(
        {"status": "DONE", "orderId": order_id, "totalAmount": amount}
    ).encode()
    return client.post(
        "/v1/payment/webhook",
        content=body,
        headers={
            "TossPayments-Signature": hmac.new(
                b"test-secret", body, hashlib.sha256
            ).hexdigest(),
            "Content-Type": "application/json",
        },
    )


def _ledger(payments_file) -> list:
    return json.loads(payments_file.read_text(encoding="utf-8"))


def test_confirm_credits_once_and_sends_expected_amount(stores, monkeypatch):
    calls = _mock_toss(monkeypatch)
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok", "duplicate": False}
    assert credit_store.get_balance(USER_ID) == before + 10

    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["order_id"] == order_id
    assert ledger[0]["status"] == "DONE"
    assert ledger[0]["amount"] == 20000

    assert len(calls) == 1
    sent = calls[0]
    assert sent["url"] == "https://api.tosspayments.com/v1/payments/confirm"
    assert sent["method"] == "POST"
    assert sent["timeout"] == 10
    assert sent["body"] == {
        "paymentKey": "pk_test_1",
        "orderId": order_id,
        "amount": 20000,
    }
    expected_basic = base64.b64encode(f"{SECRET}:".encode()).decode()
    assert sent["headers"]["authorization"] == f"Basic {expected_basic}"
    assert sent["headers"]["content-type"] == "application/json"


def test_confirm_sends_order_price_not_client_amount(stores, monkeypatch):
    """클라이언트가 정가를 보내더라도 서버는 자기 계산값을 보낸다."""
    calls = _mock_toss(monkeypatch)
    order_id = _order_id("credit", "large")

    assert _confirm(order_id, 160000).status_code == 200
    assert calls[0]["body"]["amount"] == 160000
    assert credit_store.get_balance(USER_ID) == 100 + 100


def test_confirm_subscription_changes_plan_once(stores, monkeypatch):
    _mock_toss(monkeypatch)
    order_id = _order_id("subscription", "Pro")

    r = _confirm(order_id, 29000)

    assert r.status_code == 200
    assert r.json() == {"status": "ok", "duplicate": False}
    assert subscription_store.get_subscription(USER_ID)["plan"] == "Pro"
    assert len(_ledger(stores)) == 1


def test_confirm_then_webhook_applies_once(stores, monkeypatch):
    _mock_toss(monkeypatch)
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    assert _confirm(order_id, 20000).json()["duplicate"] is False
    after_confirm = credit_store.get_balance(USER_ID)
    assert after_confirm == before + 10

    hook = _webhook(order_id, 20000)
    assert hook.status_code == 200
    assert hook.json() == {"status": "ok", "duplicate": True}
    assert credit_store.get_balance(USER_ID) == after_confirm
    assert len(_ledger(stores)) == 1


def test_webhook_then_confirm_applies_once(stores, monkeypatch):
    _mock_toss(monkeypatch)
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    assert _webhook(order_id, 20000).json()["duplicate"] is False
    after_hook = credit_store.get_balance(USER_ID)
    assert after_hook == before + 10

    r = _confirm(order_id, 20000)
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "duplicate": True}
    assert credit_store.get_balance(USER_ID) == after_hook
    assert len(_ledger(stores)) == 1


def test_confirm_rejects_someone_elses_order_without_calling_toss(stores, monkeypatch):
    calls = _mock_toss(monkeypatch)
    order_id = _order_id("credit", "small", user_id=str(uuid.uuid4()))
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 403
    assert r.json()["detail"] == "not_order_owner"
    assert calls == [], "소유자 검증 전에 토스를 호출하면 안 된다"
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == []


def test_confirm_rejects_amount_mismatch_without_calling_toss(stores, monkeypatch):
    calls = _mock_toss(monkeypatch)
    order_id = _order_id("credit", "large")  # 정가 160000

    r = _confirm(order_id, 20000)

    assert r.status_code == 400
    assert r.json()["detail"] == "amount_mismatch"
    assert calls == []
    assert _ledger(stores) == []


def test_confirm_rejects_unknown_item(stores, monkeypatch):
    calls = _mock_toss(monkeypatch)

    unknown_pkg = _confirm(_order_id("credit", "enormous"), 20000)
    assert unknown_pkg.status_code == 400
    assert "unknown package" in unknown_pkg.json()["detail"]

    unknown_plan = _confirm(_order_id("subscription", "Platinum"), 29000)
    assert unknown_plan.status_code == 400
    assert "unknown plan" in unknown_plan.json()["detail"]

    unknown_type = _confirm(_order_id("giftcard", "small"), 20000)
    assert unknown_type.status_code == 400

    assert calls == []
    assert _ledger(stores) == []


def test_confirm_without_secret_key_is_unavailable(stores, monkeypatch):
    calls = _mock_toss(monkeypatch)
    monkeypatch.setattr(payment_router, "_TOSS_SECRET_KEY", "  ")

    r = _confirm(_order_id("credit", "small"), 20000)

    assert r.status_code == 503
    assert r.json()["detail"] == "toss_not_configured"
    assert calls == []
    assert _ledger(stores) == []


def test_toss_rejection_passes_through_and_records_nothing(stores, monkeypatch):
    error = urllib.error.HTTPError(
        payment_router._TOSS_CONFIRM_URL,
        400,
        "Bad Request",
        hdrs=None,
        fp=io.BytesIO(
            json.dumps(
                {
                    "code": "ALREADY_PROCESSED_PAYMENT",
                    "message": "이미 처리된 결제 입니다.",
                }
            ).encode()
        ),
    )
    _mock_toss(monkeypatch, error=error)
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 402
    detail = r.json()["detail"]
    assert detail["code"] == "ALREADY_PROCESSED_PAYMENT"
    assert detail["message"] == "이미 처리된 결제 입니다."
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == [], "재시도 가능한 실패는 원장에 남기지 않는다"


def test_network_failure_returns_502_and_records_nothing(stores, monkeypatch):
    _mock_toss(monkeypatch, error=urllib.error.URLError(TimeoutError("timed out")))
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 502
    assert r.json()["detail"] == "toss_unreachable"
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == []


def test_non_done_status_is_not_fulfilled(stores, monkeypatch):
    _mock_toss(monkeypatch, payload={"status": "CANCELED"})
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "NOT_DONE"
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == []
