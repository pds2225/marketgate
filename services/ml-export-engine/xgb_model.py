"""
XGBoost 보정 모델
중력모형의 예측을 기반으로 추가 특성을 활용하여 정확도를 높이는 모델
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score, mean_squared_error
import joblib
import shap
from typing import Tuple, Dict


class XGBoostRefinementModel:
    """
    XGBoost 기반 보정 모델

    중력모형의 예측값 + 추가 특성을 입력으로 받아
    실제 수출액을 더 정확하게 예측
    """

    def __init__(self, **xgb_params):
        """
        Args:
            **xgb_params: XGBoost 하이퍼파라미터
        """
        default_params = {
            'objective': 'reg:squarederror',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42
        }
        default_params.update(xgb_params)

        self.model = xgb.XGBRegressor(**default_params)
        self.feature_names = [
            'gravity_pred',          # 중력모형 예측값
            'gdp_growth',            # GDP 성장률
            'lpi_score',             # 물류성과지수
            'tariff_rate',           # 관세율
            'culture_index',         # 문화적 유사성
            'regulation_index'       # 규제 편의성
        ]
        self.is_fitted = False
        self.explainer = None

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        XGBoost용 특성 준비

        Args:
            df: gravity_pred 컬럼이 포함된 데이터프레임

        Returns:
            pd.DataFrame: XGBoost 입력 특성
        """
        if 'gravity_pred' not in df.columns:
            raise ValueError("gravity_pred 컬럼이 필요합니다.")

        features = df[self.feature_names].copy()
        return features

    def fit(self, df: pd.DataFrame, y: pd.Series,
            eval_set: Tuple[pd.DataFrame, pd.Series] = None) -> 'XGBoostRefinementModel':
        """
        XGBoost 모델 학습

        Args:
            df: gravity_pred 포함 학습 데이터
            y: 타겟 변수 (export_value_usd)
            eval_set: 검증 세트 (df, y)

        Returns:
            self
        """
        # 특성 준비
        X = self._prepare_features(df)

        # 로그 변환
        y_log = np.log(y + 1)

        # 검증 세트 준비
        if eval_set is not None:
            eval_df, eval_y = eval_set
            eval_X = self._prepare_features(eval_df)
            eval_y_log = np.log(eval_y + 1)
            eval_set_transformed = [(eval_X, eval_y_log)]
        else:
            eval_set_transformed = None

        # 모델 학습
        self.model.fit(
            X, y_log,
            eval_set=eval_set_transformed,
            verbose=False
        )
        self.is_fitted = True

        # SHAP Explainer 생성 (설명 가능성)
        self.explainer = shap.TreeExplainer(self.model)

        # 특성 중요도 출력
        print("\n[XGBoost 특성 중요도]")
        importance = self.model.feature_importances_
        for name, imp in sorted(zip(self.feature_names, importance),
                                key=lambda x: x[1], reverse=True):
            print(f"  {name:20s}: {imp:.4f}")

        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        XGBoost 예측

        Args:
            df: gravity_pred 포함 데이터

        Returns:
            np.ndarray: 예측값 (원래 스케일)
        """
        if not self.is_fitted:
            raise ValueError("모델이 학습되지 않았습니다. fit()을 먼저 호출하세요.")

        X = self._prepare_features(df)
        y_log_pred = self.model.predict(X)
        y_pred = np.exp(y_log_pred) - 1

        return y_pred

    def evaluate(self, df: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        모델 평가

        Args:
            df: 입력 데이터
            y: 실제 타겟

        Returns:
            dict: 평가 메트릭
        """
        y_pred = self.predict(df)

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

    def explain_prediction(self, df: pd.DataFrame, index: int = 0) -> Dict[str, float]:
        """
        SHAP을 이용한 예측 설명

        Args:
            df: 입력 데이터
            index: 설명할 샘플의 인덱스

        Returns:
            dict: 각 특성의 기여도
        """
        if self.explainer is None:
            raise ValueError("모델이 학습되지 않았습니다.")

        X = self._prepare_features(df)
        shap_values = self.explainer.shap_values(X.iloc[index:index+1])

        # 특성별 기여도
        explanation = {}
        for name, value in zip(self.feature_names, shap_values[0]):
            explanation[name] = float(value)

        return explanation

    def save(self, filepath: str):
        """모델 저장"""
        joblib.dump(self, filepath)
        print(f"XGBoost 모델 저장: {filepath}")

    @staticmethod
    def load(filepath: str) -> 'XGBoostRefinementModel':
        """모델 로드"""
        return joblib.load(filepath)


