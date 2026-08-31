"""인콰이어리 발송 큐 저장소 (P0 파일럿).

상태 흐름:
    draft → review_required → approved → queued → sent / failed
    sent  → delivered / bounced / replied / no_response

- 실제 이메일 발송은 하지 않는다. 관리자가 수동/반자동 발송 후 결과를 기록한다.
- 과금(credit_transaction_id)은 이번 P0 범위에서 제외 — 항상 None으로 저장만 한다.
- 다른 *_store.py 와 동일한 JSON 파일 + threading.Lock 패턴을 따른다.
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone

INQUIRIES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "inquiries.json")

_lock = threading.Lock()

# 허용되는 상태 전이 (이 표에 없는 전이는 ValueError)
STATUS_FLOW: dict[str, set[str]] = {
    "draft": {"review_required"},
    "review_required": {"approved", "rejected"},
    "approved": {"queued"},
    "queued": {"sent", "failed"},
    "sent": {"delivered", "bounced", "replied", "no_response"},
    "delivered": {"replied", "no_response"},
    "rejected": set(),
    "failed": set(),
    "bounced": set(),
    "replied": set(),
    "no_response": set(),
}

ALL_STATUSES = set(STATUS_FLOW.keys())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    try:
        with open(INQUIRIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(INQUIRIES_PATH), exist_ok=True)
    with open(INQUIRIES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_inquiry(
    *,
    user_id: str,
    buyer_id: str,
    buyer_name: str,
    recipient_email: str,
    hs_code: str,
    sender_company: str,
    sender_name: str,
    message: str = "",
    country: str = "",
    sender_email: str = "",
    draft_ko: str = "",
    draft_en: str = "",
) -> dict:
    now = _now()
    record = {
        "inquiry_id": str(uuid.uuid4()),
        "user_id": user_id,
        "buyer_id": buyer_id,
        "buyer_name": buyer_name,
        "sender_company_id": sender_company,
        "sender_name": sender_name,
        "recipient_email": recipient_email,
        "hs_code": hs_code,
        "country": country,
        "message": message,
        "sender_email": sender_email,
        "draft_ko": draft_ko,
        "draft_en": draft_en,
        "status": "draft",
        "approved_by": None,
        "review_note": None,
        "delivery_provider": None,
        "provider_message_id": None,
        "sent_at": None,
        "replied_at": None,
        "failure_reason": None,
        # 과금은 P0 범위 제외 — 필드만 확보해 두고 항상 None
        "credit_transaction_id": None,
        "created_at": now,
        "updated_at": now,
        "history": [{"status": "draft", "at": now, "by": user_id}],
    }
    with _lock:
        data = _load()
        data[record["inquiry_id"]] = record
        _save(data)
    return record


def get_inquiry(inquiry_id: str) -> dict | None:
    return _load().get(inquiry_id)


def list_inquiries(user_id: str | None = None, status: str | None = None) -> list[dict]:
    items = list(_load().values())
    if user_id is not None:
        items = [item for item in items if item.get("user_id") == user_id]
    if status is not None:
        items = [item for item in items if item.get("status") == status]
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return items


def delete_user_inquiries(user_id: str) -> int:
    """Remove only inquiries owned by one isolated E2E user."""
    with _lock:
        data = _load()
        inquiry_ids = [
            inquiry_id
            for inquiry_id, item in data.items()
            if item.get("user_id") == user_id
        ]
        for inquiry_id in inquiry_ids:
            del data[inquiry_id]
        if inquiry_ids:
            _save(data)
        return len(inquiry_ids)


def transition(
    inquiry_id: str,
    new_status: str,
    *,
    by: str,
    approved_by: str | None = None,
    review_note: str | None = None,
    delivery_provider: str | None = None,
    provider_message_id: str | None = None,
    failure_reason: str | None = None,
) -> dict:
    """상태 전이. 허용되지 않은 전이는 ValueError."""
    if new_status not in ALL_STATUSES:
        raise ValueError(f"unknown_status:{new_status}")
    with _lock:
        data = _load()
        record = data.get(inquiry_id)
        if record is None:
            raise KeyError("inquiry_not_found")
        current = record.get("status", "draft")
        if new_status not in STATUS_FLOW.get(current, set()):
            raise ValueError(f"invalid_transition:{current}->{new_status}")

        now = _now()
        record["status"] = new_status
        record["updated_at"] = now
        if approved_by is not None:
            record["approved_by"] = approved_by
        if review_note is not None:
            record["review_note"] = review_note
        if delivery_provider is not None:
            record["delivery_provider"] = delivery_provider
        if provider_message_id is not None:
            record["provider_message_id"] = provider_message_id
        if failure_reason is not None:
            record["failure_reason"] = failure_reason
        if new_status == "sent":
            record["sent_at"] = now
        if new_status == "replied":
            record["replied_at"] = now
        record.setdefault("history", []).append({"status": new_status, "at": now, "by": by})
        _save(data)
    return record
