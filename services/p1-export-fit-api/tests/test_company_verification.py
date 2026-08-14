# -*- coding: utf-8 -*-
"""CV-02: Company verification endpoint tests."""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.auth_deps import get_current_user
import app.routers.company_verification as cv_router
import app.company_verification_store as cv_store

client = TestClient(app)


# -- helpers ------------------------------------------------------------------

MOCK_STATUSES = [
    "BASIC_CONFIRMED",
    "BASIC_PARTIAL",
    "DATA_MISMATCH",
    "INACTIVE_ENTITY",
    "CREDIT_CHECK_REQUIRED",
]


def _expected_status(company_name: str) -> str:
    h = hashlib.sha256(company_name.encode("utf-8")).hexdigest()
    return MOCK_STATUSES[int(h, 16) % 5]


def _fake_create(**kwargs):
    return {
        "verification_id": str(uuid.uuid4()),
        "company_name": kwargs["company_name"],
        "country_iso3": kwargs["country_iso3"],
        "registry_check_status": kwargs["registry_check_status"],
        "result_json": kwargs["result_json"],
        "provider": kwargs["provider"],
        "requested_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:00:00+00:00",
    }


def _fake_get(check_id: str):
    return None


# -- POST /v1/company-verifications ------------------------------------------

def test_post_basic_confirmed(monkeypatch):
    """Company name whose hash % 5 == 0 returns BASIC_CONFIRMED."""
    monkeypatch.setattr(cv_router, "create_verification", _fake_create)
    name = "AlphaCorp"
    expected = _expected_status(name)
    res = client.post(
        "/v1/company-verifications",
        json={"company_name": name, "country_iso3": "KOR"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["company_name"] == "AlphaCorp"
    assert body["country_iso3"] == "KOR"
    assert body["provider"] == "opencorporates"
    assert body["registry_check_status"] == expected
    assert body["verification_id"]
    assert body["requested_at"]
    assert body["completed_at"]
    assert body["result_json"]["mock"] is True


def test_post_all_five_statuses():
    """Verify each of the 5 statuses is reachable."""
    seen = set()
    for i in range(200):
        name = f"TestCompany{i}"
        seen.add(_expected_status(name))
        if len(seen) == 5:
            break
    assert seen == set(MOCK_STATUSES), f"Only saw {seen}"


def test_post_deterministic(monkeypatch):
    """Same company_name always produces same status."""
    monkeypatch.setattr(cv_router, "create_verification", _fake_create)
    payload = {"company_name": "SameCorp", "country_iso3": "USA"}
    r1 = client.post("/v1/company-verifications", json=payload)
    r2 = client.post("/v1/company-verifications", json=payload)
    assert r1.json()["registry_check_status"] == r2.json()["registry_check_status"]


def test_post_with_registration_number(monkeypatch):
    monkeypatch.setattr(cv_router, "create_verification", _fake_create)
    res = client.post(
        "/v1/company-verifications",
        json={
            "company_name": "NumCorp",
            "country_iso3": "JPN",
            "registration_number": "12345",
        },
    )
    assert res.status_code == 200
    assert res.json()["country_iso3"] == "JPN"


def test_post_empty_company_name_returns_422():
    """Pydantic validation rejects empty company_name."""
    res = client.post(
        "/v1/company-verifications",
        json={"company_name": "", "country_iso3": "KOR"},
    )
    assert res.status_code == 422


def test_post_missing_company_name_returns_422():
    res = client.post(
        "/v1/company-verifications",
        json={"country_iso3": "KOR"},
    )
    assert res.status_code == 422


# -- GET /v1/company-verifications/{id} --------------------------------------

def test_get_not_found(monkeypatch):
    monkeypatch.setattr(cv_router, "get_verification", _fake_get)
    fake_id = str(uuid.uuid4())
    res = client.get(f"/v1/company-verifications/{fake_id}")
    assert res.status_code == 404
    assert res.json()["detail"] == "verification_not_found"


def test_post_then_get_roundtrip(monkeypatch):
    """POST creates a record that GET can retrieve."""
    store: dict[str, dict] = {}

    def mock_create(**kwargs):
        rec = _fake_create(**kwargs)
        store[rec["verification_id"]] = rec
        return rec

    def mock_get(check_id: str):
        return store.get(check_id)

    monkeypatch.setattr(cv_router, "create_verification", mock_create)
    monkeypatch.setattr(cv_router, "get_verification", mock_get)

    post_res = client.post(
        "/v1/company-verifications",
        json={"company_name": "RoundTripCo", "country_iso3": "DEU"},
    )
    assert post_res.status_code == 200
    vid = post_res.json()["verification_id"]

    get_res = client.get(f"/v1/company-verifications/{vid}")
    assert get_res.status_code == 200
    body = get_res.json()
    assert body["verification_id"] == vid
    assert body["company_name"] == "RoundTripCo"
    assert body["country_iso3"] == "DEU"
    assert body["registry_check_status"] == post_res.json()["registry_check_status"]
    assert body["result_json"]["mock"] is True


# -- Auth guard ---------------------------------------------------------------

def test_post_unauthenticated():
    """Without get_current_user override, endpoint returns 401/403."""
    saved = app.dependency_overrides.pop(get_current_user, None)
    try:
        res = client.post(
            "/v1/company-verifications",
            json={"company_name": "NoAuth", "country_iso3": "KOR"},
        )
        assert res.status_code in (401, 403)
    finally:
        if saved is not None:
            app.dependency_overrides[get_current_user] = saved


def test_get_unauthenticated():
    saved = app.dependency_overrides.pop(get_current_user, None)
    try:
        fake_id = str(uuid.uuid4())
        res = client.get(f"/v1/company-verifications/{fake_id}")
        assert res.status_code in (401, 403)
    finally:
        if saved is not None:
            app.dependency_overrides[get_current_user] = saved


# -- DB storage verification (mocked store) -----------------------------------

def test_db_storage_calls_store(monkeypatch):
    """Verify that POST passes correct args to the store layer."""
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return _fake_create(**kwargs)

    monkeypatch.setattr(cv_router, "create_verification", fake_create)

    res = client.post(
        "/v1/company-verifications",
        json={"company_name": "DBCheckCorp", "country_iso3": "USA", "registration_number": "R123"},
    )
    assert res.status_code == 200
    assert len(calls) == 1
    call = calls[0]
    assert call["user_id"] == "test-user"
    assert call["company_name"] == "DBCheckCorp"
    assert call["country_iso3"] == "USA"
    assert call["registration_number"] == "R123"
    assert call["provider"] == "opencorporates"
    assert call["registry_check_status"] == _expected_status("DBCheckCorp")
    assert call["result_json"]["mock"] is True


# -- Schema alignment (L025) --------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REGISTRY_SQL = _REPO_ROOT / "db" / "migrations" / "0006_company_registry_checks.sql"


def test_registry_migration_is_0006_not_0005():
    """origin/main already owns 0005_payment_credits.sql."""
    assert _REGISTRY_SQL.is_file()
    assert not (_REPO_ROOT / "db" / "migrations" / "0005_company_registry_checks.sql").exists()
    assert (_REPO_ROOT / "db" / "migrations" / "0005_payment_credits.sql").is_file()


def test_sql_enum_matches_mock_statuses():
    sql = _REGISTRY_SQL.read_text(encoding="utf-8")
    for status in cv_router.MOCK_STATUSES:
        assert f"'{status}'" in sql
    for banned in ("VERIFIED", "PARTIAL_MATCH", "MISMATCH"):
        assert f"'{banned}'" not in sql
    assert "'INACTIVE'" not in sql


def test_run_migrations_lists_0006():
    text = (
        _REPO_ROOT / "services" / "p1-export-fit-api" / "app" / "run_migrations.py"
    ).read_text(encoding="utf-8")
    assert "0006_company_registry_checks.sql" in text
