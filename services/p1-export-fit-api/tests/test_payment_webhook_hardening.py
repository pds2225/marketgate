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
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from main import app
from app import credit_store, payment_store, subscription_store
from app.routers import payment as payment_router


client = TestClient(app)
# 서버 예외를 응답으로 받으려면 별도 클라이언트가 필요하다 (기본값은 재발생).
error_client = TestClient(app, raise_server_exceptions=False)


def _sign(body: bytes, secret: str = "test-secret") -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _post_body(body: bytes, http=None):
    return (http or client).post(
        "/v1/payment/webhook",
        content=body,
        headers={
            "TossPayments-Signature": _sign(body),
            "Content-Type": "application/json",
        },
    )


def _post(order_id: str, amount: int, http=None, **extra):
    payload = {"status": "DONE", "orderId": order_id, "totalAmount": amount}
    payload.update(extra)
    return _post_body(json.dumps(payload).encode(), http=http)


def _post_wrapped(
    order_id: str,
    amount: int,
    event_type: str = "PAYMENT_STATUS_CHANGED",
    **extra,
):
    """공식 문서 형태: {eventType, createdAt, data:{Payment}}."""
    payment = {
        "paymentKey": "pk_test_" + uuid.uuid4().hex[:12],
        "orderId": order_id,
        "status": "DONE",
        "totalAmount": amount,
    }
    payment.update(extra)
    body = json.dumps(
        {
            "eventType": event_type,
            "createdAt": "2026-07-28T00:00:00+09:00",
            "data": payment,
        }
    ).encode()
    return _post_body(body)


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
    # 이 테스트들은 실계정 없이 합성 user_id로 웹훅을 쏜다 — 미등록 사용자
    # 가드(unknown_user)는 별도 테스트에서 검증하므로 여기서는 존재한다고 본다.
    monkeypatch.setattr(
        payment_router, "find_user_by_id", lambda uid: {"user_id": uid}
    )
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
    """apply_fn runs while the ledger lock is held — re-entry must not deadlock.

    A regression here must FAIL this test, not wedge the run: the probe thread
    would block forever holding the module lock, so it is a daemon and the lock
    is swapped out on the way if it never came back.
    """
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

    threading.Thread(target=_run, daemon=True).start()
    try:
        assert done.wait(timeout=5), (
            "fulfill_payment_once deadlocked on a re-entrant read"
        )
        assert seen == [[]]
    finally:
        if not done.is_set():
            # 교착된 프로브가 잠금을 영구 점유한다 — 새 잠금으로 갈아끼워
            # 뒤따르는 테스트까지 멈추지 않게 한다.
            payment_store._lock = threading.RLock()


def test_subscription_amount_mismatch_leaves_plan_unchanged(stores):
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.subscription.Advanced.{uuid.uuid4().hex[:12]}"

    r = _post(order_id, 29000)  # Advanced는 79000
    assert r.status_code == 200
    assert r.json()["needs_review"] is True
    assert subscription_store.get_subscription(user_id)["plan"] == "Basic"
    assert _ledger(stores)[0]["status"] == "NEEDS_REVIEW"


def test_corrected_retry_recovers_a_needs_review_payment(stores):
    """NEEDS_REVIEW는 종결이 아니다 — 금액이 정정된 재전송은 이행돼야 한다.

    그러지 않으면 값이 틀렸다가 고쳐진 정상 결제가 영원히 미이행으로 남는다.
    """
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.large.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    bad = _post(order_id, 20000)  # large는 160000
    assert bad.json()["needs_review"] is True
    assert credit_store.get_balance(user_id) == before

    good = _post(order_id, 160000)
    assert good.status_code == 200
    assert good.json() == {"status": "ok", "duplicate": False, "recovered": True}
    assert credit_store.get_balance(user_id) == before + 100

    ledger = _ledger(stores)
    assert len(ledger) == 1, "복구는 새 행을 만들지 않고 기존 행을 승격한다"
    assert ledger[0]["status"] == "DONE"
    assert ledger[0]["amount"] == 160000

    # 복구 후에는 DONE — 재전송은 다시 중복으로 흡수된다.
    again = _post(order_id, 160000)
    assert again.json() == {"status": "ok", "duplicate": True}
    assert credit_store.get_balance(user_id) == before + 100
    assert len(_ledger(stores)) == 1


