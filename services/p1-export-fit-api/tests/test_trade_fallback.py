from fastapi.testclient import TestClient
import pytest

from app.models import PredictRequest
from app.services.buyer_shortlist import build_buyer_shortlist
from app.services.data_loaders import (
    get_world_trade_value_usd,
    kotra_candidate_scores,
    load_datastore,
)
from main import app
from app.services.scoring import _allocate_world_trade_proxy_value, recommend_countries


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_allocate_world_trade_proxy_value_respects_kotra_weights():
    scores = {"USA": 30.0, "JPN": 10.0, "VNM": 10.0}

    usa_value = _allocate_world_trade_proxy_value(1_000.0, "USA", scores)
    jpn_value = _allocate_world_trade_proxy_value(1_000.0, "JPN", scores)

    assert usa_value == 600.0
    assert jpn_value == 200.0


def test_kor_2023_world_trade_total_exists_for_hs_330499():
    ds = load_datastore()
    value = get_world_trade_value_usd(ds.trade, 2023, "KOR", "330499")

    assert value is not None
    assert value > 0


def test_recommend_countries_returns_at_least_five_results_for_kor_2023():
    req = PredictRequest(
        hs_code="330499",
        exporter_country_iso3="KOR",
        top_n=5,
        year=2023,
    )

    results, _, diagnostics = recommend_countries(req)

    assert len(results) >= 5
    assert diagnostics["candidate_count"] >= len(results)
    assert diagnostics["returned_count"] == len(results)
    assert "trade_signal_counts" in diagnostics
    assert "quality_warnings" in diagnostics
    assert all(item["explanation"]["trade_signal_source"] in {"partner_observed", "world_total_allocated"} for item in results)
    # 데이터 품질 개선 후: 실제 국가별 무역 데이터가 충분하면 world_total_allocated 없을 수 있음
    # assert any(item["explanation"]["trade_signal_source"] == "world_total_allocated" for item in results)
    assert all("missing_indicators" in item["explanation"] for item in results)


def test_recommend_countries_reports_zero_result_reasons_when_all_candidates_are_excluded():
    ds = load_datastore()
    excluded = sorted(kotra_candidate_scores("330499", ds.mofa, ds.kotra).keys())
    req = PredictRequest(
        hs_code="330499",
        exporter_country_iso3="KOR",
        top_n=5,
        year=2023,
        filters={"exclude_countries_iso3": excluded, "min_trade_value_usd": 0},
    )

    results, _, diagnostics = recommend_countries(req)

    assert results == []
    assert diagnostics["returned_count"] == 0
    assert diagnostics["eligible_count"] == 0
    assert diagnostics["hard_filter_reason_counts"]["USER_EXCLUDED"] >= 1
    assert "USER_EXCLUDED" in diagnostics["zero_result_reasons"]
    assert diagnostics["sample_countries_by_reason"]["USER_EXCLUDED"]


def test_v1_predict_contract_includes_diagnostics_for_kor_330499_2023(client):
    response = client.post(
        "/v1/predict",
        json={
            "hs_code": "330499",
            "exporter_country_iso3": "KOR",
            "top_n": 5,
            "year": 2023,
        },
    )

    assert response.status_code == 200

    body = response.json()
    diagnostics = body["data"]["diagnostics"]
    results = body["data"]["results"]
    buyers = body["data"]["buyers"]

    assert body["status"] == "ok"
    assert diagnostics["candidate_count"] >= diagnostics["eligible_count"] >= diagnostics["returned_count"]
    assert diagnostics["returned_count"] == len(results)
    assert "trade_signal_counts" in diagnostics
    assert "zero_result_reasons" in diagnostics
    assert "quality_warnings" in diagnostics
    assert buyers["status"] in {"ok", "unavailable"}
    assert "items" in buyers
    assert "soft_penalty_distribution" in buyers["meta"]
    assert "country_shortlist_comparison" in buyers["meta"]
    assert "selected_opportunity_match_scores" in buyers["meta"]


def test_predict_alias_returns_legacy_shape_with_diagnostics(client):
    response = client.post(
        "/predict",
        json={
            "hs_code": "330499",
            "exporter_country": "KOR",
            "top_n": 5,
            "year": 2023,
        },
    )

    assert response.status_code == 200

    body = response.json()
    top_countries = body["top_countries"]

    assert body["data_source"] == "p1"
    assert "diagnostics" in body
    assert isinstance(top_countries, list)
    if top_countries:
        first = top_countries[0]
        assert "country" in first
        assert "score" in first
        assert "explanation" in first


