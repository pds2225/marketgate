"""Bounded, process-local prediction cache. Authentication stays outside it."""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from datetime import date
import json
from threading import Lock
from time import monotonic
from typing import Any, Callable

from app.models import PredictRequest


class PredictCache:
    def __init__(self, maxsize: int = 128, ttl_seconds: float = 300.0):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._entries: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = Lock()
        # Fixed-size single-flight locks coalesce concurrent identical requests.
        self._flights = [Lock() for _ in range(16)]

    @staticmethod
    def key(req: PredictRequest, user_id: str) -> str:
        # Include every present/future model field, nested filters, and date-based
        # opportunity scoring. List order and None/default distinctions survive.
        return json.dumps(
            [user_id, date.today().isoformat(), req.model_dump(mode="json")],
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        )

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def get_or_compute(
        self, req: PredictRequest, user_id: str | None,
        compute: Callable[[], dict[str, Any]],
        cacheable: Callable[[dict[str, Any]], bool] = lambda _: True,
    ) -> dict[str, Any]:
        if not user_id:
            return compute()
        key = self.key(req, user_id)
        with self._flights[hash(key) % len(self._flights)]:
            with self._lock:
                now = monotonic()
                # Expire all stale entries to keep memory bounded under churn.
                for stale in [k for k, (expiry, _) in self._entries.items() if expiry <= now]:
                    del self._entries[stale]
                entry = self._entries.get(key)
                if entry is not None:
                    self._entries.move_to_end(key)
                    return deepcopy(entry[1])
            result = compute()
            if cacheable(result):
                with self._lock:
                    self._entries[key] = (monotonic() + self.ttl_seconds, deepcopy(result))
                    self._entries.move_to_end(key)
                    while len(self._entries) > self.maxsize:
                        self._entries.popitem(last=False)
            return result