def test_still_invalid_retry_is_blocked_not_fulfilled(stores):
    """여전히 검증에 실패하는 재전송은 blocked_by로 표시된다 (ops 신호)."""
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.enormous.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    assert _post(order_id, 20000).json()["needs_review"] is True
    retry = _post(order_id, 20000)

    assert retry.status_code == 200
    assert retry.json() == {
        "status": "ok",
        "needs_review": True,
        "duplicate": True,
        "blocked_by": "NEEDS_REVIEW",
    }
    assert credit_store.get_balance(user_id) == before
    assert len(_ledger(stores)) == 1


def test_corrupt_ledger_fails_closed(stores):
    """손상된 원장은 빈 원장이 아니다 — 5xx로 실패하고 이행하지 않는다.

    빈 목록으로 취급하면 이미 이행된 order_id가 전부 재이행 가능해진다.
    5xx면 Toss가 재전송하므로 운영자가 파일을 복구한 뒤 정상 처리된다.
    """
    stores.write_text("{ this is not valid json", encoding="utf-8")
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.small.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    r = _post(order_id, 20000, http=error_client)

    assert r.status_code >= 500, "손상된 원장에서 200을 주면 안 된다"
    assert credit_store.get_balance(user_id) == before
    assert stores.read_text(encoding="utf-8") == "{ this is not valid json"


def test_deliveries_without_any_id_get_distinct_rows(stores):
    """orderId도 paymentKey도 없으면 배달마다 별도 행 — 합쳐지면 결제가 유실된다."""
    body = json.dumps({"status": "DONE", "totalAmount": 20000}).encode()

    r1 = _post_body(body)
    r2 = _post_body(body)

    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["needs_review"] is True
    assert r2.json()["needs_review"] is True

    ledger = _ledger(stores)
    assert len(ledger) == 2, "멱등 키가 없는 두 결제가 한 행으로 합쳐졌다"
    assert len({row["order_id"] for row in ledger}) == 2
    assert all(row["status"] == "NEEDS_REVIEW" for row in ledger)


def test_invalid_json_with_valid_signature_is_recorded(stores):
    """서명이 이미 Toss 발신을 증명했다 — 400은 재전송 예산만 태운다."""
    body = b"{not json at all"

    r = _post_body(body)

    assert r.status_code == 200
    assert r.json()["needs_review"] is True
    ledger = _ledger(stores)
    assert len(ledger) == 1
    expected_key = f"invalid-json:{hashlib.sha256(body).hexdigest()[:16]}"
    assert ledger[0]["order_id"] == expected_key
    assert ledger[0]["status"] == "NEEDS_REVIEW"

    # 같은 본문 재전송은 같은 키 → 행이 늘지 않는다.
    assert _post_body(body).json()["duplicate"] is True
    assert len(_ledger(stores)) == 1


def test_wrapped_toss_payload_fulfills_once(stores):
    """공식 문서 형태의 래핑 페이로드가 실제로 이행돼야 한다.

    루트에서 status/orderId를 읽던 시절에는 실 웹훅이 전량 {"status":"ignored"}로
    빠져 원장 기록조차 남지 않았다 (docs/LESSONS.md L018).
    """
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.small.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    r1 = _post_wrapped(order_id, 20000)
    assert r1.status_code == 200
    assert r1.json() == {"status": "ok", "duplicate": False}
    assert credit_store.get_balance(user_id) == before + 10

    r2 = _post_wrapped(order_id, 20000)
    assert r2.json() == {"status": "ok", "duplicate": True}
    assert credit_store.get_balance(user_id) == before + 10

    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["order_id"] == order_id
    assert ledger[0]["status"] == "DONE"


