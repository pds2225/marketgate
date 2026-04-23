from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
