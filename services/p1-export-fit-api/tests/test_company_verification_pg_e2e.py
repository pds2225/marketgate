# -*- coding: utf-8 -*-
"""MG-001 real Postgres E2E: enum contract + user isolation.

Skipped unless DATABASE_URL is set (local/CI with Postgres).
Clears conftest auth overrides so JWT user switching is real.
"""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext

from main import app
from app.auth_store import create_user
from app.auth_deps import create_access_token, get_current_user, get_token_payload
from app import company_verification_store as store

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL required for MG-001 Postgres E2E",
)

client = TestClient(app)
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALLOWED = {
    "BASIC_CONFIRMED",
    "BASIC_PARTIAL",
    "DATA_MISMATCH",
    "INACTIVE_ENTITY",
    "CREDIT_CHECK_REQUIRED",
}


@pytest.fixture
def real_auth():
    saved = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_token_payload, None)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


def test_mg001_postgres_enum_and_user_isolation(real_auth):
    ua = create_user(f"a-{uuid.uuid4().hex[:8]}@example.com", pwd.hash("pass-a-123456"))
    ub = create_user(f"b-{uuid.uuid4().hex[:8]}@example.com", pwd.hash("pass-b-123456"))
    tok_a = create_access_token(ua["user_id"])
    tok_b = create_access_token(ub["user_id"])

    post = client.post(
        "/v1/company-verifications",
        json={"company_name": "E2E Corp", "country_iso3": "usa"},
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert post.status_code == 200, post.text
    body = post.json()
    assert body["registry_check_status"] in ALLOWED
    assert body["country_iso3"] == "USA"
    vid = body["verification_id"]

    own = client.get(
        f"/v1/company-verifications/{vid}",
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert own.status_code == 200
    assert own.json()["verification_id"] == vid

    other = client.get(
        f"/v1/company-verifications/{vid}",
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert other.status_code == 404
    assert other.json()["detail"] == "verification_not_found"
    assert ua["user_id"] not in other.text
    assert "E2E Corp" not in other.text

    conn = store.get_conn()
    assert conn is not None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, registry_check_status::text FROM core.company_registry_checks WHERE check_id=%s",
                (vid,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == ua["user_id"]
            assert row[1] in ALLOWED
    finally:
        store.put_conn(conn)
