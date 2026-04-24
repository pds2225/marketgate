from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task06_fit_score import (  # noqa: E402
    _component_hs_match_score,
    _keyword_hint_regex,
    _keyword_overlap,
    _smoke_opportunity,
    fit_score_v0,
    score_buyers,
    smoke_test_fit_score,
)


def _fit_score_result(
    *,
    buyer: dict[str, str],
    supplier_profile: dict[str, str],
    opportunity: dict[str, str] | None = None,
) -> dict[str, object]:
    return fit_score_v0(
        buyer=buyer,
        supplier_profile=supplier_profile,
        opportunity=opportunity,
        reference_date=date(2026, 4, 22),
    )


def test_fit_score_rejects_gate_fail() -> None:
    buyer = {
        "normalized_name": "Glow Beauty LLC",
        "country_norm": "미국",
        "hs_code_norm": "330499",
        "keywords_norm": "cosmetics | serum | cream",
        "has_contact": True,
    }
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "330499",
        "target_keywords_norm": "cosmetics | serum | cream",
        "banned_countries": "미국",
    }

    result = fit_score_v0(buyer=buyer, supplier_profile=supplier_profile, reference_date=date(2026, 4, 22))

    assert result["decision"] == "rejected"
    assert result["final_score"] == 0
    assert result["score_breakdown"]["final_weighted_score"] == 0
    assert "banned_country" in result["gate_classification"]["hard_fail"]
    assert len(result["explanation_reasons"]) == 3


def test_fit_score_hs_match_signal_shortlist() -> None:
    buyer = {
        "normalized_name": "Glow Beauty LLC",
        "country_norm": "미국",
        "hs_code_norm": "330499",
        "keywords_norm": "cosmetics | serum | cream",
        "capacity": "150",
        "contact_email": "hello@glowbeauty.example",
        "has_contact": True,
    }
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "3304",
        "target_keywords_norm": "cosmetics | serum | cream | mask",
        "required_capacity": 100,
    }
    opportunity = {
        "title": "Hydrating serum inquiry",
        "country_norm": "미국",
        "valid_until": "2026-06-30",
        "signal_type": "inquiry",
        "keywords_norm": "serum | cream | cosmetics",
    }

    result = fit_score_v0(
        buyer=buyer,
        supplier_profile=supplier_profile,
        opportunity=opportunity,
        reference_date=date(2026, 4, 22),
    )

    assert result["decision"] == "shortlist"
    assert result["final_score"] >= 80
    assert result["score_breakdown"]["country_match_score"] == 1.0
    assert result["score_breakdown"]["hs_match_score"] >= 0.9
    assert result["score_breakdown"]["contact_score"] == 1.0
    assert result["score_breakdown"]["activity_score"] >= 0.8
    assert result["score_breakdown"]["opportunity_signal_score"] == 1.0
    assert result["score_breakdown"]["soft_penalty_score"] <= 10
    assert len(result["explanation_reasons"]) == 3
    assert "제품 적합도" in result["explanation_reasons"][0]


def test_fit_score_soft_penalties_keep_candidate_in_ranking() -> None:
    buyer = {
        "normalized_name": "Mask Lab",
        "country_norm": "캐나다",
        "hs_code_norm": "",
        "keywords_norm": "serum | cream | ampoule",
        "contact_email": "",
        "has_contact": False,
    }
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "",
        "target_keywords_norm": "serum | cream | mask",
    }
    opportunity = {
        "title": "Serum mask consultation",
        "country_norm": "미국",
        "valid_until": "2026-06-30",
        "signal_type": "consultation",
        "keywords_norm": "serum | cream | mask",
    }

    result = fit_score_v0(
        buyer=buyer,
        supplier_profile=supplier_profile,
        opportunity=opportunity,
        reference_date=date(2026, 4, 22),
    )

    assert result["decision"] == "candidate"
    assert result["final_score"] > 0
    assert "country_mismatch" in result["gate_classification"]["soft_penalty"]
    assert "missing_contact" in result["gate_classification"]["soft_penalty"]
    assert "missing_certification" in result["gate_classification"]["soft_penalty"]
    assert "unclear_moq" in result["gate_classification"]["soft_penalty"]
    assert result["score_breakdown"]["hs_match_score"] > 0
    assert result["score_breakdown"]["country_match_score"] == 0.0


