from dataclasses import dataclass

@dataclass(frozen=True)
class Files:
    # csv 파일 로드라서, 일단 상대 경로로 접근. ****** 추후 db화 예정임
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