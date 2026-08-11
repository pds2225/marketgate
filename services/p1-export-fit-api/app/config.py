from dataclasses import dataclass

@dataclass(frozen=True)
class Files:
    # TODO: 현재 CSV 파일 기반 로드. DB 전환 시 경로 및 로더 교체 필요
    KOTRA_RECO = "csv/kotra_export_recommend_all.csv"
    MOFA_ISO3 = "csv/외교부_국가표준코드_20251222.csv"
    TRADE = "csv/trade_data.csv"
    WB_GDP = "csv/WB_WDI_NY_GDP_MKTP_CD_define column.csv"
    WB_GDP_GROWTH = "csv/WB_WDI_NY_GDP_MKTP_KD_ZG_define column.csv"
    DISTANCE = "csv/country_distance.csv"


WEIGHTS = {
    "trade_volume_score": 0.40,
    "growth_score": 0.25,
    "gdp_score": 0.20,
    "distance_score": 0.15,
}

SOFT_RULES = {
    "bottom_trade_percentile": 0.30,
    "top_distance_percentile": 0.70,
    "penalty_bottom_trade": -5.0,
    "penalty_top_distance": -5.0,
    "penalty_negative_growth": -3.0,
    # restricted / blocked는 데이터 확보 후 적용 (일단은 제재국은 없이 진행하겠다고 전달 드림(2월 3일 카톡 메신저))
    "penalty_restricted": -10.0,
}

# 점수 정규화 이상치 방어 (matchB).
# min-max 정규화가 극단 이상치(예: 마카오 코로나 반등 성장률 75.3%)에 만점을 주어
# 실수입수요가 0에 가까운 국가를 상위로 끌어올리는 결함을 막는다.
# - winsorize_*: 정규화 직전 상/하위 분위수로 클리핑해 이상치 1~2개가 스케일을 지배하지 못하게 한다.
# - low_demand_*: 실수입수요(trade_score)가 임계 이하인 국가는 성장률 단독으로 상위 진입 못 하게
#   성장 기여분을 곱셈형으로 강등한다(수요 없는데 성장률만 높아 1순위 되는 것 차단).
SCORE_NORMALIZATION = {
    # 이상치 클리핑 분위수 (growth/gdp). 0.05~0.95 = 상하위 5% 윈저라이즈.
    "winsorize_lower_quantile": 0.05,
    "winsorize_upper_quantile": 0.95,
    # 실수입수요(trade_score) 저수요 게이트 임계. 이 이하면 성장 기여분을 강등.
    "low_demand_trade_threshold": 0.05,
    # 저수요 국가의 성장 기여분에 곱하는 계수(0~1). 0.0이면 성장 단독 상위 진입 완전 차단.
    "low_demand_growth_multiplier": 0.0,
}