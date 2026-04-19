from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from app.models import PredictRequest
from app.config import WEIGHTS, SOFT_RULES
from app.services.data_loaders import (
    load_datastore,
    kotra_candidates_iso3,
    get_trade_value_usd,
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


def recommend_countries(req: PredictRequest) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ds = load_datastore()

    hs6 = req.hs_code
    exporter = req.exporter_country_iso3
    year = req.year or 2023
    top_n = req.top_n or 10

    exclude = (req.filters.exclude_countries_iso3 or []) if req.filters else []
    min_trade = float(req.filters.min_trade_value_usd or 0.0) if req.filters else 0.0

    # 1) 후보군 로드: kotra csv 에서.
    candidates = kotra_candidates_iso3(hs6, ds.mofa, ds.kotra)
    filters_applied: List[str] = []
    if exclude:
        filters_applied.extend([f"exclude_{x}" for x in exclude])
    if min_trade > 0:
        filters_applied.append(f"min_trade_value_usd>={int(min_trade)}")

    # 후보군이 비면 빈 결과 리턴할 것
    if not candidates:
        input_echo = {
            "hs_code": hs6,
            "exporter_country_iso3": exporter,
            "top_n": top_n,
            "year": year,
        }
        return [], input_echo

    # 2) Hard Filter 관련 사항
    rows = []
    hard_reasons = {}  

    for p in candidates:
        reasons = []

        # 사용자 제외
        if p in exclude:
            reasons.append("USER_EXCLUDED")

        trade_val = get_trade_value_usd(ds.trade, year, exporter, p, hs6)
        if trade_val is None:
            reasons.append("NO_TRADE_DATA")
        else:
            if trade_val < min_trade:
                reasons.append("MIN_TRADE_VALUE")

        dist_km = get_distance_km(ds.distance, exporter, p)
        if dist_km is None:
            reasons.append("NO_DISTANCE_DATA")

        gdp = get_wb_value(ds.wb_gdp, year, p)
        if gdp is None:
            # 여기는 Hard filter 부분은 아님
            # (Hard Filter 목록에 GDP/WB 누락 내용은 없지만 개발 과정 중 missing 파악 중 - ************ 최종 개발 시 제거할 것!)
            logger.warning(f"[WB] GDP missing: {p} year={year}")

        growth = get_wb_value(ds.wb_growth, year, p)
        if growth is None:
            logger.warning(f"[WB] GDP growth missing: {p} year={year}")

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
            }
        )

    if not rows:
        input_echo = {
            "hs_code": hs6,
            "exporter_country_iso3": exporter,
            "top_n": top_n,
            "year": year,
        }
        return [], input_echo

    # 3) Min-Max 정규화 부분
    trade_raw = [r["trade_value_usd"] for r in rows]
    gdp_raw = [r["gdp_usd"] for r in rows]
    growth_raw = [r["gdp_growth_pct"] for r in rows]
    dist_raw = [r["distance_km"] for r in rows]

    trade_norm = _minmax_norm(trade_raw)
    gdp_norm = _minmax_norm(gdp_raw)
    growth_norm = _minmax_norm(growth_raw)
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

        # 5) 가중합으로 하나의 종합 적합도 점수 만들기(0~1)
        base01 = (
            WEIGHTS["trade_volume_score"] * comp["trade_volume_score"] +
            WEIGHTS["growth_score"] * comp["growth_score"] +
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

        # restricted/blocked는 데이터 수령 전이라 미적용 !!!!!!!!!  **** 최종 완성 시 누락 주의-요청 드림(2/3)

        fit = base01 * 100.0 + soft
        fit = max(0.0, min(100.0, fit))
        fit = round(fit, 1)

        # 모두 점수 기준으로 표기함
        contributions = [
            ("historical_trade_value_usd", WEIGHTS["trade_volume_score"] * comp["trade_volume_score"], "positive"),
            ("partner_gdp_growth_pct", WEIGHTS["growth_score"] * comp["growth_score"], "positive"),
            ("partner_gdp_usd", WEIGHTS["gdp_score"] * comp["gdp_score"], "positive"),
            ("distance_km", WEIGHTS["distance_score"] * comp["distance_score"], "positive"),
        ]
        contributions.sort(key=lambda x: x[1], reverse=True)
        top_factors = [{"factor": contributions[0][0], "direction": contributions[0][2]}]
        if len(contributions) > 1:
            top_factors.append({"factor": contributions[1][0], "direction": contributions[1][2]})

        results.append(
            {
                "partner_country_iso3": r["partner_iso3"],
                "fit_score": fit,
                "score_components": {
                    # 0~100 점수로 노출하고 싶으면
                    "trade_volume_score": round(comp["trade_volume_score"], 4),
                    "growth_score": round(comp["growth_score"], 4),
                    "gdp_score": round(comp["gdp_score"], 4),
                    "distance_score": round(comp["distance_score"], 4),
                    "soft_adjustment": round(soft, 1),
                },
                "explanation": {
                    "top_factors": top_factors,
                    "data_sources": ["KOTRA(csv)", "MOFA(csv)", "World Bank(csv)", "CEPII(csv)", "TradeData(csv)"],
                    "filters_applied": filters_applied,
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
    return results, input_echo
