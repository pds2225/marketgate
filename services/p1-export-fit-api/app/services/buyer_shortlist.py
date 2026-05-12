from __future__ import annotations

from collections import Counter, defaultdict
import sys
from datetime import date
from pathlib import Path
from typing import Any

from app.models import BuyerShortlistData


ROOT = Path(__file__).resolve().parents[4]
COSMETICS_DIR = ROOT / "services" / "cosmetics_mvp_preprocess"
COSMETICS_OUTPUT_DIR = COSMETICS_DIR / "output"
BUYER_CSV = COSMETICS_OUTPUT_DIR / "buyer_candidate.csv"
OPPORTUNITY_CSV = COSMETICS_OUTPUT_DIR / "opportunity_item.csv"

if str(COSMETICS_DIR) not in sys.path:
    sys.path.insert(0, str(COSMETICS_DIR))

from shortlist_service import build_supplier_profile, shortlist_buyers  # noqa: E402


ISO3_TO_TARGET_COUNTRY = {
    "AUS": "호주",
    "BRA": "브라질",
    "CAN": "캐나다",
    "CHN": "중국",
    "DEU": "독일",
    "FRA": "프랑스",
    "GBR": "영국",
    "HKG": "홍콩",
    "IDN": "인도네시아",
    "IND": "인도",
    "JPN": "일본",
    "MEX": "멕시코",
    "MYS": "말레이시아",
    "NLD": "네덜란드",
    "PHL": "필리핀",
    "SGP": "싱가포르",
    "THA": "태국",
    "TWN": "대만",
    "USA": "미국",
    "VNM": "베트남",
}

MAX_SOURCE_COUNTRIES = 3
_BLOCKED_BUYER_NAMES = {
    "medical device co",
    "medical cosmetics buyer",
}
_BLOCKED_BUYER_KEYWORDS = (
    "medical device",
    "pharma supplement",
    "beauty equipment",
)


def _is_blocked_item(item: dict[str, Any]) -> bool:
    buyer_name = str(item.get("buyer_name") or "").strip().casefold()
    if buyer_name in _BLOCKED_BUYER_NAMES:
        return True
    return any(keyword in buyer_name for keyword in _BLOCKED_BUYER_KEYWORDS)


def _empty_buyer_meta(source_countries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "returned_count": 0,
        "shortlist_count": 0,
        "candidate_count": 0,
        "rejected_count": 0,
        "filtered_buyer_rows": 0,
        "scored_rows": 0,
        "merged_country_count": len(source_countries),
        "deduped_item_count": 0,
        "selected_opportunity_titles": [],
        "selected_opportunity_countries": [],
        "selected_opportunity_signal_types": [],
        "selected_opportunity_match_scores": [],
        "soft_penalty_distribution": {},
        "country_shortlist_before_merge": {},
        "country_shortlist_after_merge": {},
        "country_shortlist_delta": {},
        "country_shortlist_comparison": {},
    }


def _source_country_from_result(result: dict[str, Any]) -> dict[str, Any] | None:
    iso3 = str(result.get("partner_country_iso3") or "").upper()
    target_country_name = ISO3_TO_TARGET_COUNTRY.get(iso3, "")
    if not iso3 or not target_country_name:
        return None
    return {
        "rank": int(result.get("rank") or 0),
        "partner_country_iso3": iso3,
        "target_country_name": target_country_name,
        "fit_score": float(result.get("fit_score") or 0.0),
    }


def _dedupe_key(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(item.get("buyer_name") or "").strip().casefold(),
        str(item.get("country_norm") or "").strip().casefold(),
        str(item.get("contact_email") or "").strip().casefold(),
        str(item.get("contact_website") or "").strip().casefold(),
        str(item.get("source_dataset") or "").strip().casefold(),
    )


