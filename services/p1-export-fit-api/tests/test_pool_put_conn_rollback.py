# -*- coding: utf-8 -*-
"""Regression: pooled connections must end transactions before reuse.

Critical path: credit deduct SELECT … FOR UPDATE then insufficient_credits
returned the connection to ThreadedConnectionPool(maxconn=4) still holding
the row lock. Concurrent balance/charge/deduct for that user blocked until
restart. put_conn now rollbacks; deduct also rollbacks on error.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import credit_store
from app import db_conn
from app import company_verification_store as cvs


class _Conn:
    def __init__(self):
        self.rollbacks = 0
        self.commits = 0
        self.put = False

    def rollback(self):
        self.rollbacks += 1

    def commit(self):
        self.commits += 1


def test_put_conn_rollbacks_before_pool_return(monkeypatch):
    conn = _Conn()
    calls = []

    class _Pool:
        def putconn(self, c):
            calls.append(c)

    monkeypatch.setattr(db_conn, "_tx", type("T", (), {})())
    monkeypatch.setattr(db_conn, "_get_pool", lambda: _Pool())
    # Ensure not treated as shared transaction conn
    db_conn._tx.conn = None

    db_conn.put_conn(conn)

    assert conn.rollbacks == 1
    assert calls == [conn]


def test_put_conn_skips_shared_transaction_conn(monkeypatch):
    conn = _Conn()
    put_calls = []

    class _Pool:
        def putconn(self, c):
            put_calls.append(c)

    monkeypatch.setattr(db_conn, "_get_pool", lambda: _Pool())
    db_conn._tx.conn = conn

    db_conn.put_conn(conn)

    assert conn.rollbacks == 0
    assert put_calls == []
    db_conn._tx.conn = None


def test_deduct_insufficient_credits_rollbacks_for_update(monkeypatch):
    class _Cur:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=None):
            pass

        def fetchone(self):
            return (2, [])  # balance 2; unlock costs 5

    class _Conn2:
        def __init__(self):
            self.rollbacks = 0
            self.commits = 0

        def cursor(self):
            return _Cur()

        def rollback(self):
            self.rollbacks += 1

        def commit(self):
            self.commits += 1

    conn = _Conn2()
    monkeypatch.setattr(credit_store, "is_available", lambda: True)
    monkeypatch.setattr(credit_store, "in_transaction", lambda: False)
    monkeypatch.setattr(credit_store, "get_conn", lambda: conn)
    # Bypass put_conn double-rollback so we assert store-level rollback.
    monkeypatch.setattr(credit_store, "put_conn", lambda c: None)

    with pytest.raises(ValueError, match="insufficient_credits"):
        credit_store.deduct("user-1", 5, action="contact_unlock")

    assert conn.commits == 0
    assert conn.rollbacks == 1


def test_create_verification_rolls_back_on_insert_error(monkeypatch):
    class _Cur:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, *a, **k):
            raise RuntimeError("simulated insert failure")

    class _Conn3:
        def __init__(self):
            self.rollbacks = 0

        def cursor(self):
            return _Cur()

        def rollback(self):
            self.rollbacks += 1

        def commit(self):
            raise AssertionError("commit must not run after failed insert")

    conn = _Conn3()
    monkeypatch.setattr(cvs, "get_conn", lambda: conn)
    monkeypatch.setattr(cvs, "put_conn", lambda c: None)

    with pytest.raises(RuntimeError, match="simulated insert failure"):
        cvs.create_verification(
            user_id="u1",
            company_name="FailCo",
            country_iso3="KOR",
            registration_number=None,
            provider="opencorporates",
            registry_check_status="BASIC_CONFIRMED",
            result_json={"mock": True},
        )

    assert conn.rollbacks == 1
