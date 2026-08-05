"""인콰이어리 발송 큐 API (P0 파일럿).

사용자: 초안 생성(draft) → 검토 요청(review_required)
관리자: 승인/반려 → 큐 등록 → 발송 성공/실패 기록 → 결과(회신 등) 기록

실제 이메일 발송은 이 API가 수행하지 않는다(관리자 수동/반자동 발송 후 결과 기록).
연락처(recipient_email)가 없는 바이어는 초안 생성 자체를 422로 거부한다.
"""

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.auth_deps import get_current_user, require_admin
from app.inquiry_store import (
    create_inquiry,
    get_inquiry,
    list_inquiries,
    transition,
)
from app.services.inquiry_service import build_draft

router = APIRouter(prefix="/v1", tags=["inquiries"])

_RESULT_STATUSES = {"delivered", "bounced", "replied", "no_response"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _transition_or_400(inquiry_id: str, new_status: str, **kwargs) -> dict:
    try:
        return transition(inquiry_id, new_status, **kwargs)
    except KeyError:
        raise HTTPException(status_code=404, detail="inquiry_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ── 사용자 엔드포인트 ─────────────────────────────────────────────


@router.post("/inquiries")
def create_dispatch_draft(
    payload: Dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
):
    buyer_name = _clean(payload.get("buyer_name"))
    recipient_email = _clean(payload.get("recipient_email"))
    hs_code = _clean(payload.get("hs_code"))
    sender_company = _clean(payload.get("sender_company"))
    sender_name = _clean(payload.get("sender_name"))

    if not buyer_name:
        raise HTTPException(status_code=422, detail="buyer_name_required")
    if not recipient_email or "@" not in recipient_email:
        # 연락처 없는 바이어는 발송 요청을 만들 수 없다 (프론트 비활성화 + 서버 이중 방어)
        raise HTTPException(status_code=422, detail="contact_missing")
    if not sender_company or not sender_name:
        raise HTTPException(status_code=422, detail="sender_required")

    draft = build_draft(
        buyer_name=buyer_name,
        contact_email=recipient_email,
        hs_code=hs_code,
        sender_company=sender_company,
        sender_name=sender_name,
        message=payload.get("message", ""),
        country=payload.get("country"),
        match_relevance=payload.get("match_relevance"),
        recommendation_lines=payload.get("recommendation_lines"),
        sender_email=payload.get("sender_email", ""),
    )

    record = create_inquiry(
        user_id=user["user_id"],
        buyer_id=_clean(payload.get("buyer_id")) or buyer_name.lower(),
        buyer_name=buyer_name,
        recipient_email=recipient_email,
        hs_code=hs_code,
        sender_company=sender_company,
        sender_name=sender_name,
        message=_clean(payload.get("message")),
        country=_clean(payload.get("country")),
        sender_email=_clean(payload.get("sender_email")),
        draft_ko=draft["draft_ko"],
        draft_en=draft["draft_en"],
    )
    return record


@router.post("/inquiries/{inquiry_id}/submit")
def submit_for_review(inquiry_id: str, user: dict = Depends(get_current_user)):
    record = get_inquiry(inquiry_id)
    if record is None:
        raise HTTPException(status_code=404, detail="inquiry_not_found")
    if record.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="not_owner")
    return _transition_or_400(inquiry_id, "review_required", by=user["user_id"])


@router.get("/inquiries")
def my_inquiries(user: dict = Depends(get_current_user)):
    return {"items": list_inquiries(user_id=user["user_id"])}


# ── 관리자 엔드포인트 (403 가드 + 접근 로그) ─────────────────────


@router.get("/admin/inquiries")
def admin_list_inquiries(
    status: str | None = Query(default=None),
    admin: dict = Depends(require_admin),
):
    return {"items": list_inquiries(status=status)}


@router.post("/admin/inquiries/{inquiry_id}/approve")
def admin_approve(inquiry_id: str, admin: dict = Depends(require_admin)):
    return _transition_or_400(
        inquiry_id, "approved", by=admin["user_id"], approved_by=admin.get("email")
    )


@router.post("/admin/inquiries/{inquiry_id}/reject")
def admin_reject(
    inquiry_id: str,
    payload: Dict[str, Any] = Body(default={}),
    admin: dict = Depends(require_admin),
):
    return _transition_or_400(
        inquiry_id,
        "rejected",
        by=admin["user_id"],
        review_note=_clean(payload.get("reason")) or "반려 사유 미기재",
    )


@router.post("/admin/inquiries/{inquiry_id}/queue")
def admin_queue(inquiry_id: str, admin: dict = Depends(require_admin)):
    return _transition_or_400(inquiry_id, "queued", by=admin["user_id"])


@router.post("/admin/inquiries/{inquiry_id}/mark-sent")
def admin_mark_sent(
    inquiry_id: str,
    payload: Dict[str, Any] = Body(default={}),
    admin: dict = Depends(require_admin),
):
    return _transition_or_400(
        inquiry_id,
        "sent",
        by=admin["user_id"],
        provider_message_id=_clean(payload.get("provider_message_id")) or None,
    )


@router.post("/admin/inquiries/{inquiry_id}/mark-failed")
def admin_mark_failed(
    inquiry_id: str,
    payload: Dict[str, Any] = Body(default={}),
    admin: dict = Depends(require_admin),
):
    failure_reason = _clean(payload.get("failure_reason"))
    if not failure_reason:
        raise HTTPException(status_code=422, detail="failure_reason_required")
    return _transition_or_400(
        inquiry_id, "failed", by=admin["user_id"], failure_reason=failure_reason
    )


@router.post("/admin/inquiries/{inquiry_id}/record-result")
def admin_record_result(
    inquiry_id: str,
    payload: Dict[str, Any] = Body(default={}),
    admin: dict = Depends(require_admin),
):
    result = _clean(payload.get("result"))
    if result not in _RESULT_STATUSES:
        raise HTTPException(status_code=422, detail="invalid_result")
    return _transition_or_400(inquiry_id, result, by=admin["user_id"])
