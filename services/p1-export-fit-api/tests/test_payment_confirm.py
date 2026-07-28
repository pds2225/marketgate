"""결제 승인(confirm) — 승인하지 않으면 결제가 매입되지 않고 EXPIRE된다.

토스 API는 전부 목으로 대체한다(네트워크 호출 없음). 검증 포인트:
  - 승인 요청에 실리는 금액은 클라이언트가 보낸 값이 아니라 주문서 정가다
  - 소유자·금액·상품 검증은 네트워크 호출 **이전**에 끝난다
  - confirm과 웹훅은 같은 order_id를 공유하므로 순서와 무관하게 1회만 적용된다
  - 토스가 거절하거나 닿지 않으면 원장에 아무것도 남기지 않는다(재시도 가능)
"""
from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import io
import json
import pathlib
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


def _mock_toss(monkeypatch, *, payload=None, error=None, query_payload=None):
    """urlopen을 가로채고, 실제로 나간 요청을 기록해 돌려준다.

    기본 응답은 실제 토스처럼 요청 금액을 그대로 되돌려준다 — 승인 응답의
    totalAmount 검증이 정상 경로에서 통과하도록.

    query_payload가 있으면 GET /v1/payments/{paymentKey} 조회에 사용한다.
    """
    calls: list[dict] = []

    def _fake_urlopen(request, timeout=None):
        raw = request.data
        sent = json.loads(raw.decode("utf-8")) if raw else None
        calls.append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "headers": {k.lower(): v for k, v in request.headers.items()},
                "body": sent,
                "timeout": timeout,
            }
        )
        if request.get_method() == "GET":
            if query_payload is None:
                raise AssertionError("unexpected payment query without query_payload")
            return _FakeResponse(query_payload)
        if error is not None:
            raise error
        return _FakeResponse(
            payload
            or {
                "status": "DONE",
                "orderId": sent["orderId"],
                "paymentKey": sent["paymentKey"],
                "totalAmount": sent["amount"],
            }
        )

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


def test_confirm_large_package_credits_full_amount(stores, monkeypatch):
    """가장 비싼 패키지의 성공 경로 — 100크레딧이 실제로 적립되는지.

    구조(AST) 핀은 금액의 출처만 고정한다. 카탈로그 조회가 엉뚱한 패키지를
    집어도 AST는 통과하므로, 런타임에서 크레딧 수량까지 확인해야 한다.
    """
    calls = _mock_toss(monkeypatch)
    order_id = _order_id("credit", "large")
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 160000)

    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok", "duplicate": False}
    assert credit_store.get_balance(USER_ID) == before + 100

    ledger = _ledger(stores)
    assert len(ledger) == 1
    assert ledger[0]["status"] == "DONE"
    assert ledger[0]["order_id"] == order_id
    assert ledger[0]["package"] == "large"
    assert ledger[0]["amount"] == 160000
    assert calls[0]["body"]["amount"] == 160000


# ── 금액 출처 고정 (구조 검사) ──────────────────────────────────
# 런타임 테스트로는 이 성질을 잡을 수 없다: 금액 불일치 가드가 400으로 먼저
# 막기 때문에 네트워크 호출 시점에는 payload.amount == expected가 항상 참이고,
# 둘을 바꿔치기해도 어떤 테스트도 실패하지 않는다(실측 확인). 그래서 "카탈로그에서
# 유도한 값을 쓴다"는 성질 자체를 AST로 고정한다.


def _confirm_ast():
    src = pathlib.Path(payment_router.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    funcs = {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return funcs


def _catalog_names(confirm) -> list[str]:
    """_expected_amount(...) 결과가 바인딩되는 이름들."""
    return [
        target.id
        for node in ast.walk(confirm)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "id", None) == "_expected_amount"
        for target in node.targets
        if isinstance(target, ast.Name)
    ]


def test_confirm_is_sync_and_only_webhook_is_async():
    """sync def여야 FastAPI가 스레드풀에서 돌린다 — 네트워크 I/O가 루프를 막지 않는다."""
    funcs = _confirm_ast()
    assert not isinstance(funcs["confirm"], ast.AsyncFunctionDef)
    async_names = sorted(
        name for name, fn in funcs.items() if isinstance(fn, ast.AsyncFunctionDef)
    )
    assert async_names == ["webhook"], f"unexpected async functions: {async_names}"


def test_amount_sent_to_toss_is_catalog_derived():
    """승인 요청의 amount는 카탈로그 조회값이어야 한다 — 클라이언트 입력 금지."""
    funcs = _confirm_ast()
    confirm = funcs["confirm"]
    catalog = _catalog_names(confirm)
    assert catalog, "_expected_amount() 결과가 이름에 바인딩돼야 한다"

    sent = []
    for node in ast.walk(confirm):
        if not isinstance(node, ast.Dict):
            continue
        keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
        if "paymentKey" not in keys or "amount" not in keys:
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "amount":
                sent.append(ast.unparse(value))

    assert sent, "승인 요청 본문(dict with paymentKey+amount)을 찾지 못했다"
    assert all(expr in catalog for expr in sent), (
        f"client value reaches Toss: amount={sent}, catalog names={catalog}"
    )


def test_ledger_amount_is_catalog_derived():
    """원장에 남는 금액도 카탈로그 값이어야 한다."""
    funcs = _confirm_ast()
    confirm = funcs["confirm"]
    catalog = _catalog_names(confirm)

    recorded = [
        ast.unparse(kw.value)
        for node in ast.walk(confirm)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "fulfill_payment_once"
        for kw in node.keywords
        if kw.arg == "amount"
    ]
    assert recorded, "confirm이 fulfill_payment_once(amount=...)를 호출해야 한다"
    assert all(expr in catalog for expr in recorded), (
        f"client value reaches the ledger: amount={recorded}, catalog={catalog}"
    )


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
                    "code": "REJECT_CARD_COMPANY",
                    "message": "카드사 승인이 거절되었습니다.",
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
    assert detail["code"] == "REJECT_CARD_COMPANY"
    assert detail["message"] == "카드사 승인이 거절되었습니다."
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == [], "재시도 가능한 실패는 원장에 남기지 않는다"


def test_already_processed_queries_and_fulfills(stores, monkeypatch):
    """토스 승인은 됐는데 원장 기록이 없는 재시도 — 조회 후 이행한다.

    트리거: 첫 confirm이 토스 DONE 직후 크래시/타임아웃 → 원장 미기록.
    재시도가 ALREADY_PROCESSED를 402로만 끝내면 돈만 빠지고 크레딧이 없다.
    웹훅 서명도 fail-closed라 조회 API가 유일한 복구 경로다.
    """
    order_id = _order_id("credit", "small")
    payment_key = "pk_already_1"
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
    calls = _mock_toss(
        monkeypatch,
        error=error,
        query_payload={
            "status": "DONE",
            "orderId": order_id,
            "paymentKey": payment_key,
            "totalAmount": 20000,
        },
    )
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000, payment_key=payment_key)

    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok", "duplicate": False}
    assert credit_store.get_balance(USER_ID) == before + 10
    assert len(_ledger(stores)) == 1
    assert [c["method"] for c in calls] == ["POST", "GET"]
    assert calls[1]["url"].endswith(f"/v1/payments/{payment_key}")


