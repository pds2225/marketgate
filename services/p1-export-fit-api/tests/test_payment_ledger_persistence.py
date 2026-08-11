"""L027: payment ledger + credits must survive Render ephemeral wipe.

When DATABASE_URL is set, fulfill_payment_once and credit charge must use
Postgres. Otherwise a cold start clears payments.json/credits.json and a
confirm/webhook retry double-grants purchased credits.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import credit_store, payment_store


class _MemDb:
    """Minimal stand-in for psycopg2 connection/cursor used by stores."""

    def __init__(self):
        self.payments: dict[str, dict] = {}
        self.credits: dict[str, dict] = {}
        self._locked_order: str | None = None

    def cursor(self):
        return _MemCur(self)

    def commit(self):
        return None

    def rollback(self):
        return None


class _MemCur:
    def __init__(self, db: _MemDb):
        self.db = db
        self._rows: list = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        sql_n = " ".join(sql.split())
        params = params or ()
        self._rows = []

        if "FROM payment_ledger" in sql_n and "FOR UPDATE" in sql_n:
            order_id = params[0]
            row = self.db.payments.get(order_id)
            self._rows = [self._payment_tuple(order_id, row)] if row else []
            return

        if sql_n.startswith("INSERT INTO payment_ledger"):
            (
                order_id,
                user_id,
                product_type,
                package,
                plan,
                amount,
                status,
                _created,
                updated,
            ) = params
            self.db.payments[order_id] = {
                "user_id": user_id,
                "product_type": product_type,
                "package": package,
                "plan": plan,
                "amount": amount,
                "status": status,
                "updated_at": updated,
            }
            return

        if sql_n.startswith("UPDATE payment_ledger"):
            user_id, product_type, package, plan, amount, status, updated, order_id = params
            row = self.db.payments[order_id]
            row.update(
                {
                    "user_id": user_id,
                    "product_type": product_type,
                    "package": package,
                    "plan": plan,
                    "amount": amount,
                    "status": status,
                    "updated_at": updated,
                }
            )
            return

        if "FROM credit_accounts" in sql_n and "FOR UPDATE" in sql_n:
            user_id = params[0]
            row = self.db.credits.get(user_id)
            if row:
                self._rows = [(row["balance"], row["history"])]
            else:
                self._rows = []
            return

        if sql_n.startswith("INSERT INTO credit_accounts") and "ON CONFLICT" in sql_n:
            if "DO NOTHING" in sql_n:
                user_id, balance, history, _updated = params
                self.db.credits.setdefault(
                    user_id,
                    {"balance": balance, "history": json.loads(history)},
                )
                return
            user_id, balance, history, _updated = params
            self.db.credits[user_id] = {
                "balance": balance,
                "history": json.loads(history),
            }
            return

        raise AssertionError(f"unhandled SQL in fake db: {sql_n}")

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    @staticmethod
    def _payment_tuple(order_id: str, row: dict):
        return (
            order_id,
            row["user_id"],
            row["product_type"],
            row["package"],
            row["plan"],
            row["amount"],
            row["status"],
            row["updated_at"],
        )


@pytest.fixture()
def pg_stores(monkeypatch, tmp_path):
    """Force Postgres path with an in-memory fake, keep files empty/wiped."""
    db = _MemDb()
    monkeypatch.setattr(payment_store, "PAYMENTS_PATH", str(tmp_path / "payments.json"))
    monkeypatch.setattr(credit_store, "CREDITS_PATH", str(tmp_path / "credits.json"))
    monkeypatch.setattr(payment_store, "is_available", lambda: True)
    monkeypatch.setattr(credit_store, "is_available", lambda: True)

    def _tx():
        class _Ctx:
            def __enter__(self):
                return db

            def __exit__(self, *a):
                return False

        return _Ctx()

    monkeypatch.setattr(payment_store, "transaction", _tx)
    monkeypatch.setattr(credit_store, "get_conn", lambda: db)
    monkeypatch.setattr(credit_store, "put_conn", lambda _c: None)
    monkeypatch.setattr(credit_store, "in_transaction", lambda: True)
    return db


def test_fulfill_does_not_double_after_file_wipe(pg_stores):
    user_id = "u-l027"
    order_id = "ord-l027-credit"
    applied = {"n": 0}

    def apply_fn():
        applied["n"] += 1
        credit_store.charge(user_id, 30, note="pack")

    first = payment_store.fulfill_payment_once(
        order_id=order_id,
        user_id=user_id,
        product_type="credit",
        package="medium",
        plan=None,
        amount=54000,
        apply_fn=apply_fn,
    )
    assert first["duplicate"] is False
    assert applied["n"] == 1
    assert credit_store.get_balance(user_id) == credit_store.DEFAULT_BALANCE + 30

    # Simulate Render ephemeral wipe of JSON ledgers.
    Path(payment_store.PAYMENTS_PATH).unlink(missing_ok=True)
    Path(credit_store.CREDITS_PATH).unlink(missing_ok=True)

    second = payment_store.fulfill_payment_once(
        order_id=order_id,
        user_id=user_id,
        product_type="credit",
        package="medium",
        plan=None,
        amount=54000,
        apply_fn=apply_fn,
    )
    assert second["duplicate"] is True
    assert applied["n"] == 1
    assert credit_store.get_balance(user_id) == credit_store.DEFAULT_BALANCE + 30