def test_wrapped_non_payment_event_is_ignored(stores):
    """CANCEL_STATUS_CHANGED 등은 오늘 범위 밖 — 원장을 건드리지 않는다."""
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.small.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    r = _post_wrapped(order_id, 20000, event_type="CANCEL_STATUS_CHANGED")

    assert r.status_code == 200
    assert r.json() == {"status": "ignored", "event_type": "CANCEL_STATUS_CHANGED"}
    assert credit_store.get_balance(user_id) == before
    assert _ledger(stores) == []


def test_wrapped_payload_still_validates_amount(stores):
    """래핑 페이로드에서도 하드닝 로직에 도달해야 한다 — 봉투만 벗기고 끝이 아니다."""
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.large.{uuid.uuid4().hex[:12]}"
    before = credit_store.get_balance(user_id)

    r = _post_wrapped(order_id, 20000)  # large는 160000

    assert r.status_code == 200
    assert r.json()["needs_review"] is True
    assert credit_store.get_balance(user_id) == before
    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["status"] == "NEEDS_REVIEW"
    assert ledger[0]["order_id"] == order_id


def test_missing_signature_header_is_rejected(stores):
    """서명 스킴 확정 전까지 fail-closed가 유지돼야 한다 (docs/LESSONS.md L018)."""
    body = json.dumps(
        {"status": "DONE", "orderId": "x.credit.small.y", "totalAmount": 20000}
    ).encode()

    unsigned = client.post(
        "/v1/payment/webhook",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert unsigned.status_code == 401
    assert unsigned.json()["detail"] == "invalid_signature"

    wrong = client.post(
        "/v1/payment/webhook",
        content=body,
        headers={
            "TossPayments-Signature": "deadbeef",
            "Content-Type": "application/json",
        },
    )
    assert wrong.status_code == 401
    assert _ledger(stores) == [], "거부된 웹훅은 원장에 남지 않는다"


def test_unknown_user_is_not_fulfilled(stores, monkeypatch):
    """존재하지 않는 계정으로는 이행하지 않는다 — 지갑을 새로 만들지 않는다."""
    monkeypatch.setattr(payment_router, "find_user_by_id", lambda uid: None)
    user_id = str(uuid.uuid4())
    order_id = f"{user_id}.credit.small.{uuid.uuid4().hex[:12]}"

    r = _post(order_id, 20000)

    assert r.status_code == 200
    assert r.json()["needs_review"] is True
    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["status"] == "NEEDS_REVIEW"
    assert ledger[0]["user_id"] == user_id

    # 지갑이 생성되지 않았어야 한다 (파일에 사용자 키가 없다).
    credits = json.loads(
        Path(credit_store.CREDITS_PATH).read_text(encoding="utf-8")
    )
    assert user_id not in credits

    # 재전송은 중복으로 흡수된다.
    assert _post(order_id, 20000).json()["duplicate"] is True
    assert len(_ledger(stores)) == 1


def test_render_yaml_pins_a_single_worker():
    """인프로세스 잠금이 유일한 멱등 게이트다 — 워커를 늘리면 무효화된다.

    근거: docs/LESSONS.md L014 (2프로세스 실험 5/5회 양쪽 모두 적립).
    order_id DB unique index 도입 전까지 이 핀을 풀면 안 된다.
    """
    render_yaml = Path(__file__).resolve().parents[1] / "render.yaml"
    config = yaml.safe_load(render_yaml.read_text(encoding="utf-8"))
    env_vars = {
        entry["key"]: entry.get("value")
        for entry in config["services"][0]["envVars"]
    }
    assert env_vars.get("UVICORN_WORKERS") == "1", (
        "UVICORN_WORKERS must stay '1' until order_id has a DB unique index "
        "(docs/LESSONS.md L014)"
    )
