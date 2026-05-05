from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task07_shortlist_api import create_app  # noqa: E402


def _build_output_dir() -> Path:
    output_dir = ROOT / f".tmp_task07_api_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def test_shortlist_api_returns_ranked_items() -> None:
    output_dir = _build_output_dir()
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
                "keywords_norm": "mask | serum | cream",
                "has_contact": "True",
                "contact_email": "sales@masklab.example",
            },
        ]
    )
    opportunity_rows = pd.DataFrame(
        [
            {
                "title": "Hydrating ampoule inquiry",
                "country_norm": "미국",
                "valid_until": "2025-11-30",
                "signal_type": "inquiry",
                "keywords_norm": "ampoule | serum | cream",
                "product_name_norm": "Hydrating ampoule",
            }
        ]
    )

    try:
        buyer_rows.to_csv(output_dir / "buyer_candidate.csv", index=False, encoding="utf-8-sig")
        opportunity_rows.to_csv(output_dir / "opportunity_item.csv", index=False, encoding="utf-8-sig")

        completed = subprocess.run(
            [
                "python",
                "task07_shortlist_api.py",
                "--demo-request",
                "--output-dir",
                str(output_dir),
                "--reference-date",
                date(2025, 6, 1).isoformat(),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        assert completed.returncode == 0, completed.stderr
        assert "[task07-demo] meta =" in completed.stdout
        assert "returned_count': 2" in completed.stdout
        assert "soft_penalty_distribution" in completed.stdout
        assert "recommendation_lines" in completed.stdout
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shortlist_api_rejects_invalid_reference_date() -> None:
    completed = subprocess.run(
        [
            "python",
            "task07_shortlist_api.py",
            "--demo-request",
            "--output-dir",
            str(ROOT / "output"),
            "--reference-date",
            "not-a-date",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert completed.returncode != 0
    assert "reference_date" in (completed.stderr + completed.stdout)


def _write_task07_policy_fixture(output_dir: Path) -> None:
    buyer_rows = pd.DataFrame(
        [
            {
                "normalized_name": "Medical Device Co",
                "title": "Medical Device Co",
                "country_norm": "미국",
                "hs_code_norm": "",
                "keywords_norm": "medical | device",
                "has_contact": "True",
                "contact_email": "medical@example.com",
                "certification": "FDA",
                "moq": "100",
            },
            {
                "normalized_name": "Serum Lab",
                "title": "Serum Lab",
                "country_norm": "미국",
                "hs_code_norm": "",
                "keywords_norm": "serum | cream",
                "has_contact": "True",
                "contact_email": "serum@example.com",
                "certification": "FDA",
                "moq": "100",
            },
        ]
    )
    opportunity_rows = pd.DataFrame(
        [
            {
                "title": "Skincare serum inquiry",
                "country_norm": "미국",
                "valid_until": "2025-11-30",
                "signal_type": "inquiry",
                "keywords_norm": "serum | cream",
                "product_name_norm": "Skincare serum",
            }
        ]
    )

    buyer_rows.to_csv(output_dir / "buyer_candidate.csv", index=False, encoding="utf-8-sig")
    opportunity_rows.to_csv(output_dir / "opportunity_item.csv", index=False, encoding="utf-8-sig")


def _get_task07_policy_payload(output_dir: Path, **params: object) -> dict[str, object]:
    client = TestClient(create_app(output_dir=output_dir))
    response = client.get(
        "/buyers/shortlist",
        params={
            "supplier_name": "K-Beauty Supplier",
            "target_country_norm": "미국",
            "target_hs_code_norm": "330499",
            "target_keywords_norm": "serum | cream",
            "target_product_name_norm": "Skincare serum",
            "opportunity_title_contains": "serum",
            "opportunity_country_norm": "미국",
            "reference_date": "2025-06-01",
            "limit": 10,
            **params,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_tc_api_1_include_rejected_keeps_non_rejected_low_hs_match_candidate() -> None:
    output_dir = _build_output_dir()
    try:
        _write_task07_policy_fixture(output_dir)
        payload = _get_task07_policy_payload(output_dir, include_rejected=True)

        item_names = {item["buyer_name"] for item in payload["items"]}
        decisions_by_name = {item["buyer_name"]: item["decision"] for item in payload["items"]}

        assert "Medical Device Co" in item_names
        assert decisions_by_name["Medical Device Co"] != "rejected"
        assert decisions_by_name["Serum Lab"] != "rejected"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_tc_api_2_include_rejected_keeps_rejected_items_and_reports_pre_filter_count() -> None:
    output_dir = _build_output_dir()
    try:
        _write_task07_policy_fixture(output_dir)
        payload = _get_task07_policy_payload(output_dir, banned_countries="미국", include_rejected=True)
        decisions_by_name = {item["buyer_name"]: item["decision"] for item in payload["items"]}

        assert decisions_by_name["Medical Device Co"] == "rejected"
        assert decisions_by_name["Serum Lab"] == "rejected"
        assert payload["meta"]["returned_count"] == 2
        assert payload["meta"]["pre_filter_rejected_count"] == 2
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_tc_api_3_default_response_keeps_non_rejected_low_hs_match_candidate() -> None:
    output_dir = _build_output_dir()
    try:
        _write_task07_policy_fixture(output_dir)
        payload = _get_task07_policy_payload(output_dir)
        item_names = {item["buyer_name"] for item in payload["items"]}

        assert "Medical Device Co" in item_names
        assert "Serum Lab" in item_names
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def _write_task07_blocked_buyers_fixture(output_dir: Path) -> None:
    buyer_rows = pd.DataFrame(
        [
            {
                "normalized_name": "Medical Cosmetics Buyer",
                "title": "Medical Cosmetics Buyer",
                "country_norm": "미국",
                "hs_code_norm": "",
                "keywords_norm": "medical | cosmetics",
                "has_contact": "True",
                "contact_email": "mc@example.com",
            },
            {
                "normalized_name": "Beauty Equipment Buyer",
                "title": "Beauty Equipment Buyer",
                "country_norm": "미국",
                "hs_code_norm": "",
                "keywords_norm": "beauty | equipment",
                "has_contact": "True",
                "contact_email": "be@example.com",
            },
            {
                "normalized_name": "Pharma Supplement Buyer",
                "title": "Pharma Supplement Buyer",
                "country_norm": "미국",
                "hs_code_norm": "",
                "keywords_norm": "pharma | supplement",
                "has_contact": "True",
                "contact_email": "ps@example.com",
            },
            {
                "normalized_name": "Serum Lab",
                "title": "Serum Lab",
                "country_norm": "미국",
                "hs_code_norm": "330499",
                "keywords_norm": "serum | cream",
                "has_contact": "True",
                "contact_email": "serum@example.com",
            },
        ]
    )
    opportunity_rows = pd.DataFrame(
        [
            {
                "title": "Skincare serum inquiry",
                "country_norm": "미국",
                "valid_until": "2025-11-30",
                "signal_type": "inquiry",
                "keywords_norm": "serum | cream",
                "product_name_norm": "Skincare serum",
            }
        ]
    )
    buyer_rows.to_csv(output_dir / "buyer_candidate.csv", index=False, encoding="utf-8-sig")
    opportunity_rows.to_csv(output_dir / "opportunity_item.csv", index=False, encoding="utf-8-sig")


def test_tc_api_4_include_rejected_does_not_hide_low_hs_match_candidates() -> None:
    output_dir = _build_output_dir()
    try:
        _write_task07_blocked_buyers_fixture(output_dir)
        payload = _get_task07_policy_payload(output_dir, include_rejected=True)
        item_names = {item["buyer_name"] for item in payload["items"]}

        assert "Medical Cosmetics Buyer" in item_names
        assert "Beauty Equipment Buyer" in item_names
        assert "Pharma Supplement Buyer" in item_names
        assert "Serum Lab" in item_names
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
