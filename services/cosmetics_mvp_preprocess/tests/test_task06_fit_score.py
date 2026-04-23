from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task06_fit_score import (  # noqa: E402
    fit_score_v0,
    score_buyers,
    smoke_test_fit_score,
)


def test_fit_score_rejects_gate_fail() -> None:
    buyer = {
        "normalized_name": "Glow Beauty LLC",
        "country_norm": "베트남",
        "hs_code_norm": "330499",
        "keywords_norm": "cosmetics | serum | cream",
        "has_contact": True,
    }
    supplier_profile = {
        "target_country_norm": "미국",
        "target_hs_code_norm": "330499",
        "target_keywords_norm": "cosmetics | serum | cream",
    }

    result = fit_score_v0(buyer=buyer, supplier_profile=supplier_profile, reference_date=date(2026, 4, 22))

    assert result["decision"] == "rejected"
    assert result["final_score"] == 0
    assert result["score_breakdown"] == {
        "hs_score": 0,
        "keyword_score": 0,
        "country_score": 0,
        "capacity_score": 0,
        "contact_score": 0,
        "recency_score": 0,
        "signal_score": 0,
    }
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
    assert result["final_score"] == 88
    assert result["score_breakdown"] == {
        "hs_score": 27,
        "keyword_score": 3,
        "country_score": 20,
        "capacity_score": 10,
        "contact_score": 5,
        "recency_score": 8,
        "signal_score": 15,
    }
    assert len(result["explanation_reasons"]) == 3
    assert "HS 적합도" in result["explanation_reasons"][0]


def test_fit_score_keyword_primary_without_hs() -> None:
    buyer = {
        "normalized_name": "Mask Lab",
        "country_norm": "미국",
        "hs_code_norm": "",
        "keywords_norm": "serum | cream | ampoule",
        "contact_email": "sales@masklab.example",
        "has_contact": True,
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
    assert result["score_breakdown"]["hs_score"] == 0
    assert result["score_breakdown"]["keyword_score"] == 10
    assert result["score_breakdown"]["signal_score"] == 15
    assert result["score_breakdown"]["country_score"] == 20
    assert result["final_score"] == 58


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
