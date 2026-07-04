"""B5 — Export Readiness Check 단위 테스트.

service 순수함수를 *직접 호출*(인증 HTTP·라우터 미경유, G4)해 fixture AC·집계경로·드리프트
교차검증·런타임 스파이(G5)를 단정한다. 기대값은 PLAN.md 정규화 규칙표에서 결정론적으로 산출.
"""
from __future__ import annotations

import builtins
import socket

from app.services.readiness import (
    READINESS_THRESHOLDS,
    READINESS_WEIGHTS,
    aggregate_buyer_signal,
    compute_readiness,
)

# 스파이가 socket.socket 을 교체하기 전에 requests/httpx 를 미리 로드 (ssl→socket 상속 회피)
try:
    import requests as _requests  # noqa: F401
except ImportError:  # pragma: no cover
    _requests = None
try:
    import httpx as _httpx  # noqa: F401
except ImportError:  # pragma: no cover
    _httpx = None


# --- SSOT 상수 고정 (드리프트 방지) ---


def test_weights_and_thresholds_are_locked() -> None:
    assert READINESS_WEIGHTS == {"market": 0.35, "buyer": 0.30, "margin": 0.25, "compliance": 0.10}
    assert READINESS_THRESHOLDS == {"pass": 75, "warn": 50}
    # 가중치 합 == 1.0 (만점 100 보장)
    assert abs(sum(READINESS_WEIGHTS.values()) - 1.0) < 1e-9


# --- Fixture AC (규칙표에서 결정론적으로 계산한 값) ---


def test_fixture_a_full_pass_scores_100() -> None:
    result = compute_readiness(
        country_fit_score=90, compliance=None, buyer_signal="strong", margin_grade="보통"
    )
    assert result["readiness_score"] == 100
    assert result["dimensions"] == {
        "market": "pass",
        "buyer": "pass",
        "margin": "pass",
        "compliance": "pass",
    }
    assert result["verdict"] == "pass"


def test_fixture_ru_restricted_loses_compliance_weight_scores_90() -> None:
    result = compute_readiness(
        country_fit_score=90, compliance="restricted", buyer_signal="strong", margin_grade="보통"
    )
    assert result["readiness_score"] == 90
    assert result["dimensions"]["compliance"] == "warn"
    assert result["dimensions"]["market"] == "pass"
    assert result["dimensions"]["buyer"] == "pass"
    assert result["dimensions"]["margin"] == "pass"


def test_fixture_mixed_all_warn_scores_55() -> None:
    result = compute_readiness(
        country_fit_score=60, compliance=None, buyer_signal="weak", margin_grade="손익분기"
    )
    assert result["readiness_score"] == 55
    assert result["dimensions"] == {
        "market": "warn",
        "buyer": "warn",
        "margin": "warn",
        "compliance": "pass",
    }
    assert result["verdict"] == "warn"


def test_fixture_margin_floor_jeokja_demotes_to_fail_scores_75() -> None:
    # M1 실데이터 정합: margin_rate≤0 인 지배적 케이스("적자")가 margin fail 로 강등
    result = compute_readiness(
        country_fit_score=90, compliance=None, buyer_signal="strong", margin_grade="적자"
    )
    assert result["readiness_score"] == 75
    assert result["dimensions"]["margin"] == "fail"
    assert result["dimensions"]["market"] == "pass"
    assert result["verdict"] == "pass"  # 75 == threshold pass


def test_fixture_empty_no_market_scores_0() -> None:
    # predict results==[] (HS_NOT_SUPPORTED / NO_BUYERS) → country_fit_score 없음
    result = compute_readiness(country_fit_score=None)
    assert result["readiness_score"] == 0
    assert all(v == "warn" for v in result["dimensions"].values())
    assert result["reason"] == "no_market"


# --- buyer_signal 집계경로 AC (M-A: raw items 를 헬퍼에 통과) ---


def test_aggregate_buyer_signal_takes_max_relevance_among_shortlist() -> None:
    items = [
        {"decision": "shortlist", "match_relevance": "weak"},
        {"decision": "shortlist", "match_relevance": "strong"},
        {"decision": "candidate", "match_relevance": "strong"},
    ]
    assert aggregate_buyer_signal(items) == "strong"


