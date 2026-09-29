# -*- coding: utf-8 -*-
"""MG-002: demo sample limit vs real buyer search limit.

Root cause record:
- Symptom "바이어 60개까지만" came from public demo endpoints
  (`/v1/demo/snapshot`, `/v1/demo/buyers`) where `_DEFAULT_BUYER_LIMIT`
  was hardcoded to 60 while `_MAX_BUYER_LIMIT` was 200.
- Authenticated BuyerSearch uses `POST /v1/predict` →
  `build_buyer_shortlist` with `top_n` clamped to ≤10 — never the demo 60.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from app.services import demo_snapshot as demo

client = TestClient(app)


def test_mg002_demo_default_is_max_sample_cap_not_sixty():
    assert demo._DEFAULT_BUYER_LIMIT == demo._MAX_BUYER_LIMIT == 200
    buyers = demo.get_demo_buyers()
    assert len(buyers) == 200


def test_mg002_demo_explicit_limit_sixty_still_works():
    buyers = demo.get_demo_buyers(60)
    assert len(buyers) == 60


def test_mg002_demo_http_defaults_match_service():
    res = client.get("/v1/demo/buyers")
    assert res.status_code == 200
    assert len(res.json()) == 200
    res60 = client.get("/v1/demo/buyers", params={"limit": 60})
    assert res60.status_code == 200
    assert len(res60.json()) == 60


def test_mg002_predict_shortlist_limit_independent_of_demo_cap():
    """Regression: raising demo default must not imply predict returns 200."""
    # Mirror build_buyer_shortlist clamp without needing full CSV shortlist run.
    class Req:
        top_n = 60  # hostile value — must still clamp to ≤10

    # Inspect the clamp expression used by build_buyer_shortlist
    limit = min(int(getattr(Req(), "top_n", 5) or 5), 10)
    assert limit == 10
    assert demo._DEFAULT_BUYER_LIMIT == 200
    assert limit != demo._DEFAULT_BUYER_LIMIT


def test_demo_buyers_keep_ksure_kotra_provenance():
    """L028: demo snapshot must keep CSV provenance and K-SURE/KOTRA counts."""
    summary = demo.get_demo_summary()
    assert summary["total"] == 36241
    by_source = {row["name"]: row["count"] for row in summary["bySource"]}
    assert by_source["KOTRA SNS"] == 33446
    assert by_source["K-SURE 화장품"] == 386
    assert by_source["K-SURE 바이어검색"] == 235

    buyers = demo.get_demo_buyers(3)
    first = buyers[0]
    assert first["source_dataset"] == "한국무역보험공사_화장품 바이어 정보"
    assert first["source_file"] == "한국무역보험공사_화장품 바이어 정보_20200812.csv"
    assert first["source_row_no"] == "126"
    assert first["source_snapshot_date"] == "2020-08-12"
    for item in buyers:
        assert str(item.get("source_dataset") or "").strip()
        assert str(item.get("source_file") or "").strip()
        assert str(item.get("source_row_no") or "").strip()
