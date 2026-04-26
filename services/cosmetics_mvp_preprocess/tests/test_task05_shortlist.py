from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task05_shortlist import (  # noqa: E402
    buyer_hard_gate,
    enrich_text_signal_fields,
    infer_hs_code_with_score,
    is_ambiguous_product,
    is_expired,
    is_signal_usable,
    match_hs_or_keywords,
    normalize_hs_code,
    normalize_opportunity_record,
    opportunity_hard_gate,
    parse_date,
)
from shortlist_service import _select_opportunity  # noqa: E402


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
    assert normalized["hs_code_norm"] == "330499"


def test_normalize_opportunity_record_infers_hs_from_cosmetics_text() -> None:
    normalized = normalize_opportunity_record(
        {
            "title": "Hydrating ampoule mask",
            "keywords_norm": "ampoule | serum | beauty",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
        },
        reference_date=date(2026, 4, 22),
    )

    assert normalized["hs_code_norm"] == "330499"


def test_infer_hs_code_with_score_supports_korean_and_english_keywords() -> None:
    result = infer_hs_code_with_score(
        "Hydrating toner",
        "수분 토너 선크림 세트",
        "skincare | toner | sunscreen",
    )

    assert result["hs_code"] == "330499"
    assert result["match_score"] >= 0.7
    assert result["matched_keywords"]


def test_enrich_text_signal_fields_builds_keywords_from_title_when_keywords_empty() -> None:
    enriched = enrich_text_signal_fields(
        {
            "keywords_norm": "",
            "title": "skincare serum",
            "product_name_norm": "",
            "description": "",
        }
    )

    inferred = infer_hs_code_with_score(
        enriched.get("keywords_norm"),
        enriched.get("product_name_norm"),
        enriched.get("title"),
    )

    assert "skincare serum" in enriched["keywords_norm"]
    assert inferred["hs_code"] == "330499"


def test_enrich_text_signal_fields_uses_description_when_product_name_missing() -> None:
    enriched = enrich_text_signal_fields(
        {
            "keywords_norm": "",
            "title": "",
            "product_name_norm": "",
            "description": "기초화장품 세럼",
        }
    )

    inferred = infer_hs_code_with_score(
        enriched.get("keywords_norm"),
        enriched.get("product_name_norm"),
        enriched.get("description"),
    )

    assert enriched["description"] == "기초화장품 세럼"
    assert inferred["hs_code"] == "330499"


def test_infer_hs_code_with_score_does_not_pass_empty_text() -> None:
    result = infer_hs_code_with_score("", "", None)

    assert result["hs_code"] == ""
    assert result["match_score"] == 0.0


def test_infer_hs_code_with_score_does_not_misclassify_non_cosmetics() -> None:
    result = infer_hs_code_with_score(
        "industrial valve",
        "metal parts",
        "factory machinery spare part",
    )

    assert result["hs_code"] == ""


@pytest.mark.parametrize(
    "value",
    [
        "beauty",
        "cosmetic",
        "beauty cosmetic",
        "Beauty Equipment",
        "skin device",
        "medical cosmetics",
        "medicine_&_medical_supplies",
        "medical supplies",
    ],
)
def test_infer_hs_code_with_score_blocks_weak_or_medical_terms(value: str) -> None:
    result = infer_hs_code_with_score(value)

    assert result["hs_code"] == ""
    assert result["match_score"] == 0.0


@pytest.mark.parametrize(
    ("value", "expected_keyword"),
    [
        ("Anti Wrinkle Micro Patch", "micro patch"),
        ("skincare serum", "serum"),
        ("기초화장품 세럼", "기초화장품"),
    ],
)
def test_infer_hs_code_with_score_keeps_strong_cosmetics_terms(
    value: str,
    expected_keyword: str,
) -> None:
    result = infer_hs_code_with_score(value)

    assert result["hs_code"] == "330499"
    assert expected_keyword in result["matched_keywords"]


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
    assert keyword["match_mode"] in {"keyword", "hs_inferred", "hs_inferred_prefix_4"}
    assert mismatch["matched"] is False
    assert mismatch["reason"] == "hs_mismatch"


def test_match_hs_or_keywords_does_not_bypass_medicine_hs_with_cosmetics_inference() -> None:
    buyer = {
        "hs_code_norm": "330499",
        "keywords_norm": "skincare | serum",
        "title": "Cosmetics buyer",
    }
    opportunity = {
        "hs_code_norm": "300490",
        "keywords_norm": "medicine",
        "product_name_norm": "medicine",
        "title": "medicine",
    }

    result = match_hs_or_keywords(buyer, opportunity)

    assert result["matched"] is False
    assert result["reason"] == "hs_mismatch"