def test_aggregate_buyer_signal_none_when_no_shortlist() -> None:
    items = [
        {"decision": "candidate", "match_relevance": "strong"},
        {"decision": "rejected", "match_relevance": "strong"},
    ]
    assert aggregate_buyer_signal(items) == "none"


def test_aggregate_buyer_signal_empty_items() -> None:
    assert aggregate_buyer_signal([]) == "none"
    assert aggregate_buyer_signal(None) == "none"


def test_aggregate_then_compute_uses_shortlist_max() -> None:
    # 집계 헬퍼 → compute 까지 한 경로로 연결 (손으로 buyer_signal 주지 않음)
    items = [
        {"decision": "shortlist", "match_relevance": "weak"},
        {"decision": "shortlist", "match_relevance": "strong"},
    ]
    signal = aggregate_buyer_signal(items)
    result = compute_readiness(
        country_fit_score=90, compliance=None, buyer_signal=signal, margin_grade="보통"
    )
    assert result["dimensions"]["buyer"] == "pass"  # strong → pass


# --- 드리프트 교차검증 (Pre-mortem #2): 같은 fit_score → market 판정 동일, 감점은 compliance 만 ---


def test_drift_same_fit_score_same_market_verdict_penalty_only_compliance() -> None:
    base = compute_readiness(
        country_fit_score=90, compliance=None, buyer_signal="strong", margin_grade="보통"
    )
    restricted = compute_readiness(
        country_fit_score=90, compliance="restricted", buyer_signal="strong", margin_grade="보통"
    )
    # 같은 country_fit_score(90) → market verdict 동일 (fit 재유도/이중감점 0)
    assert base["dimensions"]["market"] == restricted["dimensions"]["market"] == "pass"
    # buyer·margin 차원도 동일 입력이므로 불변
    assert base["dimensions"]["buyer"] == restricted["dimensions"]["buyer"]
    assert base["dimensions"]["margin"] == restricted["dimensions"]["margin"]
    # 차이는 오직 compliance 차원과 그로 인한 -10점
    assert restricted["dimensions"]["compliance"] == "warn"
    assert base["readiness_score"] - restricted["readiness_score"] == 10


def test_drift_restricted_penalty_is_exactly_10_points() -> None:
    # compliance 가중 0.10 × (1.0-0.0) × 100 == 정확히 10점 고정 (M-C)
    for fit, buyer, margin in [(90, "strong", "보통"), (60, "weak", "손익분기"), (80, "strong", "적자")]:
        clean = compute_readiness(
            country_fit_score=fit, compliance=None, buyer_signal=buyer, margin_grade=margin
        )
        restricted = compute_readiness(
            country_fit_score=fit, compliance="restricted", buyer_signal=buyer, margin_grade=margin
        )
        assert clean["readiness_score"] - restricted["readiness_score"] == 10


# --- G5 런타임 스파이: compute_readiness 실행 중 open(쓰기)·socket·requests·httpx 호출 0 ---


def test_readiness_runtime_spy_no_file_write_or_network(monkeypatch) -> None:
    violations: list[tuple] = []
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
            violations.append(("open_write", file, mode))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)

    def boom_socket(*args, **kwargs):
        violations.append(("socket",))
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", boom_socket)

    def make_spy(name):
        def spy(*a, **k):
            violations.append((name,))
            raise AssertionError(f"{name} network attempted")

        return spy

    if _requests is not None and hasattr(_requests, "request"):
        monkeypatch.setattr(_requests, "request", make_spy("requests"))
    if _httpx is not None and hasattr(_httpx, "request"):
        monkeypatch.setattr(_httpx, "request", make_spy("httpx"))

    # 집계 + 계산 + 빈결과 경로 모두 실행
    items = [{"decision": "shortlist", "match_relevance": "strong"}]
    signal = aggregate_buyer_signal(items)
    scored = compute_readiness(
        country_fit_score=90, compliance="restricted", buyer_signal=signal, margin_grade="적자"
    )
    empty = compute_readiness(country_fit_score=None)

    # market(90→pass→1.0)·buyer(strong→pass→1.0)·margin(적자→fail→0.0)·compliance(restricted→warn→0.0)
    # → 0.35 + 0.30 + 0 + 0 = 0.65 → round(65) == 65
    assert scored["readiness_score"] == 65
    assert empty["readiness_score"] == 0
    assert violations == []
