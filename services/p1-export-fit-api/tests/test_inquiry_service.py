from __future__ import annotations

import builtins
import socket
from uuid import UUID

from app.services.inquiry_service import build_draft

# 스파이가 socket.socket 을 교체하기 전에 requests/httpx(및 ssl 의존성)를 미리 로드해 둔다.
# (ssl 모듈은 import 시 socket.socket 을 상속하므로, 패치 후 첫 import 가 일어나면 안 됨)
try:
    import requests as _requests  # noqa: F401
except ImportError:  # pragma: no cover
    _requests = None
try:
    import httpx as _httpx  # noqa: F401
except ImportError:  # pragma: no cover
    _httpx = None


def test_build_draft_returns_required_fields() -> None:
    result = build_draft(
        buyer_name="Serum Lab",
        contact_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate",
        sender_name="Kim",
        message="We can supply skincare products.",
    )

    UUID(result["inquiry_id"])
    assert result["created_at"]
    assert result["draft_ko"]
    assert result["draft_en"]
    assert result["status"] == "draft_ready"


def test_inquiry_template_substitution() -> None:
    result = build_draft(
        buyer_name="Serum Lab",
        contact_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate",
        sender_name="Kim",
        message="Custom note",
    )

    assert "Serum Lab" in result["draft_ko"]
    assert "330499" in result["draft_ko"]
    assert "MarketGate" in result["draft_ko"]
    assert "Kim" in result["draft_ko"]
    assert "Custom note" in result["draft_ko"]
    assert "Serum Lab" in result["draft_en"]
    assert "330499" in result["draft_en"]
    assert "MarketGate" in result["draft_en"]
    assert "Kim" in result["draft_en"]
    assert "Custom note" in result["draft_en"]


def test_inquiry_template_falls_back_unknown_for_blank_values() -> None:
    result = build_draft(
        buyer_name="",
        contact_email="",
        hs_code="",
        sender_company="",
        sender_name="",
    )

    assert result["contact_email"] == "Unknown"
    assert "Unknown" in result["draft_ko"]
    assert "Unknown" in result["draft_en"]


# --- B6: AI Sales Letter 개인화 (additive — 기존 동작 회귀 0) ---


def test_build_draft_personalizes_with_buyer_payload() -> None:
    result = build_draft(
        buyer_name="ACME",
        contact_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate",
        sender_name="Kim",
        country="DE",
        match_relevance="strong",
    )

    UUID(result["inquiry_id"])
    assert "ACME" in result["draft_en"]
    assert "DE" in result["draft_en"]
    # recommendation 이유 문자열 1개 이상 포함 (match_relevance=strong → "strong match")
    assert "strong match" in result["draft_en"]
    assert "ACME" in result["draft_ko"]
    assert "DE" in result["draft_ko"]
    assert result["personalized"] is True
    assert result["country"] == "DE"
    assert result["match_relevance"] == "strong"


def test_build_draft_includes_recommendation_lines_verbatim() -> None:
    reason = "High import demand for cosmetics in Germany"
    result = build_draft(
        buyer_name="ACME",
        contact_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate",
        sender_name="Kim",
        country="DE",
        match_relevance="weak",
        recommendation_lines=[reason, "Verified contact available"],
    )

    assert reason in result["draft_en"]
    assert reason in result["draft_ko"]


def test_build_draft_without_buyer_payload_is_unchanged() -> None:
    base = build_draft(
        buyer_name="Serum Lab",
        contact_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate",
        sender_name="Kim",
        message="Custom note",
    )

    assert base["personalized"] is False
    assert base["country"] is None
    assert base["match_relevance"] is None
    # 개인화 블록이 본문에 끼어들지 않아야 함 (기존 draft 의미 보존 = 회귀 0)
    assert "Why this opportunity fits" not in base["draft_en"]
    assert "이 거래가 귀사에 적합한 이유" not in base["draft_ko"]


def test_build_draft_runtime_spy_no_file_write_or_network(monkeypatch) -> None:
    """G5 런타임 스파이: build_draft 실행 중 open(쓰기)·socket·requests·httpx 호출 0."""
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

    # requests/httpx 는 모듈 최상단에서 이미 로드됨 — 여기서는 request() 만 감시한다.
    def make_spy(name):
        def spy(*a, **k):
            violations.append((name,))
            raise AssertionError(f"{name} network attempted")

        return spy

    if _requests is not None and hasattr(_requests, "request"):
        monkeypatch.setattr(_requests, "request", make_spy("requests"))
    if _httpx is not None and hasattr(_httpx, "request"):
        monkeypatch.setattr(_httpx, "request", make_spy("httpx"))

    result = build_draft(
        buyer_name="ACME",
        contact_email="buyer@example.com",
        hs_code="330499",
        sender_company="MarketGate",
        sender_name="Kim",
        country="DE",
        match_relevance="strong",
        recommendation_lines=["High import demand in DE"],
    )

    assert result["draft_en"]
    assert violations == []