def test_already_processed_order_mismatch_is_not_fulfilled(stores, monkeypatch):
    """남의 이미 승인된 paymentKey로 내 orderId를 적립시키려는 경로를 막는다."""
    order_id = _order_id("credit", "small")
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
    _mock_toss(
        monkeypatch,
        error=error,
        query_payload={
            "status": "DONE",
            "orderId": "attacker.credit.small.ffffffff",
            "paymentKey": "pk_stolen",
            "totalAmount": 20000,
        },
    )
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000, payment_key="pk_stolen")

    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "ORDER_MISMATCH"
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == []


def test_already_processed_query_failure_returns_502(stores, monkeypatch):
    """조회도 실패하면 프론트가 실패로 단정하지 않도록 502를 준다."""
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
    calls: list[dict] = []

    def _fake_urlopen(request, timeout=None):
        raw = request.data
        sent = json.loads(raw.decode("utf-8")) if raw else None
        calls.append({"method": request.get_method(), "body": sent})
        if request.get_method() == "GET":
            raise urllib.error.URLError(TimeoutError("timed out"))
        raise error

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 502
    assert r.json()["detail"] == "toss_unreachable"
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == []
    assert [c["method"] for c in calls] == ["POST", "GET"]


def test_network_failure_returns_502_and_records_nothing(stores, monkeypatch):
    _mock_toss(monkeypatch, error=urllib.error.URLError(TimeoutError("timed out")))
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 502
    assert r.json()["detail"] == "toss_unreachable"
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == []


def test_confirm_retry_does_not_call_toss_again(stores, monkeypatch):
    """재승인은 원장에서 걸러야 한다.

    실제 토스는 2번째 승인에 ALREADY_PROCESSED_PAYMENT(4xx)를 준다. 그걸 402로
    올리면 크레딧은 정상 적립됐는데 프론트는 결제 실패 화면을 띄운다.
    """
    calls = _mock_toss(monkeypatch)
    order_id = _order_id("credit", "small")
    before = credit_store.get_balance(USER_ID)

    first = _confirm(order_id, 20000)
    assert first.json() == {"status": "ok", "duplicate": False}

    second = _confirm(order_id, 20000)

    assert second.status_code == 200
    assert second.json() == {"status": "ok", "duplicate": True}
    assert len(calls) == 1, f"재승인이 토스를 다시 호출했다: {len(calls)}회"
    assert credit_store.get_balance(USER_ID) == before + 10
    assert len(_ledger(stores)) == 1


def test_confirmed_amount_mismatch_is_not_fulfilled(stores, monkeypatch):
    """토스가 돌려준 승인 금액이 정가와 다르면 이행하지 않는다."""
    order_id = _order_id("credit", "small")
    _mock_toss(
        monkeypatch,
        payload={
            "status": "DONE",
            "orderId": order_id,
            "paymentKey": "pk_test_1",
            "totalAmount": 1000,  # 정가는 20000
        },
    )
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "AMOUNT_MISMATCH"
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == []


def test_non_done_status_is_not_fulfilled(stores, monkeypatch):
    order_id = _order_id("credit", "small")
    _mock_toss(
        monkeypatch,
        payload={
            "status": "CANCELED",
            "orderId": order_id,
            "paymentKey": "pk_test_1",
            "totalAmount": 20000,
        },
    )
    before = credit_store.get_balance(USER_ID)

    r = _confirm(order_id, 20000)

    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "NOT_DONE"
    assert credit_store.get_balance(USER_ID) == before
    assert _ledger(stores) == []
