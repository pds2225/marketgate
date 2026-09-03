"""Atomic persistence and concurrent read tests for the inquiry JSON store."""

from __future__ import annotations

import json
import threading

import pytest

import app.inquiry_store as store


def _create(index: int = 0) -> dict:
    return store.create_inquiry(
        user_id="user-1",
        buyer_id=f"buyer-{index}",
        buyer_name=f"Buyer {index}",
        recipient_email=f"buyer{index}@example.com",
        hs_code="330499",
        sender_company="MarketGate Seller",
        sender_name="Seller User",
    )


def test_failed_atomic_replace_keeps_previous_json(tmp_path, monkeypatch):
    path = tmp_path / "inquiries.json"
    monkeypatch.setattr(store, "INQUIRIES_PATH", str(path))
    first = _create()

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(store.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        _create(1)

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert list(persisted) == [first["inquiry_id"]]
    assert list(tmp_path.glob(".inquiries-*.tmp")) == []


def test_concurrent_reads_never_observe_partial_json(tmp_path, monkeypatch):
    path = tmp_path / "inquiries.json"
    monkeypatch.setattr(store, "INQUIRIES_PATH", str(path))
    errors: list[Exception] = []
    counts: list[int] = []

    def writer():
        try:
            for index in range(30):
                _create(index)
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def reader():
        try:
            for _ in range(60):
                counts.append(len(store.list_inquiries(user_id="user-1")))
                if path.exists():
                    json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert counts == sorted(counts)
    assert len(store.list_inquiries(user_id="user-1")) == 30
