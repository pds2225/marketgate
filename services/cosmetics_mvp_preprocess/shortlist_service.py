from __future__ import annotations

from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from task05_shortlist import (
    COSMETICS_HS_RULES,
    ENCODINGS,
    KEYWORD_MATCH_STOPWORDS,
    _keyword_match_variants,
    match_hs_or_keywords,
    normalize_hs_code,
    normalize_keywords,
    normalize_opportunity_record,
    normalize_text,
    parse_date,
)
from task06_fit_score import score_buyers
from task08_recommendation import build_recommendation_lines


ROOT = Path(__file__).resolve().parent


def _soft_penalty_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        gate_classification = row.get("gate_classification") or {}
        for code in gate_classification.get("soft_penalty", []):
            normalized = normalize_text(code)
            if normalized:
                counter[normalized] += 1
    return dict(sorted(counter.items()))


def _read_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"출력 파일이 없습니다: {path}")
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        for engine in (None, "python"):
            try:
                kwargs: dict[str, Any] = {
                    "dtype": str,
                    "keep_default_na": False,
                    "encoding": encoding,
                }
                if engine is not None:
                    kwargs["engine"] = engine
                    kwargs["on_bad_lines"] = "skip"
                return pd.read_csv(path, **kwargs)
            except (UnicodeDecodeError, pd.errors.ParserError, MemoryError, OSError) as exc:
                last_error = exc
                continue
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"CSV 로드에 실패했습니다: {path}")


@lru_cache(maxsize=8)
def _load_frame_cached(output_dir_str: str, filename: str) -> pd.DataFrame:
    return _read_frame(Path(output_dir_str) / filename)


def clear_shortlist_cache() -> None:
    _load_frame_cached.cache_clear()


def load_buyer_frame(output_dir: Path | None = None) -> pd.DataFrame:
    base_dir = output_dir or (ROOT / "output")
    return _load_frame_cached(str(base_dir), "buyer_candidate.csv").copy()


def load_opportunity_frame(output_dir: Path | None = None) -> pd.DataFrame:
    base_dir = output_dir or (ROOT / "output")
    return _load_frame_cached(str(base_dir), "opportunity_item.csv").copy()


def build_supplier_profile(
    *,
    supplier_name: str = "MarketGate Supplier",
    target_country_norm: str = "",
    target_hs_code_norm: str = "",
    target_keywords_norm: str = "",
    target_product_name_norm: str = "",
    required_capacity: float | int | None = None,
    banned_countries: str = "",
) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "supplier_name": supplier_name,
        "target_country_norm": normalize_text(target_country_norm),
        "target_hs_code_norm": normalize_text(target_hs_code_norm),
        "target_keywords_norm": normalize_text(target_keywords_norm),
        "target_product_name_norm": normalize_text(target_product_name_norm),
        "banned_countries": normalize_text(banned_countries),
    }
    if required_capacity is not None:
        profile["required_capacity"] = required_capacity
    return profile


def _build_target_match_record(supplier_profile: Mapping[str, Any] | None) -> dict[str, Any]:
    profile = supplier_profile or {}
    target_hs = normalize_hs_code(profile.get("target_hs_code_norm"))
    target_keywords = normalize_keywords(profile.get("target_keywords_norm"))
    if not target_keywords and target_hs:
        for hs_code, keywords in COSMETICS_HS_RULES:
            if hs_code.startswith(target_hs) or target_hs.startswith(hs_code[:4]):
                target_keywords = normalize_keywords(" | ".join(keywords))
                break
    return {
        "hs_code_norm": target_hs,
        "keywords_norm": target_keywords,
        "title": normalize_text(profile.get("target_title") or profile.get("target_product_name_norm")),
        "normalized_name": normalize_text(profile.get("target_product_name_norm")),
    }


def _opportunity_fit_score(opportunity: Mapping[str, Any], supplier_profile: Mapping[str, Any] | None) -> int:
    target_record = _build_target_match_record(supplier_profile)
    if not any(target_record.values()):
        return 0

    score = 0
    match = match_hs_or_keywords(target_record, opportunity)
    mode = str(match.get("match_mode") or "")
    matched = bool(match.get("matched", False))
    if mode == "hs_exact":
        score += 70  # raised from 60: ensures hs_exact beats hs_prefix_2+max_keyword (20+45=65)
    elif mode == "hs_inferred":
        score += 50  # inferred exact HS — previously unhandled (scored 0)
    elif mode == "hs_prefix_4":
        score += 40
    elif mode == "hs_inferred_prefix_4":
        score += 30  # inferred prefix-4 HS — previously unhandled (scored 0)
    elif mode == "hs_prefix_2":
        score += 20
    elif mode == "keyword" and matched:
        score += 25  # only on actual keyword match, not keyword_mismatch

    # strong HS match already proves relevance — don't penalise missing keywords
    strong_hs_match = mode in ("hs_exact", "hs_inferred", "hs_prefix_4", "hs_inferred_prefix_4")

    target_terms = set()
    target_terms.update(_keyword_match_variants(target_record.get("keywords_norm")))
    target_terms.update(_keyword_match_variants(target_record.get("title")))
    opportunity_terms = set()
    opportunity_terms.update(_keyword_match_variants(opportunity.get("keywords_norm")))
    opportunity_terms.update(_keyword_match_variants(opportunity.get("product_name_norm")))
    opportunity_terms.update(_keyword_match_variants(opportunity.get("title")))
    keyword_overlap = target_terms & opportunity_terms

    if keyword_overlap:
        score += 30 + min(len(keyword_overlap) * 5, 15)
    elif target_terms and not strong_hs_match:
        score -= 40

    return score


