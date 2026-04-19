"""
UN Comtrade API 연동 모듈 (강화 버전)
실제 국제 무역 데이터를 가져옵니다.

개선 사항:
- count-only 응답 방어 (재요청 로직)
- value 컬럼 자동 탐색 (primaryValue, tradeValue, netWgt 등)
- exponential backoff 재시도
- 상세한 에러 메시지

API Documentation: https://comtradeplus.un.org/
"""

import requests
import pandas as pd
import time
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime


class UNComtradeAPI:
    """UN Comtrade API 클라이언트 (강화 버전)"""

    # value 컬럼 후보 (우선순위 순)
    VALUE_COLUMN_CANDIDATES = [
        'primaryValue',
        'tradeValue',
        'fobvalue',
        'cifvalue',
        'netWgt',
        'grossWgt'
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: UN Comtrade API 키 (없으면 무료 API 사용, 제한적)
        """
        self.base_url = "https://comtradeplus.un.org/api/get"
        self.api_key = api_key
        self.rate_limit_delay = 1.0 if api_key else 6.0
        self.max_retries = 3
        self.timeout = 30

    def _make_request_with_retry(self, params: dict, retry_count: int = 0) -> Tuple[bool, dict]:
        """
        재시도 로직을 포함한 API 요청

        Returns:
            (success: bool, data: dict)
        """
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            if response.status_code == 200:
                data = response.json()
                return True, data

            elif response.status_code == 429:  # Too Many Requests
                if retry_count < self.max_retries:
                    wait_time = (2 ** retry_count) * self.rate_limit_delay
                    print(f"  [429 Rate Limit] {wait_time:.1f}초 대기 후 재시도...")
                    time.sleep(wait_time)
                    return self._make_request_with_retry(params, retry_count + 1)
                else:
                    return False, {"error": "Rate limit exceeded after retries"}

            elif response.status_code >= 500:  # Server Error
                if retry_count < self.max_retries:
                    wait_time = (2 ** retry_count) * 2
                    print(f"  [5xx Error] {wait_time:.1f}초 대기 후 재시도...")
                    time.sleep(wait_time)
                    return self._make_request_with_retry(params, retry_count + 1)
                else:
                    return False, {"error": f"Server error {response.status_code}"}

            else:
                return False, {"error": f"HTTP {response.status_code}"}

        except requests.Timeout:
            if retry_count < self.max_retries:
                print(f"  [Timeout] 재시도 {retry_count + 1}/{self.max_retries}...")
                time.sleep(2 ** retry_count)
                return self._make_request_with_retry(params, retry_count + 1)
            else:
                return False, {"error": "Request timeout after retries"}

        except Exception as e:
            return False, {"error": str(e)}

    def _find_value_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        DataFrame에서 사용 가능한 value 컬럼 찾기

        Returns:
            컬럼명 또는 None
        """
        for candidate in self.VALUE_COLUMN_CANDIDATES:
            if candidate in df.columns:
                # 숫자형이고 null이 아닌 값이 있는지 확인
                if pd.api.types.is_numeric_dtype(df[candidate]):
                    if df[candidate].notna().any():
                        return candidate

        return None

    def _validate_response_data(self, data: dict) -> Tuple[bool, str, pd.DataFrame]:
        """
        응답 데이터 검증

        Returns:
            (is_valid: bool, message: str, df: pd.DataFrame)
        """
        if "data" not in data:
            return False, "응답에 'data' 필드가 없습니다", pd.DataFrame()

        if not data["data"]:
            return False, "데이터가 비어있습니다", pd.DataFrame()

        df = pd.DataFrame(data["data"])

        # count-only 응답 체크
        if list(df.columns) == ['count']:
            return False, "count-only 응답 (실제 데이터 없음)", df

        # 필수 컬럼 체크
        if 'partnerCode' not in df.columns:
            return False, f"필수 컬럼 'partnerCode' 누락. 컬럼: {list(df.columns)}", df

        if 'period' not in df.columns:
            return False, f"필수 컬럼 'period' 누락. 컬럼: {list(df.columns)}", df

        # value 컬럼 찾기
        value_col = self._find_value_column(df)
        if not value_col:
            return False, f"value 컬럼을 찾을 수 없습니다. 컬럼: {list(df.columns)}", df

        return True, f"정상 ({len(df)}행, value={value_col})", df

    def get_trade_data(self,
                       reporter: str = "KOR",
                       partner: str = None,
                       hs_code: str = "33",
                       year: int = 2023,
                       trade_flow: str = "X") -> pd.DataFrame:
        """
        무역 데이터 조회 (강화 버전)

        Args:
            reporter: 보고국 (ISO-3 코드)
            partner: 상대국 (ISO-3 코드, None이면 전체)
            hs_code: HS 코드
            year: 연도
            trade_flow: X(수출), M(수입)

        Returns:
            pd.DataFrame: 무역 데이터 (실패시 빈 DataFrame)
        """
        print(f"[UN Comtrade] {reporter} -> {partner or 'ALL'}, HS {hs_code}, {year}")

        # 기본 파라미터
        params = {
            "reporterCode": reporter,
            "period": year,
            "flowCode": trade_flow,
            "cmdCode": hs_code,
            "partnerCode": partner if partner else "0",
            "format": "json"
        }

        if self.api_key:
            params["subscription-key"] = self.api_key

        # 1차 시도
        success, data = self._make_request_with_retry(params)

        if not success:
            print(f"  -> 오류: {data.get('error', 'Unknown')}")
            return pd.DataFrame()

        # 응답 검증
        is_valid, message, df = self._validate_response_data(data)

        if is_valid:
            print(f"  -> {message}")
            return df

        # count-only 응답인 경우 재요청 (다른 파라미터)
        if "count-only" in message.lower():
            print(f"  -> {message}, 파라미터 변경 후 재요청...")

            # 전체 파트너로 변경
            if partner:
                params["partnerCode"] = "0"
                success, data = self._make_request_with_retry(params)

                if success:
                    is_valid, message, df = self._validate_response_data(data)
                    if is_valid:
                        print(f"  -> 재요청 성공: {message}")
                        return df

        # 최종 실패
        print(f"  -> 실패: {message}")
        return pd.DataFrame()

    def get_export_value_by_partner(self,
                                     reporter: str = "KOR",
                                     partners: List[str] = None,
                                     hs_code: str = "33",
                                     year: int = 2023) -> Dict[str, float]:
        """
        국가별 수출액 조회 (강화 버전)

        Returns:
            dict: {국가코드: 수출액(USD)}
        """
        result = {}

        if partners is None:
            # 전체 국가 조회
            df = self.get_trade_data(reporter, None, hs_code, year, "X")

            if not df.empty:
                value_col = self._find_value_column(df)

                if value_col and "partnerCode" in df.columns:
                    # 국가별 집계
                    grouped = df.groupby("partnerCode")[value_col].sum()
                    result = grouped.to_dict()
                    print(f"  -> {len(result)}개 국가 수출액 집계 완료")
                else:
                    print(f"  -> 집계 실패: value_col={value_col}, columns={list(df.columns)}")
        else:
            # 특정 국가들만 조회
            for partner in partners:
                df = self.get_trade_data(reporter, partner, hs_code, year, "X")

                if not df.empty:
                    value_col = self._find_value_column(df)
                    if value_col:
                        result[partner] = float(df[value_col].sum())
                    else:
                        result[partner] = 0.0
                else:
                    result[partner] = 0.0

        return result

    def get_historical_data(self,
                           reporter: str = "KOR",
                           partner: str = "USA",
                           hs_code: str = "33",
                           start_year: int = 2020,
                           end_year: int = 2023) -> pd.DataFrame:
        """과거 데이터 수집 (시계열)"""
        all_data = []

        for year in range(start_year, end_year + 1):
            df = self.get_trade_data(reporter, partner, hs_code, year, "X")

            if not df.empty:
                df["year"] = year
                all_data.append(df)

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()


class ComtradeDataFetcher:
    """
    UN Comtrade API와 더미 데이터를 자동 전환하는 래퍼
    API 실패시 더미 데이터로 폴백
    """

    def __init__(self, api_key: Optional[str] = None, use_real_data: bool = False):
        """
        Args:
            api_key: UN Comtrade API 키
            use_real_data: True면 실데이터 사용, False면 더미 데이터
        """
        self.use_real_data = use_real_data
        self.api = UNComtradeAPI(api_key) if use_real_data else None

    def get_export_values(self,
                         reporter: str = "KOR",
                         partners: List[str] = None,
                         hs_code: str = "33",
                         year: int = 2023) -> Dict[str, float]:
        """
        수출액 조회 (실데이터 또는 더미)

        Returns:
            dict: {국가코드: 수출액(USD)}
        """
        if self.use_real_data and self.api:
            try:
                result = self.api.get_export_value_by_partner(
                    reporter, partners, hs_code, year
                )

                # 결과가 비어있으면 더미로 폴백
                if not result:
                    print(f"[경고] 실데이터가 비어있음, 더미 데이터 사용")
                    return self._get_dummy_export_values(partners, hs_code)

                return result

            except Exception as e:
                print(f"[경고] 실데이터 수집 실패, 더미 데이터 사용: {e}")
                return self._get_dummy_export_values(partners, hs_code)
        else:
            return self._get_dummy_export_values(partners, hs_code)

    def _get_dummy_export_values(self,
                                partners: List[str] = None,
                                hs_code: str = "33") -> Dict[str, float]:
        """더미 수출액 생성"""
        import numpy as np

        if partners is None:
            partners = [
                'USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'IND', 'VNM',
                'THA', 'SGP', 'MYS', 'IDN', 'AUS', 'CAN', 'MEX'
            ]

        # 더미 데이터 (현실적인 범위)
        np.random.seed(hash(hs_code) % 2**32)
        result = {}

        for partner in partners:
            # 국가별 특성 반영
            if partner in ['USA', 'CHN', 'JPN']:
                base_value = np.random.uniform(50000000, 200000000)
            elif partner in ['VNM', 'THA', 'SGP', 'MYS']:
                base_value = np.random.uniform(10000000, 80000000)
            else:
                base_value = np.random.uniform(5000000, 50000000)

            result[partner] = base_value

        return result


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("UN Comtrade API 테스트 (강화 버전)")
    print("=" * 60)

    # 더미 데이터 모드
    fetcher = ComtradeDataFetcher(use_real_data=False)

    print("\n[더미 데이터 모드]")
    export_values = fetcher.get_export_values(
        reporter="KOR",
        partners=['USA', 'CHN', 'JPN', 'VNM'],
        hs_code="33"
    )

    print("\n수출액 (USD):")
    for country, value in export_values.items():
        print(f"  {country}: ${value:,.0f}")
