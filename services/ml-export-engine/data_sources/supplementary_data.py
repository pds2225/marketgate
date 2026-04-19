"""
보조 데이터 소스 모듈
- 관세율 (WTO/UN TRAINS)
- 거리 데이터
- FTA 정보
- 문화적 유사성
- 규제 지표
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import math


class SupplementaryDataProvider:
    """보조 데이터 제공자"""

    def __init__(self, use_real_data: bool = False):
        self.use_real_data = use_real_data

        # 한국의 위도/경도
        self.korea_coords = (37.5665, 126.9780)

        # 주요 국가 좌표 (더미/폴백용)
        self.country_coords = {
            'USA': (37.0902, -95.7129),
            'CHN': (35.8617, 104.1954),
            'JPN': (36.2048, 138.2529),
            'DEU': (51.1657, 10.4515),
            'GBR': (55.3781, -3.4360),
            'FRA': (46.2276, 2.2137),
            'IND': (20.5937, 78.9629),
            'VNM': (14.0583, 108.2772),
            'THA': (15.8700, 100.9925),
            'SGP': (1.3521, 103.8198),
            'MYS': (4.2105, 101.9758),
            'IDN': (-0.7893, 113.9213),
            'PHL': (12.8797, 121.7740),
            'AUS': (-25.2744, 133.7751),
            'CAN': (56.1304, -106.3468),
            'MEX': (23.6345, -102.5528),
            'BRA': (-14.2350, -51.9253),
            'RUS': (61.5240, 105.3188),
            'ARG': (-38.4161, -63.6167),
            'CHL': (-35.6751, -71.5430),
            'ESP': (40.4637, -3.7492),
            'ITA': (41.8719, 12.5674),
            'NLD': (52.1326, 5.2913),
            'POL': (51.9194, 19.1451),
            'SAU': (23.8859, 45.0792),
            'ARE': (23.4241, 53.8478),
            'EGY': (26.8206, 30.8025),
            'ZAF': (-30.5595, 22.9375),
            'PAK': (30.3753, 69.3451),
            'BGD': (23.6850, 90.3563),
        }

        # FTA 체결 국가 (한국 기준, 2024년 기준)
        self.korea_fta_partners = [
            'USA', 'CHN', 'SGP', 'VNM', 'AUS', 'CAN', 'GBR',
            'CHL', 'NZL', 'PER', 'TUR', 'COL', 'ISR'
        ]

    def get_distance(self, countries: List[str]) -> Dict[str, float]:
        """
        한국으로부터의 거리 계산 (km)

        Returns:
            dict: {국가코드: 거리(km)}
        """
        result = {}

        for country in countries:
            if country in self.country_coords:
                coords = self.country_coords[country]
                distance = self._haversine_distance(
                    self.korea_coords,
                    coords
                )
                result[country] = distance
            else:
                # 알려지지 않은 국가는 평균 거리
                result[country] = 8000.0

        return result

    def _haversine_distance(self,
                           coord1: Tuple[float, float],
                           coord2: Tuple[float, float]) -> float:
        """
        Haversine 공식으로 두 지점 간 거리 계산

        Args:
            coord1: (위도, 경도)
            coord2: (위도, 경도)

        Returns:
            float: 거리 (km)
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        # 라디안으로 변환
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine 공식
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # 지구 반지름 (km)
        r = 6371

        return c * r

    def get_fta_status(self, countries: List[str]) -> Dict[str, int]:
        """
        FTA 체결 여부 (한국 기준)

        Returns:
            dict: {국가코드: 1 (체결) or 0 (미체결)}
        """
        result = {}

        for country in countries:
            result[country] = 1 if country in self.korea_fta_partners else 0

        return result

    def get_tariff_rates(self, countries: List[str],
                        hs_code: str = "33") -> Dict[str, float]:
        """
        관세율 조회 (%)

        실제로는 WTO API나 UN TRAINS 데이터베이스 사용
        현재는 더미 데이터

        Returns:
            dict: {국가코드: 관세율(%)}
        """
        result = {}
        np.random.seed(hash(hs_code) % 2**32)

        for country in countries:
            if country in self.korea_fta_partners:
                # FTA 체결국은 낮은 관세
                tariff = np.random.uniform(0, 3)
            else:
                # 미체결국은 높은 관세
                tariff = np.random.uniform(3, 15)

            result[country] = tariff

        return result

    def get_culture_index(self, countries: List[str]) -> Dict[str, float]:
        """
        문화적 유사성 지수 (0-100)

        실제로는 Hofstede 문화 차원 이론 등 사용
        현재는 지역 기반 더미 데이터

        Returns:
            dict: {국가코드: 지수 (높을수록 유사)}
        """
        result = {}
        np.random.seed(42)

        # 동아시아 국가
        east_asia = ['CHN', 'JPN', 'VNM', 'THA', 'SGP', 'MYS', 'IDN', 'PHL']

        for country in countries:
            if country in east_asia:
                # 동아시아는 높은 유사도
                result[country] = np.random.uniform(60, 90)
            else:
                # 기타 국가
                result[country] = np.random.uniform(30, 70)

        return result

    def get_regulation_index(self, countries: List[str]) -> Dict[str, float]:
        """
        규제 편의성 지수 (0-100, 높을수록 좋음)

        실제로는 World Bank Doing Business Index 사용
        현재는 더미 데이터

        Returns:
            dict: {국가코드: 지수}
        """
        result = {}
        np.random.seed(43)

        # 규제가 우수한 국가
        top_countries = ['SGP', 'USA', 'GBR', 'AUS', 'CAN', 'DEU', 'JPN']

        for country in countries:
            if country in top_countries:
                result[country] = np.random.uniform(70, 95)
            else:
                result[country] = np.random.uniform(40, 70)

        return result


