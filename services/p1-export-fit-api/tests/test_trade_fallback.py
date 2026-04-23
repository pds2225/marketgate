from app.models import PredictRequest
from app.services.data_loaders import (
    get_world_trade_value_usd,
    kotra_candidate_scores,
    load_datastore,
)
from app.services.scoring import _allocate_world_trade_proxy_value, recommend_countries


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
    assert any(item["explanation"]["trade_signal_source"] == "world_total_allocated" for item in results)
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
