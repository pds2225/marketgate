"""
API 테스트 스크립트
서버가 실행 중일 때 사용
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"


def test_health_check():
    """헬스 체크 테스트"""
    print("=" * 60)
    print("헬스 체크 테스트")
    print("=" * 60)

    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_prediction():
    """예측 API 테스트"""
    print("=" * 60)
    print("수출 유망국 추천 테스트")
    print("=" * 60)

    # 요청 데이터
    request_data = {
        "hs_code": "33",
        "exporter_country": "KOR",
        "top_n": 5
    }

    print(f"요청 데이터: {json.dumps(request_data, indent=2)}")
    print()

    # API 호출
    response = requests.post(
        f"{API_BASE_URL}/predict",
        json=request_data
    )

    print(f"Status Code: {response.status_code}")
    print()

    if response.status_code == 200:
        result = response.json()
        print("추천 결과:")
        print()

        for i, country in enumerate(result['top_countries'], 1):
            print(f"{i}. {country['country']}")
            print(f"   점수: {country['score']:.4f}")
            print(f"   예상 수출액: ${country['expected_export_usd']:,.0f}")
            print(f"   주요 요인:")

            # 설명 정렬 (절댓값 기준)
            explanation = country['explanation']
            sorted_factors = sorted(
                explanation.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )

            for factor, value in sorted_factors[:3]:  # 상위 3개만
                sign = "+" if value > 0 else ""
                print(f"     - {factor}: {sign}{value:.4f}")
            print()
    else:
        print(f"오류: {response.text}")


def test_different_hs_codes():
    """다양한 HS 코드 테스트"""
    print("=" * 60)
    print("다양한 HS 코드 테스트")
    print("=" * 60)

    hs_codes = ["33", "84", "85", "87"]  # 화장품, 기계, 전자, 자동차

    for hs_code in hs_codes:
        print(f"\n[HS 코드: {hs_code}]")

        response = requests.post(
            f"{API_BASE_URL}/predict",
            json={
                "hs_code": hs_code,
                "exporter_country": "KOR",
                "top_n": 3
            }
        )

        if response.status_code == 200:
            result = response.json()
            top_3 = [c['country'] for c in result['top_countries'][:3]]
            print(f"Top 3: {', '.join(top_3)}")
        else:
            print(f"오류: {response.status_code}")


if __name__ == "__main__":
    try:
        print("\nVALUE-UP AI API 테스트 시작\n")
        print(f"API URL: {API_BASE_URL}")
        print()

        # 1. 헬스 체크
        test_health_check()

        # 2. 기본 예측 테스트
        test_prediction()

        # 3. 다양한 HS 코드 테스트
        test_different_hs_codes()

        print("\n" + "=" * 60)
        print("모든 테스트 완료!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n오류: API 서버에 연결할 수 없습니다.")
        print("먼저 'python api.py'로 서버를 실행하세요.")
    except Exception as e:
        print(f"\n예상치 못한 오류: {e}")