def _merge_shortlist_results(
    *,
    source_countries: list[dict[str, Any]],
    shortlist_results: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    merged_items: list[dict[str, Any]] = []
    shortlist_total = 0
    candidate_total = 0
    rejected_total = 0
    total_filtered_rows = 0
    total_scored_rows = 0
    selected_titles: list[str] = []
    selected_countries: list[str] = []
    signal_types: list[str] = []
    match_score_entries: list[dict[str, Any]] = []
    soft_penalty_counter: Counter[str] = Counter()
    country_shortlist_before_merge: dict[str, int] = {}
    country_returned_after_merge: dict[str, int] = defaultdict(int)

    for source_country, shortlist in zip(source_countries, shortlist_results):
        meta = shortlist.get("meta") or {}
        shortlist_total += int(meta.get("shortlist_count", 0) or 0)
        candidate_total += int(meta.get("candidate_count", 0) or 0)
        rejected_total += int(meta.get("rejected_count", 0) or 0)
        total_filtered_rows += int(meta.get("filtered_buyer_rows", 0) or 0)
        total_scored_rows += int(meta.get("scored_rows", 0) or 0)
        country_key = source_country["partner_country_iso3"]
        country_shortlist_before_merge[country_key] = int(meta.get("shortlist_count", 0) or 0)
        soft_penalty_counter.update(
            {
                str(key): int(value or 0)
                for key, value in (meta.get("soft_penalty_distribution") or {}).items()
            }
        )

        selected_title = str(meta.get("selected_opportunity_title") or "").strip()
        selected_country = str(meta.get("selected_opportunity_country_norm") or "").strip()
        signal_type = str(meta.get("selected_opportunity_signal_type") or "").strip()
        match_score = int(meta.get("selected_opportunity_match_score") or 0)
        if selected_title:
            selected_titles.append(selected_title)
        if selected_country:
            selected_countries.append(selected_country)
        if signal_type:
            signal_types.append(signal_type)
        match_score_entries.append({
            "country_iso3": country_key,
            "opportunity_title": selected_title,
            "match_score": match_score,
        })

        for item in shortlist.get("items") or []:
            enriched = dict(item)
            enriched["source_target_country_iso3"] = source_country["partner_country_iso3"]
            enriched["source_target_country_name"] = source_country["target_country_name"]
            enriched["source_target_country_rank"] = source_country["rank"]
            enriched["_source_fit_score"] = source_country["fit_score"]
            merged_items.append(enriched)

    deduped_items: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    merged_items.sort(
        key=lambda item: (
            {"shortlist": 2, "candidate": 1, "rejected": 0}.get(str(item.get("decision") or ""), 0),
            float(item.get("final_score") or 0.0),
            1 if item.get("has_contact") else 0,
            float(item.get("_source_fit_score") or 0.0),
            -(int(item.get("source_target_country_rank") or 999)),
        ),
        reverse=True,
    )
    for item in merged_items:
        key = _dedupe_key(item)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        item.pop("_source_fit_score", None)
        deduped_items.append(item)

    deduped_items = [item for item in deduped_items if not _is_blocked_item(item)]

    if limit > 0:
        deduped_items = deduped_items[:limit]

    for item in deduped_items:
        source_iso3 = str(item.get("source_target_country_iso3") or "").upper()
        if source_iso3:
            country_returned_after_merge[source_iso3] += 1

    country_shortlist_after_merge = {
        source_country["partner_country_iso3"]: int(country_returned_after_merge.get(source_country["partner_country_iso3"], 0))
        for source_country in source_countries
    }
    country_shortlist_delta = {
        iso3: country_shortlist_after_merge.get(iso3, 0) - before_count
        for iso3, before_count in country_shortlist_before_merge.items()
    }
    country_shortlist_comparison = {
        iso3: {
            "country_name": ISO3_TO_TARGET_COUNTRY.get(iso3, ""),
            "before_merge_shortlist_count": before_count,
            "after_merge_returned_count": country_shortlist_after_merge.get(iso3, 0),
            "delta": country_shortlist_delta.get(iso3, 0),
        }
        for iso3, before_count in country_shortlist_before_merge.items()
    }

    merged_meta = {
        "returned_count": len(deduped_items),
        "shortlist_count": shortlist_total,
        "candidate_count": candidate_total,
        "rejected_count": rejected_total,
        "filtered_buyer_rows": total_filtered_rows,
        "scored_rows": total_scored_rows,
        "merged_country_count": len(source_countries),
        "deduped_item_count": len(deduped_items),
        "selected_opportunity_titles": selected_titles,
        "selected_opportunity_countries": selected_countries,
        "selected_opportunity_signal_types": signal_types,
        "selected_opportunity_match_scores": match_score_entries,
        "soft_penalty_distribution": dict(sorted(soft_penalty_counter.items())),
        "country_shortlist_before_merge": country_shortlist_before_merge,
        "country_shortlist_after_merge": country_shortlist_after_merge,
        "country_shortlist_delta": country_shortlist_delta,
        "country_shortlist_comparison": country_shortlist_comparison,
    }
    return deduped_items, merged_meta


def build_buyer_shortlist(req: Any, country_results: list[dict[str, Any]]) -> BuyerShortlistData:
    source_countries = [
        source_country
        for source_country in (_source_country_from_result(result) for result in country_results[:MAX_SOURCE_COUNTRIES])
        if source_country is not None
    ]
    top_country = source_countries[0] if source_countries else {}
    top_country_iso3 = str(top_country.get("partner_country_iso3") or "").upper()
    target_country_name = str(top_country.get("target_country_name") or "")
    limit = min(int(getattr(req, "top_n", 5) or 5), 10)
    include_rejected = bool(getattr(req, "include_rejected", False))

    if not BUYER_CSV.exists():
        meta = _empty_buyer_meta(source_countries)
        meta["missing_output"] = True
        meta["missing_files"] = [str(BUYER_CSV)]
        return BuyerShortlistData(
            status="ok",
            target_country_iso3=top_country_iso3,
            target_country_name=target_country_name or None,
            source_countries=source_countries,
            meta=meta,
            items=[],
            error=None,
        )

    # opportunity_item.csv가 없으면 임시 빈 파일 생성 (shortlist_service 호환성)
    if not OPPORTUNITY_CSV.exists():
        try:
            import pandas as pd
            empty_opportunity = pd.DataFrame(columns=[
                "title", "country_norm", "hs_code_norm", "keywords_norm",
                "product_name_norm", "signal_usable", "valid_until"
            ])
            OPPORTUNITY_CSV.parent.mkdir(parents=True, exist_ok=True)
            empty_opportunity.to_csv(OPPORTUNITY_CSV, index=False, encoding="utf-8-sig")
        except Exception as exc:
            logger.warning(f"[buyer_shortlist] opportunity_item.csv 임시 생성 실패: {exc}")

    try:
        shortlist_results: list[dict[str, Any]] = []
        # 키워드를 req에서 가져오거나 HS 코드 기반 추론에 맡김
        target_keywords = str(
            getattr(req, "target_keywords_norm", "") or getattr(req, "keywords", "") or ""
        )
        # 국가별 내부 후보 풀을 넓혀 병합 후 상위 limit 선택 품질 향상
        internal_limit = min(limit * 3, 30)
        for source_country in source_countries:
            supplier_profile = build_supplier_profile(
                supplier_name="ValueUp Supplier",
                target_country_norm=source_country["target_country_name"],
                target_hs_code_norm=str(getattr(req, "hs_code", "") or ""),
                target_keywords_norm=target_keywords,
            )
            shortlist_results.append(
                shortlist_buyers(
                    output_dir=COSMETICS_OUTPUT_DIR,
                    supplier_profile=supplier_profile,
                    reference_date=date.today(),
                    limit=internal_limit,
                    opportunity_country_norm=source_country["target_country_name"],
                    include_rejected=include_rejected,
                )
            )

        items, merged_meta = _merge_shortlist_results(
            source_countries=source_countries,
            shortlist_results=shortlist_results,
            limit=limit,
        )
        return BuyerShortlistData(
            status="ok",
            target_country_iso3=top_country_iso3,
            target_country_name=target_country_name or None,
            source_countries=source_countries,
            meta=merged_meta,
            items=items,
            error=None,
        )
    except Exception as exc:
        return BuyerShortlistData(
            status="unavailable",
            target_country_iso3=top_country_iso3,
            target_country_name=target_country_name or None,
            source_countries=source_countries,
            meta=_empty_buyer_meta(source_countries),
            items=[],
            error=str(exc),
        )
