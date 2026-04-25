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

from task09_validate_top20 import validate_top20  # noqa: E402


def _build_output_dir() -> Path:
    output_dir = ROOT / f".tmp_task09_top20_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def test_validate_top20_passes_on_synthetic_cosmetics_rows() -> None:
    output_dir = _build_output_dir()
    buyer_rows = pd.DataFrame(
        [
            {
                "normalized_name": f"Glow Buyer {index:02d}",
                "title": f"Glow Buyer {index:02d}",
                "country_norm": "미국",
                "hs_code_norm": "330499",
                "keywords_norm": "cosmetics | serum | cream | ampoule",
                "has_contact": "True",
                "contact_email": f"buyer{index:02d}@example.com",
            }
            for index in range(25)
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

        result = validate_top20(
            output_dir=output_dir,
            reference_date=date(2025, 6, 1),
            limit=20,
            opportunity_title_contains="ampoule",
            supplier_profile_overrides={
                "target_country_norm": "미국",
                "target_hs_code_norm": "3304",
                "target_keywords_norm": "cosmetics | serum | cream | ampoule",
                "target_product_name_norm": "cosmetics",
            },
        )

        assert result["quality"]["passed"] is True
        assert len(result["top20"]) == 20
        assert result["top20"][0]["final_score"] >= result["top20"][-1]["final_score"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
