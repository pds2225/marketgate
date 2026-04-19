"""
실데이터 통합 수집기
모든 데이터 소스를 통합하여 학습/예측용 데이터프레임 생성
"""

import pandas as pd
import numpy as np
from typing import List, Optional
import os
from datetime import datetime

from data_sources.un_comtrade import ComtradeDataFetcher
from data_sources.world_bank import WorldBankDataFetcher
from data_sources.supplementary_data import SupplementaryDataProvider


class RealDataCollector:
    """
    실데이터 통합 수집기

    여러 데이터 소스를 통합하여 모델 학습/예측용 데이터 생성
    """

    # 주요 타겟 국가 리스트
    DEFAULT_COUNTRIES = [
        'USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'IND', 'ITA', 'BRA', 'CAN',
        'RUS', 'AUS', 'ESP', 'MEX', 'IDN', 'NLD', 'SAU', 'TUR', 'CHE', 'POL',
        'BEL', 'SWE', 'ARG', 'NOR', 'AUT', 'ARE', 'NGA', 'ISR', 'HKG', 'SGP',
        'MYS', 'THA', 'VNM', 'PHL', 'PAK', 'BGD', 'EGY', 'ZAF', 'CHL', 'COL'
    ]

    def __init__(self,
                 use_real_data: bool = False,
                 comtrade_api_key: Optional[str] = None):
        """
        Args:
            use_real_data: True면 실제 API 호출, False면 더미 데이터
            comtrade_api_key: UN Comtrade API 키
        """
        self.use_real_data = use_real_data

        # 데이터 소스 초기화
        self.comtrade = ComtradeDataFetcher(
            api_key=comtrade_api_key,
            use_real_data=use_real_data
        )
        self.world_bank = WorldBankDataFetcher(use_real_data=use_real_data)
        self.supplementary = SupplementaryDataProvider(use_real_data=use_real_data)

        print(f"[RealDataCollector] 모드: {'실데이터' if use_real_data else '더미 데이터'}")

    def collect_training_data(self,
                             exporter: str = "KOR",
                             hs_codes: List[str] = None,
                             countries: List[str] = None,
                             year: int = 2023) -> pd.DataFrame:
        """
        학습용 데이터 수집

        Args:
            exporter: 수출국 (기본: 한국)
            hs_codes: HS 코드 리스트
            countries: 타겟 국가 리스트
            year: 연도

        Returns:
            pd.DataFrame: 학습용 데이터
        """
        if hs_codes is None:
            hs_codes = ['33', '84', '85', '87', '27', '39', '90', '30', '29', '72']

        if countries is None:
            countries = self.DEFAULT_COUNTRIES

        print(f"\n[데이터 수집 시작]")
        print(f"  수출국: {exporter}")
        print(f"  타겟 국가: {len(countries)}개")
        print(f"  HS 코드: {len(hs_codes)}개")
        print(f"  연도: {year}")

        all_data = []

        # 1. World Bank 데이터 (국가별 한 번만)
        print(f"\n[1/3] World Bank 데이터 수집...")
        gdp_data = self.world_bank.get_gdp(countries, year)
        growth_data = self.world_bank.get_gdp_growth(countries, year)
        lpi_data = self.world_bank.get_lpi(countries, year)

        # 2. 보조 데이터 (국가별 한 번만)
        print(f"\n[2/3] 보조 데이터 수집...")
        distance_data = self.supplementary.get_distance(countries)
        fta_data = self.supplementary.get_fta_status(countries)
        culture_data = self.supplementary.get_culture_index(countries)
        regulation_data = self.supplementary.get_regulation_index(countries)

        # 3. UN Comtrade 데이터 (HS 코드별)
        print(f"\n[3/3] UN Comtrade 데이터 수집...")
        for hs_code in hs_codes:
            print(f"  HS {hs_code}...")

            # 관세율 (HS 코드별 다름)
            tariff_data = self.supplementary.get_tariff_rates(countries, hs_code)

            # 수출액
            export_data = self.comtrade.get_export_values(
                reporter=exporter,
                partners=countries,
                hs_code=hs_code,
                year=year
            )

            # 국가별 데이터 생성
            for country in countries:
                row = {
                    'exporter_country': exporter,
                    'target_country': country,
                    'hs_code': hs_code,
                    'gdp_target': gdp_data.get(country, 1000),
                    'gdp_growth': growth_data.get(country, 3.0),
                    'distance_km': distance_data.get(country, 8000),
                    'lpi_score': lpi_data.get(country, 3.0),
                    'fta': fta_data.get(country, 0),
                    'tariff_rate': tariff_data.get(country, 5.0),
                    'culture_index': culture_data.get(country, 50),
                    'regulation_index': regulation_data.get(country, 60),
                    'export_value_usd': export_data.get(country, 0)
                }
                all_data.append(row)

        # DataFrame 생성
        df = pd.DataFrame(all_data)

        # 수출액이 0인 행 제거 (데이터가 없는 경우)
        df = df[df['export_value_usd'] > 0]

        print(f"\n[데이터 수집 완료]")
        print(f"  총 {len(df)} 레코드")
        print(f"  수출액 범위: ${df['export_value_usd'].min():,.0f} ~ ${df['export_value_usd'].max():,.0f}")

        return df

    def collect_prediction_data(self,
                               exporter: str = "KOR",
                               hs_code: str = "33",
                               countries: List[str] = None,
                               year: int = 2023) -> pd.DataFrame:
        """
        예측용 데이터 수집 (수출액 제외)

        Args:
            exporter: 수출국
            hs_code: HS 코드
            countries: 타겟 국가 리스트
            year: 연도

        Returns:
            pd.DataFrame: 예측용 데이터
        """
        if countries is None:
            countries = self.DEFAULT_COUNTRIES

        print(f"\n[예측 데이터 수집]")
        print(f"  수출국: {exporter}")
        print(f"  HS 코드: {hs_code}")
        print(f"  타겟 국가: {len(countries)}개")

        # 1. World Bank 데이터
        gdp_data = self.world_bank.get_gdp(countries, year)
        growth_data = self.world_bank.get_gdp_growth(countries, year)
        lpi_data = self.world_bank.get_lpi(countries, year)

        # 2. 보조 데이터
        distance_data = self.supplementary.get_distance(countries)
        fta_data = self.supplementary.get_fta_status(countries)
        culture_data = self.supplementary.get_culture_index(countries)
        regulation_data = self.supplementary.get_regulation_index(countries)
        tariff_data = self.supplementary.get_tariff_rates(countries, hs_code)

        # 데이터프레임 생성
        data = []
        for country in countries:
            row = {
                'exporter_country': exporter,
                'target_country': country,
                'hs_code': hs_code,
                'gdp_target': gdp_data.get(country, 1000),
                'gdp_growth': growth_data.get(country, 3.0),
                'distance_km': distance_data.get(country, 8000),
                'lpi_score': lpi_data.get(country, 3.0),
                'fta': fta_data.get(country, 0),
                'tariff_rate': tariff_data.get(country, 5.0),
                'culture_index': culture_data.get(country, 50),
                'regulation_index': regulation_data.get(country, 60),
            }
            data.append(row)

        df = pd.DataFrame(data)

        print(f"  -> {len(df)} 국가 데이터 생성")

        return df

    def save_to_csv(self, df: pd.DataFrame, filename: str = None):
        """데이터를 CSV로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_collected_{timestamp}.csv"

        filepath = os.path.join("backend", "data", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        df.to_csv(filepath, index=False)
        print(f"\n[저장 완료] {filepath}")

        return filepath


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("실데이터 수집기 테스트")
    print("=" * 60)

    # 더미 데이터 모드로 테스트
    collector = RealDataCollector(use_real_data=False)

    # 소규모 테스트
    print("\n[테스트 1] 학습 데이터 수집")
    train_df = collector.collect_training_data(
        exporter="KOR",
        hs_codes=['33', '84'],  # 2개만
        countries=['USA', 'CHN', 'JPN', 'VNM', 'SGP'],  # 5개만
        year=2023
    )

    print("\n학습 데이터 샘플:")
    print(train_df.head(10))

    print("\n[테스트 2] 예측 데이터 수집")
    pred_df = collector.collect_prediction_data(
        exporter="KOR",
        hs_code="33",
        countries=['USA', 'CHN', 'JPN'],
        year=2023
    )

    print("\n예측 데이터 샘플:")
    print(pred_df)

    # CSV 저장
    # collector.save_to_csv(train_df, "test_training_data.csv")

    print("\n" + "=" * 60)
    print("실제 API 사용 방법:")
    print("=" * 60)
    print("""
# .env 파일 생성:
UN_COMTRADE_API_KEY=your_api_key_here

# 코드:
import os
from real_data_collector import RealDataCollector

# API 키 로드
comtrade_key = os.getenv('UN_COMTRADE_API_KEY')

# 실데이터 수집기 생성
collector = RealDataCollector(
    use_real_data=True,
    comtrade_api_key=comtrade_key
)

# 데이터 수집
df = collector.collect_training_data(
    exporter="KOR",
    hs_codes=['33'],
    year=2023
)
""")