def _select_opportunity(
    opportunities: pd.DataFrame,
    *,
    supplier_profile: Mapping[str, Any] | None = None,
    opportunity_title_contains: str = "",
    opportunity_country_norm: str = "",
    reference_date: date | None = None,
) -> dict[str, Any] | None:
    if opportunities.empty:
        return None

    title_filter = normalize_text(opportunity_title_contains).casefold()
    country_filter = normalize_text(opportunity_country_norm)
    candidates: list[tuple[int, int, int, date, dict[str, Any]]] = []
    for record in opportunities.to_dict(orient="records"):
        normalized = normalize_opportunity_record(record, reference_date=reference_date)
        title = normalize_text(normalized.get("title")).casefold()
        country = normalize_text(normalized.get("country_norm"))
        if title_filter and title_filter not in title:
            continue
        if country_filter and country_filter != country:
            continue
        score = 0
        if title_filter and title == title_filter:
            score += 2
        if country_filter and country == country_filter:
            score += 1
        fit_score = _opportunity_fit_score(normalized, supplier_profile)
        signal_usable_score = 1 if normalized.get("signal_usable") else 0
        valid_until = parse_date(normalized.get("valid_until")) or date.min
        candidates.append((fit_score, signal_usable_score, score, valid_until, normalized))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
    return candidates[0][4]


def shortlist_buyers(
    *,
    output_dir: Path | None = None,
    supplier_profile: Mapping[str, Any],
    reference_date: date | None = None,
    limit: int = 20,
    opportunity_title_contains: str = "",
    opportunity_country_norm: str = "",
    include_rejected: bool = False,
) -> dict[str, Any]:
    buyers = load_buyer_frame(output_dir=output_dir)
    opportunities = load_opportunity_frame(output_dir=output_dir)

    target_country = normalize_text(supplier_profile.get("target_country_norm"))
    filtered_buyers = buyers
    if target_country:
        filtered_buyers = filtered_buyers[
            filtered_buyers["country_norm"].astype(str).eq(target_country)
        ].copy()

    selected_opportunity = _select_opportunity(
        opportunities,
        supplier_profile=supplier_profile,
        opportunity_title_contains=opportunity_title_contains,
        opportunity_country_norm=opportunity_country_norm or target_country,
        reference_date=reference_date,
    )

    scoring_supplier_profile = dict(supplier_profile)
    if not normalize_keywords(scoring_supplier_profile.get("target_keywords_norm")):
        scoring_target = _build_target_match_record(supplier_profile)
        if normalize_keywords(scoring_target.get("keywords_norm")):
            scoring_supplier_profile["target_keywords_norm"] = scoring_target["keywords_norm"]
    # expired/ambiguous 기회도 activity_score(날짜 기반)는 계산 가능 — component score가 각각 0으로 처리
    scoring_opportunity = selected_opportunity

    scored_all = score_buyers(
        buyers=filtered_buyers.to_dict(orient="records"),
        supplier_profile=scoring_supplier_profile,
        opportunity=scoring_opportunity,
        reference_date=reference_date,
    )
    shortlist_count = sum(1 for row in scored_all if row["decision"] == "shortlist")
    candidate_count = sum(1 for row in scored_all if row["decision"] == "candidate")
    rejected_count = sum(1 for row in scored_all if row["decision"] == "rejected")
    soft_penalty_distribution = _soft_penalty_distribution(scored_all)
    soft_penalty_row_count = sum(
        1
        for row in scored_all
        if (row.get("gate_classification") or {}).get("soft_penalty")
    )

    scored = scored_all
    if not include_rejected:
        scored = [row for row in scored if row["decision"] != "rejected"]
    if limit > 0:
        scored = scored[:limit]

    items: list[dict[str, Any]] = []
    for row in scored:
        buyer = row["buyer"]
        recommendation_lines = build_recommendation_lines(row)
        explanation_reasons = [
            normalize_text(line)
            for line in row.get("explanation_reasons", [])
            if normalize_text(line)
        ]
        if not explanation_reasons:
            explanation_reasons = recommendation_lines
        items.append(
            {
                "buyer_name": normalize_text(buyer.get("normalized_name")) or normalize_text(buyer.get("title")),
                "source_dataset": normalize_text(buyer.get("source_dataset")),
                "country_norm": normalize_text(buyer.get("country_norm")),
                "hs_code_norm": normalize_text(buyer.get("hs_code_norm")),
                "keywords_norm": normalize_text(buyer.get("keywords_norm")),
                "has_contact": str(buyer.get("has_contact", "")).strip().lower() == "true",
                "contact_email": normalize_text(buyer.get("contact_email")),
                "contact_name": normalize_text(buyer.get("contact_name")),
                "contact_phone": normalize_text(buyer.get("contact_phone")),
                "contact_website": normalize_text(buyer.get("contact_website")),
                "final_score": row["final_score"],
                "decision": row["decision"],
                "score_breakdown": row["score_breakdown"],
                "recommendation_lines": recommendation_lines,
                "explanation_reasons": explanation_reasons[:3],
                "matched_by": normalize_text(row.get("matched_by")),
                "matched_terms": list(row.get("matched_terms", [])),
            }
        )

    returned_count = len(items)

    return {
        "meta": {
            "supplier_profile": dict(supplier_profile),
            "scoring_supplier_profile": scoring_supplier_profile,
            "reference_date": (reference_date or date.today()).isoformat(),
            "selected_opportunity_title": normalize_text((selected_opportunity or {}).get("title")),
            "selected_opportunity_country_norm": normalize_text((selected_opportunity or {}).get("country_norm")),
            "selected_opportunity_hs_code_norm": normalize_text((selected_opportunity or {}).get("hs_code_norm")),
            "selected_opportunity_keywords_norm": normalize_text((selected_opportunity or {}).get("keywords_norm")),
            "selected_opportunity_valid_until": normalize_text((selected_opportunity or {}).get("valid_until")),
            "selected_opportunity_signal_type": normalize_text((selected_opportunity or {}).get("signal_type")),
            "selected_opportunity_signal_usable": bool((selected_opportunity or {}).get("signal_usable", False)),
            "selected_opportunity_match_score": int(_opportunity_fit_score(selected_opportunity or {}, supplier_profile)),
            "scoring_opportunity_applied": scoring_opportunity is not None,
            "total_buyer_rows": int(len(buyers)),
            "filtered_buyer_rows": int(len(filtered_buyers)),
            "scored_rows": int(len(scored_all)),
            "include_rejected": bool(include_rejected),
            "returned_count": returned_count,
            "shortlist_count": shortlist_count,
            "candidate_count": candidate_count,
            "rejected_count": rejected_count,
            "soft_penalty_row_count": soft_penalty_row_count,
            "soft_penalty_distribution": soft_penalty_distribution,
        },
        "items": items,
    }


