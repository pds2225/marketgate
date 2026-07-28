"""JWT 시크릿 fail-closed 가드.

dev fallback 은 리포지토리에 그대로 노출된 리터럴이라 관리자 토큰 위조가 가능하다.
Render 런타임(RENDER 마커)에서는 APP_ENV 설정 여부와 무관하게 기동을 막는다.
로컬 개발(마커 없음)은 기존대로 fallback 을 쓴다.

env 는 호출 시점에 읽으므로 모듈 임포트 캐시(JWT_SECRET) 대신
_resolve_jwt_secret() 을 직접 호출해 검증한다.

CI 주의: RENDER 마커가 설정된 환경에서 테스트를 돌리려면 더미 JWT_SECRET 을 함께
넣어야 한다 (`RENDER=true JWT_SECRET=ci-dummy pytest` → 전체 통과). 빼먹으면
개별 테스트가 아니라 pytest 수집 단계가 죽는다 — auth_deps 임포트 시점에
JWT_SECRET 이 바인딩되므로(app/auth_deps.py) 의도된 fail-closed 동작이다.
"""
from __future__ import annotations

import pytest

from app.auth_deps import _resolve_jwt_secret

DEV_FALLBACK = "dev-secret-change-in-prod"


def test_render_without_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(RuntimeError) as exc:
        _resolve_jwt_secret()
    assert "Render dashboard" in str(exc.value)


def test_render_never_returns_dev_fallback(monkeypatch):
    """APP_ENV 를 빠뜨려도 Render 에서는 위조 가능한 리터럴이 나오면 안 된다."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("RENDER", "srv-abc123")
    with pytest.raises(RuntimeError):
        _resolve_jwt_secret()


def test_render_with_secret_returns_secret(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("JWT_SECRET", "x")
    assert _resolve_jwt_secret() == "x"


def test_production_without_secret_still_fails(monkeypatch):
    """기존 APP_ENV=production 가드 고정 (RENDER 마커 없이도 실패)."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        _resolve_jwt_secret()


def test_local_dev_keeps_fallback(monkeypatch):
    """마커가 하나도 없으면 로컬 개발 동작은 그대로."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    assert _resolve_jwt_secret() == DEV_FALLBACK