def test_match_hs_or_keywords_uses_inferred_hs_when_buyer_hs_missing() -> None:
    buyer = {
        "hs_code_norm": "",
        "normalized_name": "Daily Sun Cream",
        "keywords_norm": "sun cream | sunscreen | skincare",
        "title": "Daily Sun Cream",
    }
    opportunity = {
        "hs_code_norm": "330499",
        "product_name_norm": "UV Sunscreen",
        "keywords_norm": "sunscreen | skincare",
        "title": "Cosmetics inquiry",
    }

    result = match_hs_or_keywords(buyer, opportunity)

    assert result["matched"] is True
    assert result["match_mode"] == "hs_inferred"
    assert result["hs_inference_score"] >= 0.6
    assert result["buyer_hs_code_norm"] == "330499"


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


def test_select_opportunity_prioritizes_target_hs_over_more_recent_generic_item() -> None:
    rows = [
        {
            "title": "Genuine Matcha Powder",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": "genuine matcha powder",
            "valid_until": "2026-05-12",
            "signal_type": "inquiry",
        },
        {
            "title": "Cellcurin Hair Ampoule",
            "country_norm": "미국",
            "hs_code_norm": "330499",
            "keywords_norm": "cellcurin hair ampoule | ampoule | serum",
            "valid_until": "2025-11-24",
            "signal_type": "inquiry",
        },
    ]
    opportunities = pd.DataFrame(rows)

    legacy_selected = max(
        rows,
        key=lambda item: (
            1 if item["country_norm"] == "미국" else 0,
            parse_date(item["valid_until"]) or date.min,
        ),
    )

    selected = _select_opportunity(
        opportunities,
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "ampoule | serum | cosmetics",
        },
        opportunity_country_norm="미국",
        reference_date=date(2026, 4, 22),
    )

    assert legacy_selected["title"] == "Genuine Matcha Powder"
    assert selected is not None
    assert selected["title"] == "Cellcurin Hair Ampoule"


def test_select_opportunity_hs_exact_beats_partial_hs_with_broad_keywords() -> None:
    """TASK-01 regression: hs_exact with no keywords must beat hs_prefix_2 + cosmetics keyword soup.

    Before fix: hs_exact scored 60-40=20 (keyword penalty applied), hs_prefix_2+keywords scored 65
    → wrong opportunity was selected.
    After fix: hs_exact scores 70 (no penalty for strong HS match) vs hs_prefix_2+keywords=65
    → correct opportunity is selected.
    """
    rows = [
        {
            "title": "K-beauty serum export",
            "country_norm": "미국",
            "hs_code_norm": "330499",  # exact HS match, no keywords
            "keywords_norm": "",
            "valid_until": "2026-09-01",
            "signal_type": "inquiry",
        },
        {
            "title": "Cosmetics and toiletries bulk",
            "country_norm": "미국",
            "hs_code_norm": "330100",  # prefix-2 match only ("33"), but many cosmetics keywords
            "keywords_norm": "cosmetics | serum | cream | lotion",
            "valid_until": "2026-09-01",
            "signal_type": "inquiry",
        },
    ]
    selected = _select_opportunity(
        pd.DataFrame(rows),
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "",
        },
        opportunity_country_norm="미국",
        reference_date=date(2026, 4, 22),
    )

    assert selected is not None
    assert selected["title"] == "K-beauty serum export", (
        "hs_exact (70) must outrank hs_prefix_2 + keyword overlap (20+45=65)"
    )


def test_opportunity_fit_score_keyword_mismatch_does_not_get_positive_base() -> None:
    """TASK-01: keyword_mismatch should not receive +25 base score.

    Before fix: mode='keyword' added +25 regardless of matched flag,
    so a mismatch scored 25-40=-15 instead of the correct 0-40=-40.
    After fix: only matched=True keyword hits receive the +25 bonus.
    """
    from shortlist_service import _opportunity_fit_score

    opportunity_mismatch = {
        "title": "Industrial valve parts",
        "country_norm": "미국",
        "hs_code_norm": "",
        "keywords_norm": "industrial | valve | machinery",
    }
    score = _opportunity_fit_score(
        opportunity_mismatch,
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "ampoule | serum",
        },
    )
    assert score < 0, f"keyword_mismatch should score negative, got {score}"
