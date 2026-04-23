from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task05_shortlist import (  # noqa: E402
    KEYWORD_MATCH_STOPWORDS,
    buyer_hard_gate,
    match_hs_or_keywords,
    normalize_country,
    normalize_hs_code,
    normalize_keywords,
    normalize_opportunity_record,
    normalize_text,
    opportunity_hard_gate,
    parse_date,
)


SCORE_WEIGHTS = {
    "hs_score": 30,
    "country_score": 20,
    "signal_score": 15,
    "recency_score": 10,
    "capacity_score": 10,
    "contact_score": 5,
    "keyword_score": 10,
}
SHORTLIST_THRESHOLD = 70
SMOKE_KEYWORD_RE = re.compile(
    r"cosmetic|makeup|serum|cream|mask|sunscreen|shampoo|toner|ampoule|lotion|lipstick|foundation",
    re.IGNORECASE,
)
DEFAULT_SMOKE_SUPPLIER_PROFILE = {
    "supplier_name": "MarketGate Cosmetics Supplier",
    "target_country_norm": "미국",
    "target_hs_code_norm": "3304",
    "target_keywords_norm": "cosmetics | makeup | serum | cream | mask | sunscreen | shampoo | toner",
}


def _first_non_empty(record: Mapping[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = normalize_text(record.get(key))
        if value:
            return value
    return ""


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = normalize_text(value).casefold()
    return text in {"1", "true", "y", "yes", "t"}


def _to_float(value: Any) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.]+", "", text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_banned_countries(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        banned = [normalize_text(item) for item in value if normalize_text(item)]
        return banned or None
    text = normalize_text(value)
    if not text:
        return None
    banned = [normalize_text(item) for item in re.split(r"[,\|;/]+", text) if normalize_text(item)]
    return banned or None


def _target_context(
    supplier_profile: Mapping[str, Any] | None,
    opportunity: Mapping[str, Any] | None,
) -> dict[str, str]:
    supplier = supplier_profile or {}
    target_country = _first_non_empty(
        supplier,
        ("target_country_norm", "preferred_country_norm", "country_norm", "country"),
    )
    target_hs = _first_non_empty(
        supplier,
        ("target_hs_code_norm", "hs_code_norm", "hs_code", "product_hs_code_norm"),
    )
    target_keywords = _first_non_empty(
        supplier,
        (
            "target_keywords_norm",
            "keywords_norm",
            "keywords",
            "product_keywords_norm",
            "product_keywords",
        ),
    )
    target_product_name = _first_non_empty(
        supplier,
        ("target_product_name_norm", "product_name_norm", "product_name", "product"),
    )
    target_title = _first_non_empty(supplier, ("target_title", "title"))

    if opportunity is not None:
        if not target_country:
            target_country = _first_non_empty(opportunity, ("country_norm", "country", "country_raw"))
        if not target_hs:
            target_hs = _first_non_empty(opportunity, ("hs_code_norm", "hs_code", "hs_code_raw"))
        if not target_keywords:
            target_keywords = _first_non_empty(opportunity, ("keywords_norm", "keywords_raw"))
        if not target_product_name:
            target_product_name = _first_non_empty(opportunity, ("product_name_norm", "normalized_name"))
        if not target_title:
            target_title = _first_non_empty(opportunity, ("title",))

    return {
        "country_norm": normalize_text(target_country),
        "hs_code_norm": normalize_hs_code(target_hs),
        "keywords_norm": normalize_keywords(target_keywords),
        "product_name_norm": normalize_text(target_product_name),
        "title": normalize_text(target_title),
    }


def _required_capacity(supplier_profile: Mapping[str, Any] | None) -> float | None:
    supplier = supplier_profile or {}
    for key in ("required_capacity", "min_capacity", "target_capacity"):
        value = _to_float(supplier.get(key))
        if value is not None:
            return value
    return None


def _normalized_opportunity(
    opportunity: Mapping[str, Any] | None,
    reference_date: date | None,
) -> dict[str, Any] | None:
    if opportunity is None:
        return None
    return normalize_opportunity_record(opportunity, reference_date=reference_date)


def _build_gate_bundle(
    buyer: Mapping[str, Any],
    supplier_profile: Mapping[str, Any] | None,
    opportunity: Mapping[str, Any] | None,
    gate_result: Mapping[str, Any] | None,
    reference_date: date | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    normalized_opportunity = _normalized_opportunity(opportunity, reference_date=reference_date)
    target = _target_context(supplier_profile, normalized_opportunity)
    required_capacity = _required_capacity(supplier_profile)
    banned_countries = _parse_banned_countries((supplier_profile or {}).get("banned_countries"))

    buyer_gate_input: Mapping[str, Any] | None = None
    opportunity_gate_input: Mapping[str, Any] | None = None
    if gate_result is not None:
        if "buyer_gate" in gate_result or "opportunity_gate" in gate_result:
            buyer_gate_input = gate_result.get("buyer_gate")  # type: ignore[assignment]
            opportunity_gate_input = gate_result.get("opportunity_gate")  # type: ignore[assignment]
        else:
            buyer_gate_input = gate_result

    buyer_gate = dict(
        buyer_gate_input
        or buyer_hard_gate(
            buyer,
            normalized_opportunity,
            target_country_norm=target["country_norm"],
            target_hs_code_norm=target["hs_code_norm"],
            target_keywords_norm=target["keywords_norm"],
            target_product_name_norm=target["product_name_norm"],
            target_title=target["title"],
            banned_countries=banned_countries,
            required_capacity=required_capacity,
        )
    )

    opportunity_gate: dict[str, Any] | None = None
    if normalized_opportunity is not None:
        opportunity_gate = dict(
            opportunity_gate_input
            or opportunity_hard_gate(normalized_opportunity, reference_date=reference_date)
        )

    return target, buyer_gate, opportunity_gate


def _keyword_terms(record: Mapping[str, Any], keys: Iterable[str]) -> set[str]:
    tokens: set[str] = set()
    for key in keys:
        normalized = normalize_keywords(record.get(key))
        if not normalized:
            normalized = normalize_keywords(normalize_text(record.get(key)).replace(" ", " | "))
        for token in normalized.split(" | "):
            raw_candidates = [token.casefold(), *re.split(r"[\s_\-\/,&\(\)\[\]]+", token.casefold())]
            for candidate in raw_candidates:
                compact = re.sub(r"[^0-9a-z가-힣]+", "", candidate)
                if len(compact) <= 2 or compact in KEYWORD_MATCH_STOPWORDS:
                    continue
                tokens.add(compact)
    return tokens


def _keyword_overlap(buyer: Mapping[str, Any], target: Mapping[str, Any]) -> list[str]:
    buyer_terms = _keyword_terms(buyer, ("keywords_norm", "normalized_name", "title"))
    target_terms = _keyword_terms(target, ("keywords_norm", "product_name_norm", "title"))
    return sorted(buyer_terms & target_terms)


def _keyword_hint_regex(supplier_profile: Mapping[str, Any]) -> re.Pattern[str] | None:
    raw_keywords = normalize_keywords(supplier_profile.get("target_keywords_norm"))
    tokens: list[str] = []
    for token in raw_keywords.split(" | "):
        token = token.strip()
        if len(token) <= 3:
            continue
        if re.sub(r"[^0-9a-z가-힣]+", "", token.casefold()) in KEYWORD_MATCH_STOPWORDS:
            continue
        tokens.append(re.escape(token))
    if not tokens:
        return None
    return re.compile("|".join(tokens), re.IGNORECASE)


def _has_usable_contact(buyer: Mapping[str, Any]) -> bool:
    return bool(
        _first_non_empty(
            buyer,
            ("contact_email", "contact_phone", "contact_website", "contact_name"),
        )
    )


def _contact_score(buyer: Mapping[str, Any]) -> int:
    if _has_usable_contact(buyer):
        return SCORE_WEIGHTS["contact_score"]
    return 0


def _capacity_score(buyer: Mapping[str, Any], required_capacity: float | None) -> int:
    if required_capacity is None or required_capacity <= 0:
        return 0
    capacity = None
    for key in ("capacity", "monthly_capacity", "annual_capacity", "production_capacity", "supply_capacity", "max_capacity"):
        value = _to_float(buyer.get(key))
        if value is not None:
            capacity = value
            break
    if capacity is None:
        return 0
    ratio = capacity / required_capacity
    if ratio >= 1.5:
        return SCORE_WEIGHTS["capacity_score"]
    if ratio >= 1.2:
        return 8
    if ratio >= 1.0:
        return 6
    return 0


def _country_score(buyer: Mapping[str, Any], target: Mapping[str, Any]) -> int:
    target_country = normalize_country(target.get("country_norm"))
    buyer_country = normalize_country(_first_non_empty(buyer, ("country_norm", "country", "country_raw")))
    if target_country and buyer_country and target_country == buyer_country:
        return SCORE_WEIGHTS["country_score"]
    return 0


def _hs_score(match_mode: str) -> int:
    if match_mode == "hs_exact":
        return SCORE_WEIGHTS["hs_score"]
    if match_mode == "hs_prefix_4":
        return 27
    if match_mode == "hs_prefix_2":
        return 22
    return 0


def _keyword_score(match_mode: str, overlap_terms: list[str]) -> int:
    overlap_count = len(overlap_terms)
    if overlap_count <= 0:
        return 0
    if match_mode.startswith("hs"):
        return min(3, overlap_count)
    if overlap_count >= 3:
        return SCORE_WEIGHTS["keyword_score"]
    if overlap_count == 2:
        return 8
    return 6


def _score_signal(opportunity_gate: Mapping[str, Any] | None) -> int:
    if opportunity_gate and opportunity_gate.get("passed") and _normalize_bool(opportunity_gate.get("signal_usable")):
        return SCORE_WEIGHTS["signal_score"]
    return 0


def _recency_score(opportunity: Mapping[str, Any] | None, opportunity_gate: Mapping[str, Any] | None, reference_date: date | None) -> int:
    if opportunity is None or opportunity_gate is None or _normalize_bool(opportunity_gate.get("expired")):
        return 0
    ref = reference_date or date.today()
    valid_until = parse_date(opportunity.get("valid_until"))
    created_at = parse_date(opportunity.get("created_at"))
    if valid_until is not None:
        days = (valid_until - ref).days
    elif created_at is not None:
        days = (ref - created_at).days
    else:
        return 0
    if days < 0:
        return 0
    if days <= 30:
        return SCORE_WEIGHTS["recency_score"]
    if days <= 90:
        return 8
    if days <= 183:
        return 6
    return 0


def _zero_breakdown() -> dict[str, int]:
    return {key: 0 for key in SCORE_WEIGHTS}


def _gate_failure_reasons(buyer_gate: Mapping[str, Any], opportunity_gate: Mapping[str, Any] | None) -> list[str]:
    mapping = {
        "country_mismatch": "타깃 국가와 buyer 국가가 맞지 않아 Hard Gate에서 탈락했습니다.",
        "banned_country": "금지 국가 규칙에 걸려 후보에서 제외했습니다.",
        "hs_mismatch": "제품 HS 또는 핵심 키워드가 맞지 않아 탈락했습니다.",
        "capacity_fail": "요구 생산능력을 충족하지 못해 탈락했습니다.",
        "signal_type_invalid": "signal_type이 shortlist 대상 유형이 아니어서 탈락했습니다.",
        "expired": "기회 신호가 만료되어 점수 계산 대상에서 제외했습니다.",
        "ambiguous_product": "title/product가 불명확해 점수 계산 대상에서 제외했습니다.",
    }
    reasons = []
    for code in buyer_gate.get("gate_reason", []):
        reasons.append(mapping.get(str(code), f"Hard Gate 사유: {code}"))
    if opportunity_gate is not None:
        for code in opportunity_gate.get("gate_reason", []):
            reasons.append(mapping.get(str(code), f"Hard Gate 사유: {code}"))
    if not reasons:
        reasons.append("Hard Gate 미통과로 Fit Score 계산을 생략했습니다.")
    while len(reasons) < 3:
        reasons.append("Hard Gate 미통과로 ranking 후보에서 제외했습니다.")
    return reasons[:3]


def _explanation_reasons(
    buyer: Mapping[str, Any],
    target: Mapping[str, Any],
    normalized_opportunity: Mapping[str, Any] | None,
    buyer_gate: Mapping[str, Any],
    opportunity_gate: Mapping[str, Any] | None,
    score_breakdown: Mapping[str, int],
    match_result: Mapping[str, Any],
    overlap_terms: list[str],
    required_capacity: float | None,
) -> list[str]:
    if not buyer_gate.get("passed") or (opportunity_gate is not None and not opportunity_gate.get("passed")):
        return _gate_failure_reasons(buyer_gate, opportunity_gate)

    buyer_hs = normalize_hs_code(_first_non_empty(buyer, ("hs_code_norm", "hs_code", "hs_code_raw")))
    target_hs = normalize_hs_code(target.get("hs_code_norm"))
    target_country = normalize_text(target.get("country_norm"))
    buyer_country = normalize_text(_first_non_empty(buyer, ("country_norm", "country", "country_raw")))

    if score_breakdown["hs_score"] > 0:
        if overlap_terms:
            reason_1 = (
                f"HS 적합도가 높습니다 ({buyer_hs or '-'} vs {target_hs or '-'}) "
                f"그리고 {', '.join(overlap_terms[:2])} 키워드가 함께 겹칩니다."
            )
        else:
            reason_1 = f"HS 적합도가 높습니다 ({buyer_hs or '-'} vs {target_hs or '-'})."
    elif score_breakdown["keyword_score"] > 0:
        reason_1 = f"제품 키워드가 맞물립니다 ({', '.join(overlap_terms[:3])})."
    else:
        reason_1 = "제품 적합성은 Hard Gate 기준을 통과했지만 추가 가점은 제한적입니다."

    if score_breakdown["country_score"] > 0:
        reason_2 = f"타깃 국가 {target_country}과 buyer 국가 {buyer_country}이 일치합니다."
    else:
        reason_2 = "국가 조건은 추가 가점을 만들 정도로 명확하지 않았습니다."

    execution_parts: list[str] = []
    if score_breakdown["signal_score"] > 0 and normalized_opportunity is not None:
        signal_type = normalize_text((opportunity_gate or {}).get("signal_type")) or normalize_text(normalized_opportunity.get("signal_type"))
        execution_parts.append(f"최근 6개월 내 사용 가능한 {signal_type or 'opportunity'} signal이 있습니다")
    if score_breakdown["recency_score"] > 0:
        execution_parts.append("신호 시점이 비교적 최근입니다")
    if score_breakdown["capacity_score"] > 0 and required_capacity is not None:
        execution_parts.append(f"요구 생산능력 {required_capacity:g} 기준을 충족합니다")
    if score_breakdown["contact_score"] > 0:
        execution_parts.append("연락 가능한 contact 정보가 확인됩니다")
    if not execution_parts:
        execution_parts.append("실행 가능성 관련 가점은 제한적입니다")
    reason_3 = ", ".join(execution_parts) + "."

    return [reason_1, reason_2, reason_3]


def recommendation_lines_v0(score_result: Mapping[str, Any]) -> list[str]:
    lines = [normalize_text(line) for line in score_result.get("explanation_reasons", []) if normalize_text(line)]
    while len(lines) < 3:
        lines.append("추천 근거를 생성할 수 있는 정보가 제한적입니다.")
    return lines[:3]


def fit_score_v0(
    buyer: Mapping[str, Any],
    supplier_profile: Mapping[str, Any],
    opportunity: Mapping[str, Any] | None = None,
    gate_result: Mapping[str, Any] | None = None,
    reference_date: date | None = None,
) -> dict[str, Any]:
    normalized_opportunity = _normalized_opportunity(opportunity, reference_date=reference_date)
    target, buyer_gate, opportunity_gate = _build_gate_bundle(
        buyer=buyer,
        supplier_profile=supplier_profile,
        opportunity=normalized_opportunity,
        gate_result=gate_result,
        reference_date=reference_date,
    )

    gate_passed = _normalize_bool(buyer_gate.get("passed"))
    if opportunity_gate is not None:
        gate_passed = gate_passed and _normalize_bool(opportunity_gate.get("passed"))

    if not gate_passed:
        explanation_reasons = _gate_failure_reasons(buyer_gate, opportunity_gate)
        return {
            "final_score": 0,
            "score_breakdown": _zero_breakdown(),
            "explanation_reasons": explanation_reasons,
            "recommendation_lines": recommendation_lines_v0({"explanation_reasons": explanation_reasons}),
            "decision": "rejected",
            "matched_by": "",
            "matched_terms": [],
            "gate_result": {
                "buyer_gate": buyer_gate,
                "opportunity_gate": opportunity_gate,
            },
        }

    match_result = match_hs_or_keywords(buyer, target)
    overlap_terms = _keyword_overlap(buyer, target)
    required_capacity = _required_capacity(supplier_profile)

    matched_by = normalize_text(buyer_gate.get("matched_by")) or normalize_text(match_result.get("match_mode"))
    breakdown = {
        "hs_score": _hs_score(matched_by),
        "keyword_score": _keyword_score(matched_by or normalize_text(match_result.get("match_mode")), overlap_terms),
        "country_score": _country_score(buyer, target),
        "capacity_score": _capacity_score(buyer, required_capacity),
        "contact_score": _contact_score(buyer),
        "recency_score": _recency_score(normalized_opportunity, opportunity_gate, reference_date),
        "signal_score": _score_signal(opportunity_gate),
    }
    final_score = int(sum(breakdown.values()))
    decision = "shortlist" if final_score >= SHORTLIST_THRESHOLD else "candidate"
    explanation_reasons = _explanation_reasons(
        buyer=buyer,
        target=target,
        normalized_opportunity=normalized_opportunity,
        buyer_gate=buyer_gate,
        opportunity_gate=opportunity_gate,
        score_breakdown=breakdown,
        match_result=match_result,
        overlap_terms=overlap_terms,
        required_capacity=required_capacity,
    )

    return {
        "final_score": final_score,
        "score_breakdown": breakdown,
        "explanation_reasons": explanation_reasons,
        "recommendation_lines": recommendation_lines_v0({"explanation_reasons": explanation_reasons}),
        "decision": decision,
        "matched_by": matched_by,
        "matched_terms": overlap_terms[:5],
        "gate_result": {
            "buyer_gate": buyer_gate,
            "opportunity_gate": opportunity_gate,
        },
    }


def score_buyers(
    buyers: Iterable[Mapping[str, Any]],
    supplier_profile: Mapping[str, Any],
    opportunity: Mapping[str, Any] | None = None,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for buyer in buyers:
        result = fit_score_v0(
            buyer=buyer,
            supplier_profile=supplier_profile,
            opportunity=opportunity,
            reference_date=reference_date,
        )
        enriched = dict(result)
        enriched["buyer"] = dict(buyer)
        results.append(enriched)
    results.sort(
        key=lambda item: (
            {"shortlist": 2, "candidate": 1, "rejected": 0}.get(item["decision"], 0),
            item["final_score"],
            item["score_breakdown"]["contact_score"],
            item["score_breakdown"]["keyword_score"],
            item["score_breakdown"]["hs_score"],
            item["score_breakdown"]["signal_score"],
        ),
        reverse=True,
    )
    return results


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"파일이 없습니다: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    return frame.to_dict(orient="records")


def _smoke_opportunity(
    opportunities: list[dict[str, Any]],
    supplier_profile: Mapping[str, Any],
    reference_date: date,
) -> dict[str, Any] | None:
    target_country = normalize_text((supplier_profile or {}).get("target_country_norm"))
    supplier_target = _target_context(supplier_profile, None)
    ranked: list[tuple[int, date, dict[str, Any]]] = []
    for opportunity in opportunities:
        normalized = normalize_opportunity_record(opportunity, reference_date=reference_date)
        gate = opportunity_hard_gate(normalized, reference_date=reference_date)
        if not gate.get("passed"):
            continue
        if target_country and normalize_text(normalized.get("country_norm")) != target_country:
            continue
        text = " ".join(
            [
                normalize_text(normalized.get("title")),
                normalize_text(normalized.get("keywords_norm")),
                normalize_text(normalized.get("product_name_norm")),
            ]
        )
        overlap_terms = _keyword_overlap(normalized, supplier_target)
        if not overlap_terms and not SMOKE_KEYWORD_RE.search(text):
            continue
        valid_until = parse_date(normalized.get("valid_until")) or date.min
        ranked.append((len(overlap_terms), valid_until, normalized))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return ranked[0][2]


def smoke_test_fit_score(
    output_dir: Path | None = None,
    supplier_profile: Mapping[str, Any] | None = None,
    reference_date: date | None = None,
    sample_size: int = 200,
    random_seed: int = 42,
) -> dict[str, Any]:
    base_dir = output_dir or (ROOT / "output")
    ref = reference_date or date(2024, 3, 1)
    supplier = dict(DEFAULT_SMOKE_SUPPLIER_PROFILE)
    if supplier_profile:
        supplier.update({key: value for key, value in supplier_profile.items()})

    buyers = _load_rows(base_dir / "buyer_candidate.csv")
    opportunities = _load_rows(base_dir / "opportunity_item.csv")
    smoke_opportunity = _smoke_opportunity(opportunities, supplier, reference_date=ref)

    sampled_buyers = pd.DataFrame(buyers)
    if normalize_text(supplier.get("target_country_norm")):
        sampled_buyers = sampled_buyers[
            sampled_buyers["country_norm"].astype(str).eq(normalize_text(supplier.get("target_country_norm")))
        ]
    hint_regex = _keyword_hint_regex(supplier)
    target_hs = normalize_hs_code(supplier.get("target_hs_code_norm"))
    if not sampled_buyers.empty and (hint_regex is not None or target_hs):
        text = (
            sampled_buyers["title"].astype(str)
            + " "
            + sampled_buyers["normalized_name"].astype(str)
            + " "
            + sampled_buyers["keywords_norm"].astype(str)
        )
        hs_mask = sampled_buyers["hs_code_norm"].astype(str).str.startswith(target_hs[:4], na=False) if target_hs else False
        keyword_mask = text.str.contains(hint_regex, na=False) if hint_regex is not None else False
        contact_mask = (
            sampled_buyers.get("has_contact", pd.Series(False, index=sampled_buyers.index)).astype(str).str.lower().eq("true")
            | sampled_buyers.get("contact_email", pd.Series("", index=sampled_buyers.index)).astype(str).ne("")
        )
        sampled_buyers = sampled_buyers.copy()
        sampled_buyers["_hs_match"] = hs_mask if isinstance(hs_mask, pd.Series) else int(bool(hs_mask))
        sampled_buyers["_keyword_match"] = keyword_mask if isinstance(keyword_mask, pd.Series) else int(bool(keyword_mask))
        sampled_buyers["_contact_match"] = contact_mask.astype(int)
        sampled_buyers = sampled_buyers[(sampled_buyers["_hs_match"] > 0) | (sampled_buyers["_keyword_match"] > 0)].copy()
        sampled_buyers = sampled_buyers.sort_values(
            by=["_hs_match", "_keyword_match", "_contact_match", "normalized_name"],
            ascending=[False, False, False, True],
        )
    if len(sampled_buyers) > sample_size:
        sampled_buyers = sampled_buyers.head(sample_size)

    scored = score_buyers(
        buyers=sampled_buyers.to_dict(orient="records"),
        supplier_profile=supplier,
        opportunity=smoke_opportunity,
        reference_date=ref,
    )

    decision_counts = {
        "rejected": sum(1 for row in scored if row["decision"] == "rejected"),
        "candidate": sum(1 for row in scored if row["decision"] == "candidate"),
        "shortlist": sum(1 for row in scored if row["decision"] == "shortlist"),
    }
    eligible = [row for row in scored if row["decision"] != "rejected"]
    shortlist_rate = float(decision_counts["shortlist"] / len(scored)) if scored else 0.0
    average_score = float(sum(row["final_score"] for row in eligible) / len(eligible)) if eligible else 0.0

    return {
        "reference_date": ref.isoformat(),
        "sample_size": len(scored),
        "decision_counts": decision_counts,
        "shortlist_rate": round(shortlist_rate, 3),
        "average_score": round(average_score, 2),
        "opportunity_title": normalize_text((smoke_opportunity or {}).get("title")),
        "opportunity_country_norm": normalize_text((smoke_opportunity or {}).get("country_norm")),
        "top_results": [
            {
                "buyer_name": _first_non_empty(item["buyer"], ("normalized_name", "title")),
                "country_norm": _first_non_empty(item["buyer"], ("country_norm",)),
                "final_score": item["final_score"],
                "decision": item["decision"],
            }
            for item in scored[:10]
        ],
    }


def _demo() -> None:
    reference_date = date(2026, 4, 22)
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
        "supplier_name": "K-Beauty Supplier",
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
        reference_date=reference_date,
    )
    print("[demo] fit_score =", result)


def _smoke_demo(output_dir: Path, sample_size: int, reference_date: date) -> None:
    result = smoke_test_fit_score(
        output_dir=output_dir,
        reference_date=reference_date,
        sample_size=sample_size,
    )
    print("[smoke] summary =", result)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TASK-06 Fit Score v0")
    parser.add_argument("--demo", action="store_true", help="샘플 입력으로 Fit Score 결과를 출력한다.")
    parser.add_argument("--smoke-test", action="store_true", help="실데이터 output 기준 smoke test를 수행한다.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output",
        help="buyer_candidate.csv / opportunity_item.csv 위치",
    )
    parser.add_argument(
        "--reference-date",
        type=str,
        default="2024-03-01",
        help="TASK-06 smoke 기준일",
    )
    parser.add_argument("--sample-size", type=int, default=200, help="smoke test buyer sample 수")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    reference_date = date.fromisoformat(args.reference_date)
    if args.demo or not any(vars(args).values()):
        _demo()
    if args.smoke_test:
        _smoke_demo(args.output_dir, args.sample_size, reference_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
