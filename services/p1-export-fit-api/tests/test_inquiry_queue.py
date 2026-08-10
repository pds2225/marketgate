"""인콰이어리 발송 큐 (P0) — 상태머신·연락처 검증·발송 결과 저장 테스트."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
import app.inquiry_store as inquiry_store
import app.auth_deps as auth_deps

client = TestClient(app)

VALID_PAYLOAD = {
    "buyer_name": "acme trading gmbh",
    "recipient_email": "buyer@acme-trading.de",
    "hs_code": "330499",
    "sender_company": "(주)마켓게이트",
    "sender_name": "홍길동",
    "message": "K-뷰티 스킨케어 제품 공급 제안",
    "country": "germany",
}


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(inquiry_store, "INQUIRIES_PATH", str(tmp_path / "inquiries.json"))
    monkeypatch.setattr(
        auth_deps, "ADMIN_ACCESS_LOG_PATH", str(tmp_path / "admin_access_log.json")
    )
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    yield


@pytest.fixture
def as_admin(monkeypatch):
    # conftest 의 mock 사용자(test@example.com)를 관리자 명단에 올린다.
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    yield


def _create_draft() -> dict:
    res = client.post("/v1/inquiries", json=VALID_PAYLOAD)
    assert res.status_code == 200, res.text
    return res.json()


def test_create_without_contact_returns_422():
    payload = dict(VALID_PAYLOAD)
    payload["recipient_email"] = ""
    res = client.post("/v1/inquiries", json=payload)
    assert res.status_code == 422
    assert res.json()["detail"] == "contact_missing"


def test_create_with_invalid_email_returns_422():
    payload = dict(VALID_PAYLOAD)
    payload["recipient_email"] = "no-at-sign"
    res = client.post("/v1/inquiries", json=payload)
    assert res.status_code == 422
    assert res.json()["detail"] == "contact_missing"


def test_create_returns_draft_with_required_fields():
    record = _create_draft()
    assert record["status"] == "draft"
    assert record["recipient_email"] == VALID_PAYLOAD["recipient_email"]
    assert record["buyer_id"] == VALID_PAYLOAD["buyer_name"].lower()
    assert record["sender_company_id"] == VALID_PAYLOAD["sender_company"]
    assert record["approved_by"] is None
    assert record["provider_message_id"] is None
    assert record["sent_at"] is None
    assert record["replied_at"] is None
    assert record["failure_reason"] is None
    assert record["credit_transaction_id"] is None
    assert record["draft_ko"] and record["draft_en"]


def test_happy_path_draft_to_sent_to_replied(as_admin):
    record = _create_draft()
    inquiry_id = record["inquiry_id"]

    res = client.post(f"/v1/inquiries/{inquiry_id}/submit")
    assert res.status_code == 200
    assert res.json()["status"] == "review_required"

    res = client.post(f"/v1/admin/inquiries/{inquiry_id}/approve")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "test@example.com"

    res = client.post(f"/v1/admin/inquiries/{inquiry_id}/queue")
    assert res.status_code == 200
    assert res.json()["status"] == "queued"

    res = client.post(
        f"/v1/admin/inquiries/{inquiry_id}/mark-sent",
        json={"provider_message_id": "smtp-manual-0001"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "sent"
    assert body["sent_at"] is not None
    assert body["provider_message_id"] == "smtp-manual-0001"

    res = client.post(
        f"/v1/admin/inquiries/{inquiry_id}/record-result", json={"result": "replied"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "replied"
    assert body["replied_at"] is not None

    statuses = [h["status"] for h in body["history"]]
    assert statuses == ["draft", "review_required", "approved", "queued", "sent", "replied"]


def test_failed_dispatch_stores_failure_reason(as_admin):
    record = _create_draft()
    inquiry_id = record["inquiry_id"]
    client.post(f"/v1/inquiries/{inquiry_id}/submit")
    client.post(f"/v1/admin/inquiries/{inquiry_id}/approve")
    client.post(f"/v1/admin/inquiries/{inquiry_id}/queue")

    res = client.post(f"/v1/admin/inquiries/{inquiry_id}/mark-failed", json={})
    assert res.status_code == 422
    assert res.json()["detail"] == "failure_reason_required"

    res = client.post(
        f"/v1/admin/inquiries/{inquiry_id}/mark-failed",
        json={"failure_reason": "SMTP 5.1.1 수신자 주소 없음"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "failed"
    assert body["failure_reason"] == "SMTP 5.1.1 수신자 주소 없음"

    stored = inquiry_store.get_inquiry(inquiry_id)
    assert stored["status"] == "failed"
    assert stored["failure_reason"] == "SMTP 5.1.1 수신자 주소 없음"


def test_reject_stores_review_note(as_admin):
    record = _create_draft()
    inquiry_id = record["inquiry_id"]
    client.post(f"/v1/inquiries/{inquiry_id}/submit")

    res = client.post(
        f"/v1/admin/inquiries/{inquiry_id}/reject", json={"reason": "수신자 확인 필요"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "rejected"
    assert body["review_note"] == "수신자 확인 필요"


def test_invalid_transition_returns_409(as_admin):
    record = _create_draft()
    inquiry_id = record["inquiry_id"]
    # draft 상태에서 곧바로 approve 는 불가 (review_required 를 거쳐야 함)
    res = client.post(f"/v1/admin/inquiries/{inquiry_id}/approve")
    assert res.status_code == 409
    assert "invalid_transition" in res.json()["detail"]


def test_my_inquiries_lists_own_records():
    record = _create_draft()
    res = client.get("/v1/inquiries")
    assert res.status_code == 200
    ids = [item["inquiry_id"] for item in res.json()["items"]]
    assert record["inquiry_id"] in ids