def test_fit_score_shortlists_buyer_without_hs_via_inference() -> None:
    buyer = {
        "normalized_name": "Daily Sun Care",
        "title": "Daily Sun Care",
        "country_norm": "미국",
        "hs_code_norm": "",
        "keywords_norm": "sunscreen | toner | skincare",
        "contact_email": "sales@suncare.example",
        "has_contact": True,
        "certification": "FDA",
        "moq": "100",
    }
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "330499",
        "target_keywords_norm": "sunscreen | toner | skincare",
    }
    opportunity = {
        "title": "UV sunscreen inquiry",
        "country_norm": "미국",
        "valid_until": "2026-06-30",
        "signal_type": "inquiry",
        "product_name_norm": "UV sunscreen",
        "keywords_norm": "sunscreen | skincare | toner",
    }

    result = fit_score_v0(
        buyer=buyer,
        supplier_profile=supplier_profile,
        opportunity=opportunity,
        reference_date=date(2026, 4, 22),
    )

    assert result["decision"] == "shortlist"
    assert result["score_breakdown"]["hs_match_type"] == "hs_inferred"
    assert result["score_breakdown"]["hs_match_score"] >= 0.6
    assert "HS 추정 기반 매칭" in result["explanation_reasons"][0]


@pytest.mark.parametrize(
    "buyer_keywords",
    [
        "beauty",
        "beauty | cosmetic",
        "medical cosmetics",
    ],
)
def test_fit_score_does_not_award_hs_inference_for_weak_or_blocked_keywords(
    buyer_keywords: str,
) -> None:
    buyer = {
        "normalized_name": "Generic Buyer",
        "title": "Generic Buyer",
        "country_norm": "미국",
        "hs_code_norm": "",
        "keywords_norm": buyer_keywords,
        "contact_email": "buyer@example.com",
        "has_contact": True,
        "certification": "FDA",
        "moq": "100",
    }
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "330499",
        "target_keywords_norm": "sunscreen | toner | skincare",
    }
    opportunity = {
        "title": "UV sunscreen inquiry",
        "country_norm": "미국",
        "valid_until": "2026-06-30",
        "signal_type": "inquiry",
        "product_name_norm": "UV sunscreen",
        "keywords_norm": "sunscreen | skincare | toner",
    }

    result = fit_score_v0(
        buyer=buyer,
        supplier_profile=supplier_profile,
        opportunity=opportunity,
        reference_date=date(2026, 4, 22),
    )

    assert result["matched_by"] not in {"hs_inferred", "hs_inferred_prefix_4"}
    assert result["score_breakdown"]["hs_match_type"] == "keyword"
    assert result["score_breakdown"]["hs_match_score"] == 0.0


@pytest.mark.parametrize(
    ("buyer_title", "buyer_keywords"),
    [
        ("Skincare Serum Buyer", "skincare | serum"),
        ("Anti Wrinkle Micro Patch Buyer", "anti wrinkle | micro patch"),
    ],
)
def test_fit_score_awards_hs_inference_for_strong_cosmetics_keywords(
    buyer_title: str,
    buyer_keywords: str,
) -> None:
    buyer = {
        "normalized_name": buyer_title,
        "title": buyer_title,
        "country_norm": "미국",
        "hs_code_norm": "",
        "keywords_norm": buyer_keywords,
        "contact_email": "buyer@example.com",
        "has_contact": True,
        "certification": "FDA",
        "moq": "100",
    }
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "330499",
        "target_keywords_norm": "serum | skincare | ampoule",
    }
    opportunity = {
        "title": "K-Beauty serum inquiry",
        "country_norm": "미국",
        "valid_until": "2026-06-30",
        "signal_type": "inquiry",
        "product_name_norm": "Hydrating Serum",
        "keywords_norm": "serum | skincare | ampoule",
    }

    result = fit_score_v0(
        buyer=buyer,
        supplier_profile=supplier_profile,
        opportunity=opportunity,
        reference_date=date(2026, 4, 22),
    )

    assert result["matched_by"] == "hs_inferred"
    assert result["score_breakdown"]["hs_match_type"] == "hs_inferred"
    assert result["score_breakdown"]["hs_match_score"] >= 0.6


