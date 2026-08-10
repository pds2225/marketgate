"""관리자 접근통제 — 비관리자 403, 관리자 200, 접근 로그 저장 검증."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from main import app
import app.inquiry_store as inquiry_store
import app.auth_deps as auth_deps
import app.credit_store as credit_store
import app.subscription_store as subscription_store

client = TestClient(app)

ADMIN_ENDPOINTS = [
    ("GET", "/v1/admin/inquiries"),
    ("POST", "/v1/admin/inquiries/none/approve"),
    ("POST", "/v1/admin/inquiries/none/reject"),
    ("POST", "/v1/admin/inquiries/none/queue"),
    ("POST", "/v1/admin/inquiries/none/mark-sent"),
    ("POST", "/v1/admin/inquiries/none/mark-failed"),
    ("POST", "/v1/admin/inquiries/none/record-result"),
    # 잔액·플랜을 직접 바꾸는 변이 — 결제를 거치지 않는 자가 지급 경로였다.
    ("POST", "/v1/credits/charge"),
    ("POST", "/v1/subscription/change"),
]


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(inquiry_store, "INQUIRIES_PATH", str(tmp_path / "inquiries.json"))
    monkeypatch.setattr(
        auth_deps, "ADMIN_ACCESS_LOG_PATH", str(tmp_path / "admin_access_log.json")
    )
    # 관리자 허용 경로가 실제로 금전 상태를 바꾸므로 저장소도 격리한다.
    monkeypatch.setattr(credit_store, "CREDITS_PATH", str(tmp_path / "credits.json"))
    monkeypatch.setattr(
        subscription_store, "SUBSCRIPTIONS_PATH", str(tmp_path / "subscriptions.json")
    )
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    yield


def _read_log() -> list[dict]:
    try:
        with open(auth_deps.ADMIN_ACCESS_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_non_admin_gets_403_on_all_admin_endpoints(method, path):
    res = client.request(method, path, json={})
    assert res.status_code == 403, f"{method} {path} -> {res.status_code}"
    assert res.json()["detail"] == "admin_required"


def test_denied_access_is_logged():
    client.get("/v1/admin/inquiries")
    entries = _read_log()
    assert entries, "접근 로그가 기록되어야 한다"
    last = entries[-1]
    assert last["allowed"] is False
    assert last["path"] == "/v1/admin/inquiries"
    assert last["email"] == "test@example.com"


def test_admin_env_allows_access_and_logs(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    res = client.get("/v1/admin/inquiries")
    assert res.status_code == 200
    assert res.json() == {"items": []}
    last = _read_log()[-1]
    assert last["allowed"] is True


def test_credits_charge_is_admin_only(monkeypatch):
    """결제를 거치지 않는 잔액 지급은 관리자 전용이어야 한다."""
    denied = client.post("/v1/credits/charge", json={"amount": 500})
    assert denied.status_code == 403
    assert denied.json()["detail"] == "admin_required"
    assert credit_store.get_balance("test-user") == credit_store.DEFAULT_BALANCE

    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    allowed = client.post("/v1/credits/charge", json={"amount": 500})
    assert allowed.status_code == 200
    assert allowed.json()["balance"] == credit_store.DEFAULT_BALANCE + 500
    assert _read_log()[-1]["allowed"] is True


def test_subscription_change_is_admin_only(monkeypatch):
    """결제를 거치지 않는 플랜 변경은 관리자 전용이어야 한다."""
    denied = client.post("/v1/subscription/change", json={"plan": "Advanced"})
    assert denied.status_code == 403
    assert denied.json()["detail"] == "admin_required"
    assert subscription_store.get_subscription("test-user")["plan"] == "Basic"

    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    allowed = client.post("/v1/subscription/change", json={"plan": "Advanced"})
    assert allowed.status_code == 200
    assert allowed.json()["plan"] == "Advanced"
    assert subscription_store.get_subscription("test-user")["plan"] == "Advanced"


def test_me_exposes_role(monkeypatch):
    res = client.get("/v1/auth/me")
    assert res.status_code == 200
    assert res.json()["role"] == "user"

    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    res = client.get("/v1/auth/me")
    assert res.status_code == 200
    assert res.json()["role"] == "admin"


def test_role_field_on_user_record_grants_admin(monkeypatch):
    assert auth_deps.is_admin({"email": "x@y.z", "role": "admin"}) is True
    assert auth_deps.is_admin({"email": "x@y.z", "role": "user"}) is False
