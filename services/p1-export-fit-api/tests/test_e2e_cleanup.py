from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth_store, credit_store, inquiry_store, subscription_store
from app.routers import e2e as e2e_router
from main import app as production_app


TOKEN = "e2e-test-token-that-is-at-least-32-characters"
EMAIL = "e2e-cleanup-test@example.com"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(e2e_router.router)
    return TestClient(app)


def _isolate_stores(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(auth_store, "USERS_PATH", str(tmp_path / "users.json"))
    monkeypatch.setattr(
        auth_store, "BLACKLIST_PATH", str(tmp_path / "token_blacklist.json")
    )
    monkeypatch.setattr(credit_store, "CREDITS_PATH", str(tmp_path / "credits.json"))
    monkeypatch.setattr(
        subscription_store,
        "SUBSCRIPTIONS_PATH",
        str(tmp_path / "subscriptions.json"),
    )
    monkeypatch.setattr(
        inquiry_store, "INQUIRIES_PATH", str(tmp_path / "inquiries.json")
    )


def test_production_app_does_not_register_e2e_routes():
    paths = {
        path
        for route in production_app.routes
        if (path := getattr(route, "path", None)) is not None
    }
    assert "/v1/e2e/identity" not in paths
    assert "/v1/e2e/cleanup" not in paths


def test_e2e_routes_fail_closed_outside_e2e(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    response = _client().get("/v1/e2e/identity")
    assert response.status_code == 404


def test_cleanup_requires_configured_valid_token(monkeypatch):
    monkeypatch.setenv("APP_ENV", "e2e")
    monkeypatch.delenv("E2E_ADMIN_TOKEN", raising=False)
    unconfigured = _client().post("/v1/e2e/cleanup", json={"email": EMAIL})
    assert unconfigured.status_code == 503

    monkeypatch.setenv("E2E_ADMIN_TOKEN", TOKEN)
    denied = _client().post(
        "/v1/e2e/cleanup",
        json={"email": EMAIL},
        headers={"X-E2E-Admin-Token": "wrong-token"},
    )
    assert denied.status_code == 401


def test_cleanup_rejects_non_e2e_email(monkeypatch):
    monkeypatch.setenv("APP_ENV", "e2e")
    monkeypatch.setenv("E2E_ADMIN_TOKEN", TOKEN)
    response = _client().post(
        "/v1/e2e/cleanup",
        json={"email": "real-user@example.com"},
        headers={"X-E2E-Admin-Token": TOKEN},
    )
    assert response.status_code == 400


def test_cleanup_removes_only_generated_user_data(tmp_path, monkeypatch):
    _isolate_stores(tmp_path, monkeypatch)
    monkeypatch.setenv("APP_ENV", "e2e")
    monkeypatch.setenv("E2E_ADMIN_TOKEN", TOKEN)

    user = auth_store.create_user(EMAIL, "not-used-by-this-test")
    user_id = user["user_id"]
    credit_store.deduct(user_id, amount=5, action="contact_unlock")
    subscription_store.change_plan(user_id, "Pro")
    inquiry_store.create_inquiry(
        user_id=user_id,
        buyer_id="buyer-1",
        buyer_name="Synthetic Buyer",
        recipient_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate E2E",
        sender_name="E2E",
    )

    response = _client().post(
        "/v1/e2e/cleanup",
        json={"email": EMAIL, "user_id": user_id},
        headers={"X-E2E-Admin-Token": TOKEN},
    )
    assert response.status_code == 200
    assert response.json() == {
        "deleted": True,
        "email": EMAIL,
        "inquiries_deleted": 1,
        "credit_deleted": True,
        "subscription_deleted": True,
    }
    assert auth_store.find_user_by_email(EMAIL) is None
    assert user_id not in credit_store._load()
    assert user_id not in subscription_store._load()
    assert inquiry_store.list_inquiries(user_id=user_id) == []