def test_fit_score_does_not_bypass_medical_hs_with_inference() -> None:
    buyer = {
        "normalized_name": "Medical Buyer",
        "title": "Medical Buyer",
        "country_norm": "미국",
        "hs_code_norm": "300490",
        "keywords_norm": "medicine",
        "contact_email": "buyer@example.com",
        "has_contact": True,
        "certification": "FDA",
        "moq": "100",
    }
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "330499",
        "target_keywords_norm": "serum | skincare",
    }
    opportunity = {
        "title": "Skincare serum inquiry",
        "country_norm": "미국",
        "valid_until": "2026-06-30",
        "signal_type": "inquiry",
        "product_name_norm": "Skincare serum",
        "keywords_norm": "serum | skincare",
    }

    result = fit_score_v0(
        buyer=buyer,
        supplier_profile=supplier_profile,
        opportunity=opportunity,
        reference_date=date(2026, 4, 22),
    )

    assert result["matched_by"] not in {"hs_inferred", "hs_inferred_prefix_4"}
    assert result["score_breakdown"]["hs_match_type"] == "keyword"
    assert result["score_breakdown"]["hs_match_score"] == 0.0


def test_hs_exact_score_cap_is_one_point_zero() -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "Exact Buyer",
            "country_norm": "미국",
            "hs_code_norm": "330499",
            "keywords_norm": "",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "",
        },
    )

    assert result["score_breakdown"]["hs_match_type"] == "hs_exact"
    assert result["score_breakdown"]["hs_match_score"] == 1.0


def test_hs_prefix_4_score_cap_is_zero_point_nine() -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "Prefix4 Buyer",
            "country_norm": "미국",
            "hs_code_norm": "330499",
            "keywords_norm": "",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330490",
            "target_keywords_norm": "",
        },
    )

    assert result["score_breakdown"]["hs_match_type"] == "hs_prefix_4"
    assert result["score_breakdown"]["hs_match_score"] <= 0.9
    assert result["score_breakdown"]["hs_match_score"] == 0.9


def test_hs_prefix_2_score_cap_is_zero_point_seven_five() -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "Prefix2 Buyer",
            "country_norm": "미국",
            "hs_code_norm": "330499",
            "keywords_norm": "",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330100",
            "target_keywords_norm": "",
        },
    )

    assert result["score_breakdown"]["hs_match_type"] == "hs_prefix_2"
    assert result["score_breakdown"]["hs_match_score"] <= 0.75
    assert result["score_breakdown"]["hs_match_score"] == 0.75


def test_hs_inferred_score_cap_is_zero_point_eight() -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "Inference Buyer",
            "title": "Inference Buyer",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": "sunscreen | toner | skincare | serum",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "sunscreen | toner | skincare | serum",
        },
        opportunity={
            "title": "UV sunscreen inquiry",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": "UV sunscreen serum",
            "keywords_norm": "sunscreen | toner | skincare | serum",
        },
    )

    assert result["score_breakdown"]["hs_match_type"] == "hs_inferred"
    assert result["score_breakdown"]["hs_match_score"] <= 0.8
    assert result["score_breakdown"]["hs_match_score"] >= 0.6


