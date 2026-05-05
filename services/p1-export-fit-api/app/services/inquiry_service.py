from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


UNKNOWN = "Unknown"


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return text or UNKNOWN


def build_draft(
    *,
    buyer_name: Any,
    contact_email: Any,
    hs_code: Any,
    sender_company: Any,
    sender_name: Any,
    message: Any = "",
) -> dict[str, str]:
    buyer = _clean(buyer_name)
    email = _clean(contact_email)
    hs = _clean(hs_code)
    company = _clean(sender_company)
    sender = _clean(sender_name)
    note = _clean(message) if str(message or "").strip() else "Additional details can be shared upon request."
    inquiry_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    draft_ko = (
        f"안녕하세요, {buyer} 담당자님.\n\n"
        f"{company}의 {sender}입니다. HS 코드 {hs} 관련 제품 공급 가능성을 논의하고자 연락드립니다.\n"
        f"{note}\n\n"
        f"검토 가능하시면 회신 부탁드립니다.\n"
        f"연락처: {email}"
    )
    draft_en = (
        f"Dear {buyer},\n\n"
        f"My name is {sender} from {company}. We are reaching out to discuss a potential supply opportunity "
        f"for products under HS code {hs}.\n"
        f"{note}\n\n"
        f"Please let us know if you are open to reviewing this inquiry.\n"
        f"Contact: {email}"
    )

    return {
        "inquiry_id": inquiry_id,
        "buyer_name": buyer,
        "contact_email": email,
        "hs_code": hs,
        "sender_company": company,
        "sender_name": sender,
        "message": note,
        "draft_ko": draft_ko,
        "draft_en": draft_en,
        "created_at": created_at,
        "status": "draft_ready",
    }
