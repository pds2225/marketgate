"""MG-006 contact ownership challenge API tests."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from main import app
from app.auth_deps import get_current_user
import app.routers.contact_verification as contact_router

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_challenges(monkeypatch):
    contact_router._reset_for_tests()
    monkeypatch.setenv("CONTACT_VERIFICATION_DRY_RUN", "true")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("RENDER", raising=False)
    yield
    contact_router._reset_for_tests()


def _request(channel="email", recipient="owner@example.com"):
    return client.post(
        "/v1/contact-verifications",
        json={"channel": channel, "recipient": recipient},
    )


def test_dry_run_request_masks_recipient_and_returns_preview_token():
    response = _request()
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "pending"
    assert body["previous_state"] == "not_requested"
    assert body["method"] == "email_link"
    assert body["delivery_status"] == "dry_run_preview"
    assert body["recipient_fingerprint"].startswith("sha256:")
    assert body["preview_token"]
    assert "owner@example.com" not in response.text


def test_request_then_confirm_returns_frontend_proof_contract():
    pending = _request().json()
    response = client.post(
        f"/v1/contact-verifications/{pending['challenge_id']}/confirm",
        json={"token": pending["preview_token"]},
    )
    assert response.status_code == 200
    proof = response.json()
    assert proof["state"] == "ownership_verified"
    assert proof["previous_state"] == "pending"
    assert proof["method"] == "email_link"
    assert proof["challenge_id"] == pending["challenge_id"]
    assert proof["recipient_fingerprint"] == pending["recipient_fingerprint"]
    assert proof["verified_at"]
    assert "preview_token" not in proof


def test_status_read_never_returns_preview_token():
    pending = _request().json()
    response = client.get(f"/v1/contact-verifications/{pending['challenge_id']}")
    assert response.status_code == 200
    assert "preview_token" not in response.json()


def test_wrong_token_does_not_promote_and_counts_attempt():
    pending = _request().json()
    response = client.post(
        f"/v1/contact-verifications/{pending['challenge_id']}/confirm",
        json={"token": "wrong-token"},
    )
    assert response.status_code == 400
    status = client.get(f"/v1/contact-verifications/{pending['challenge_id']}").json()
    assert status["state"] == "pending"
    assert status["attempts"] == 1


def test_fifth_wrong_token_fails_challenge():
    pending = _request().json()
    url = f"/v1/contact-verifications/{pending['challenge_id']}/confirm"
    for _ in range(5):
        response = client.post(url, json={"token": "wrong-token"})
        assert response.status_code == 400
    status = client.get(f"/v1/contact-verifications/{pending['challenge_id']}").json()
    assert status["state"] == "failed"
    assert client.post(url, json={"token": pending["preview_token"]}).status_code == 409


def test_expired_challenge_cannot_be_confirmed():
    pending = _request().json()
    contact_router._CHALLENGES[pending["challenge_id"]]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    response = client.post(
        f"/v1/contact-verifications/{pending['challenge_id']}/confirm",
        json={"token": pending["preview_token"]},
    )
    assert response.status_code == 410
    assert response.json()["detail"] == "contact_verification_expired"


def test_production_never_exposes_preview_token(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    response = _request()
    assert response.status_code == 200
    assert response.json()["delivery_status"] == "provider_required"
    assert "preview_token" not in response.json()


def test_pending_challenge_limit_and_expired_cleanup():
    challenge_ids = []
    for index in range(10):
        response = _request("email", f"owner{index}@example.com")
        assert response.status_code == 200
        challenge_ids.append(response.json()["challenge_id"])
    blocked = _request("email", "owner10@example.com")
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "too_many_pending_verifications"

    contact_router._CHALLENGES[challenge_ids[0]]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    retried = _request("email", "owner10@example.com")
    assert retried.status_code == 200
    assert contact_router._CHALLENGES[challenge_ids[0]]["state"] == "expired"


@pytest.mark.parametrize(
    ("channel", "recipient", "detail"),
    [("email", "not-email", "invalid_email"), ("sms", "123", "invalid_phone")],
)
def test_invalid_recipient_rejected(channel, recipient, detail):
    response = _request(channel, recipient)
    assert response.status_code == 422
    assert response.json()["detail"] == detail


def test_other_user_cannot_read_or_confirm_challenge():
    pending = _request().json()
    saved = app.dependency_overrides[get_current_user]
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "other-user",
        "email": "other@example.com",
        "plan": "Basic",
    }
    try:
        url = f"/v1/contact-verifications/{pending['challenge_id']}"
        assert client.get(url).status_code == 404
        assert client.post(
            f"{url}/confirm", json={"token": pending["preview_token"]}
        ).status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = saved


def test_verified_contact_can_be_revoked():
    pending = _request().json()
    url = f"/v1/contact-verifications/{pending['challenge_id']}"
    client.post(f"{url}/confirm", json={"token": pending["preview_token"]})
    response = client.post(f"{url}/revoke")
    assert response.status_code == 200
    assert response.json()["state"] == "revoked"
    assert response.json()["previous_state"] == "ownership_verified"
