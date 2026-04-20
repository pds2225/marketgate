from app.models import PredictRequest
from app.services.data_loaders import get_world_trade_value_usd, load_datastore
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

    results, _ = recommend_countries(req)

    assert len(results) >= 5
    assert all(item["explanation"]["trade_signal_source"] in {"partner_observed", "world_total_allocated"} for item in results)
    assert any(item["explanation"]["trade_signal_source"] == "world_total_allocated" for item in results)
