from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
P1_DIR = ROOT / "services" / "p1-export-fit-api"
COSMETICS_DIR = ROOT / "services" / "cosmetics_mvp_preprocess"
if str(P1_DIR) not in sys.path:
    sys.path.insert(0, str(P1_DIR))
if str(COSMETICS_DIR) not in sys.path:
    sys.path.insert(0, str(COSMETICS_DIR))

from app.models import PredictRequest  # noqa: E402
from app.services.scoring import recommend_countries  # noqa: E402
from app.services.buyer_shortlist import ISO3_TO_TARGET_COUNTRY, MAX_SOURCE_COUNTRIES  # noqa: E402
from shortlist_service import build_supplier_profile, load_buyer_frame, load_opportunity_frame, _select_opportunity  # noqa: E402
from task05_shortlist import enrich_text_signal_fields, infer_hs_code_with_score, match_hs_or_keywords, normalize_text  # noqa: E402
from task06_fit_score import score_buyers  # noqa: E402


def _source_country(result: dict[str, Any]) -> dict[str, Any] | None:
    iso3 = str(result.get("partner_country_iso3") or "").upper()
    country_name = ISO3_TO_TARGET_COUNTRY.get(iso3, "")
    if not iso3 or not country_name:
        return None
    return {
        "partner_country_iso3": iso3,
        "target_country_name": country_name,
        "rank": int(result.get("rank") or 0),
    }


def _classify_failure_reason(record: dict[str, Any], target_record: dict[str, Any]) -> str:
    raw = dict(record)
    enriched = enrich_text_signal_fields(record)
    raw_texts = [
        normalize_text(raw.get("keywords_norm")),
        normalize_text(raw.get("product_name_norm")),
        normalize_text(raw.get("title")),
        normalize_text(raw.get("description")),
    ]
    enriched_texts = [
        normalize_text(enriched.get("keywords_norm")),
        normalize_text(enriched.get("product_name_norm")),
        normalize_text(enriched.get("title")),
        normalize_text(enriched.get("description")),
    ]
    if not any(enriched_texts):
        return "empty_text_signal"
    if not normalize_text(enriched.get("hs_code_norm")) and not normalize_text(enriched.get("keywords_norm")):
        return "missing_hs_and_missing_keyword"
    inferred = infer_hs_code_with_score(
        enriched.get("keywords_norm"),
        enriched.get("product_name_norm"),
        enriched.get("title"),
        enriched.get("description"),
        enriched.get("category"),
    )
    if inferred.get("hs_code") == "330499" and float(inferred.get("match_score") or 0.0) < 0.7:
        return "weak_cosmetics_keyword"
    if inferred.get("hs_code") != "330499":
        if normalize_text(enriched.get("country_norm")) and normalize_text(target_record.get("country_norm")) and normalize_text(enriched.get("country_norm")) == normalize_text(target_record.get("country_norm")):
            if any(raw_texts):
                return "country_only_match"
        return "non_cosmetics_product"
    return "unknown"


def _empty_ratio(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    empty_count = sum(1 for row in rows if not normalize_text(row.get(key)))
    return round(empty_count / len(rows), 4)


def diagnose(req: PredictRequest) -> dict[str, Any]:
    country_results, _, _ = recommend_countries(req)
    source_countries = [
        source
        for source in (_source_country(result) for result in country_results[:MAX_SOURCE_COUNTRIES])
        if source is not None
    ]

    buyers = load_buyer_frame()
    opportunities = load_opportunity_frame()
    mismatch_rows: list[dict[str, Any]] = []

    for source_country in source_countries:
        supplier_profile = build_supplier_profile(
            supplier_name="ValueUp Supplier",
            target_country_norm=source_country["target_country_name"],
            target_hs_code_norm=req.hs_code,
        )
        filtered_buyers = buyers[buyers["country_norm"].astype(str).eq(source_country["target_country_name"])].copy()
        selected_opportunity = _select_opportunity(
            opportunities,
            supplier_profile=supplier_profile,
            opportunity_country_norm=source_country["target_country_name"],
            reference_date=date.today(),
        )
        scored = score_buyers(
            buyers=filtered_buyers.to_dict(orient="records"),
            supplier_profile=supplier_profile,
            opportunity=selected_opportunity,
            reference_date=date.today(),
        )
        target_record = enrich_text_signal_fields(selected_opportunity or supplier_profile)
        for row in scored:
            gate_classification = row.get("gate_classification") or {}
            if "hs_mismatch" not in (gate_classification.get("soft_penalty") or []):
                continue
            buyer = enrich_text_signal_fields(row["buyer"])
            match_result = match_hs_or_keywords(buyer, target_record)
            mismatch_rows.append(
                {
                    "source_name": normalize_text(buyer.get("source_dataset")),
                    "source_type": normalize_text(buyer.get("record_type")),
                    "company_or_title": normalize_text(buyer.get("normalized_name")) or normalize_text(buyer.get("title")),
                    "hs_code_norm": normalize_text(buyer.get("hs_code_norm")),
                    "keywords_norm": normalize_text(buyer.get("keywords_norm")),
                    "product_name_norm": normalize_text(buyer.get("product_name_norm")),
                    "title": normalize_text(buyer.get("title")),
                    "description": normalize_text(buyer.get("description")),
                    "country_norm": normalize_text(buyer.get("country_norm")),
                    "match_reason": normalize_text(match_result.get("match_mode")),
                    "mismatch_reason": "hs_mismatch",
                    "failure_reason": _classify_failure_reason(buyer, target_record),
                }
            )

    failure_counts = Counter(row["failure_reason"] for row in mismatch_rows)
    sample_rows = sorted(
        mismatch_rows,
        key=lambda row: (
            1 if row["failure_reason"] == "empty_text_signal" else 0,
            1 if not row["keywords_norm"] else 0,
            1 if not row["product_name_norm"] else 0,
            1 if not row["title"] else 0,
            row["company_or_title"],
        ),
        reverse=True,
    )[:20]

    return {
        "sample_rows": sample_rows,
        "empty_ratio": {
            "keywords_norm": _empty_ratio(mismatch_rows, "keywords_norm"),
            "product_name_norm": _empty_ratio(mismatch_rows, "product_name_norm"),
            "title": _empty_ratio(mismatch_rows, "title"),
            "description": _empty_ratio(mismatch_rows, "description"),
        },
        "failure_reason_counts": dict(sorted(failure_counts.items())),
        "mismatch_count": len(mismatch_rows),
    }


def main() -> int:
    req = PredictRequest(
        hs_code="330499",
        exporter_country_iso3="KOR",
        top_n=5,
        year=2023,
    )
    result = diagnose(req)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