def test_hs_inferred_prefix_4_score_cap_is_zero_point_seven_five() -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "Inference Prefix Buyer",
            "title": "Inference Prefix Buyer",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": "sunscreen | toner | skincare",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330490",
            "target_keywords_norm": "sunscreen | toner | skincare",
        },
        opportunity={
            "title": "UV sunscreen inquiry",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": "UV sunscreen",
            "keywords_norm": "sunscreen | skincare | toner",
        },
    )

    assert result["score_breakdown"]["hs_match_type"] == "hs_inferred_prefix_4"
    assert result["score_breakdown"]["hs_match_score"] <= 0.75
    assert result["score_breakdown"]["hs_match_score"] >= 0.6


def test_keyword_fallback_does_not_outscore_hs_inferred() -> None:
    inferred_result = _fit_score_result(
        buyer={
            "normalized_name": "Inference Buyer",
            "title": "Inference Buyer",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": "skincare | serum",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "skincare | serum",
        },
        opportunity={
            "title": "Skincare serum inquiry",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": "Skincare serum",
            "keywords_norm": "skincare | serum",
        },
    )
    keyword_result = _fit_score_result(
        buyer={
            "normalized_name": "Keyword Buyer",
            "title": "Keyword Buyer",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": "hydrating | cream",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "",
            "target_keywords_norm": "hydrating | cream",
        },
        opportunity={
            "title": "Hydrating cream inquiry",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": "Hydrating cream",
            "keywords_norm": "hydrating | cream",
        },
    )

    assert inferred_result["score_breakdown"]["hs_match_type"] == "hs_inferred"
    assert keyword_result["score_breakdown"]["hs_match_type"] == "keyword"
    assert keyword_result["score_breakdown"]["hs_match_score"] <= inferred_result["score_breakdown"]["hs_match_score"]


@pytest.mark.parametrize(
    ("buyer_title", "buyer_keywords"),
    [
        ("Medical Cosmetics Buyer", "medical cosmetics"),
        ("Beauty Equipment Buyer", "beauty equipment"),
    ],
)
def test_blocked_or_non_cosmetics_cases_do_not_receive_hs_score(
    buyer_title: str,
    buyer_keywords: str,
) -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": buyer_title,
            "title": buyer_title,
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": buyer_keywords,
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "skincare | serum",
        },
        opportunity={
            "title": "Skincare serum inquiry",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": "Skincare serum",
            "keywords_norm": "skincare | serum",
        },
    )

    assert result["score_breakdown"]["hs_match_score"] == 0.0 or result["decision"] != "shortlist"


@pytest.mark.parametrize(
    "buyer_keywords",
    [
        "medical cosmetics",
        "pharma supplement",
    ],
)
def test_keyword_direct_match_does_not_allow_weak_or_blocked_terms(
    buyer_keywords: str,
) -> None:
    overlap_terms = _keyword_overlap(
        {
            "normalized_name": "",
            "title": "",
            "keywords_norm": buyer_keywords,
        },
        {
            "title": "",
            "product_name_norm": "",
            "keywords_norm": buyer_keywords,
        },
    )

    assert overlap_terms == []
    assert _component_hs_match_score("", overlap_terms) == 0.0


def test_keyword_direct_match_allows_strong_cosmetics_terms() -> None:
    overlap_terms = _keyword_overlap(
        {
            "normalized_name": "Skincare Serum Buyer",
            "title": "Skincare Serum Buyer",
            "keywords_norm": "skincare | serum",
        },
        {
            "title": "Skincare Serum Target",
            "product_name_norm": "Skincare serum",
            "keywords_norm": "skincare | serum",
        },
    )

    assert "serum" in overlap_terms
    assert _component_hs_match_score("", overlap_terms) > 0.0