def train_xgboost_model(train_df: pd.DataFrame,
                        test_df: pd.DataFrame) -> XGBoostRefinementModel:
    """
    XGBoost 모델 학습 파이프라인

    Args:
        train_df: gravity_pred 포함 학습 데이터
        test_df: gravity_pred 포함 테스트 데이터

    Returns:
        XGBoostRefinementModel: 학습된 모델
    """
    print("=" * 60)
    print("XGBoost 보정 모델 학습 시작")
    print("=" * 60)

    # 타겟 변수
    y_train = train_df['export_value_usd']
    y_test = test_df['export_value_usd']

    # 모델 생성 및 학습
    model = XGBoostRefinementModel()
    model.fit(train_df, y_train, eval_set=(test_df, y_test))

    # 평가
    print("\n[학습 세트 성능]")
    train_metrics = model.evaluate(train_df, y_train)
    for key, value in train_metrics.items():
        print(f"  {key:15s}: {value:.4f}")

    print("\n[테스트 세트 성능]")
    test_metrics = model.evaluate(test_df, y_test)
    for key, value in test_metrics.items():
        print(f"  {key:15s}: {value:.4f}")

    print("\nXGBoost 모델 학습 완료!")
    print("=" * 60)

    return model


def compare_models(train_df: pd.DataFrame, test_df: pd.DataFrame):
    """
    중력모형 vs XGBoost 성능 비교

    Args:
        train_df: gravity_pred 포함 학습 데이터
        test_df: gravity_pred 포함 테스트 데이터
    """
    print("\n" + "=" * 60)
    print("모델 성능 비교")
    print("=" * 60)

    y_test = test_df['export_value_usd']

    # 중력모형 성능
    gravity_pred = test_df['gravity_pred']
    gravity_r2 = r2_score(y_test, gravity_pred)
    gravity_rmse = np.sqrt(mean_squared_error(y_test, gravity_pred))

    print("\n[중력모형 (Baseline)]")
    print(f"  R²   : {gravity_r2:.4f}")
    print(f"  RMSE : {gravity_rmse:.2f}")

    # XGBoost 성능 (이미 학습된 모델 필요)
    # 여기서는 참고용으로만 표시
    print("\n[XGBoost (위 결과 참조)]")


if __name__ == '__main__':
    # 테스트
    from data_generator import generate_dummy_data
    from gravity_model import train_gravity_model

    print("XGBoost 모델 테스트...")

    # 1. 더미 데이터 생성
    df = generate_dummy_data(5000)

    # 2. 중력모형 학습 (gravity_pred 생성 위해)
    gravity_model, train_df, test_df = train_gravity_model(df)

    # 3. XGBoost 모델 학습
    xgb_model = train_xgboost_model(train_df, test_df)

    # 4. 모델 저장
    import os
    os.makedirs('backend/models', exist_ok=True)
    xgb_model.save('backend/models/xgboost_model.pkl')

    # 5. 성능 비교
    compare_models(train_df, test_df)

    # 6. 예측 설명 샘플
    print("\n[예측 설명 샘플]")
    explanation = xgb_model.explain_prediction(test_df, index=0)
    sample_row = test_df.iloc[0]
    print(f"국가: {sample_row['target_country']}, HS코드: {sample_row['hs_code']}")
    print("특성 기여도:")
    for feature, contribution in sorted(explanation.items(),
                                       key=lambda x: abs(x[1]), reverse=True):
        print(f"  {feature:20s}: {contribution:+.4f}")
