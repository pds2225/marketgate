"""
전체 파이프라인 테스트 스크립트
의존성 체크부터 모델 학습, 예측까지 전체 흐름 확인
"""

import sys
import os


def check_dependencies():
    """의존성 패키지 확인"""
    print("=" * 60)
    print("의존성 체크")
    print("=" * 60)

    required_packages = [
        'pandas', 'numpy', 'sklearn', 'xgboost', 'shap',
        'fastapi', 'uvicorn', 'joblib'
    ]

    missing = []
    for package in required_packages:
        try:
            if package == 'sklearn':
                __import__('sklearn')
            else:
                __import__(package)
            print(f"[OK] {package}")
        except ImportError:
            print(f"[FAIL] {package} (설치 필요)")
            missing.append(package)

    if missing:
        print(f"\n[!] 누락된 패키지: {', '.join(missing)}")
        print("pip install -r requirements.txt 실행이 필요합니다.")
        return False

    print("\n모든 의존성이 설치되어 있습니다!")
    return True


def test_data_generation():
    """데이터 생성 테스트"""
    print("\n" + "=" * 60)
    print("1단계: 데이터 생성 테스트")
    print("=" * 60)

    from data_generator import generate_dummy_data, generate_prediction_data

    # 학습 데이터 생성
    train_data = generate_dummy_data(1000)  # 테스트용으로 1000개만
    print(f"학습 데이터 생성: {train_data.shape}")
    print(f"컬럼: {list(train_data.columns)}")
    print(f"\n샘플 데이터:")
    print(train_data.head(3))

    # 예측 데이터 생성
    pred_data = generate_prediction_data('33')
    print(f"\n예측 데이터 생성: {pred_data.shape}")

    return train_data


def test_gravity_model(df):
    """중력모형 테스트"""
    print("\n" + "=" * 60)
    print("2단계: 중력모형 학습 테스트")
    print("=" * 60)

    from gravity_model import train_gravity_model

    gravity_model, train_df, test_df = train_gravity_model(df, test_size=0.2)

    print(f"\n중력모형 예측 샘플:")
    print(test_df[['target_country', 'export_value_usd', 'gravity_pred']].head())

    return gravity_model, train_df, test_df


def test_xgboost_model(train_df, test_df):
    """XGBoost 모델 테스트"""
    print("\n" + "=" * 60)
    print("3단계: XGBoost 모델 학습 테스트")
    print("=" * 60)

    from xgb_model import train_xgboost_model

    xgb_model = train_xgboost_model(train_df, test_df)

    # 최종 예측
    final_pred = xgb_model.predict(test_df)
    print(f"\nXGBoost 최종 예측 샘플:")

    import pandas as pd
    result = pd.DataFrame({
        'country': test_df['target_country'].values,
        'actual': test_df['export_value_usd'].values,
        'gravity_pred': test_df['gravity_pred'].values,
        'xgb_pred': final_pred
    })
    print(result.head(10))

    return xgb_model


def test_prediction_pipeline(gravity_model, xgb_model):
    """전체 예측 파이프라인 테스트"""
    print("\n" + "=" * 60)
    print("4단계: 예측 파이프라인 테스트")
    print("=" * 60)

    from data_generator import generate_prediction_data
    import pandas as pd

    # 새로운 데이터로 예측
    hs_code = '33'
    pred_df = generate_prediction_data(hs_code)

    # 중력모형 예측
    feature_cols = ['gdp_target', 'distance_km', 'fta', 'lpi_score', 'tariff_rate']
    pred_df['gravity_pred'] = gravity_model.predict(pred_df[feature_cols])

    # XGBoost 최종 예측
    pred_df['final_pred'] = xgb_model.predict(pred_df)

    # 점수 정규화
    min_pred = pred_df['final_pred'].min()
    max_pred = pred_df['final_pred'].max()
    pred_df['score'] = (pred_df['final_pred'] - min_pred) / (max_pred - min_pred)

    # 상위 10개 국가
    top_10 = pred_df.nlargest(10, 'score')

    print(f"\n수출 유망국 Top 10 (HS 코드: {hs_code}):")
    print("-" * 60)
    for i, (idx, row) in enumerate(top_10.iterrows(), 1):
        print(f"{i:2d}. {row['target_country']:5s} | "
              f"점수: {row['score']:.4f} | "
              f"예상 수출액: ${row['final_pred']:,.0f}")

    return top_10


def save_models(gravity_model, xgb_model):
    """모델 저장"""
    print("\n" + "=" * 60)
    print("5단계: 모델 저장")
    print("=" * 60)

    os.makedirs('backend/models', exist_ok=True)

    gravity_model.save('backend/models/gravity_model.pkl')
    xgb_model.save('backend/models/xgboost_model.pkl')

    print("모델 저장 완료!")


def main():
    """메인 실행 함수"""
    print("\n")
    print("=" * 60)
    print("VALUE-UP AI 백엔드 엔진 테스트".center(60))
    print("=" * 60)
    print()

    try:
        # 의존성 체크
        if not check_dependencies():
            print("\n⚠ 의존성 설치 후 다시 실행해주세요.")
            print("명령어: pip install -r requirements.txt")
            return

        # 1. 데이터 생성
        df = test_data_generation()

        # 2. 중력모형 학습
        gravity_model, train_df, test_df = test_gravity_model(df)

        # 3. XGBoost 학습
        xgb_model = test_xgboost_model(train_df, test_df)

        # 4. 예측 파이프라인
        top_countries = test_prediction_pipeline(gravity_model, xgb_model)

        # 5. 모델 저장
        save_models(gravity_model, xgb_model)

        # 최종 요약
        print("\n" + "=" * 60)
        print("전체 파이프라인 테스트 완료!")
        print("=" * 60)
        print("\n다음 단계:")
        print("1. API 서버 실행: python api.py")
        print("2. API 테스트: python test_api.py")
        print("3. API 문서 확인: http://localhost:8000/docs")
        print()

    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == '__main__':
    main()
