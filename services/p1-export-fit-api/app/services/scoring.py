from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from app.models import PredictRequest
from app.config import WEIGHTS, SOFT_RULES, SCORE_NORMALIZATION
from app.services import compliance
from app.services.confidence import build_data_coverage
from app.services.data_loaders import (
    load_datastore,
    kotra_candidate_scores,
    get_trade_value_usd,
    get_world_trade_value_usd,
    get_wb_value,
    get_distance_km,
)
from app.utils import logger


def _minmax_norm(values: List[float]) -> List[float]:
    """
    norm = (x-min)/(max-min), max==min이면 0.5
    """
    arr = np.array(values, dtype=float)
    mn = float(np.min(arr))
    mx = float(np.max(arr))
    if mx == mn:
        return [0.5 for _ in values]
    return [float((x - mn) / (mx - mn)) for x in values]


def _winsorize(values: List[float]) -> List[float]:
    """
    이상치 방어 (matchB): 정규화 직전 상/하위 분위수로 클리핑(윈저라이즈)한다.
    극단 이상치 1~2개(예: 마카오 코로나 반등 성장률 75.3%)가 min-max 스케일을
    독점해 만점으로 증폭되는 것을 막는다. 결정론·재현성 유지(같은 입력 → 같은 출력).
    표본이 2개 이하면 분위수 의미가 없어 원본을 그대로 반환한다.
    """
    if len(values) <= 2:
        return [float(v) for v in values]
    arr = np.array(values, dtype=float)
    lo = float(np.quantile(arr, SCORE_NORMALIZATION["winsorize_lower_quantile"]))
    hi = float(np.quantile(arr, SCORE_NORMALIZATION["winsorize_upper_quantile"]))
    if hi <= lo:
        return [float(v) for v in values]
    return [float(min(max(v, lo), hi)) for v in values]


def _allocate_world_trade_proxy_value(
    world_trade_value_usd: Optional[float],
    partner_iso3: str,
    candidate_score_map: Dict[str, float],
) -> Optional[float]:
    """
    한국 2023 trade_data 처럼 partnerISO=W00 세계 합계만 있는 경우,
    KOTRA 수출행동점수를 가중치로 사용해 후보국별 proxy trade를 만든다.
    """
    if world_trade_value_usd is None or world_trade_value_usd <= 0:
        return None

    weight = float(candidate_score_map.get(partner_iso3, 0.0))
    positive_weights = [max(float(v), 0.0) for v in candidate_score_map.values()]
    total_weight = sum(positive_weights)
    n = float(len(candidate_score_map) or 1)

    if total_weight <= 0:
        # KOTRA 가중치가 없어도 균등 배분 proxy를 부여해 data_missing 배제를 방지한다
        return float(world_trade_value_usd) / n

    non_positive_count = sum(1 for v in candidate_score_map.values() if float(v) <= 0)
    equal_share = float(world_trade_value_usd) / n
    if weight <= 0:
        return equal_share

    zero_weight_pool = equal_share * non_positive_count
    weighted_pool = max(float(world_trade_value_usd) - zero_weight_pool, 0.0)
    return weighted_pool * (weight / total_weight)


