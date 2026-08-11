"""L024/L025/L026: refresh must rotate; logout must revoke; consume is atomic+durable.

Regression guards:
1. POST /v1/auth/refresh returns a new refresh_token and rejects reuse of the old one.
2. A second refresh with the rotated token succeeds (session can continue).
3. POST /v1/auth/logout with refresh_token prevents subsequent refresh.
4. Concurrent refresh with the same token yields exactly one success (L025).
5. With DATABASE_URL, consume_jti writes Postgres — not only ephemeral file (L026).
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


def test_consume_jti_uses_postgres_when_available(monkeypatch, tmp_path):
    """L026: with DATABASE_URL, consume must hit Postgres — not ephemeral file.

    If consume_jti only appends token_blacklist.json while is_blacklisted reads
    Postgres, a Render cold start clears the file and the same refresh_token
    can be reused to mint a new live chain.
    """
    import app.auth_store as auth_store

    monkeypatch.setattr(auth_store, "BLACKLIST_PATH", str(tmp_path / "token_blacklist.json"))
    monkeypatch.setattr(auth_store, "is_available", lambda: True)

    store: set[str] = set()

    class _Cur:
        def __init__(self):
            self._row = None

        def execute(self, sql, params=None):
            jti = params[0]
            if "RETURNING" in sql:
                if jti in store:
                    self._row = None
                else:
                    store.add(jti)
                    self._row = (jti,)
            elif sql.strip().startswith("SELECT"):
                self._row = (1,) if jti in store else None
            else:
                store.add(jti)
                self._row = None

        def fetchone(self):
            return self._row

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class _Conn:
        def cursor(self):
            return _Cur()

        def commit(self):
            return None

    monkeypatch.setattr(auth_store, "get_conn", lambda: _Conn())
    monkeypatch.setattr(auth_store, "put_conn", lambda _c: None)

    assert auth_store.consume_jti("jti-l026") is True
    assert "jti-l026" in store
    # Ephemeral file must stay untouched when Postgres is the source of truth.
    assert not (tmp_path / "token_blacklist.json").exists()
    assert auth_store.consume_jti("jti-l026") is False
    assert auth_store.is_blacklisted("jti-l026") is True
