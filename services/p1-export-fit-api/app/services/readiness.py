"""B5 — Export Readiness Check (순수함수, FastAPI import 금지).

predict 결과의 핵심필드 DTO를 받아 0~100 준비도 점수 + 차원별 판정을 만든다.
SSOT 재사용 원칙: 국가fit=scoring.py(post-penalty fit_score), 제재=compliance.py(categorical),
마진=simulation.py(profit_grade) 의 *결과만 소비*하며 점수·제재·마진을 재계산/재감점하지 않는다.

네트워크·파일쓰기·전역상태 변경 0 (순수함수).
"""
from __future__ import annotations

from typing import Any, Optional

# --- SSOT 상수 (재계산·재감점 금지) ---
READINESS_WEIGHTS = {"market": 0.35, "buyer": 0.30, "margin": 0.25, "compliance": 0.10}
READINESS_THRESHOLDS = {"pass": 75, "warn": 50}  # score>=75 pass, 50<=score<75 warn, <50 fail

# verdict → numeric 기여 (정규화 규칙표 ②)
#  - 3-state 차원(market/buyer/margin): pass→1.0, warn→0.5, fail→0.0
#  - compliance(binary): pass(None)→1.0, warn(restricted)→0.0  (restricted면 0.10 가중 전부 상실)
_THREE_STATE_NUMERIC = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
_COMPLIANCE_NUMERIC = {"pass": 1.0, "warn": 0.0}

# buyer match_relevance 우선순위 (strong > weak > none)
_RELEVANCE_RANK = {"strong": 3, "weak": 2, "none": 1}

# margin(profit_grade) → verdict (M1: 숫자 임계 폐기, simulation 카테고리 소비)
#  실데이터는 margin_rate≤0 이라 "보통" 이하만 도달하지만 "우수" 매핑도 정의해 둔다.
_MARGIN_VERDICT = {"우수": "pass", "보통": "pass", "손익분기": "warn", "적자": "fail"}

# buyer_signal → verdict
_BUYER_VERDICT = {"strong": "pass", "weak": "warn", "none": "fail"}

# 빈 결과(results==[]) 전 차원 표기
_DIMENSIONS_EMPTY = {"market": "warn", "buyer": "warn", "margin": "warn", "compliance": "warn"}


def aggregate_buyer_signal(items: Optional[list[dict[str, Any]]]) -> str:
    """predict ``data.buyers.items`` 에서 ``decision=="shortlist"`` 인 항목의 max match_relevance.

    shortlist 0건이면 ``"none"``. (M-A: 손으로 buyer_signal 을 주지 않고 raw items 를 이 경로로
    통과시켜 집계 정확성을 검증해야 함. decision 코드값은 buyer_shortlist.py 의 shortlist/candidate/rejected.)
    """
    if not items:
        return "none"
    best = "none"
    best_rank = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("decision", "") or "").strip() != "shortlist":
            continue
        relevance = str(item.get("match_relevance", "") or "none").strip().lower()
        rank = _RELEVANCE_RANK.get(relevance, 0)
        if rank > best_rank:
            best_rank = rank
            best = relevance if relevance in _RELEVANCE_RANK else "none"
    return best


def _market_verdict(country_fit_score: float) -> str:
    """post-penalty fit_score(0~100)를 THRESHOLDS 와 직접 비교 — fit 재유도·재감점 0 (A3)."""
    if country_fit_score >= READINESS_THRESHOLDS["pass"]:
        return "pass"
    if country_fit_score >= READINESS_THRESHOLDS["warn"]:
        return "warn"
    return "fail"


def _buyer_verdict(buyer_signal: Optional[str]) -> str:
    return _BUYER_VERDICT.get(str(buyer_signal or "none").strip().lower(), "fail")


def _margin_verdict(margin_grade: Optional[str]) -> str:
    if margin_grade is None:
        return "warn"  # simulation 미수행 시 중립(미상)
    return _MARGIN_VERDICT.get(str(margin_grade).strip(), "warn")


def _compliance_verdict(compliance: Optional[str]) -> str:
    """binary: None/빈값=pass, 그 외(restricted 등 제재 신호)=warn.

    BLOCKED(KP/IR/SY/CU)는 filter_blocked_results 로 상류 제거되어 results 에 도달하지 않으므로
    여기에는 fail 상태가 없다 (C4).
    """
    if compliance is None:
        return "pass"
    if str(compliance).strip().lower() in ("", "none", "null"):
        return "pass"
    return "warn"


def compute_readiness(
    *,
    country_fit_score: Optional[float] = None,
    compliance: Optional[str] = None,
    buyer_signal: Optional[str] = "none",
    margin_grade: Optional[str] = None,
    top_buyer_name: Optional[str] = None,
) -> dict[str, Any]:
    """핵심 readiness 계산. ``country_fit_score is None`` → 빈 시장(no_market).

    반환: ``readiness_score``(int), ``verdict``(pass/warn/fail), ``dimensions``(차원별 categorical),
    ``reason``, ``top_buyer_name``, ``weights``.
    """
    # 빈 결과 경로 (results==[] → HS_NOT_SUPPORTED / NO_BUYERS)
    if country_fit_score is None:
        return {
            "readiness_score": 0,
            "verdict": "fail",
            "dimensions": dict(_DIMENSIONS_EMPTY),
            "reason": "no_market",
            "top_buyer_name": top_buyer_name,
            "weights": dict(READINESS_WEIGHTS),
        }

    dimensions = {
        "market": _market_verdict(float(country_fit_score)),
        "buyer": _buyer_verdict(buyer_signal),
        "margin": _margin_verdict(margin_grade),
        "compliance": _compliance_verdict(compliance),
    }

    numeric = {
        "market": _THREE_STATE_NUMERIC[dimensions["market"]],
        "buyer": _THREE_STATE_NUMERIC[dimensions["buyer"]],
        "margin": _THREE_STATE_NUMERIC[dimensions["margin"]],
        "compliance": _COMPLIANCE_NUMERIC[dimensions["compliance"]],
    }

    weighted = sum(READINESS_WEIGHTS[d] * numeric[d] for d in READINESS_WEIGHTS)
    score = round(weighted * 100)

    if score >= READINESS_THRESHOLDS["pass"]:
        verdict = "pass"
    elif score >= READINESS_THRESHOLDS["warn"]:
        verdict = "warn"
    else:
        verdict = "fail"

    return {
        "readiness_score": score,
        "verdict": verdict,
        "dimensions": dimensions,
        "reason": "scored",
        "top_buyer_name": top_buyer_name,
        "weights": dict(READINESS_WEIGHTS),
    }
