"""MG-007 safe queued → sent dry-run integration tests."""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.auth_deps import require_admin
import app.inquiry_store as inquiry_store

client = TestClient(app)

VALID_PAYLOAD = {
    "buyer_name": "Acme Buyer",
    "recipient_email": "buyer@example.com",
    "hs_code": "330499",
    "sender_company": "MarketGate Seller",
    "sender_name": "Seller User",
}


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(inquiry_store, "INQUIRIES_PATH", str(tmp_path / "inquiries.json"))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("INQUIRY_DELIVERY_DRY_RUN", "true")
    monkeypatch.delenv("RENDER", raising=False)
    saved = app.dependency_overrides.get(require_admin)
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-user",
        "email": "admin@example.com",
        "role": "admin",
    }
    yield
    if saved is None:
        app.dependency_overrides.pop(require_admin, None)
    else:
        app.dependency_overrides[require_admin] = saved


def _create_queued_inquiry():
    created = client.post("/v1/inquiries", json=VALID_PAYLOAD)
    assert created.status_code == 200
    inquiry_id = created.json()["inquiry_id"]
    assert client.post(f"/v1/inquiries/{inquiry_id}/submit").status_code == 200
    assert client.post(f"/v1/admin/inquiries/{inquiry_id}/approve").status_code == 200
    assert client.post(f"/v1/admin/inquiries/{inquiry_id}/queue").status_code == 200
    return inquiry_id


def test_dry_run_dispatch_moves_queued_to_sent_and_customer_can_read_status():
    inquiry_id = _create_queued_inquiry()
    response = client.post(f"/v1/admin/inquiries/{inquiry_id}/dispatch-dry-run")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sent"
    assert body["provider_message_id"].startswith("dryrun:")
    assert body["sent_at"]
    assert [entry["status"] for entry in body["history"]] == [
        "draft",
        "review_required",
        "approved",
        "queued",
        "sent",
    ]

    mine = client.get("/v1/inquiries")
    assert mine.status_code == 200
    assert mine.json()["items"][0]["status"] == "sent"


def test_production_blocks_dry_run_dispatch(monkeypatch):
    inquiry_id = _create_queued_inquiry()
    monkeypatch.setenv("APP_ENV", "production")
    response = client.post(f"/v1/admin/inquiries/{inquiry_id}/dispatch-dry-run")
    assert response.status_code == 409
    assert response.json()["detail"] == "inquiry_delivery_provider_unavailable"
    assert client.get("/v1/inquiries").json()["items"][0]["status"] == "queued"


def test_render_blocks_dry_run_even_when_flag_is_enabled(monkeypatch):
    inquiry_id = _create_queued_inquiry()
    monkeypatch.setenv("RENDER", "true")
    response = client.post(f"/v1/admin/inquiries/{inquiry_id}/dispatch-dry-run")
    assert response.status_code == 409


def test_unqueued_inquiry_is_rejected_without_state_change():
    created = client.post("/v1/inquiries", json=VALID_PAYLOAD)
    inquiry_id = created.json()["inquiry_id"]
    response = client.post(f"/v1/admin/inquiries/{inquiry_id}/dispatch-dry-run")
    assert response.status_code == 422
    assert response.json()["detail"] == "inquiry_not_queued"
    assert client.get("/v1/inquiries").json()["items"][0]["status"] == "draft"


def test_unknown_inquiry_returns_404():
    response = client.post("/v1/admin/inquiries/missing/dispatch-dry-run")
    assert response.status_code == 404

