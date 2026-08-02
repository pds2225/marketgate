from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


UNKNOWN = "Unknown"

# 한글 국가명 → 영문 (영문 초안용). buyer_shortlist.ISO3_TO_TARGET_COUNTRY의 값 집합과 맞춘다.
_COUNTRY_KO_TO_EN = {
    "호주": "Australia",
    "브라질": "Brazil",
    "캐나다": "Canada",
    "중국": "China",
    "독일": "Germany",
    "프랑스": "France",
    "영국": "United Kingdom",
    "홍콩": "Hong Kong",
    "인도네시아": "Indonesia",
    "인도": "India",
    "일본": "Japan",
    "멕시코": "Mexico",
    "말레이시아": "Malaysia",
    "네덜란드": "Netherlands",
    "필리핀": "Philippines",
    "싱가포르": "Singapore",
    "태국": "Thailand",
    "대만": "Taiwan",
    "미국": "United States",
    "베트남": "Vietnam",
}


def _country_en(country: str) -> str:
    """영문 초안에 넣을 국가명. 영문(ASCII)이면 그대로, 한글이면 매핑, 둘 다 아니면 빈 문자열."""
    text = country.strip()
    if not text:
        return ""
    if text.isascii():
        return text
    return _COUNTRY_KO_TO_EN.get(text, "")

# B6 — 매칭 강도별 개인화 사유 문구 (자사 원작성, 발송·저장 없음)
_RELEVANCE_VALUES = {"strong", "weak", "none"}
_RELEVANCE_REASON_EN = {
    "strong": "your company is a strong match for this product category based on our buyer-fit analysis",
    "weak": "your company shows relevant buyer-fit signals for this product category",
    "none": "we see a potential fit for this product category",
}
_RELEVANCE_REASON_KO = {
    "strong": "당사 바이어 적합성 분석 결과 귀사는 본 품목군에 강하게 부합합니다",
    "weak": "당사 분석 결과 귀사는 본 품목군과 관련된 적합 신호를 보입니다",
    "none": "본 품목군에서 잠재적 적합성이 확인되었습니다",
}


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return text or UNKNOWN


def _norm_relevance(value: Any) -> str:
    """match_relevance 입력을 strong/weak/none 로 정규화. 그 외/빈값은 ""(미지정)."""
    text = str(value or "").strip().lower()
    return text if text in _RELEVANCE_VALUES else ""


def _clean_lines(value: Any) -> list[str]:
    """recommendation_lines(문자열 또는 리스트)를 공백 제거한 문자열 리스트로 정규화."""
    if not value:
        return []
    items = [value] if isinstance(value, str) else list(value)
    return [str(x).strip() for x in items if str(x or "").strip()]


def _build_proposal_en(country: str, relevance: str, rec_lines: list[str]) -> str:
    reason = _RELEVANCE_REASON_EN[relevance or "none"]
    header = "Why this opportunity fits your team"
    if country:
        header += f" in {country}"
    lines = [f"{header}: {reason}."]
    lines.extend(f"- {line}" for line in rec_lines)
    tail = "We would be glad to tailor product specifications, pricing, and MOQ"
    tail += f" for the {country} market." if country else "."
    return "\n".join(lines) + "\n" + tail + "\n\n"


def _build_proposal_ko(country: str, relevance: str, rec_lines: list[str]) -> str:
    reason = _RELEVANCE_REASON_KO[relevance or "none"]
    header = "이 거래가 귀사에 적합한 이유"
    if country:
        header += f" ({country})"
    lines = [f"{header}: {reason}."]
    lines.extend(f"- {line}" for line in rec_lines)
    if country:
        tail = f"제품 사양과 가격, 최소주문수량(MOQ)을 {country} 시장에 맞춰 제안드릴 수 있습니다."
    else:
        tail = "제품 사양과 가격, 최소주문수량(MOQ)을 맞춤 제안드릴 수 있습니다."
    return "\n".join(lines) + "\n" + tail + "\n\n"


def build_draft(
    *,
    buyer_name: Any,
    contact_email: Any,
    hs_code: Any,
    sender_company: Any,
    sender_name: Any,
    message: Any = "",
    country: Any = None,
    match_relevance: Any = None,
    recommendation_lines: Any = None,
    sender_email: Any = "",
) -> dict[str, Any]:
    buyer = _clean(buyer_name)
    email = _clean(contact_email)
    hs = _clean(hs_code)
    company = _clean(sender_company)
    sender = _clean(sender_name)
    sender_contact = _clean(sender_email)
    user_note = str(message or "").strip()
    # fallback 문구는 초안 언어에 맞춰 분리 (사용자가 직접 쓴 메시지는 양쪽에 그대로)
    note_ko = user_note or "추가 자료는 요청 시 공유드리겠습니다."
    note_en = user_note or "Additional details can be shared upon request."
    inquiry_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # B6 개인화 입력(전부 미전달이면 기존 draft와 바이트 단위 동일 = 회귀 0)
    country_raw = str(country or "").strip()
    country_en = _country_en(country_raw)
    relevance = _norm_relevance(match_relevance)
    rec_lines = _clean_lines(recommendation_lines)[:3]
    personalized = bool(country_raw or relevance or rec_lines)

    proposal_en = _build_proposal_en(country_en, relevance, rec_lines) if personalized else ""
    proposal_ko = _build_proposal_ko(country_raw, relevance, rec_lines) if personalized else ""

    # 회신 받을 연락처는 '발신자' 연락처다. 수신자(바이어) 이메일을 본문에 넣지 않는다.
    contact_line_ko = f"연락처: {sender_contact}" if sender_contact and sender_contact != UNKNOWN else ""
    contact_line_en = f"Contact: {sender_contact}" if sender_contact and sender_contact != UNKNOWN else ""

    draft_ko = (
        f"안녕하세요, {buyer} 담당자님.\n\n"
        f"{company}의 {sender}입니다. HS 코드 {hs} 관련 제품 공급 가능성을 논의하고자 연락드립니다.\n"
        f"{note_ko}\n\n"
        f"{proposal_ko}"
        f"검토 가능하시면 회신 부탁드립니다."
        + (f"\n{contact_line_ko}" if contact_line_ko else "")
    )
    draft_en = (
        f"Dear {buyer},\n\n"
        f"My name is {sender} from {company}. We are reaching out to discuss a potential supply opportunity "
        f"for products under HS code {hs}.\n"
        f"{note_en}\n\n"
        f"{proposal_en}"
        f"Please let us know if you are open to reviewing this inquiry."
        + (f"\n{contact_line_en}" if contact_line_en else "")
    )

    return {
        "inquiry_id": inquiry_id,
        "buyer_name": buyer,
        "contact_email": email,
        "hs_code": hs,
        "sender_company": company,
        "sender_name": sender,
        "message": user_note,
        "sender_email": sender_contact if sender_contact != UNKNOWN else "",
        "draft_ko": draft_ko,
        "draft_en": draft_en,
        "created_at": created_at,
        "status": "draft_ready",
        # B6 가산 필드 (additive — 기존 키 의미 불변)
        "personalized": personalized,
        "country": country_raw or None,
        "match_relevance": relevance or None,
    }