@pytest.mark.parametrize(
    "shared_keywords",
    [
        "cosmetic",
        "medical cosmetics",
        "pharma supplement",
    ],
)
def test_fit_score_keyword_fallback_blocks_shared_weak_or_blocked_terms(
    shared_keywords: str,
) -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "",
            "title": "",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": shared_keywords,
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "",
            "target_keywords_norm": shared_keywords,
        },
        opportunity={
            "title": "",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": shared_keywords,
            "keywords_norm": shared_keywords,
        },
    )

    assert result["score_breakdown"]["hs_match_score"] == 0.0
    assert result["score_breakdown"]["hs_match_type"] == "keyword"


def test_fit_score_keyword_fallback_blocks_beauty_equipment_title_overlap() -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "Equipment Buyer",
            "title": "Beauty Equipment",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": "",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "",
            "target_keywords_norm": "beauty equipment",
        },
        opportunity={
            "title": "Beauty Equipment",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": "Beauty Equipment",
            "keywords_norm": "beauty equipment",
        },
    )

    assert result["score_breakdown"]["hs_match_score"] == 0.0


def test_fit_score_keyword_fallback_preserves_valid_cosmetics_signal() -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "Skincare Serum Buyer",
            "title": "Skincare Serum Buyer",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": "skincare | serum",
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "skincare | serum",
        },
        opportunity={
            "title": "Skincare serum inquiry",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": "Skincare serum",
            "keywords_norm": "skincare | serum",
        },
    )

    assert result["score_breakdown"]["hs_match_score"] > 0.0
    assert result["score_breakdown"]["hs_match_type"] in {"hs_inferred", "keyword"}


@pytest.mark.parametrize(
    "buyer_keywords",
    [
        "medical cosmetics",
        "beauty equipment",
    ],
)
def test_blocked_buyers_do_not_shortlist_via_smoke_or_keyword_paths(
    buyer_keywords: str,
) -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": "",
            "title": "",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": buyer_keywords,
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "",
            "target_keywords_norm": buyer_keywords,
        },
        opportunity={
            "title": "",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": buyer_keywords,
            "keywords_norm": buyer_keywords,
        },
    )

    assert result["score_breakdown"]["hs_match_score"] == 0.0
    assert result["decision"] != "shortlist"


def test_smoke_opportunity_skips_blocked_medical_opportunity() -> None:
    opportunities = [
        {
            "title": "Medical mask therapy opportunity",
            "country_norm": "미국",
            "valid_until": "2026-07-30",
            "signal_type": "inquiry",
            "product_name_norm": "Medical mask therapy",
            "keywords_norm": "medical | mask | therapy",
        },
        {
            "title": "Skincare serum inquiry",
            "country_norm": "미국",
            "valid_until": "2026-07-30",
            "signal_type": "inquiry",
            "product_name_norm": "Skincare serum",
            "keywords_norm": "skincare | serum",
        },
    ]

    selected = _smoke_opportunity(
        opportunities,
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "",
            "target_keywords_norm": "skincare | serum",
        },
        reference_date=date(2026, 4, 22),
    )

    assert selected is not None
    assert selected["title"] == "Skincare serum inquiry"


@pytest.mark.parametrize(
    ("buyer_title", "buyer_keywords"),
    [
        ("Skincare Serum Buyer", "skincare | serum"),
        ("Sunscreen Toner Buyer", "sunscreen | toner"),
    ],
)
def test_valid_cosmetics_buyers_keep_positive_score(
    buyer_title: str,
    buyer_keywords: str,
) -> None:
    result = _fit_score_result(
        buyer={
            "normalized_name": buyer_title,
            "title": buyer_title,
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": buyer_keywords,
            "contact_email": "buyer@example.com",
            "has_contact": True,
            "certification": "FDA",
            "moq": "100",
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": buyer_keywords,
        },
        opportunity={
            "title": f"{buyer_title} inquiry",
            "country_norm": "미국",
            "valid_until": "2026-06-30",
            "signal_type": "inquiry",
            "product_name_norm": buyer_title,
            "keywords_norm": buyer_keywords,
        },
    )

    assert result["score_breakdown"]["hs_match_score"] > 0.0
    assert result["decision"] in {"candidate", "shortlist"}


