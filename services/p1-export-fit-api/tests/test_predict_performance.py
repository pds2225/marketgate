"""MG-015: full JSON equality with original main and cache/index invariants."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
import gc
import hashlib
import json
import math
from pathlib import Path
import threading
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient
from fastapi import HTTPException
import pandas as pd
import pytest

from app.models import PredictRequest
from app.auth_deps import get_current_user
from app.services import data_loaders as loaders
from app.services import buyer_shortlist
from app.services import predict_cache
from app.services.predict_cache import PredictCache
import main as api

GOLDEN = Path(__file__).parent / "fixtures/predict_golden"


@pytest.fixture
def golden_snapshot(monkeypatch):
    import shortlist_service

    manifest = json.loads((GOLDEN / "manifest.json").read_text(encoding="utf-8"))

    class SnapshotDate(date):
        @classmethod
        def today(cls):
            return date.fromisoformat(manifest["reference_date"])

    monkeypatch.setattr(buyer_shortlist, "date", SnapshotDate)
    # The original opportunity CSV is an ignored, empty local output. Include
    # its exact snapshot so a clean PR checkout can reproduce the golden test.
    original_loader = shortlist_service._load_frame_cached
    opportunity_frame = shortlist_service._read_frame(GOLDEN / "opportunity_item.csv")

    def snapshot_loader(output_dir_str, filename):
        if filename == "opportunity_item.csv" and Path(output_dir_str) == buyer_shortlist.COSMETICS_OUTPUT_DIR:
            return opportunity_frame
        return original_loader(output_dir_str, filename)

    monkeypatch.setattr(shortlist_service, "_load_frame_cached", snapshot_loader)


@pytest.fixture(autouse=True)
def clear_prediction_cache():
    api._PREDICT_CACHE.clear()
    yield
    api._PREDICT_CACHE.clear()


def test_golden_dataset_matches_original_main_snapshot():
    manifest = json.loads((GOLDEN / "manifest.json").read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parents[3]
    assert manifest["base_sha"] == "09ae2f7c49da503c9be221e85f885434affb42df"
    for filename, expected in manifest["data_sha256"].items():
        fixture = manifest.get("fixture_overrides", {}).get(filename)
        snapshot = GOLDEN / fixture if fixture else root / filename
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == expected, filename


@pytest.mark.parametrize("name", ["330499", "854140", "210690", "620343", "330499_filters"])
def test_real_predict_miss_and_hit_equal_original_json(name, monkeypatch, golden_snapshot):
    golden = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
    calls = []
    original = api.recommend_countries

    def counted(req):
        calls.append(req)
        return original(req)

    monkeypatch.setattr(api, "recommend_countries", counted)
    client = TestClient(api.app)
    request_ids = []
    for _ in range(2):
        response = client.post("/v1/predict", json=golden["request"])
        assert response.status_code == 200
        body = response.json()
        request_ids.append(body.pop("request_id"))
        assert body.pop("timestamp")
        # Exact dict/list/float equality: no tolerance or field exclusions other
        # than request metadata. Includes all ranks, buyers, scores and fields.
        assert body == golden["response"]
    assert request_ids[0] != request_ids[1]
    assert len(calls) == 1


@pytest.mark.parametrize("changes", [
    {"hs_code": "854140"}, {"exporter_country_iso3": "USA"},
    {"top_n": 3}, {"year": 2022}, {"filters": None},
    {"filters": {"exclude_countries_iso3": ["USA"]}},
    {"filters": {"min_trade_value_usd": 1}},
])
def test_cache_key_includes_every_current_request_field(changes):
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR", top_n=5, year=2023)
    altered = PredictRequest(**{**req.model_dump(), **changes})
    assert PredictCache.key(req, "user-a") != PredictCache.key(altered, "user-a")


def test_cache_key_includes_future_fields_and_user_identity():
    class ExtendedRequest(PredictRequest):
        keywords: list[str] = []
        include_rejected: bool = False
    req = ExtendedRequest(hs_code="330499", exporter_country_iso3="KOR")
    assert PredictCache.key(req, "a") != PredictCache.key(req, "b")
    for changed in (req.model_copy(update={"keywords": ["serum"]}), req.model_copy(update={"include_rejected": True})):
        assert PredictCache.key(req, "a") != PredictCache.key(changed, "a")


def test_cache_ttl_lru_and_defensive_deep_copy(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(predict_cache, "monotonic", lambda: clock[0])
    cache = PredictCache(maxsize=2, ttl_seconds=10)
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR")
    source = {"results": [{"score": 1, "terms": ["serum"]}]}
    calls = []

    def compute():
        calls.append(True)
        return deepcopy(source)

    first = cache.get_or_compute(req, "a", compute)
    first["results"][0]["terms"].append("poison")
    hit = cache.get_or_compute(req, "a", compute)
    assert hit == source
    hit["results"][0]["score"] = 99
    assert cache.get_or_compute(req, "a", compute) == source
    assert len(calls) == 1
    cache.get_or_compute(req, "b", compute)
    cache.get_or_compute(req, "a", compute)  # a is most recently used
    cache.get_or_compute(req, "c", compute)  # evicts b
    cache.get_or_compute(req, "b", compute)
    assert len(calls) == 4
    assert len(cache._entries) == 2
    clock[0] = 10.0  # expiry boundary is a miss
    cache.get_or_compute(req, "b", compute)
    assert len(calls) == 5


def test_concurrent_identical_requests_compute_once():
    cache = PredictCache()
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR")
    barrier = threading.Barrier(4)
    calls = []

    def compute():
        calls.append(True)
        time.sleep(0.02)
        return {"nested": [1]}

    def request(_):
        barrier.wait()
        return cache.get_or_compute(req, "same-user", compute)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(request, range(4)))
    assert len(calls) == 1
    assert results == [{"nested": [1]}] * 4
    assert len({id(result["nested"]) for result in results}) == 4


def test_failures_and_requests_without_identity_are_not_cached():
    cache = PredictCache()
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR")
    calls = []

    def compute():
        calls.append(True)
        return {"unavailable": True}

    for _ in range(2):
        cache.get_or_compute(req, None, compute)
        cache.get_or_compute(req, "a", compute, cacheable=lambda _: False)
    assert len(calls) == 4
    assert not cache._entries


def test_endpoint_refreshes_metadata_and_separates_users(monkeypatch):
    calls = []
    metadata = iter(["first", "second", "third"])
    metadata_times = iter(["time1", "time2", "time3"])
    monkeypatch.setattr(api, "new_request_id", lambda: next(metadata))
    monkeypatch.setattr(api, "now_seoul_iso", lambda: next(metadata_times))
    monkeypatch.setattr(api, "recommend_countries", lambda req: (calls.append(req) or [], {}, {}))
    monkeypatch.setattr(api, "build_buyer_shortlist", lambda *_: SimpleNamespace(status="ok", meta={}))
    monkeypatch.setattr(loaders, "load_datastore", lambda: SimpleNamespace(load_errors=[]))
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR")
    first = api.predict(req, {"user_id": "a"})
    second = api.predict(req, {"user_id": "a"})
    third = api.predict(req, {"user_id": "b"})
    assert len(calls) == 2
    assert [item["request_id"] for item in (first, second, third)] == ["first", "second", "third"]
    assert [item["timestamp"] for item in (first, second, third)] == ["time1", "time2", "time3"]


def test_cached_prediction_still_requires_authentication(monkeypatch):
    golden = json.loads((GOLDEN / "854140.json").read_text(encoding="utf-8"))
    client = TestClient(api.app)
    assert client.post("/v1/predict", json=golden["request"]).status_code == 200

    def deny():
        raise HTTPException(status_code=401, detail="authentication required")

    def must_not_compute(_):
        raise AssertionError("unauthenticated request reached prediction")

    monkeypatch.setitem(api.app.dependency_overrides, get_current_user, deny)
    monkeypatch.setattr(api, "recommend_countries", must_not_compute)
    assert client.post("/v1/predict", json=golden["request"]).status_code == 401


def test_trade_index_preserves_duplicate_order_hs4_precedence_and_frames():
    trade = pd.DataFrame({
        "refYear": [2023] * 7, "reporterISO": [" kor "] * 7,
        "partnerISO": ["w00"] * 7,
        "cmdCode": ["3304", "33", "3304", "3304", "3304", "33", "330499"],
        "trade_value_usd": [1e16, 999.0, 1.0, -1e16, 3.0, 5.0, 10000.0],
    })
    snapshot = trade.copy(deep=True)
    base = loaders._trade_rows_for_reporter_partner(trade, 2023, "KOR", "W00")
    expected = loaders._match_trade_value_by_hs(base, "330499")
    assert loaders.get_world_trade_value_usd(trade, 2023, "KOR", "330499") == expected
    assert loaders.get_world_trade_value_usd(trade, 2022, "KOR", "330499") is None
    assert loaders.get_world_trade_value_usd(trade, 2023, "KOR", "854140") is None
    pd.testing.assert_frame_equal(trade, snapshot)


def test_wb_distance_means_preserve_old_float_nan_whitespace_and_no_mutation():
    wb = pd.DataFrame({"REF_AREA": ["usa", "USA", "usa", "USA", " USA ", "JPN"],
                       "TIME_PERIOD": [2023] * 6, "OBS_VALUE": [1e16, 1.0, -1e16, 3.0, 100.0, "bad"]})
    distance = pd.DataFrame({"origin_country": ["kor"] * 6,
                             "target_country": wb["REF_AREA"], "distance_km": wb["OBS_VALUE"]})
    snapshots = (wb.copy(deep=True), distance.copy(deep=True))
    for iso in ("USA", " USA ", "JPN", "XXX"):
        selected = wb[(wb["REF_AREA"].astype(str).str.upper() == iso) & (wb["TIME_PERIOD"].astype(int) == 2023)]
        expected = None if selected.empty else float(pd.to_numeric(selected["OBS_VALUE"], errors="coerce").dropna().mean())
        for actual in (loaders.get_wb_value(wb, 2023, iso), loaders.get_distance_km(distance, "KOR", iso)):
            assert (math.isnan(actual) if expected is not None and math.isnan(expected) else actual == expected)
    pd.testing.assert_frame_equal(wb, snapshots[0])
    pd.testing.assert_frame_equal(distance, snapshots[1])


def test_kotra_index_keeps_python_average_and_mapping_order():
    kotra = pd.DataFrame({"HSCD": [330499, 330499, 330499, 330499, 999999],
                          "NAT_NAME": ["미 국"] * 5, "EXP_BHRC_SCR": [1e16, 1.0, -1e16, 3.0, 900.0]})
    mofa = pd.DataFrame({"한글명": ["미국"], "국제표준화기구_3자리": [" usa "]})
    snapshot = kotra.copy(deep=True)
    assert loaders.kotra_candidate_scores("330499", mofa, kotra) == {"USA": max(sum([1e16, 1.0, -1e16, 3.0]) / 4, 0.1)}
    assert loaders.kotra_candidate_scores("000000", mofa, kotra) == {}
    pd.testing.assert_frame_equal(kotra, snapshot)


def test_indexes_release_replaced_dataframes():
    frame = pd.DataFrame({"HSCD": [330499]})
    identity = id(frame)
    loaders._kotra_hs_positions(frame)
    assert identity in loaders._FRAME_LOOKUPS
    del frame
    gc.collect()
    assert identity not in loaders._FRAME_LOOKUPS
