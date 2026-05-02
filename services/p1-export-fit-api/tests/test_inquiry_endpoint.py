from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_post_inquiry_returns_draft_ready() -> None:
    response = client.post(
        "/v1/inquiry",
        json={
            "buyer_name": "Serum Lab",
            "contact_email": "buyer@example.com",
            "hs_code": "330499",
            "sender_company": "MarketGate",
            "sender_name": "Kim",
            "message": "We can supply skincare products.",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "draft_ready"
    assert result["inquiry_id"]
    assert result["draft_ko"]
    assert result["draft_en"]
    assert "Serum Lab" in result["draft_ko"]
    assert "MarketGate" in result["draft_en"]
    assert "330499" in result["draft_ko"]


def test_post_inquiry_omitting_message_defaults() -> None:
    response = client.post(
        "/v1/inquiry",
        json={
            "buyer_name": "Test Buyer",
            "contact_email": "test@test.com",
            "hs_code": "854231",
            "sender_company": "TestCo",
            "sender_name": "Lee",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "draft_ready"
    assert "Additional details can be shared upon request." in result["draft_en"]


def test_post_inquiry_blank_values_fallback() -> None:
    response = client.post(
        "/v1/inquiry",
        json={
            "buyer_name": "",
            "contact_email": "",
            "hs_code": "",
            "sender_company": "",
            "sender_name": "",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "draft_ready"
    assert "Unknown" in result["draft_ko"]
    assert "Unknown" in result["draft_en"]