@pytest.mark.parametrize(
    "blocked_keywords",
    [
        "medical cosmetics",
        "beauty equipment",
        "pharma supplement",
        "medical serum",
        "cosmetic device serum",
    ],
)
def test_keyword_hint_regex_and_smoke_opportunity_share_blocked_keyword_exclusions(
    blocked_keywords: str,
) -> None:
    hint_regex = _keyword_hint_regex({"target_keywords_norm": blocked_keywords})
    if hint_regex is not None:
        assert not hint_regex.search(blocked_keywords)

    selected = _smoke_opportunity(
        [
            {
                "title": blocked_keywords,
                "country_norm": "미국",
                "valid_until": "2026-07-30",
                "signal_type": "inquiry",
                "product_name_norm": blocked_keywords,
                "keywords_norm": blocked_keywords,
            }
        ],
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "",
            "target_keywords_norm": blocked_keywords,
        },
        reference_date=date(2026, 4, 22),
    )

    assert selected is None


@pytest.mark.parametrize(
    "strong_keywords",
    [
        "skincare serum",
        "sunscreen toner",
    ],
)
def test_keyword_hint_regex_and_smoke_opportunity_keep_strong_cosmetics_signals(
    strong_keywords: str,
) -> None:
    hint_regex = _keyword_hint_regex({"target_keywords_norm": strong_keywords})

    assert hint_regex is not None
    assert hint_regex.search(strong_keywords)

    selected = _smoke_opportunity(
        [
            {
                "title": strong_keywords,
                "country_norm": "미국",
                "valid_until": "2026-07-30",
                "signal_type": "inquiry",
                "product_name_norm": strong_keywords,
                "keywords_norm": strong_keywords,
            }
        ],
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "",
            "target_keywords_norm": strong_keywords,
        },
        reference_date=date(2026, 4, 22),
    )

    assert selected is not None
    assert selected["title"] == strong_keywords


def test_fit_score_contact_and_hs_match_shortlists_without_opportunity() -> None:
    """contact+HS 일치 바이어는 opportunity 없어도 상위 candidate로 유지돼야 한다."""
    result = fit_score_v0(
        buyer={
            "normalized_name": "K-Beauty Distributor",
            "country_norm": "미국",
            "hs_code_norm": "330499",
            "keywords_norm": "cosmetics | serum | cream",
            "contact_email": "contact@kbeauty.example",
            "has_contact": True,
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "3304",
            "target_keywords_norm": "cosmetics | serum | cream | mask",
        },
        opportunity=None,
        reference_date=date(2026, 4, 22),
    )

    assert result["decision"] == "candidate", f"expected candidate, got {result['decision']} (score={result['final_score']})"
    assert result["final_score"] < 70
    assert result["final_score"] >= 65
    assert result["score_breakdown"]["hs_match_score"] >= 0.9
    assert result["score_breakdown"]["contact_score"] == 1.0
    assert result["gate_classification"]["hard_fail"] == []


def test_fit_score_has_contact_true_hs_prefix4_shortlists_without_opportunity() -> None:
    """has_contact=True + hs_prefix_4 + country 일치 바이어는 opportunity 없이도 candidate여야 한다."""
    result = fit_score_v0(
        buyer={
            "normalized_name": "K-Beauty Wholesale",
            "country_norm": "미국",
            "hs_code_norm": "330499",
            "keywords_norm": "cosmetics | serum | cream",
            "has_contact": True,
        },
        supplier_profile={
            "target_country_norm": "미국",
            "target_hs_code_norm": "3304",
            "target_keywords_norm": "cosmetics | serum | cream | mask",
        },
        opportunity=None,
        reference_date=date(2026, 4, 22),
    )

    assert result["decision"] == "candidate", (
        f"expected candidate, got {result['decision']} (score={result['final_score']})"
    )
    assert result["final_score"] < 70
    assert result["final_score"] >= 60
    assert result["score_breakdown"]["hs_match_score"] >= 0.9
    assert result["score_breakdown"]["contact_score"] == 0.6
    assert result["gate_classification"]["hard_fail"] == []


