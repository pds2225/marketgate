"""B7 — Export Action Plan 30/60/90 단위 테스트.

service 순수함수를 직접 호출(G4)해 3구간 고정·top_buyer 참조·결정론·런타임 스파이(G5)를 단정한다.
"""
from __future__ import annotations

import builtins
import socket

from app.services.action_plan import WINDOWS, build_action_plan

try:
    import requests as _requests  # noqa: F401
except ImportError:  # pragma: no cover
    _requests = None
try:
    import httpx as _httpx  # noqa: F401
except ImportError:  # pragma: no cover
    _httpx = None


def test_windows_constant_is_three_fixed_ranges() -> None:
    assert WINDOWS == ["0-30", "31-60", "61-90"]


def test_high_readiness_plan_references_top_buyer_in_phase0() -> None:
    result = build_action_plan(readiness_score=88, top_buyer_name="ACME", buyer_signal="strong")
    assert len(result["phases"]) == 3
    assert [p["window"] for p in result["phases"]] == ["0-30", "31-60", "61-90"]
    assert "ACME" in result["phases"][0]["actions"][0]
    for phase in result["phases"]:
        assert len(phase["actions"]) >= 1
        assert all(isinstance(a, str) and a.strip() for a in phase["actions"])
    assert result["track"] == "ready"


def test_low_readiness_plan_includes_verification_actions() -> None:
    result = build_action_plan(readiness_score=30, top_buyer_name="ACME", buyer_signal="none")
    assert len(result["phases"]) == 3
    phase0 = result["phases"][0]["actions"]
    assert "ACME" in phase0[0]
    assert "검증" in " ".join(phase0)  # 저준비도 → 검증/보강 액션
    assert result["track"] == "foundational"


def test_mid_readiness_plan_is_improving_track() -> None:
    result = build_action_plan(readiness_score=60, top_buyer_name="ACME", buyer_signal="weak")
    assert result["track"] == "improving"
    assert "ACME" in result["phases"][0]["actions"][0]


def test_action_plan_is_deterministic() -> None:
    a = build_action_plan(readiness_score=88, top_buyer_name="ACME", buyer_signal="strong")
    b = build_action_plan(readiness_score=88, top_buyer_name="ACME", buyer_signal="strong")
    assert a == b


def test_action_plan_fallback_buyer_when_name_missing() -> None:
    result = build_action_plan(readiness_score=88, top_buyer_name=None, buyer_signal="strong")
    assert len(result["phases"]) == 3
    assert result["phases"][0]["actions"][0].strip()  # buyer 없어도 비어있지 않음


def test_action_plan_focus_areas_from_dimensions() -> None:
    dims = {"market": "pass", "buyer": "warn", "margin": "fail", "compliance": "pass"}
    result = build_action_plan(
        readiness_score=70, top_buyer_name="ACME", buyer_signal="weak", dimensions=dims
    )
    assert "바이어 신호" in result["focus_areas"]
    assert "수익성" in result["focus_areas"]
    assert "시장 적합성" not in result["focus_areas"]
    assert "규제·제재" not in result["focus_areas"]


def test_action_plan_runtime_spy_no_file_write_or_network(monkeypatch) -> None:
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

    result = build_action_plan(
        readiness_score=30,
        top_buyer_name="ACME",
        buyer_signal="none",
        dimensions={"market": "fail", "buyer": "fail", "margin": "fail", "compliance": "warn"},
    )
    assert result["phases"]
    assert violations == []
