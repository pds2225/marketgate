"""관리자 접근통제 — 비관리자 403, 관리자 200, 접근 로그 저장 검증."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from main import app
import app.inquiry_store as inquiry_store
import app.auth_deps as auth_deps

client = TestClient(app)

ADMIN_ENDPOINTS = [
    ("GET", "/v1/admin/inquiries"),
    ("POST", "/v1/admin/inquiries/none/approve"),
    ("POST", "/v1/admin/inquiries/none/reject"),
    ("POST", "/v1/admin/inquiries/none/queue"),
    ("POST", "/v1/admin/inquiries/none/mark-sent"),
    ("POST", "/v1/admin/inquiries/none/mark-failed"),
    ("POST", "/v1/admin/inquiries/none/record-result"),
]


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(inquiry_store, "INQUIRIES_PATH", str(tmp_path / "inquiries.json"))
    monkeypatch.setattr(
        auth_deps, "ADMIN_ACCESS_LOG_PATH", str(tmp_path / "admin_access_log.json")
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