def test_v1_snapshot_exposes_normalized_git_state(client):
    response = client.get("/v1/snapshot")

    assert response.status_code == 200
    body = response.json()["data"]

    assert "status_key" in body
    assert "status_text" in body
    assert "is_git_repo" in body


def test_build_buyer_shortlist_merges_top_three_countries(monkeypatch):
    captured_countries = []
    captured_profiles = []

    def fake_build_supplier_profile(**kwargs):
        captured_profiles.append(kwargs)
        return kwargs

    def fake_shortlist_buyers(**kwargs):
        target_country = kwargs["supplier_profile"]["target_country_norm"]
        captured_countries.append(target_country)
        return {
            "meta": {
                "filtered_buyer_rows": 2,
                "scored_rows": 2,
                "shortlist_count": 1,
                "candidate_count": 1,
                "rejected_count": 0,
                "soft_penalty_distribution": {
                    "missing_contact": 1 if target_country == "미국" else 0,
                    "unclear_moq": 1,
                },
                "selected_opportunity_title": f"{target_country} inquiry",
                "selected_opportunity_country_norm": target_country,
                "selected_opportunity_signal_type": "inquiry",
                "selected_opportunity_match_score": 100 if target_country == "미국" else 60,
            },
            "items": [
                {
                    "buyer_name": "Shared Buyer" if target_country != "일본" else "Japan Buyer",
                    "source_dataset": "demo",
                    "country_norm": target_country,
                    "hs_code_norm": "330499",
                    "keywords_norm": "cosmetics",
                    "has_contact": True,
                    "contact_email": f"{target_country}@example.com" if target_country != "일본" else "jp@example.com",
                    "contact_name": "",
                    "contact_phone": "",
                    "contact_website": "",
                    "final_score": 80 if target_country == "미국" else 75,
                    "decision": "shortlist",
                    "score_breakdown": {"country_score": 20},
                    "recommendation_lines": [],
                    "explanation_reasons": [f"{target_country} reason"],
                    "matched_by": "hs_exact",
                    "matched_terms": ["cosmetics"],
                }
            ],
        }

    monkeypatch.setattr("app.services.buyer_shortlist.build_supplier_profile", fake_build_supplier_profile)
    monkeypatch.setattr("app.services.buyer_shortlist.shortlist_buyers", fake_shortlist_buyers)

    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR", top_n=5, year=2023)
    country_results = [
        {"rank": 1, "partner_country_iso3": "USA", "fit_score": 91.2},
        {"rank": 2, "partner_country_iso3": "JPN", "fit_score": 88.4},
        {"rank": 3, "partner_country_iso3": "VNM", "fit_score": 84.7},
        {"rank": 4, "partner_country_iso3": "DEU", "fit_score": 80.1},
    ]

    result = build_buyer_shortlist(req, country_results)

    assert captured_countries == ["미국", "일본", "베트남"]
    assert [profile["target_hs_code_norm"] for profile in captured_profiles] == ["330499", "330499", "330499"]
    assert result.status == "ok"
    assert len(result.source_countries) == 3
    assert [item.partner_country_iso3 for item in result.source_countries] == ["USA", "JPN", "VNM"]
    assert result.meta["merged_country_count"] == 3
    assert result.meta["soft_penalty_distribution"]["unclear_moq"] == 3
    assert result.meta["soft_penalty_distribution"]["missing_contact"] == 1
    assert result.meta["country_shortlist_comparison"]["USA"]["before_merge_shortlist_count"] == 1
    assert result.meta["country_shortlist_comparison"]["USA"]["after_merge_returned_count"] == 1
    assert len(result.items) == 3
    assert result.items[0].source_target_country_iso3 == "USA"
    assert all(item.source_target_country_rank in {1, 2, 3} for item in result.items)
    # before/after 비교: 선택된 opportunity의 match_score가 meta에 노출되는지 검증
    match_scores = result.meta["selected_opportunity_match_scores"]
    assert len(match_scores) == 3
    assert all("country_iso3" in entry and "match_score" in entry for entry in match_scores)
    usa_entry = next(e for e in match_scores if e["country_iso3"] == "USA")
    assert usa_entry["match_score"] == 100
    assert usa_entry["opportunity_title"] == "미국 inquiry"