class RealDataProvider:
    """
    실제 데이터 소스 연동 (확장용)
    """

    def __init__(self):
        pass

    def get_wto_tariff(self, reporter: str, partner: str,
                      hs_code: str) -> float:
        """
        WTO 관세율 조회 (미구현)

        실제 구현시:
        1. WTO Tariff Download Facility 사용
        2. UN TRAINS 데이터베이스 사용
        3. 각국 관세청 API 사용
        """
        # TODO: 실제 API 연동
        return 5.0

    def get_hofstede_distance(self, country1: str, country2: str) -> float:
        """
        Hofstede 문화 거리 계산 (미구현)

        실제 구현시:
        Hofstede Insights API 또는 데이터셋 사용
        """
        # TODO: 실제 데이터 사용
        return 50.0


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("보조 데이터 소스 테스트")
    print("=" * 60)

    provider = SupplementaryDataProvider()
    countries = ['USA', 'CHN', 'JPN', 'VNM', 'THA', 'SGP', 'DEU']

    print("\n[거리 (km)]")
    distances = provider.get_distance(countries)
    for country, dist in distances.items():
        print(f"  KOR -> {country}: {dist:,.0f} km")

    print("\n[FTA 체결 여부]")
    fta = provider.get_fta_status(countries)
    for country, status in fta.items():
        status_str = "체결" if status == 1 else "미체결"
        print(f"  {country}: {status_str}")

    print("\n[관세율 (%)]")
    tariffs = provider.get_tariff_rates(countries, "33")
    for country, rate in tariffs.items():
        print(f"  {country}: {rate:.2f}%")

    print("\n[문화적 유사성 (0-100)]")
    culture = provider.get_culture_index(countries)
    for country, index in culture.items():
        print(f"  {country}: {index:.1f}")

    print("\n[규제 편의성 (0-100)]")
    regulation = provider.get_regulation_index(countries)
    for country, index in regulation.items():
        print(f"  {country}: {index:.1f}")
