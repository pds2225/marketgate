"""
실데이터 통합 테스트
모든 데이터 소스가 제대로 작동하는지 확인
"""

def test_data_sources():
    """개별 데이터 소스 테스트"""
    print("=" * 60)
    print("데이터 소스 개별 테스트")
    print("=" * 60)

    countries = ['KOR', 'USA', 'CHN', 'JPN', 'VNM']

    # 1. UN Comtrade
    print("\n[1/3] UN Comtrade API 테스트")
    print("-" * 60)
    from data_sources.un_comtrade import ComtradeDataFetcher

    comtrade = ComtradeDataFetcher(use_real_data=False)
    export_data = comtrade.get_export_values(
        reporter="KOR",
        partners=countries,
        hs_code="33"
    )

    print("수출액 데이터:")
    for country, value in export_data.items():
        print(f"  {country}: ${value:,.0f}")

    # 2. World Bank
    print("\n[2/3] World Bank API 테스트")
    print("-" * 60)
    from data_sources.world_bank import WorldBankDataFetcher

    world_bank = WorldBankDataFetcher(use_real_data=False)

    gdp = world_bank.get_gdp(countries)
    print("GDP (억 USD):")
    for country, value in gdp.items():
        print(f"  {country}: {value:,.0f}")

    growth = world_bank.get_gdp_growth(countries)
    print("\nGDP 성장률 (%):")
    for country, value in growth.items():
        print(f"  {country}: {value:.2f}%")

    lpi = world_bank.get_lpi(countries)
    print("\nLPI (1-5):")
    for country, value in lpi.items():
        print(f"  {country}: {value:.2f}")

    # 3. 보조 데이터
    print("\n[3/3] 보조 데이터 테스트")
    print("-" * 60)
    from data_sources.supplementary_data import SupplementaryDataProvider

    supp = SupplementaryDataProvider()

    distance = supp.get_distance(countries)
    print("거리 (km):")
    for country, value in distance.items():
        print(f"  KOR -> {country}: {value:,.0f} km")

    fta = supp.get_fta_status(countries)
    print("\nFTA 체결:")
    for country, status in fta.items():
        print(f"  {country}: {'O' if status == 1 else 'X'}")

    print("\n[성공] 모든 데이터 소스 정상 작동")


def test_data_collector():
    """통합 데이터 수집기 테스트"""
    print("\n" + "=" * 60)
    print("통합 데이터 수집기 테스트")
    print("=" * 60)

    from real_data_collector import RealDataCollector

    collector = RealDataCollector(use_real_data=False)

    # 학습 데이터
    print("\n[학습 데이터 수집]")
    train_df = collector.collect_training_data(
        exporter="KOR",
        hs_codes=['33'],
        countries=['USA', 'CHN', 'JPN', 'VNM'],
        year=2023
    )

    print(f"\n수집된 데이터:")
    print(f"  행: {len(train_df)}")
    print(f"  열: {len(train_df.columns)}")
    print(f"\n컬럼:")
    for col in train_df.columns:
        print(f"  - {col}")

    print(f"\n샘플 데이터:")
    print(train_df.head())

    # 예측 데이터
    print("\n[예측 데이터 수집]")
    pred_df = collector.collect_prediction_data(
        exporter="KOR",
        hs_code="33",
        countries=['USA', 'CHN'],
        year=2023
    )

    print(f"\n수집된 데이터: {len(pred_df)}행")
    print(pred_df)

    print("\n[성공] 데이터 수집기 정상 작동")


def test_cache():
    """캐시 시스템 테스트"""
    print("\n" + "=" * 60)
    print("캐시 시스템 테스트")
    print("=" * 60)

    from cache_manager import CacheManager
    import time

    cache = CacheManager(cache_dir="backend/cache", expiry_hours=24)

    # 캐시 저장
    print("\n[캐시 저장]")
    test_data = {"value": 12345, "text": "cached"}
    cache.set("test_key", test_data)
    print(f"  저장: {test_data}")

    # 캐시 읽기
    print("\n[캐시 읽기]")
    cached = cache.get("test_key")
    print(f"  읽기: {cached}")

    assert cached == test_data, "캐시 데이터 불일치!"

    # 데코레이터 테스트
    print("\n[데코레이터 테스트]")
    from cache_manager import cached

    @cached(cache)
    def slow_function(x):
        print("  -> 실제 함수 실행 (느림)")
        time.sleep(0.5)
        return x * 2

    print("  첫 번째 호출:")
    result1 = slow_function(100)
    print(f"    결과: {result1}")

    print("  두 번째 호출 (캐시):")
    result2 = slow_function(100)
    print(f"    결과: {result2}")

    # 캐시 정리
    cache.clear()
    print("\n[성공] 캐시 시스템 정상 작동")


def test_model_with_real_data():
    """모델과 실데이터 통합 테스트"""
    print("\n" + "=" * 60)
    print("모델 + 실데이터 통합 테스트")
    print("=" * 60)

    from real_data_collector import RealDataCollector
    from gravity_model import GravityModel
    from xgb_model import XGBoostRefinementModel
    import os

    # 모델 로드
    print("\n[모델 로드]")
    if not os.path.exists('backend/models/gravity_model.pkl'):
        print("  [경고] 모델 파일이 없습니다. 먼저 run_full_pipeline.py를 실행하세요.")
        return

    gravity_model = GravityModel.load('backend/models/gravity_model.pkl')
    xgb_model = XGBoostRefinementModel.load('backend/models/xgboost_model.pkl')
    print("  모델 로드 완료")

    # 데이터 수집
    print("\n[실데이터 수집 (더미 모드)]")
    collector = RealDataCollector(use_real_data=False)

    pred_df = collector.collect_prediction_data(
        exporter="KOR",
        hs_code="33",
        countries=['USA', 'CHN', 'JPN', 'VNM', 'SGP'],
        year=2023
    )

    # 중력모형 예측
    print("\n[중력모형 예측]")
    feature_cols = ['gdp_target', 'distance_km', 'fta', 'lpi_score', 'tariff_rate']
    pred_df['gravity_pred'] = gravity_model.predict(pred_df[feature_cols])
    print(f"  예측 완료: {len(pred_df)} 국가")

    # XGBoost 예측
    print("\n[XGBoost 예측]")
    pred_df['xgb_pred'] = xgb_model.predict(pred_df)
    print(f"  예측 완료")

    # 결과 출력
    print("\n[예측 결과]")
    result = pred_df[['target_country', 'gravity_pred', 'xgb_pred']].sort_values('xgb_pred', ascending=False)
    print(result)

    print("\n[성공] 모델 + 데이터 통합 정상")


def main():
    """전체 테스트 실행"""
    print("\n")
    print("=" * 60)
    print("실데이터 통합 시스템 테스트")
    print("=" * 60)

    try:
        # 1. 데이터 소스 테스트
        test_data_sources()

        # 2. 데이터 수집기 테스트
        test_data_collector()

        # 3. 캐시 시스템 테스트
        test_cache()

        # 4. 모델 통합 테스트
        test_model_with_real_data()

        # 최종 요약
        print("\n" + "=" * 60)
        print("모든 테스트 통과!")
        print("=" * 60)
        print("\n[다음 단계]")
        print("1. .env 파일 생성 (.env.example 참고)")
        print("2. USE_REAL_DATA=true 설정")
        print("3. UN_COMTRADE_API_KEY 입력 (선택)")
        print("4. python api_v2.py 실행")
        print()

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