def validate_shortlist_quality(result: Mapping[str, Any]) -> dict[str, Any]:
    items = list(result.get("items", []))
    if not items:
        return {
            "passed": False,
            "checks": {
                "returned_count": False,
                "contact_signal_ratio": False,
                "score_floor": False,
                "cosmetics_signal_ratio": False,
            },
            "metrics": {
                "returned_count": 0,
                "contact_signal_ratio": 0.0,
                "direct_contact_ratio": 0.0,
                "average_score": 0.0,
                "cosmetics_signal_ratio": 0.0,
            },
        }

    returned_count = len(items)
    direct_contact_ratio = (
        sum(
            1
            for item in items
            if item.get("contact_email")
            or item.get("contact_phone")
            or item.get("contact_website")
            or item.get("contact_name")
        )
        / returned_count
    )
    contact_signal_ratio = (
        sum(
            1
            for item in items
            if item.get("has_contact")
            or item.get("contact_email")
            or item.get("contact_phone")
            or item.get("contact_website")
            or item.get("contact_name")
        )
        / returned_count
    )
    average_score = sum(int(item.get("final_score", 0)) for item in items) / returned_count
    cosmetics_signal_ratio = (
        sum(
            1
            for item in items
            if str(item.get("hs_code_norm", "")).startswith("3304")
            or any(
                token
                for token in str(item.get("keywords_norm", "")).casefold().split(" | ")
                if token and token not in KEYWORD_MATCH_STOPWORDS and token in {"cosmetic", "cosmetics", "makeup", "serum", "cream", "mask", "ampoule", "bb cream", "beauty"}
            )
        )
        / returned_count
    )
    checks = {
        "returned_count": returned_count >= 20,
        "contact_signal_ratio": contact_signal_ratio >= 0.80,
        "score_floor": average_score >= 50.0,
        "cosmetics_signal_ratio": cosmetics_signal_ratio >= 0.70,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "metrics": {
            "returned_count": returned_count,
            "contact_signal_ratio": round(contact_signal_ratio, 3),
            "direct_contact_ratio": round(direct_contact_ratio, 3),
            "average_score": round(average_score, 2),
            "cosmetics_signal_ratio": round(cosmetics_signal_ratio, 3),
        },
    }
