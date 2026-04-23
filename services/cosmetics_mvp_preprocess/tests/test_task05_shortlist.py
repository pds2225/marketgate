from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task05_shortlist import (  # noqa: E402
    buyer_hard_gate,
    is_ambiguous_product,
    is_expired,
    is_signal_usable,
    match_hs_or_keywords,
    normalize_hs_code,
    normalize_opportunity_record,
    opportunity_hard_gate,
    parse_date,
)


def test_normalize_opportunity_record_renames_has_contact_to_signal_usable() -> None:
    reference_date = date(2026, 4, 22)
    record = {
        "has_contact": True,
        "signal_type": "인콰이어리",
        "valid_until": "2026-06-30",
        "title": "Hydrating serum",
        "keywords_norm": "skincare | beauty",
    }

    normalized = normalize_opportunity_record(record, reference_date=reference_date)

    assert "has_contact" not in normalized
    assert normalized["signal_type"] == "inquiry"
    assert normalized["signal_usable"] is True
    assert normalized["product_name_norm"] == "Hydrating serum"


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-06-30", date(2026, 6, 30)),
        ("2026.06.30", date(2026, 6, 30)),
        ("06/30/2026", date(2026, 6, 30)),
        ("2026/06/30", date(2026, 6, 30)),
        ("", None),
        (None, None),
    ],
)
def test_parse_date_variants(value, expected) -> None:
    assert parse_date(value) == expected


def test_signal_usable_and_expiry_rules() -> None:
    reference_date = date(2026, 4, 22)

    assert is_signal_usable("inquiry", "2026-06-30", "", title="Hydrating serum", reference_date=reference_date) is True
    assert is_signal_usable("inquiry", "2026.06.30", "", title="Hydrating serum", reference_date=reference_date) is True
    assert is_signal_usable("consultation", "", "2026-04-01", title="Hydrating serum", reference_date=reference_date) is True
    assert is_signal_usable("inquiry", "2027-01-15", "", title="Hydrating serum", reference_date=reference_date) is False
    assert is_signal_usable("inquiry", "", "", title="Hydrating serum", reference_date=reference_date) is False
    assert is_signal_usable("inquiry", "2026-06-30", "", title="test", reference_date=reference_date) is False
    assert is_signal_usable("demo", "2026-06-30", "", title="Hydrating serum", reference_date=reference_date) is False

    assert is_expired("2026-06-30", "", reference_date=reference_date) is False
    assert is_expired("2026.06.30", "", reference_date=reference_date) is False
    assert is_expired("06/30/2026", "", reference_date=reference_date) is False
    assert is_expired("", "2026-04-01", reference_date=reference_date) is False
    assert is_expired("", "2025-10-01", reference_date=reference_date) is True
    assert is_expired("", "", reference_date=reference_date) is True


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", True),
        ("A1", True),
        ("1234", True),
        ("test", True),
        ("product inquiry", True),
        ("Hydrating serum", False),
        ("비타민 세럼", False),
    ],
)
def test_ambiguous_product_detection(value: str, expected: bool) -> None:
    assert is_ambiguous_product(value) is expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("3304", "3304"),
        ("3304.99", "330499"),
        ("HS330499", "330499"),
        ("3304-99", "330499"),
    ],
)
def test_normalize_hs_code_variants(raw: str, expected: str) -> None:
    assert normalize_hs_code(raw) == expected


def test_hs_priority_then_keyword_fallback() -> None:
    buyer = {
        "hs_code_norm": "3304",
        "keywords_norm": "beauty | serum",
        "title": "Buyer profile",
    }
    opportunity_exact = {
        "hs_code_norm": "3304",
        "product_name_norm": "Lip care",
        "keywords_norm": "cosmetics",
        "title": "K-Beauty inquiry",
    }
    opportunity_family = {
        "hs_code_norm": "3304.99",
        "product_name_norm": "Lip care",
        "keywords_norm": "cosmetics",
        "title": "K-Beauty inquiry",
    }
    opportunity_keyword = {
        "hs_code_norm": "",
        "product_name_norm": "Skincare serum",
        "keywords_norm": "serum | skincare",
        "title": "Inquiry",
    }
    opportunity_mismatch = {
        "hs_code_norm": "300490",
        "product_name_norm": "Industrial parts",
        "keywords_norm": "metal",
        "title": "Parts",
    }

    exact = match_hs_or_keywords(buyer, opportunity_exact)
    family = match_hs_or_keywords(buyer, opportunity_family)
    keyword = match_hs_or_keywords(buyer, opportunity_keyword)
    mismatch = match_hs_or_keywords(buyer, opportunity_mismatch)

    assert exact["matched"] is True
    assert exact["match_mode"] == "hs_exact"
    assert family["matched"] is True
    assert family["match_mode"] in {"hs_prefix_4", "hs_prefix_2"}
    assert keyword["matched"] is True
    assert keyword["match_mode"] == "keyword"
    assert mismatch["matched"] is False
    assert mismatch["reason"] == "hs_mismatch"


def test_keyword_false_positive_guard() -> None:
    buyer = {
        "keywords_norm": "skin | care | beauty",
        "title": "Buyer profile",
    }
    opportunity = {
        "keywords_norm": "skin care | beauty",
        "title": "General item",
    }

    result = match_hs_or_keywords(buyer, opportunity)

    assert result["matched"] is False
    assert result["reason"] == "keyword_mismatch"
    assert result["matched_terms"] == []


def test_buyer_hard_gate_returns_expected_gate_reasons() -> None:
    buyer = {
        "country_norm": "베트남",
        "hs_code_norm": "330499",
        "keywords_norm": "beauty | skincare",
        "capacity": "50",
    }

    result = buyer_hard_gate(
        buyer,
        target_country_norm="미국",
        target_hs_code_norm="300490",
        target_keywords_norm="industrial | parts",
        banned_countries={"베트남"},
        required_capacity=100,
    )

    assert result["passed"] is False
    assert result["gate_reason"] == [
        "country_mismatch",
        "banned_country",
        "hs_mismatch",
        "capacity_fail",
    ]
    assert "cert_missing" not in result["gate_reason"]
    assert "contact_missing" not in result["gate_reason"]


def test_opportunity_hard_gate_returns_expected_gate_reasons() -> None:
    reference_date = date(2026, 4, 22)
    opportunity = {
        "signal_type": "demo",
        "valid_until": "",
        "created_at": "",
        "title": "product",
    }

    result = opportunity_hard_gate(opportunity, reference_date=reference_date)

    assert result["passed"] is False
    assert result["gate_reason"] == [
        "signal_type_invalid",
        "expired",
        "ambiguous_product",
    ]
    assert result["signal_usable"] is False
    assert result["expired"] is True
