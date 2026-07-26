from __future__ import annotations

from collections import Counter, defaultdict
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

from app.models import BuyerShortlistData

logger = logging.getLogger(__name__)


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

# 가산 (matchA): 바이어 출처 신뢰도 — SNS 스크랩은 '미검증 시장신호'로 표기.
# 키워드(부분 일치)로 source_dataset 한글 표기를 분류한다.
_UNVERIFIED_SOURCE_KEYWORDS = ("SNS",)
_VERIFIED_SOURCE_KEYWORDS = (
    "ITC",
    "TradeMap",
    "무역보험공사",
    "인콰이어리",
    "buyKOREA",
    "GoBizKorea",
    "B2B",
)


def _source_trust(source_dataset: str | None) -> tuple[str, bool]:
    """source_dataset → (신뢰등급, source_verified).

    - SNS 스크랩 계열: unverified (참고용 시장신호)
    - ITC/무역보험공사/인콰이어리 등 공식 거래/문의 출처: verified
    - 그 외: unknown (검증여부 미상)
    """
    text = str(source_dataset or "")
    if any(kw in text for kw in _UNVERIFIED_SOURCE_KEYWORDS):
        return "unverified", False
    if any(kw in text for kw in _VERIFIED_SOURCE_KEYWORDS):
        return "verified", True
    return "unknown", False


# 가산 (matchC): HS 관련성 등급 — 강한 HS 매칭은 우선, 약한 매칭(chapter 2자리·키워드)은 강등.
# 결과가 비지 않게 약한 매칭도 제거하지 않고 'weak'로 표기만 한다(폴백 노출).
_STRONG_MATCH_MODES = frozenset(
    {"hs_exact", "hs_prefix_4", "hs_inferred", "hs_inferred_prefix_4"}
)
_WEAK_MATCH_MODES = frozenset({"hs_prefix_2", "keyword"})


def _match_relevance(item: dict[str, Any]) -> str:
    """바이어 아이템의 HS/키워드 매칭 강도를 strong/weak/none으로 분류한다(가산).

    score_breakdown.hs_match_type을 1차 신호로, matched_by를 보조 신호로 본다.
    HS prefix-2(다른 4자리)·키워드-only 매칭은 'weak'로 강등 표기한다.
    """
    breakdown = item.get("score_breakdown") or {}
    mode = str(breakdown.get("hs_match_type") or item.get("matched_by") or "").strip()
    if mode in _STRONG_MATCH_MODES:
        return "strong"
    if mode in _WEAK_MATCH_MODES:
        return "weak"
    # hs_match_type이 비어도 matched_by가 강한 모드면 strong으로 인정
    matched_by = str(item.get("matched_by") or "").strip()
    if matched_by in _STRONG_MATCH_MODES:
        return "strong"
    if matched_by in _WEAK_MATCH_MODES:
        return "weak"
    return "none"


# matchD: 정렬 우선순위 키. 무관(none) 바이어가 decision=shortlist만으로
# 관련(strong/weak) 바이어를 제치는 것을 막는다(관련성 정확도 강화).
_DECISION_RANK = {"shortlist": 2, "candidate": 1, "rejected": 0}
_RELEVANCE_RANK = {"strong": 2, "weak": 1, "none": 0}


def _buyer_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    """바이어 정렬 키(내림차순 reverse=True). 관련성을 decision보다 먼저 보호한다(matchD).

    무관(none = HS/키워드 매칭 0)은 decision이 shortlist여도 effective 상위 티어를
    candidate(1)로 강등한다 → strong/weak 바이어가 항상 무관 바이어보다 위에 온다.
    관련성이 같으면 기존 우선순위(decision > 검증연락처 > 출처 > 점수)를 그대로 따른다.
    기존 응답 필드는 불변(정렬 순서만 정교화).
    """
    relevance_rank = _RELEVANCE_RANK.get(str(item.get("match_relevance") or "none"), 0)
    decision_rank = _DECISION_RANK.get(str(item.get("decision") or ""), 0)
    if relevance_rank == 0:
        decision_rank = min(decision_rank, 1)
    return (
        decision_rank,
        relevance_rank,
        1 if item.get("has_verified_contact") else 0,
        1 if item.get("source_verified") else 0,
        float(item.get("final_score") or 0.0),
        1 if item.get("has_contact") else 0,
        float(item.get("_source_fit_score") or 0.0),
        -(int(item.get("source_target_country_rank") or 999)),
    )


