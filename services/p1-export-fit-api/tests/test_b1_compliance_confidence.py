"""B1 — restricted 감점(-10) + 신뢰도(confidence/data_coverage) 테스트.

acceptance 값 출처: SIMULATION_SPEC §2.3/§3 + ADR-2026-06-10 (M6 결정).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from app.models import PredictRequest
from app.services import compliance
from app.services.confidence import build_data_coverage, confidence_level
import app.services.scoring as scoring_mod

client = TestClient(app)


# ---------- confidence 등급 경계 (R46: 0.8/0.6/0.4) ----------

@pytest.mark.parametrize(
    "value,expected",
    [
        (1.0, "high"), (0.8, "high"), (0.79, "medium"),
        (0.6, "medium"), (0.59, "low"),
        (0.4, "low"), (0.39, "very_low"), (0.0, "very_low"),
    ],
)
def test_confidence_level_boundaries(value, expected):
    assert confidence_level(value) == expected


# ---------- data_coverage 블록 (R44/R45/R47) ----------

def _fields(missing: int):
    """5필드 중 뒤에서 missing개를 None으로."""
    names = ["export_score", "gdp", "growth_rate", "market_size", "news_risk"]
    return {n: (None if i >= 5 - missing else 1.0) for i, n in enumerate(names)}


@pytest.mark.parametrize(
    "missing,confidence,level",
    [
        (0, 1.0, "high"),
        (1, 0.8, "high"),
        (2, 0.6, "medium"),
        (3, 0.4, "low"),
        (4, 0.2, "very_low"),
        (5, 0.0, "very_low"),
    ],
)
def test_data_coverage_confidence(missing, confidence, level):
    cov = build_data_coverage(_fields(missing))
    assert cov["confidence"] == confidence
    assert cov["confidence_level"] == level
    assert cov["total_fields"] == 5
    assert cov["available_fields"] == 5 - missing
    assert len(cov["missing_fields"]) == missing


def test_data_coverage_block_has_spec_fields():
    cov = build_data_coverage(_fields(1))
    for key in (
        "confidence", "confidence_level", "missing_rate", "total_fields",
        "available_fields", "missing_fields", "available_data", "data_source_status",
    ):
        assert key in cov
    assert cov["data_source_status"]["news_risk"] == "failed"
    assert cov["data_source_status"]["export_score"] == "success"
    assert "news_risk" not in cov["available_data"]


# ---------- restricted_info (SIM_SPEC §2.3/§5.1) ----------

def test_restricted_info_fields():
    info = compliance.restricted_info("RU")
    assert info["status"] == "restricted"
    assert info["requires_export_license"] is True
    assert info["restricted_since"] == "2022-03-01"


def test_restricted_info_iso3_normalized():
    assert compliance.restricted_info("RUS")["country_code"] == "RU"
    assert compliance.restricted_info("mmr")["restricted_since"] == "2021-02-01"


def test_restricted_info_none_for_normal():
    assert compliance.restricted_info("USA") is None


# ---------- scoring 통합: restricted -10 (R10/R40) ----------

class _DS:
    mofa = None
    kotra = None
    trade = "TRADE"
    wb_gdp = "GDP"
    wb_growth = "GROWTH"
    distance = "DIST"


def _patch_loaders(monkeypatch, candidates):
    monkeypatch.setattr(scoring_mod, "load_datastore", lambda: _DS())
    monkeypatch.setattr(
        scoring_mod, "kotra_candidate_scores",
        lambda hs6, mofa, kotra: {c: 10.0 for c in candidates},
    )
    monkeypatch.setattr(scoring_mod, "get_world_trade_value_usd", lambda *a: None)
    monkeypatch.setattr(
        scoring_mod, "get_trade_value_usd",
        lambda trade, year, exp, p, hs6: 1_000_000.0,
    )
    monkeypatch.setattr(
        scoring_mod, "get_wb_value",
        lambda store, year, p: 1_000_000_000.0 if store == "GDP" else 2.5,
    )
    monkeypatch.setattr(scoring_mod, "get_distance_km", lambda store, exp, p: 5000.0)


def test_restricted_country_gets_minus_10(monkeypatch):
    _patch_loaders(monkeypatch, ["RUS", "USA", "JPN"])
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR")
    results, _, _ = scoring_mod.recommend_countries(req)
    by = {r["partner_country_iso3"]: r for r in results}

    # 동일 입력값 → 차이는 restricted 감점뿐
    assert by["USA"]["fit_score"] - by["RUS"]["fit_score"] == 10.0
    assert by["RUS"]["score_components"]["compliance_penalty"] == -10.0
    assert by["USA"]["score_components"]["compliance_penalty"] == 0.0

    comp = by["RUS"]["compliance"]
    assert comp["status"] == "restricted"
    assert comp["penalty_applied"] == -10.0
    assert comp["requires_export_license"] is True
    assert comp["restricted_since"] == "2022-03-01"
    assert by["USA"]["compliance"] is None

    assert any(w["code"] == "RESTRICTED_COUNTRY" and w["severity"] == "high"
               for w in by["RUS"]["warnings"])


def test_scoring_result_has_data_coverage(monkeypatch):
    _patch_loaders(monkeypatch, ["USA", "JPN"])
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR")
    results, _, _ = scoring_mod.recommend_countries(req)
    cov = results[0]["data_coverage"]
    # news_risk만 결측(소스 미구현) → 4/5 → 0.8 high
    assert cov["confidence"] == 0.8
    assert cov["confidence_level"] == "high"
    assert cov["missing_fields"] == ["news_risk"]


# ---------- /v1/predict 응답 모델이 B1 필드를 보존 ----------

def _fake_diagnostics():
    return {
        "candidate_count": 1, "eligible_count": 1, "returned_count": 1,
        "hard_filter_reason_counts": {}, "missing_indicator_counts": {},
        "zero_result_reasons": [], "quality_warnings": [],
        "trade_signal_counts": {}, "sample_countries_by_reason": {},
    }


def test_predict_response_preserves_b1_fields(monkeypatch):
    import main as main_mod

    fake_result = {
        "rank": 1,
        "partner_country_iso3": "RUS",
        "fit_score": 30.0,
        "compliance": {"status": "restricted", "penalty_applied": -10.0},
        "data_coverage": {"confidence": 0.8, "confidence_level": "high"},
        "warnings": [{"code": "RESTRICTED_COUNTRY", "severity": "high", "message": "x"}],
        "score_components": {"soft_adjustment": -20.0, "compliance_penalty": -10.0},
        "explanation": {},
    }
    monkeypatch.setattr(
        main_mod, "recommend_countries",
        lambda req: ([fake_result], {"hs_code": "330499"}, _fake_diagnostics()),
    )
    monkeypatch.setattr(main_mod, "build_buyer_shortlist", lambda req, results: None)

    res = client.post(
        "/v1/predict",
        json={"hs_code": "330499", "exporter_country_iso3": "KOR"},
    )
    assert res.status_code == 200
    item = res.json()["data"]["results"][0]
    assert item["compliance"]["status"] == "restricted"
    assert item["data_coverage"]["confidence_level"] == "high"
    assert item["warnings"][0]["code"] == "RESTRICTED_COUNTRY"


# ---------- landed-cost: restricted는 200 + 경고 (blocked는 400 — B0 테스트) ----------

def test_landed_cost_restricted_returns_200_with_warning():
    res = client.post(
        "/v1/simulation/landed-cost",
        json={"hs_code": "330499", "country": "RU", "unit_price": 10, "qty": 100},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["compliance"]["status"] == "restricted"
    assert body["compliance"]["requires_export_license"] is True
    assert any(w["code"] == "RESTRICTED_COUNTRY" for w in body["warnings"])


def test_landed_cost_normal_has_no_compliance_block():
    res = client.post(
        "/v1/simulation/landed-cost",
        json={"hs_code": "330499", "country": "US", "unit_price": 10, "qty": 100},
    )
    assert res.status_code == 200
    assert "compliance" not in res.json()
