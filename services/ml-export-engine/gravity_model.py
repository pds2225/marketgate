"""
중력모형(Gravity Model) 구현
국제무역의 기본 패턴을 학습하는 베이스라인 모델
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import joblib
from typing import Tuple


class GravityModel:
    """
    중력모형 클래스

    수식:
    log(export_value) = β0 + β1*log(GDP_target) + β2*log(distance)
                        + β3*FTA + β4*LPI + ... + ε
    """

    def __init__(self):
        self.model = LinearRegression()
        self.feature_names = [
            'log_gdp_target',
            'log_distance_km',
            'fta',
            'lpi_score',
            'tariff_rate'
        ]
        self.is_fitted = False

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        중력모형용 특성 생성

        Args:
            df: 원본 데이터프레임

        Returns:
            pd.DataFrame: 변환된 특성
        """
        features = pd.DataFrame()

        # 로그 변환 (중력모형의 핵심)
        features['log_gdp_target'] = np.log(df['gdp_target'])
        features['log_distance_km'] = np.log(df['distance_km'])

        # 그대로 사용
        features['fta'] = df['fta']
        features['lpi_score'] = df['lpi_score']
        features['tariff_rate'] = df['tariff_rate']

        return features

    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'GravityModel':
        """
        중력모형 학습

        Args:
            X: 입력 특성 (gdp_target, distance_km, fta, lpi_score, tariff_rate 포함)
            y: 타겟 변수 (export_value_usd)

        Returns:
            self
        """
        # 특성 준비
        X_transformed = self._prepare_features(X)

        # 타겟 변수 로그 변환
        y_log = np.log(y + 1)  # +1은 0 방지

        # 모델 학습
        self.model.fit(X_transformed, y_log)
        self.is_fitted = True

        # 계수 출력
        print("\n[중력모형 계수]")
        for name, coef in zip(self.feature_names, self.model.coef_):
            print(f"  {name:20s}: {coef:8.4f}")
        print(f"  {'intercept':20s}: {self.model.intercept_:8.4f}")

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        중력모형 예측

        Args:
            X: 입력 특성

        Returns:
            np.ndarray: 예측값 (원래 스케일)
        """
        if not self.is_fitted:
            raise ValueError("모델이 학습되지 않았습니다. fit()을 먼저 호출하세요.")

        # 특성 준비
        X_transformed = self._prepare_features(X)

        # 로그 스케일 예측
        y_log_pred = self.model.predict(X_transformed)

        # 원래 스케일로 복원
        y_pred = np.exp(y_log_pred) - 1

        return y_pred

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """
        모델 평가

        Args:
            X: 입력 특성
            y: 실제 타겟

        Returns:
            dict: 평가 메트릭
        """
        y_pred = self.predict(X)

        r2 = r2_score(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))

        # 로그 스케일에서도 평가
        y_log = np.log(y + 1)
        y_log_pred = np.log(y_pred + 1)
        r2_log = r2_score(y_log, y_log_pred)
        rmse_log = np.sqrt(mean_squared_error(y_log, y_log_pred))

        metrics = {
            'r2': r2,
            'rmse': rmse,
            'r2_log': r2_log,
            'rmse_log': rmse_log
        }

        return metrics

    def save(self, filepath: str):
        """모델 저장"""
        joblib.dump(self, filepath)
        print(f"중력모형 저장: {filepath}")

    @staticmethod
    def load(filepath: str) -> 'GravityModel':
        """모델 로드"""
        return joblib.load(filepath)


def train_gravity_model(df: pd.DataFrame, test_size: float = 0.2) -> Tuple[GravityModel, pd.DataFrame, pd.DataFrame]:
    """
    중력모형 학습 파이프라인

    Args:
        df: 전체 데이터
        test_size: 테스트 셋 비율

    Returns:
        tuple: (학습된 모델, 학습 데이터, 테스트 데이터)
    """
    from sklearn.model_selection import train_test_split

    print("=" * 60)
    print("중력모형 학습 시작")
    print("=" * 60)

    # Train-Test 분리
    train_df, test_df = train_test_split(df, test_size=test_size, random_state=42)

    print(f"\n학습 데이터: {len(train_df)} 샘플")
    print(f"테스트 데이터: {len(test_df)} 샘플")

    # 특성과 타겟 분리
    feature_cols = ['gdp_target', 'distance_km', 'fta', 'lpi_score', 'tariff_rate']
    X_train = train_df[feature_cols]
    y_train = train_df['export_value_usd']
    X_test = test_df[feature_cols]
    y_test = test_df['export_value_usd']

    # 모델 학습
    model = GravityModel()
    model.fit(X_train, y_train)

    # 평가
    print("\n[학습 세트 성능]")
    train_metrics = model.evaluate(X_train, y_train)
    for key, value in train_metrics.items():
        print(f"  {key:15s}: {value:.4f}")

    print("\n[테스트 세트 성능]")
    test_metrics = model.evaluate(X_test, y_test)
    for key, value in test_metrics.items():
        print(f"  {key:15s}: {value:.4f}")

    # 예측값을 데이터프레임에 추가
    train_df = train_df.copy()
    test_df = test_df.copy()
    train_df['gravity_pred'] = model.predict(X_train)
    test_df['gravity_pred'] = model.predict(X_test)

    print("\n중력모형 학습 완료!")
    print("=" * 60)

    return model, train_df, test_df


if __name__ == '__main__':
    # 테스트
    from data_generator import generate_dummy_data

    print("중력모형 테스트...")

    # 더미 데이터 생성
    df = generate_dummy_data(5000)

    # 모델 학습
    gravity_model, train_df, test_df = train_gravity_model(df)

    # 모델 저장
    gravity_model.save('backend/models/gravity_model.pkl')

    # 예측 샘플 확인
    print("\n[예측 샘플 5개]")
    sample = test_df[['target_country', 'hs_code', 'export_value_usd', 'gravity_pred']].head()
    print(sample)
