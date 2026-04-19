"""
더미 데이터 생성 모듈
UN Comtrade 실데이터 형식과 호환되는 더미 데이터를 생성
"""

import pandas as pd
import numpy as np
from typing import Tuple

# 랜덤 시드 고정
np.random.seed(42)

# 국가 코드 리스트 (ISO-3)
COUNTRIES = [
    'USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'IND', 'ITA', 'BRA', 'CAN',
    'RUS', 'AUS', 'ESP', 'MEX', 'IDN', 'NLD', 'SAU', 'TUR', 'CHE', 'POL',
    'BEL', 'SWE', 'ARG', 'NOR', 'AUT', 'ARE', 'NGA', 'ISR', 'HKG', 'SGP',
    'MYS', 'THA', 'VNM', 'PHL', 'PAK', 'BGD', 'EGY', 'ZAF', 'CHL', 'COL'
]

# HS 코드 리스트 (2자리)
HS_CODES = ['33', '84', '85', '87', '27', '39', '90', '30', '29', '72']


def generate_dummy_data(n_samples: int = 5000) -> pd.DataFrame:
    """
    학습용 더미 데이터 생성

    Args:
        n_samples: 생성할 샘플 개수

    Returns:
        pd.DataFrame: 더미 데이터
    """
    data = []

    for _ in range(n_samples):
        exporter = 'KOR'  # 한국 고정
        target = np.random.choice(COUNTRIES)
        hs_code = np.random.choice(HS_CODES)

        # 경제 지표
        gdp_target = np.random.uniform(500, 25000)  # 억 USD
        gdp_growth = np.random.uniform(-2, 8)  # %

        # 거리 (한국 기준, 대략적)
        if target in ['CHN', 'JPN', 'VNM', 'THA', 'MYS', 'SGP', 'PHL']:
            distance_km = np.random.uniform(500, 3000)
        elif target in ['USA', 'CAN', 'MEX', 'BRA', 'ARG', 'CHL', 'COL']:
            distance_km = np.random.uniform(10000, 15000)
        else:
            distance_km = np.random.uniform(7000, 12000)

        # 물류 성과 지수 (1-5)
        lpi_score = np.random.uniform(2.0, 4.5)

        # FTA 존재 여부
        fta_countries = ['USA', 'CHN', 'SGP', 'VNM', 'AUS', 'CAN', 'GBR']
        fta = 1 if target in fta_countries else 0

        # 관세율 (%)
        tariff_rate = np.random.uniform(0, 15) if fta == 0 else np.random.uniform(0, 3)

        # 문화적 유사성 지수 (0-100)
        if target in ['CHN', 'JPN', 'VNM', 'THA', 'SGP']:
            culture_index = np.random.uniform(60, 90)
        else:
            culture_index = np.random.uniform(30, 70)

        # 규제 편의성 지수 (0-100, 높을수록 좋음)
        regulation_index = np.random.uniform(40, 95)

        # 실제 수출액 (종속변수) - 중력모형 기반으로 생성
        # log(export) = 상수항 + GDP효과 - 거리효과 + FTA효과 + 노이즈
        log_export = (
            5.0 +
            0.8 * np.log(gdp_target) -
            0.5 * np.log(distance_km) +
            0.7 * fta +
            0.3 * (lpi_score / 4.5) +
            0.2 * (gdp_growth / 8) -
            0.15 * (tariff_rate / 15) +
            0.1 * (culture_index / 100) +
            0.1 * (regulation_index / 100) +
            np.random.normal(0, 0.5)  # 노이즈
        )

        export_value_usd = np.exp(log_export)

        data.append({
            'exporter_country': exporter,
            'target_country': target,
            'hs_code': hs_code,
            'gdp_target': gdp_target,
            'gdp_growth': gdp_growth,
            'distance_km': distance_km,
            'lpi_score': lpi_score,
            'fta': fta,
            'tariff_rate': tariff_rate,
            'culture_index': culture_index,
            'regulation_index': regulation_index,
            'export_value_usd': export_value_usd
        })

    df = pd.DataFrame(data)
    return df


def generate_prediction_data(hs_code: str = '33') -> pd.DataFrame:
    """
    예측용 데이터 생성 (모든 국가에 대해)

    Args:
        hs_code: HS 코드

    Returns:
        pd.DataFrame: 예측용 데이터
    """
    data = []

    for target in COUNTRIES:
        exporter = 'KOR'

        # 경제 지표 (실제로는 외부 API에서 가져와야 함)
        gdp_target = np.random.uniform(500, 25000)
        gdp_growth = np.random.uniform(-2, 8)

        # 거리
        if target in ['CHN', 'JPN', 'VNM', 'THA', 'MYS', 'SGP', 'PHL']:
            distance_km = np.random.uniform(500, 3000)
        elif target in ['USA', 'CAN', 'MEX', 'BRA', 'ARG', 'CHL', 'COL']:
            distance_km = np.random.uniform(10000, 15000)
        else:
            distance_km = np.random.uniform(7000, 12000)

        lpi_score = np.random.uniform(2.0, 4.5)

        fta_countries = ['USA', 'CHN', 'SGP', 'VNM', 'AUS', 'CAN', 'GBR']
        fta = 1 if target in fta_countries else 0

        tariff_rate = np.random.uniform(0, 15) if fta == 0 else np.random.uniform(0, 3)

        if target in ['CHN', 'JPN', 'VNM', 'THA', 'SGP']:
            culture_index = np.random.uniform(60, 90)
        else:
            culture_index = np.random.uniform(30, 70)

        regulation_index = np.random.uniform(40, 95)

        data.append({
            'exporter_country': exporter,
            'target_country': target,
            'hs_code': hs_code,
            'gdp_target': gdp_target,
            'gdp_growth': gdp_growth,
            'distance_km': distance_km,
            'lpi_score': lpi_score,
            'fta': fta,
            'tariff_rate': tariff_rate,
            'culture_index': culture_index,
            'regulation_index': regulation_index
        })

    df = pd.DataFrame(data)
    return df


if __name__ == '__main__':
    # 테스트
    print("더미 데이터 생성 테스트...")

    # 학습용 데이터 생성
    train_data = generate_dummy_data(5000)
    print(f"\n학습용 데이터: {train_data.shape}")
    print(train_data.head())
    print(f"\n기초 통계:")
    print(train_data.describe())

    # 예측용 데이터 생성
    pred_data = generate_prediction_data('33')
    print(f"\n예측용 데이터: {pred_data.shape}")
    print(pred_data.head())

    # CSV로 저장
    train_data.to_csv('backend/train_data.csv', index=False)
    print("\n학습용 데이터를 train_data.csv로 저장했습니다.")