def _summarize_reason_counts(hard_reasons: Dict[str, List[str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for reasons in hard_reasons.values():
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return counts


def _sample_countries_by_reason(hard_reasons: Dict[str, List[str]], limit: int = 3) -> Dict[str, List[str]]:
    samples: Dict[str, List[str]] = {}
    for iso3, reasons in hard_reasons.items():
        for reason in reasons:
            bucket = samples.setdefault(reason, [])
            if len(bucket) < limit:
                bucket.append(iso3)
    return samples


def _build_diagnostics(
    candidate_count: int,
    rows: List[Dict[str, Any]],
    hard_reasons: Dict[str, List[str]],
    missing_indicator_counts: Dict[str, int],
) -> Dict[str, Any]:
    hard_filter_reason_counts = _summarize_reason_counts(hard_reasons)
    trade_signal_counts: Dict[str, int] = {}
    for row in rows:
        trade_signal = str(row.get("trade_signal_source", "unknown"))
        trade_signal_counts[trade_signal] = trade_signal_counts.get(trade_signal, 0) + 1

    zero_result_reasons: List[str] = []
    if candidate_count == 0:
        zero_result_reasons.append("NO_KOTRA_CANDIDATES_FOR_HS6")
    elif not rows:
        if hard_filter_reason_counts:
            zero_result_reasons.extend(sorted(hard_filter_reason_counts.keys()))
        else:
            zero_result_reasons.append("NO_ELIGIBLE_CANDIDATES")

    # 가산적 coverage_status (matchA): "데이터 없음" vs "추천 없음"을 사용자가 구분하게 한다.
    # 기존 zero_result_reasons/필드는 그대로 두고, 사용자향 분류 코드만 추가한다.
    if rows:
        coverage_status = "OK"
    elif candidate_count == 0:
        # KOTRA 후보국 레이어가 해당 HS를 커버하지 못함(예: 휴대폰 851712)
        coverage_status = "HS_NOT_SUPPORTED"
    elif hard_filter_reason_counts.get("NO_TRADE_DATA", 0) >= candidate_count:
        # 후보국은 있으나 무역데이터 커버리지에 HS가 없어 전원 탈락(예: 쌀 100630)
        coverage_status = "HS_NOT_IN_TRADE_COVERAGE"
    else:
        # 후보·데이터는 있으나 적격 바이어/국가가 0건
        coverage_status = "NO_BUYERS"

    quality_warnings: List[str] = []
    allocated_count = trade_signal_counts.get("world_total_allocated", 0)
    if allocated_count > 0:
        quality_warnings.append("TRADE_SIGNAL_USES_WORLD_TOTAL_FALLBACK")
    if rows and allocated_count == len(rows):
        quality_warnings.append("ALL_ELIGIBLE_RESULTS_USE_ALLOCATED_TRADE_SIGNAL")
    if missing_indicator_counts["gdp_missing"] > 0:
        quality_warnings.append("GDP_DATA_PARTIALLY_MISSING")
    if missing_indicator_counts["growth_missing"] > 0:
        quality_warnings.append("GDP_GROWTH_DATA_PARTIALLY_MISSING")

    coverage_message_map = {
        "OK": "",
        "HS_NOT_SUPPORTED": "이 품목(HS코드)은 아직 추천 데이터가 준비되지 않았습니다. (미지원 품목 — 바이어가 없다는 뜻이 아닙니다)",
        "HS_NOT_IN_TRADE_COVERAGE": "이 품목은 무역 데이터 커버리지에 없어 추천을 만들 수 없습니다. (데이터 미보유 — 바이어가 없다는 뜻이 아닙니다)",
        "NO_BUYERS": "조건에 맞는 추천 결과가 없습니다.",
    }

    return {
        "candidate_count": candidate_count,
        "eligible_count": len(rows),
        "returned_count": len(rows),
        "hard_filter_reason_counts": hard_filter_reason_counts,
        "missing_indicator_counts": missing_indicator_counts,
        "zero_result_reasons": zero_result_reasons,
        "quality_warnings": quality_warnings,
        "trade_signal_counts": trade_signal_counts,
        "sample_countries_by_reason": _sample_countries_by_reason(hard_reasons),
        # 가산 필드 (matchA): 미지원/데이터없음 vs 바이어없음 구분
        "coverage_status": coverage_status,
        "coverage_message": coverage_message_map.get(coverage_status, ""),
    }


def recommend_countries(req: PredictRequest) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    ds = load_datastore()

    hs6 = req.hs_code
    exporter = req.exporter_country_iso3
    year = req.year or 2023
    top_n = req.top_n or 10

    exclude = (req.filters.exclude_countries_iso3 or []) if req.filters else []
    min_trade = float(req.filters.min_trade_value_usd or 0.0) if req.filters else 0.0

    # 1) 후보군 로드: kotra csv 에서.
    candidate_score_map = kotra_candidate_scores(hs6, ds.mofa, ds.kotra)
    candidates = sorted(candidate_score_map.keys())
    world_trade_value_usd = get_world_trade_value_usd(ds.trade, year, exporter, hs6)
    filters_applied: List[str] = []
    missing_indicator_counts = {
        "trade_missing": 0,
        "distance_missing": 0,
        "gdp_missing": 0,
        "growth_missing": 0,
    }
    if exclude:
        filters_applied.extend([f"exclude_{x}" for x in exclude])
    if min_trade > 0:
        filters_applied.append(f"min_trade_value_usd>={int(min_trade)}")
    if world_trade_value_usd is not None:
        filters_applied.append("trade_fallback=world_total_allocated_by_kotra_score")

    # 후보군이 비면 빈 결과 리턴할 것
    if not candidates:
        input_echo = {
            "hs_code": hs6,
            "exporter_country_iso3": exporter,
            "top_n": top_n,
            "year": year,
        }
        diagnostics = _build_diagnostics(
            candidate_count=0,
            rows=[],
            hard_reasons={},
            missing_indicator_counts=missing_indicator_counts,
        )
        return [], input_echo, diagnostics

    # 2) Hard Filter 관련 사항
    rows = []
    hard_reasons = {}  

    for p in candidates:
        reasons = []

        # 사용자 제외
        if p in exclude:
            reasons.append("USER_EXCLUDED")

        trade_val = get_trade_value_usd(ds.trade, year, exporter, p, hs6)
        trade_signal_source = "partner_observed"
        if trade_val is None:
            trade_val = _allocate_world_trade_proxy_value(world_trade_value_usd, p, candidate_score_map)
            if trade_val is not None:
                trade_signal_source = "world_total_allocated"

        if trade_val is None:
            missing_indicator_counts["trade_missing"] += 1
            reasons.append("NO_TRADE_DATA")
        else:
            if trade_val < min_trade:
                reasons.append("MIN_TRADE_VALUE")

        dist_km = get_distance_km(ds.distance, exporter, p)
        if dist_km is None:
            missing_indicator_counts["distance_missing"] += 1
            reasons.append("NO_DISTANCE_DATA")

        gdp = get_wb_value(ds.wb_gdp, year, p)
        if gdp is None:
            missing_indicator_counts["gdp_missing"] += 1

        growth = get_wb_value(ds.wb_growth, year, p)
        if growth is None:
            missing_indicator_counts["growth_missing"] += 1

        if reasons:
            hard_reasons[p] = reasons
            continue

        rows.append(
            {
                "partner_iso3": p,
                "trade_value_usd": float(trade_val),
                "gdp_usd": float(gdp) if gdp is not None else 0.0,
                "gdp_growth_pct": float(growth) if growth is not None else 0.0,
                "distance_km": float(dist_km),
                "trade_signal_source": trade_signal_source,
                "kotra_weight_score": float(candidate_score_map.get(p, 0.0)),
                "missing_indicators": {
                    "gdp_missing": gdp is None,
                    "growth_missing": growth is None,
                },
            }
        )

    if not rows:
        input_echo = {
            "hs_code": hs6,
            "exporter_country_iso3": exporter,
            "top_n": top_n,
            "year": year,
        }
        diagnostics = _build_diagnostics(
            candidate_count=len(candidates),
            rows=[],
            hard_reasons=hard_reasons,
            missing_indicator_counts=missing_indicator_counts,
        )
        return [], input_echo, diagnostics

    # 3) Min-Max 정규화 부분
    trade_raw = [r["trade_value_usd"] for r in rows]
    gdp_raw = [r["gdp_usd"] for r in rows]
    growth_raw = [r["gdp_growth_pct"] for r in rows]
    dist_raw = [r["distance_km"] for r in rows]

    # 이상치 방어 (matchB): growth/gdp는 정규화 전 윈저라이즈로 극단 이상치를 클리핑한다.
    # (trade는 저수요 신호 자체가 의미 있어 클리핑하지 않고, distance는 유계라 불필요)
    trade_norm = _minmax_norm(trade_raw)
    gdp_norm = _minmax_norm(_winsorize(gdp_raw))
    growth_norm = _minmax_norm(_winsorize(growth_raw))
    dist_norm = _minmax_norm(dist_raw)
    # 거리는 역수를 적용함(가까울수록 높은 점수)
    distance_score = [float(1.0 - x) for x in dist_norm]

    # 4) 문서내 Soft Score 부분 계산을 위한 percentile 기준 부분
    trade_p30 = float(np.quantile(trade_raw, SOFT_RULES["bottom_trade_percentile"]))
    dist_p70 = float(np.quantile(dist_raw, SOFT_RULES["top_distance_percentile"]))

    results = []
    for i, r in enumerate(rows):
        comp = {
            "trade_volume_score": round(trade_norm[i], 6),
            "growth_score": round(growth_norm[i], 6),
            "gdp_score": round(gdp_norm[i], 6),
            "distance_score": round(distance_score[i], 6),
        }

        # 저수요 게이트 (matchB): 실수입수요(trade_score)가 임계 이하인 국가는
        # 성장률 단독으로 상위(top-N) 진입 못 하게 성장 기여분을 곱셈형으로 강등한다.
        # "수요 없는데 성장률 이상치만 높아 1순위"가 되는 것을 차단한다.
        growth_gate = 1.0
        if comp["trade_volume_score"] < SCORE_NORMALIZATION["low_demand_trade_threshold"]:
            growth_gate = SCORE_NORMALIZATION["low_demand_growth_multiplier"]
        gated_growth_score = comp["growth_score"] * growth_gate

        # 5) 가중합으로 하나의 종합 적합도 점수 만들기(0~1)
        base01 = (
            WEIGHTS["trade_volume_score"] * comp["trade_volume_score"] +
            WEIGHTS["growth_score"] * gated_growth_score +
            WEIGHTS["gdp_score"] * comp["gdp_score"] +
            WEIGHTS["distance_score"] * comp["distance_score"]
        )

        # 6) soft rule 관련
        soft = 0.0
        if r["trade_value_usd"] <= trade_p30:
            soft += SOFT_RULES["penalty_bottom_trade"]
        if r["distance_km"] >= dist_p70:
            soft += SOFT_RULES["penalty_top_distance"]
        if r["gdp_growth_pct"] < 0:
            soft += SOFT_RULES["penalty_negative_growth"]

        # restricted 국가 감점 — 목록 단일 출처는 compliance.py (SIM_SPEC §2.3 / ADR-2026-06-10)
        compliance_penalty = 0.0
        restricted_block = compliance.restricted_info(r["partner_iso3"])
        if restricted_block is not None:
            compliance_penalty = SOFT_RULES["penalty_restricted"]
            soft += compliance_penalty
            restricted_block["penalty_applied"] = compliance_penalty

        fit = base01 * 100.0 + soft
        fit = max(0.0, min(100.0, fit))
        fit = round(fit, 1)

        # 모두 점수 기준으로 표기함 (성장 기여분은 저수요 게이트 반영분 사용)
        contributions = [
            ("historical_trade_value_usd", WEIGHTS["trade_volume_score"] * comp["trade_volume_score"], "positive"),
            ("partner_gdp_growth_pct", WEIGHTS["growth_score"] * gated_growth_score, "positive"),
            ("partner_gdp_usd", WEIGHTS["gdp_score"] * comp["gdp_score"], "positive"),
            ("distance_km", WEIGHTS["distance_score"] * comp["distance_score"], "positive"),
        ]
        contributions.sort(key=lambda x: x[1], reverse=True)
        top_factors = [{"factor": contributions[0][0], "direction": contributions[0][2]}]
        if len(contributions) > 1:
            top_factors.append({"factor": contributions[1][0], "direction": contributions[1][2]})

        # 신뢰도(data_coverage) — SIM_SPEC §3. news_risk는 데이터 소스 미구현으로 항상 결측.
        data_coverage = build_data_coverage(
            {
                "export_score": r["kotra_weight_score"],
                "gdp": None if r["missing_indicators"]["gdp_missing"] else r["gdp_usd"],
                "growth_rate": None if r["missing_indicators"]["growth_missing"] else r["gdp_growth_pct"],
                "market_size": r["trade_value_usd"],
                "news_risk": None,
            }
        )

        result_warnings = []
        if restricted_block is not None:
            result_warnings.append(
                {
                    "code": "RESTRICTED_COUNTRY",
                    "severity": "high",
                    "message": (
                        f"{restricted_block['country_name']}({restricted_block['country_code']}) — "
                        f"수출 제한 국가. 수출 허가 필요, 점수 {compliance_penalty:+.0f} 반영 "
                        f"(제한 시작: {restricted_block['restricted_since']})"
                    ),
                }
            )
        if data_coverage["confidence_level"] in ("low", "very_low"):
            result_warnings.append(
                {
                    "code": "LOW_CONFIDENCE",
                    "severity": "medium",
                    "message": (
                        f"데이터 신뢰도 {data_coverage['confidence_level']} "
                        f"(confidence={data_coverage['confidence']}, "
                        f"결측: {', '.join(data_coverage['missing_fields'])})"
                    ),
                }
            )
        # 가산 (matchA): 리스크 미평가인데 high로 보이는 것을 막는 정직성 경고
        if not data_coverage.get("risk_assessed", True):
            result_warnings.append(
                {
                    "code": "RISK_NOT_ASSESSED",
                    "severity": "low",
                    "message": (
                        "리스크(뉴스·제재 동향)가 평가되지 않아 신뢰도 표시 상한이 medium입니다 "
                        "('high' 아님)."
                    ),
                }
            )

        results.append(
            {
                "partner_country_iso3": r["partner_iso3"],
                "fit_score": fit,
                "compliance": restricted_block,
                "data_coverage": data_coverage,
                "warnings": result_warnings,
                "score_components": {
                    # 0~100 점수로 노출하고 싶으면
                    "trade_volume_score": round(comp["trade_volume_score"], 4),
                    "growth_score": round(comp["growth_score"], 4),
                    "gdp_score": round(comp["gdp_score"], 4),
                    "distance_score": round(comp["distance_score"], 4),
                    "soft_adjustment": round(soft, 1),
                    "compliance_penalty": round(compliance_penalty, 1),
                },
                "explanation": {
                    "top_factors": top_factors,
                    "data_sources": ["KOTRA(csv)", "MOFA(csv)", "World Bank(csv)", "CEPII(csv)", "TradeData(csv)"],
                    "filters_applied": filters_applied,
                    "trade_signal_source": r["trade_signal_source"],
                    "kotra_weight_score": round(r["kotra_weight_score"], 4),
                    "missing_indicators": r["missing_indicators"],
                },
            }
        )

    # 7) 정렬과 top 결과 
    results.sort(key=lambda x: x["fit_score"], reverse=True)
    results = results[:top_n]

    # 8) 순위 지정하기
    for idx, item in enumerate(results, start=1):
        item["rank"] = idx

    input_echo = {
        "hs_code": hs6,
        "exporter_country_iso3": exporter,
        "top_n": top_n,
        "year": year,
    }
    diagnostics = _build_diagnostics(
        candidate_count=len(candidates),
        rows=rows,
        hard_reasons=hard_reasons,
        missing_indicator_counts=missing_indicator_counts,
    )
    diagnostics["returned_count"] = len(results)
    return results, input_echo, diagnostics
