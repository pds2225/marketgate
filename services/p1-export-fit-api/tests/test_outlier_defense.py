"""
matchB 회귀 테스트 — 점수 이상치 방어.

버그(고정 대상): min-max 정규화가 이상치에 무방비라, 실수입수요가 0에 가까운(저수요)
국가가 코로나 반등 성장률 같은 극단 이상치 하나로 growth_score=1.0이 되어
고수요 국가(중국·미국·일본·베트남)를 추월해 상위(top-N)로 올라오던 결함.

이 테스트는 "실수입수요 낮고 성장률 이상치만 높은 국가가 고수요 국가를 추월하지 못한다"를
① 합성 데이터(결정론)와 ② 실데이터(마카오 회귀)로 영구 고정한다.
"""
from __future__ import annotations

import pytest

from app.config import SCORE_NORMALIZATION
from app.models import PredictRequest
from app.services.scoring import _winsorize, recommend_countries


# ---------------------------------------------------------------------------
# ① 합성 데이터 — 윈저라이즈가 극단 이상치를 클리핑하는지 단언
# ---------------------------------------------------------------------------
def test_winsorize_clips_extreme_outlier_into_bulk_range():
    # 정상 분포(0~10)에 마카오류 극단 이상치 75.3 하나를 섞는다.
    bulk = [float(x) for x in range(0, 20)]  # 0..19
    values = bulk + [75.3]

    clipped = _winsorize(values)

    upper_q = max(clipped)
    # 이상치 75.3은 상위 분위수(95%) 근처로 강등돼야 한다 (만점 증폭 차단).
    assert upper_q < 75.3
    assert upper_q <= 20.0
    # 결정론·재현성: 같은 입력 2회 동일.
    assert _winsorize(values) == clipped


def test_winsorize_is_noop_for_tiny_samples():
    # 표본 2개 이하면 분위수가 무의미 → 원본 유지(과교정 금지).
    assert _winsorize([1.0, 100.0]) == [1.0, 100.0]
    assert _winsorize([5.0]) == [5.0]


# ---------------------------------------------------------------------------
# ② 실데이터 — 마카오(MAC) 회귀: 저수요 이상치 국가의 상위 추월 차단
# ---------------------------------------------------------------------------
def _rank_map(results):
    return {r["partner_country_iso3"]: r["rank"] for r in results}


def test_low_demand_outlier_country_does_not_outrank_high_demand_cosmetics():
    """330499(화장품): 수정 전 MAC 3위였으나, 저수입수요(trade≈0)이므로
    성장률 이상치만으로 top-5 진입하지 못해야 한다. 정상 상위국은 유지."""
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR", top_n=10, year=2023)
    results, _, _ = recommend_countries(req)
    ranks = _rank_map(results)

    # 정상 고수요 상위국은 그대로 상위 유지(과교정 금지).
    assert ranks.get("CHN") == 1
    for iso3 in ("USA", "JPN", "VNM"):
        assert iso3 in ranks, f"{iso3} should remain in results"
        assert ranks[iso3] <= 6, f"{iso3} should remain a top market"

    # 마카오는 저수요 이상치 국가 → top-5 진입 금지(수정 전 3위였음).
    mac_rank = ranks.get("MAC")
    assert mac_rank is None or mac_rank > 5, (
        f"MAC must not rank in top-5 on growth outlier alone (got rank={mac_rank})"
    )

    # 핵심 불변식: 저수요 MAC가 고수요 정상국(일본·베트남)을 추월하지 못한다.
    if mac_rank is not None:
        assert mac_rank > ranks["JPN"]
        assert mac_rank > ranks["VNM"]


def test_low_demand_outlier_country_does_not_outrank_high_demand_cars():
    """870380(자동차): 수정 전 MAC 2위였으나, 저수요이므로 상위에서 빠져야 한다."""
    req = PredictRequest(hs_code="870380", exporter_country_iso3="KOR", top_n=10, year=2023)
    results, _, _ = recommend_countries(req)
    ranks = _rank_map(results)

    assert ranks.get("USA") == 1, "USA(고수요)는 자동차 1위를 유지해야 한다"
    mac_rank = ranks.get("MAC")
    assert mac_rank is None or mac_rank > 5, (
        f"MAC must not rank in top-5 on growth outlier alone (got rank={mac_rank})"
    )


def test_low_demand_gate_zeroes_growth_contribution_in_explanation():
    """저수요(trade < 임계) 국가는 성장(partner_gdp_growth_pct)이
    top_factors의 1순위 동인이 되어선 안 된다 — 게이트로 강등되므로."""
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR", top_n=10, year=2023)
    results, _, _ = recommend_countries(req)

    threshold = SCORE_NORMALIZATION["low_demand_trade_threshold"]
    for r in results:
        trade_score = r["score_components"]["trade_volume_score"]
        if trade_score < threshold:
            primary_factor = r["explanation"]["top_factors"][0]["factor"]
            assert primary_factor != "partner_gdp_growth_pct", (
                f"{r['partner_country_iso3']} is low-demand (trade={trade_score:.4f}) "
                "but growth is still its primary factor — gate did not apply"
            )


def test_scoring_is_deterministic_and_reproducible():
    """같은 입력 2회 → 동일 결과(순위·점수). 결정론·재현성 유지."""
    req = PredictRequest(hs_code="330499", exporter_country_iso3="KOR", top_n=10, year=2023)
    first, _, _ = recommend_countries(req)
    second, _, _ = recommend_countries(req)

    assert [r["partner_country_iso3"] for r in first] == [r["partner_country_iso3"] for r in second]
    assert [r["fit_score"] for r in first] == [r["fit_score"] for r in second]