def test_score_buyers_sorts_by_final_score() -> None:
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "3304",
        "target_keywords_norm": "cosmetics | serum | cream | mask",
    }
    opportunity = {
        "title": "Hydrating serum inquiry",
        "country_norm": "미국",
        "valid_until": "2026-06-30",
        "signal_type": "inquiry",
        "keywords_norm": "serum | cream | cosmetics",
    }
    buyers = [
        {
            "normalized_name": "Top Buyer",
            "country_norm": "미국",
            "hs_code_norm": "330499",
            "keywords_norm": "cosmetics | serum | cream",
            "contact_email": "top@example.com",
            "has_contact": True,
        },
        {
            "normalized_name": "Keyword Buyer",
            "country_norm": "미국",
            "hs_code_norm": "",
            "keywords_norm": "serum | cream",
            "contact_email": "keyword@example.com",
            "has_contact": True,
        },
    ]

    results = score_buyers(
        buyers=buyers,
        supplier_profile=supplier_profile,
        opportunity=opportunity,
        reference_date=date(2026, 4, 22),
    )

    assert results[0]["buyer"]["normalized_name"] == "Top Buyer"
    assert results[0]["final_score"] > results[1]["final_score"]
    assert results[0]["score_breakdown"]["hs_match_score"] >= results[1]["score_breakdown"]["hs_match_score"]


def test_smoke_test_fit_score_reads_realistic_outputs() -> None:
    tmp_path = ROOT / f".tmp_task06_smoke_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    buyer_rows = pd.DataFrame(
        [
            {
                "normalized_name": "Glow Beauty LLC",
                "title": "Glow Beauty LLC",
                "country_norm": "미국",
                "hs_code_norm": "330499",
                "keywords_norm": "cosmetics | serum | cream",
                "has_contact": "True",
                "contact_email": "hello@glowbeauty.example",
            },
            {
                "normalized_name": "Mask Lab",
                "title": "Mask Lab",
                "country_norm": "미국",
                "hs_code_norm": "",
                "keywords_norm": "serum | cream | mask",
                "has_contact": "True",
                "contact_email": "sales@masklab.example",
            },
            {
                "normalized_name": "Industrial Parts Co",
                "title": "Industrial Parts Co",
                "country_norm": "미국",
                "hs_code_norm": "730890",
                "keywords_norm": "steel | fitting",
                "has_contact": "False",
                "contact_email": "",
            },
        ]
    )
    opportunity_rows = pd.DataFrame(
        [
            {
                "title": "Hydrating serum inquiry",
                "country_norm": "미국",
                "valid_until": "2024-06-30",
                "signal_type": "inquiry",
                "keywords_norm": "serum | cream | cosmetics",
                "product_name_norm": "Hydrating serum",
            },
            {
                "title": "Industrial fitting request",
                "country_norm": "미국",
                "valid_until": "2024-06-30",
                "signal_type": "inquiry",
                "keywords_norm": "steel | fitting",
                "product_name_norm": "Industrial fitting",
            },
        ]
    )

    try:
        buyer_rows.to_csv(tmp_path / "buyer_candidate.csv", index=False, encoding="utf-8-sig")
        opportunity_rows.to_csv(tmp_path / "opportunity_item.csv", index=False, encoding="utf-8-sig")

        result = smoke_test_fit_score(
            output_dir=tmp_path,
            supplier_profile={
                "target_country_norm": "미국",
                "target_hs_code_norm": "3304",
                "target_keywords_norm": "cosmetics | serum | cream | mask",
            },
            reference_date=date(2024, 3, 1),
            sample_size=3,
            random_seed=42,
        )

        assert result["sample_size"] >= 2
        assert result["decision_counts"]["shortlist"] >= 1
        assert result["top_results"][0]["final_score"] >= result["top_results"][-1]["final_score"]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
