"""Regression: Postgres get_subscription must end FOR UPDATE transactions.

L027 stored subscriptions in Neon with SELECT … FOR UPDATE, but active and
missing-row read paths returned the pooled connection without commit. With
ThreadedConnectionPool(maxconn=4), those row locks sit idle in the pool and
block later change_plan / require_plan for the same user.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import subscription_store


class _Cur:
    def __init__(self, row):
        self._row = row
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self._row


class _Conn:
    def __init__(self, row):
        self._row = row
        self.commits = 0
        self.rollbacks = 0
        self.cursor_obj = _Cur(row)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def pg_on(monkeypatch):
    monkeypatch.setattr(subscription_store, "is_available", lambda: True)
    monkeypatch.setattr(subscription_store, "in_transaction", lambda: False)


def test_active_subscription_read_commits_for_update(pg_on, monkeypatch):
    now = datetime.now(timezone.utc)
    row = ("Pro", now, now + timedelta(days=30))
    conn = _Conn(row)
    monkeypatch.setattr(subscription_store, "get_conn", lambda: conn)
    monkeypatch.setattr(subscription_store, "put_conn", lambda c: None)

    sub = subscription_store.get_subscription("user-paid")

    assert sub["plan"] == "Pro"
    assert conn.commits == 1
    assert any("FOR UPDATE" in sql for sql, _ in conn.cursor_obj.executed)


def test_missing_subscription_read_commits_for_update(pg_on, monkeypatch):
    conn = _Conn(None)
    monkeypatch.setattr(subscription_store, "get_conn", lambda: conn)
    monkeypatch.setattr(subscription_store, "put_conn", lambda c: None)

    sub = subscription_store.get_subscription("user-new")

    assert sub == {"plan": "Basic", "started_at": None, "expires_at": None}
    assert conn.commits == 1


def test_shared_transaction_skips_commit(pg_on, monkeypatch):
    now = datetime.now(timezone.utc)
    conn = _Conn(("Advanced", now, now + timedelta(days=10)))
    monkeypatch.setattr(subscription_store, "get_conn", lambda: conn)
    monkeypatch.setattr(subscription_store, "put_conn", lambda c: None)
    monkeypatch.setattr(subscription_store, "in_transaction", lambda: True)

    sub = subscription_store.get_subscription("user-tx")

    assert sub["plan"] == "Advanced"
    assert conn.commits == 0
