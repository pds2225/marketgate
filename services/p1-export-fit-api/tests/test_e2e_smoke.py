"""M10/M11 — 실제 엔드포인트를 그대로 호출하는 스모크 테스트.

conftest.py가 get_current_user/get_token_payload를 목으로 덮어쓰기 때문에,
이 모듈은 오버라이드를 잠시 걷어내고 register → login → Bearer 토큰으로
진짜 인증 경로를 통과시킨다. 그러지 않으면 인증이 실제로 동작하는지는
아무것도 검증하지 못한다.

바이어 조회는 POST /v1/predict다 (GET /v1/buyers 라우트는 존재하지 않는다).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from app import auth_store, credit_store, inquiry_store, subscription_store
from app.auth_deps import get_current_user, get_token_payload


client = TestClient(app)

PREDICT_PAYLOAD = {
    "hs_code": "330499",
    "exporter_country_iso3": "KOR",
    "top_n": 5,
    "year": 2023,
}


@pytest.fixture
def real_auth(tmp_path, monkeypatch):
    """목 사용자를 걷어내고, 모든 저장소를 tmp로 격리한다."""
    saved = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_token_payload, None)
    monkeypatch.setattr(auth_store, "USERS_PATH", str(tmp_path / "users.json"))
    monkeypatch.setattr(
        auth_store, "BLACKLIST_PATH", str(tmp_path / "token_blacklist.json")
    )
    monkeypatch.setattr(credit_store, "CREDITS_PATH", str(tmp_path / "credits.json"))
    monkeypatch.setattr(
        subscription_store, "SUBSCRIPTIONS_PATH", str(tmp_path / "subscriptions.json")
    )
    monkeypatch.setattr(
        inquiry_store, "INQUIRIES_PATH", str(tmp_path / "inquiries.json")
    )
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


def test_health_is_public_and_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_requires_authentication(real_auth):
    """오버라이드를 걷어낸 상태에서 무인증 호출이 실제로 막혀야 한다."""
    r = client.post("/v1/predict", json=PREDICT_PAYLOAD)
    assert r.status_code in (401, 403), r.text


def test_full_journey_register_login_predict_inquiry(real_auth):
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    password = "sm0ke-test-pw"

    reg = client.post(
        "/v1/auth/register", json={"email": email, "password": password}
    )
    assert reg.status_code == 200, reg.text

    login = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    auth = {"Authorization": f"Bearer {login.json()['access_token']}"}

    predicted = client.post("/v1/predict", json=PREDICT_PAYLOAD, headers=auth)
    assert predicted.status_code == 200, predicted.text
    data = predicted.json()["data"]
    assert data["results"], "추천 국가가 비어 있으면 안 된다"

    items = data["buyers"]["items"]
    assert items, "실 데이터에서 바이어 후보가 나와야 한다"
    with_contact = [b for b in items if str(b.get("contact_email") or "").strip()]
    assert with_contact, "연락처 있는 바이어가 최소 1건이어야 인콰이어리로 이어진다"
    buyer = with_contact[0]

    created = client.post(
        "/v1/inquiries",
        json={
            "buyer_name": buyer["buyer_name"],
            "recipient_email": buyer["contact_email"],
            "hs_code": "330499",
            "sender_company": "MarketGate",
            "sender_name": "스모크 테스터",
        },
        headers=auth,
    )
    assert created.status_code == 200, created.text
    inquiry = created.json()
    assert inquiry["status"] == "draft"
    assert inquiry["draft_en"].strip(), "영문 초안이 비어 있으면 안 된다"

    submitted = client.post(
        f"/v1/inquiries/{inquiry['inquiry_id']}/submit", headers=auth
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "review_required"

    mine = client.get("/v1/inquiries", headers=auth)
    assert mine.status_code == 200
    assert [i["inquiry_id"] for i in mine.json()["items"]] == [inquiry["inquiry_id"]]


@pytest.mark.parametrize(
    "origin", ["http://localhost:5173", "https://marketgate.vercel.app"]
)
def test_cors_origins_include_frontend(origin):
    """프론트 출처가 실제 응답 헤더로 허용돼야 한다 (설정 문자열이 아니라 동작으로 확인)."""
    r = client.get("/health", headers={"Origin": origin})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == origin

    preflight = client.options(
        "/v1/predict",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert preflight.status_code in (200, 204)
    assert preflight.headers.get("access-control-allow-origin") == origin


def test_cors_does_not_allow_arbitrary_origin():
    r = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") != "https://evil.example.com"
