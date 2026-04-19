"""
World Bank API 연동 모듈
GDP, GDP 성장률, LPI(물류성과지수) 등 경제 지표 데이터 수집

API Documentation: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

import requests
import pandas as pd
import time
from typing import Dict, List, Optional
import numpy as np


class WorldBankAPI:
    """World Bank API 클라이언트"""

    def __init__(self):
        self.base_url = "https://api.worldbank.org/v2"
        self.rate_limit_delay = 0.5  # API 호출 간격

    def get_indicator(self,
                     countries: List[str],
                     indicator: str,
                     year: int = 2023) -> Dict[str, float]:
        """
        특정 지표 조회

        Args:
            countries: 국가 코드 리스트 (ISO-3)
            indicator: 지표 코드
            year: 연도

        Returns:
            dict: {국가코드: 값}

        주요 지표 코드:
        - NY.GDP.MKTP.CD: GDP (current US$)
        - NY.GDP.MKTP.KD.ZG: GDP growth (annual %)
        - LP.LPI.OVRL.XQ: Logistics Performance Index (1-5)
        """
        result = {}

        # 국가 코드를 세미콜론으로 연결 (최대 60개)
        country_str = ";".join(countries[:60])

        url = f"{self.base_url}/country/{country_str}/indicator/{indicator}"
        params = {
            "date": year,
            "format": "json",
            "per_page": 500
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            time.sleep(self.rate_limit_delay)

            if response.status_code == 200:
                data = response.json()

                if len(data) > 1 and data[1]:
                    for item in data[1]:
                        country_code = item.get("countryiso3code")
                        value = item.get("value")

                        if country_code and value is not None:
                            result[country_code] = float(value)

                    print(f"[World Bank] {indicator}: {len(result)} 국가 데이터 수집")
                else:
                    print(f"[World Bank] {indicator}: 데이터 없음")
            else:
                print(f"[World Bank] {indicator}: 오류 {response.status_code}")

        except Exception as e:
            print(f"[World Bank] {indicator}: 예외 {e}")

        return result

    def get_gdp(self, countries: List[str], year: int = 2023) -> Dict[str, float]:
        """
        GDP 조회 (현재 가격 US$)

        Returns:
            dict: {국가코드: GDP (억 USD)}
        """
        data = self.get_indicator(countries, "NY.GDP.MKTP.CD", year)

        # 억 USD 단위로 변환
        return {k: v / 100000000 for k, v in data.items()}

    def get_gdp_growth(self, countries: List[str], year: int = 2023) -> Dict[str, float]:
        """
        GDP 성장률 조회 (연간 %)

        Returns:
            dict: {국가코드: 성장률 (%)}
        """
        return self.get_indicator(countries, "NY.GDP.MKTP.KD.ZG", year)

    def get_lpi(self, countries: List[str], year: int = 2023) -> Dict[str, float]:
        """
        물류성과지수 조회 (1-5)

        Returns:
            dict: {국가코드: LPI 점수}
        """
        # LPI는 2년마다 발표되므로, 가장 최근 데이터 사용
        # 2023년이면 2022년 데이터 시도
        for y in [year, year - 1, year - 2, year - 3]:
            data = self.get_indicator(countries, "LP.LPI.OVRL.XQ", y)
            if data:
                return data

        return {}


class WorldBankDataFetcher:
    """
    World Bank API와 더미 데이터를 자동 전환하는 래퍼
    """

    # 국가별 기본 데이터 (폴백용)
    COUNTRY_DEFAULTS = {
        'USA': {'gdp': 25000, 'growth': 2.5, 'lpi': 4.0},
        'CHN': {'gdp': 18000, 'growth': 5.0, 'lpi': 3.7},
        'JPN': {'gdp': 5000, 'growth': 1.5, 'lpi': 4.2},
        'DEU': {'gdp': 4500, 'growth': 0.5, 'lpi': 4.2},
        'GBR': {'gdp': 3200, 'growth': 1.0, 'lpi': 4.0},
        'FRA': {'gdp': 3000, 'growth': 0.8, 'lpi': 3.9},
        'IND': {'gdp': 3500, 'growth': 7.0, 'lpi': 3.4},
        'VNM': {'gdp': 430, 'growth': 6.5, 'lpi': 3.3},
        'THA': {'gdp': 500, 'growth': 3.5, 'lpi': 3.4},
        'SGP': {'gdp': 500, 'growth': 2.0, 'lpi': 4.3},
        'MYS': {'gdp': 400, 'growth': 4.5, 'lpi': 3.6},
        'IDN': {'gdp': 1300, 'growth': 5.5, 'lpi': 3.2},
        'AUS': {'gdp': 1700, 'growth': 2.0, 'lpi': 3.9},
        'CAN': {'gdp': 2200, 'growth': 2.2, 'lpi': 3.9},
        'MEX': {'gdp': 1500, 'growth': 3.0, 'lpi': 3.3},
        'BRA': {'gdp': 2100, 'growth': 2.5, 'lpi': 2.9},
        'RUS': {'gdp': 1800, 'growth': 1.5, 'lpi': 2.8},
        'KOR': {'gdp': 1700, 'growth': 2.8, 'lpi': 4.0},
    }

    def __init__(self, use_real_data: bool = False):
        """
        Args:
            use_real_data: True면 실데이터 사용
        """
        self.use_real_data = use_real_data
        self.api = WorldBankAPI() if use_real_data else None

    def get_gdp(self, countries: List[str], year: int = 2023) -> Dict[str, float]:
        """GDP 조회 (억 USD)"""
        if self.use_real_data and self.api:
            try:
                data = self.api.get_gdp(countries, year)
                # 실패한 국가는 더미로 보완
                return self._fill_missing(data, countries, 'gdp')
            except Exception as e:
                print(f"[경고] GDP 실데이터 수집 실패, 더미 사용: {e}")
                return self._get_dummy_data(countries, 'gdp')
        else:
            return self._get_dummy_data(countries, 'gdp')

    def get_gdp_growth(self, countries: List[str], year: int = 2023) -> Dict[str, float]:
        """GDP 성장률 조회 (%)"""
        if self.use_real_data and self.api:
            try:
                data = self.api.get_gdp_growth(countries, year)
                return self._fill_missing(data, countries, 'growth')
            except Exception as e:
                print(f"[경고] GDP 성장률 실데이터 수집 실패, 더미 사용: {e}")
                return self._get_dummy_data(countries, 'growth')
        else:
            return self._get_dummy_data(countries, 'growth')

    def get_lpi(self, countries: List[str], year: int = 2023) -> Dict[str, float]:
        """물류성과지수 조회 (1-5)"""
        if self.use_real_data and self.api:
            try:
                data = self.api.get_lpi(countries, year)
                return self._fill_missing(data, countries, 'lpi')
            except Exception as e:
                print(f"[경고] LPI 실데이터 수집 실패, 더미 사용: {e}")
                return self._get_dummy_data(countries, 'lpi')
        else:
            return self._get_dummy_data(countries, 'lpi')

    def _get_dummy_data(self, countries: List[str], field: str) -> Dict[str, float]:
        """더미 데이터 생성"""
        result = {}
        np.random.seed(42)

        for country in countries:
            if country in self.COUNTRY_DEFAULTS:
                # 기본값에 약간의 노이즈 추가
                base_value = self.COUNTRY_DEFAULTS[country][field]
                noise = np.random.normal(0, base_value * 0.1)
                result[country] = max(0.1, base_value + noise)
            else:
                # 알려지지 않은 국가는 중간값
                if field == 'gdp':
                    result[country] = np.random.uniform(100, 1000)
                elif field == 'growth':
                    result[country] = np.random.uniform(-2, 8)
                elif field == 'lpi':
                    result[country] = np.random.uniform(2.0, 4.5)

        return result

    def _fill_missing(self, data: Dict[str, float],
                     countries: List[str],
                     field: str) -> Dict[str, float]:
        """누락된 데이터를 더미로 채우기"""
        dummy = self._get_dummy_data(countries, field)

        for country in countries:
            if country not in data or data[country] is None:
                data[country] = dummy[country]

        return data


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("World Bank API 테스트")
    print("=" * 60)

    countries = ['KOR', 'USA', 'CHN', 'JPN', 'VNM', 'THA', 'SGP']

    # 더미 데이터 모드
    fetcher = WorldBankDataFetcher(use_real_data=False)

    print("\n[더미 데이터 모드]")

    gdp_data = fetcher.get_gdp(countries, 2023)
    print("\nGDP (억 USD):")
    for country, value in gdp_data.items():
        print(f"  {country}: {value:,.0f}")

    growth_data = fetcher.get_gdp_growth(countries, 2023)
    print("\nGDP 성장률 (%):")
    for country, value in growth_data.items():
        print(f"  {country}: {value:.2f}%")

    lpi_data = fetcher.get_lpi(countries, 2023)
    print("\nLPI (1-5):")
    for country, value in lpi_data.items():
        print(f"  {country}: {value:.2f}")

    print("\n" + "=" * 60)
    print("실제 API 사용 방법:")
    print("=" * 60)
    print("""
# World Bank API는 별도 인증키가 필요 없습니다.

from data_sources.world_bank import WorldBankDataFetcher

fetcher = WorldBankDataFetcher(use_real_data=True)

gdp = fetcher.get_gdp(['KOR', 'USA'], 2023)
growth = fetcher.get_gdp_growth(['KOR', 'USA'], 2023)
lpi = fetcher.get_lpi(['KOR', 'USA'], 2023)
""")
