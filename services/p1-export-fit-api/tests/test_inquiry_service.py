from __future__ import annotations

from uuid import UUID

from app.services.inquiry_service import build_draft


def test_build_draft_returns_required_fields() -> None:
    result = build_draft(
        buyer_name="Serum Lab",
        contact_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate",
        sender_name="Kim",
        message="We can supply skincare products.",
    )

    UUID(result["inquiry_id"])
    assert result["created_at"]
    assert result["draft_ko"]
    assert result["draft_en"]
    assert result["status"] == "draft_ready"


def test_inquiry_template_substitution() -> None:
    result = build_draft(
        buyer_name="Serum Lab",
        contact_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate",
        sender_name="Kim",
        message="Custom note",
    )

    assert "Serum Lab" in result["draft_ko"]
    assert "330499" in result["draft_ko"]
    assert "MarketGate" in result["draft_ko"]
    assert "Kim" in result["draft_ko"]
    assert "Custom note" in result["draft_ko"]
    assert "Serum Lab" in result["draft_en"]
    assert "330499" in result["draft_en"]
    assert "MarketGate" in result["draft_en"]
    assert "Kim" in result["draft_en"]
    assert "Custom note" in result["draft_en"]


def test_inquiry_template_falls_back_unknown_for_blank_values() -> None:
    result = build_draft(
        buyer_name="",
        contact_email="",
        hs_code="",
        sender_company="",
        sender_name="",
    )

    assert result["contact_email"] == "Unknown"
    assert "Unknown" in result["draft_ko"]
    assert "Unknown" in result["draft_en"]
