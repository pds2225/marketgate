"""B0 보안 + 제재 게이트 회귀 테스트.

근거: 갭 진단 2026-06-10 P0 항목 + SIMULATION_SPEC §2/§5.
"""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from main import app
from app import payment_store
from app.auth_deps import _resolve_jwt_secret, get_current_user
from app.services import compliance

client = TestClient(app)


# ---------- webhook fail-closed ----------

def _webhook_post(body: dict, signature: str):
    return client.post(
        "/v1/payment/webhook",
        content=json.dumps(body).encode(),
        headers={
            "TossPayments-Signature": signature,
            "Content-Type": "application/json",
        },
    )


def test_webhook_rejected_when_secret_not_configured(monkeypatch):
    monkeypatch.delenv("TOSS_WEBHOOK_SECRET", raising=False)
    res = _webhook_post({"status": "PENDING"}, "any-signature")
    assert res.status_code == 401


def test_webhook_rejected_on_bad_signature(monkeypatch):
    monkeypatch.setenv("TOSS_WEBHOOK_SECRET", "test-secret")
    res = _webhook_post({"status": "PENDING"}, "wrong-signature")
    assert res.status_code == 401


def test_webhook_accepted_on_valid_signature(monkeypatch):
    monkeypatch.setenv("TOSS_WEBHOOK_SECRET", "test-secret")
    body = json.dumps({"status": "PENDING"}).encode()
    sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    res = client.post(
        "/v1/payment/webhook",
        content=body,
        headers={"TossPayments-Signature": sig, "Content-Type": "application/json"},
    )
    # status != DONE 이면 ignored — 서명 검증 통과 자체를 확인
    assert res.status_code == 200
    assert res.json() == {"status": "ignored"}


def test_webhook_rejected_on_empty_signature(monkeypatch):
    monkeypatch.setenv("TOSS_WEBHOOK_SECRET", "test-secret")
    res = _webhook_post({"status": "PENDING"}, "")
    assert res.status_code == 401


# ---------- payment history 인증 + 본인 것만 ----------

def test_payment_history_requires_auth():
    saved = app.dependency_overrides.pop(get_current_user)
    try:
        res = client.get("/v1/payment/history")
        assert res.status_code in (401, 403)
    finally:
        app.dependency_overrides[get_current_user] = saved


def test_payment_history_returns_only_own_records(tmp_path, monkeypatch):
    payments_file = tmp_path / "payments.json"
    payments_file.write_text(
        json.dumps([
            {"user_id": "test-user", "product_type": "credit", "amount": 1,
             "status": "DONE", "timestamp": "2026-06-10T00:00:00+00:00"},
            {"user_id": "other-user", "product_type": "credit", "amount": 2,
             "status": "DONE", "timestamp": "2026-06-10T00:00:00+00:00"},
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(payment_store, "PAYMENTS_PATH", str(payments_file))
    res = client.get("/v1/payment/history")
    assert res.status_code == 200
    records = res.json()
    assert len(records) == 1
    assert all(r["user_id"] == "test-user" for r in records)


# ---------- register 토큰 페어 ----------

def test_register_returns_access_and_refresh_tokens(monkeypatch):
    import app.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "find_user_by_email", lambda email: None)
    monkeypatch.setattr(
        auth_router,
        "create_user",
        lambda email, hashed: {"user_id": "u-test", "email": email, "plan": "Basic"},
    )
    res = client.post(
        "/v1/auth/register",
        json={"email": "new@example.com", "password": "12345678"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token"] == body["access_token"]  # legacy 호환 키


# ---------- JWT 시크릿 fail-closed (prod) ----------

def test_jwt_secret_required_in_production(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        _resolve_jwt_secret()


def test_jwt_secret_env_wins(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "s3cret")
    monkeypatch.setenv("APP_ENV", "production")
    assert _resolve_jwt_secret() == "s3cret"


def test_jwt_secret_dev_fallback(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    assert _resolve_jwt_secret() == "dev-secret-change-in-prod"


# ---------- 제재국 컴플라이언스 (SIMULATION_SPEC §2/§5) ----------

@pytest.mark.parametrize("code", ["KP", "kp", "PRK", "IR", "IRN", "SY", "SYR", "CU", "CUB"])
def test_blocked_countries_detected(code):
    assert compliance.is_blocked(code) is True


@pytest.mark.parametrize("code", ["RU", "rus", "BLR", "BY", "MM", "MMR", "VE", "VEN"])
def test_restricted_countries_detected(code):
    assert compliance.is_restricted(code) is True
    assert compliance.restricted_since(code) is not None


@pytest.mark.parametrize("code", ["US", "USA", "JP", "JPN", "", None])
def test_normal_countries_pass(code):
    assert compliance.is_blocked(code) is False
    assert compliance.is_restricted(code) is False


def test_restricted_since_dates_match_spec():
    assert compliance.restricted_since("RU") == "2022-03-01"
    assert compliance.restricted_since("BY") == "2022-03-01"
    assert compliance.restricted_since("MM") == "2021-02-01"
    assert compliance.restricted_since("VE") == "2019-01-01"


def test_filter_blocked_results_reranks():
    results = [
        {"partner_country_iso3": "USA", "rank": 1},
        {"partner_country_iso3": "PRK", "rank": 2},
        {"partner_country_iso3": "JPN", "rank": 3},
    ]
    out = compliance.filter_blocked_results(results)
    assert [r["partner_country_iso3"] for r in out] == ["USA", "JPN"]
    assert [r["rank"] for r in out] == [1, 2]


def test_landed_cost_blocked_country_returns_400_with_spec_fields():
    res = client.post(
        "/v1/simulation/landed-cost",
        json={"hs_code": "330499", "country": "KP", "unit_price": 10, "qty": 100},
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["error"] is True
    assert detail["error_code"] == "BLOCKED_COUNTRY"
    assert detail["compliance_status"] == "blocked"
    assert detail["target_country"] == "KP"
    assert detail["country_name"] == "북한"
    assert detail["legal_notice"]
    assert detail["reference_url"]


def test_landed_cost_blocked_country_case_insensitive():
    res = client.post(
        "/v1/simulation/landed-cost",
        json={"hs_code": "330499", "country": "prk", "unit_price": 10, "qty": 100},
    )
    assert res.status_code == 400
    assert res.json()["detail"]["error_code"] == "BLOCKED_COUNTRY"