def _has_verified_contact(item: dict[str, Any]) -> bool:
    """검증된(추정 아님) 연락처 보유 여부 — 이메일이 추정이면 다른 연락수단이 있어야 인정.

    estimated 이메일밖에 없으면 '연락 가능'으로 보지 않는다(audit #3).
    """
    has_phone = bool(str(item.get("contact_phone") or "").strip())
    has_website = bool(str(item.get("contact_website") or "").strip())
    has_name = bool(str(item.get("contact_name") or "").strip())
    has_email = bool(str(item.get("contact_email") or "").strip())
    email_estimated = bool(item.get("contact_email_estimated"))
    has_verified_email = has_email and not email_estimated
    return has_verified_email or has_phone or has_website or has_name


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
        "buyer_country_mismatch": None,
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


def _build_country_mismatch_warning(
    source_countries: list[dict[str, Any]],
    returned_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """추천 1위국과 실제 반환 바이어의 주력 국가가 다르면 경고를 만든다(가산, matchA).

    반환된 바이어가 없으면 None. 1위국 바이어가 하나라도 반환되면 일치로 간주(None).
    """
    if not source_countries or not returned_items:
        return None
    top = source_countries[0]
    top_iso3 = str(top.get("partner_country_iso3") or "").upper()
    top_name = str(top.get("target_country_name") or "")

    counts: Counter[str] = Counter()
    for item in returned_items:
        iso3 = str(item.get("source_target_country_iso3") or "").upper()
        if iso3:
            counts[iso3] += 1
    if not counts:
        return None
    # 1위 추천국 바이어가 하나라도 있으면 불일치 아님
    if counts.get(top_iso3, 0) > 0:
        return None

    dominant_iso3, dominant_count = counts.most_common(1)[0]
    dominant_name = ISO3_TO_TARGET_COUNTRY.get(dominant_iso3, dominant_iso3)
    return {
        "code": "BUYER_COUNTRY_MISMATCH",
        "severity": "high",
        "recommended_country_iso3": top_iso3,
        "recommended_country_name": top_name,
        "returned_buyer_country_iso3": dominant_iso3,
        "returned_buyer_country_name": dominant_name,
        "message": (
            f"추천 1위국({top_name or top_iso3})에 노출 가능한 바이어가 없어 "
            f"{dominant_name} 바이어로 대체되었습니다. 추천국과 바이어국이 다릅니다."
        ),
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
        # 구매 신호 상세: shortlist_service meta에 이미 있는 필드를 고객 화면용으로 전달(신규 소스/합성 없음)
        opportunity_hs = str(meta.get("selected_opportunity_hs_code_norm") or "").strip()
        opportunity_keywords = str(meta.get("selected_opportunity_keywords_norm") or "").strip()
        opportunity_valid_until = str(meta.get("selected_opportunity_valid_until") or "").strip()
        opportunity_usable = bool(meta.get("selected_opportunity_signal_usable", False))
        opportunity_applied = bool(meta.get("scoring_opportunity_applied", False))
        opportunity_source = str(meta.get("selected_opportunity_source_dataset") or "").strip()
        opportunity_source_file = str(meta.get("selected_opportunity_source_file") or "").strip()
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
            "opportunity_country_norm": selected_country,
            "opportunity_signal_type": signal_type,
            "opportunity_hs_code_norm": opportunity_hs,
            "opportunity_keywords_norm": opportunity_keywords,
            "opportunity_valid_until": opportunity_valid_until,
            "opportunity_signal_usable": opportunity_usable,
            "scoring_opportunity_applied": opportunity_applied,
            "opportunity_source_dataset": opportunity_source,
            "opportunity_source_file": opportunity_source_file,
        })

        for item in shortlist.get("items") or []:
            enriched = dict(item)
            enriched["source_target_country_iso3"] = source_country["partner_country_iso3"]
            enriched["source_target_country_name"] = source_country["target_country_name"]
            enriched["source_target_country_rank"] = source_country["rank"]
            enriched["_source_fit_score"] = source_country["fit_score"]
            merged_items.append(enriched)

    # 가산 (matchA/matchC): 출처 신뢰도·추정 연락처·HS 관련성 등급을 정렬 전에 부여한다.
    # (기존 필드 불변, 추가만 / 정렬에 반영하기 위해 dedup·sort 전에 계산)
    for item in merged_items:
        verification, source_verified = _source_trust(item.get("source_dataset"))
        item["source_verification"] = verification
        item["source_verified"] = source_verified
        has_email = bool(str(item.get("contact_email") or "").strip())
        # shortlist_service가 contact_email_estimated를 제공하면 그대로 사용, 없으면 False
        item["contact_email_estimated"] = bool(item.get("contact_email_estimated", False)) and has_email
        # matchC: HS/키워드 관련성 등급 (strong=강한 HS, weak=prefix-2/keyword)
        item["match_relevance"] = _match_relevance(item)
        # matchC: 검증 연락처(추정 제외) 보유 여부
        item["has_verified_contact"] = _has_verified_contact(item)

    deduped_items: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    # matchC: 관련성·연락처·출처신뢰도를 decision/final_score 다음 우선순위로 반영한다.
    #   - 강한 HS 매칭 > 약한 매칭 (audit #7/#8) — 단 약한 매칭도 제거하지 않고 후순위 노출(폴백)
    #   - 검증 연락처 보유 우선 (audit #3) — 추정 이메일뿐인 바이어는 뒤로
    #   - 검증 출처(ITC/KSURE/인콰이어리) > SNS 스크랩 (audit #2)
    #   - 관련성 보호(matchD): 무관(none)은 shortlist여도 관련(strong/weak) 바이어를 추월 못 함
    merged_items.sort(key=_buyer_sort_key, reverse=True)
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

    # 가산 (matchA): 추천 1위국 ↔ 실제 반환 바이어국 불일치 경고를 메타로 승격한다.
    buyer_country_warning = _build_country_mismatch_warning(source_countries, deduped_items)

    # 가산 (matchC): 반환 바이어의 연락처 가용성·관련성 요약 (사용자가 '연락 가능' 여부를 즉시 파악)
    returned_total = len(deduped_items)
    contactable_count = sum(1 for item in deduped_items if item.get("has_contact"))
    verified_contactable_count = sum(
        1 for item in deduped_items if item.get("has_verified_contact")
    )
    relevance_counter: Counter[str] = Counter(
        str(item.get("match_relevance") or "none") for item in deduped_items
    )

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
        # 가산 (matchA): 추천국↔바이어국 불일치 경고 (None이면 일치)
        "buyer_country_mismatch": buyer_country_warning,
        # 가산 (matchC): 연락 가능 바이어 수 (검증 연락처/전체 연락처/총)
        "contactable_count": contactable_count,
        "verified_contactable_count": verified_contactable_count,
        "returned_total_count": returned_total,
        "contactable_summary": (
            f"연락 가능 {verified_contactable_count}/{returned_total}"
            if returned_total
            else "연락 가능 0/0"
        ),
        # 가산 (matchC): HS 관련성 등급 분포 (strong=강한 매칭, weak=약한 매칭)
        "match_relevance_distribution": dict(sorted(relevance_counter.items())),
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
