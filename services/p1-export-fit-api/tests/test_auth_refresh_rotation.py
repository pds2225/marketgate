"""L024/L025: refresh must rotate; logout must revoke refresh; consume is atomic.

Regression guards:
1. POST /v1/auth/refresh returns a new refresh_token and rejects reuse of the old one.
2. A second refresh with the rotated token succeeds (session can continue).
3. POST /v1/auth/logout with refresh_token prevents subsequent refresh.
4. Concurrent refresh with the same token yields exactly one success (L025).
"""
from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth_deps import create_access_token, create_refresh_token
import main as api_main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.auth_store.BLACKLIST_PATH", str(tmp_path / "token_blacklist.json")
    )
    return TestClient(api_main.app)


def _user_tokens(user_id: str = "u-l024"):
    return {
        "access": create_access_token(user_id),
        "refresh": create_refresh_token(user_id),
        "user_id": user_id,
    }


def test_refresh_rotates_and_rejects_reuse(client):
    tokens = _user_tokens()

    first = client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh"]}
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["refresh_token"] != tokens["refresh"]

    reuse = client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh"]}
    )
    assert reuse.status_code == 401
    assert reuse.json()["detail"] == "token_revoked"

    second = client.post(
        "/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert second.status_code == 200, second.text
    assert second.json()["refresh_token"]
    assert second.json()["refresh_token"] != body["refresh_token"]


def test_logout_revokes_refresh_token(client):
    tokens = _user_tokens("u-logout")

    logged_out = client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access']}"},
        json={"refresh_token": tokens["refresh"]},
    )
    assert logged_out.status_code == 200, logged_out.text

    revived = client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh"]}
    )
    assert revived.status_code == 401
    assert revived.json()["detail"] == "token_revoked"


def test_logout_without_refresh_body_still_succeeds(client):
    tokens = _user_tokens("u-access-only")
    res = client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access']}"},
        json={},
    )
    assert res.status_code == 200


def test_concurrent_refresh_consumes_jti_once(client):
    """Two tabs hitting /refresh together must not mint multiple live chains."""
    tokens = _user_tokens("u-l025-race")
    workers = 8
    barrier = threading.Barrier(workers)

    def once():
        barrier.wait()
        return client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh"]}
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        responses = [f.result() for f in as_completed([pool.submit(once) for _ in range(workers)])]

    successes = [r for r in responses if r.status_code == 200]
    failures = [r for r in responses if r.status_code != 200]
    assert len(successes) == 1, [r.status_code for r in responses]
    assert len(failures) == workers - 1
    assert all(r.json()["detail"] == "token_revoked" for r in failures)

    winner_refresh = successes[0].json()["refresh_token"]
    follow = client.post(
        "/v1/auth/refresh", json={"refresh_token": winner_refresh}
    )
    assert follow.status_code == 200, follow.text
