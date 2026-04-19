# 글로벌 수출 인텔리전스 플랫폼

이 프로젝트는 정부 지원 사업 평가용으로 설계된 **글로벌 수출 인텔리전스 플랫폼**의 최소 기능(MVP) 구현입니다. 해당 코드베이스는 FastAPI 기반의 백엔드 서버를 제공하며, 다음과 같은 핵심 기능을 포함합니다.

## 제공 기능

* **국가 추천 API** (`/recommend`) – 기업의 품목(HS 코드)과 현재 수출 국가, 목표(신시장 발굴/확대)를 입력받아 KOTRA 수출유망추천정보를 활용한 추천 국가 목록을 반환합니다. 현재 구현은 예제 데이터를 사용한 규칙 기반 추천을 수행하며, 실제 KOTRA API 호출을 위한 구조만 제공됩니다.
* **성과 시뮬레이션 API** (`/simulate`) – 특정 국가와 품목에 대해 시장 규모, 성장률, 기업의 가격대 및 MOQ 등을 입력받아 예상 매출 범위와 성공 확률을 단순 회귀식 기반으로 계산합니다. 데이터가 없는 경우에도 동작하도록 설계되었습니다.
* **바이어‑셀러 매칭 API** (`/match`) – 셀러 또는 바이어의 프로필을 입력하면 간단한 적합도(FitScore) 계산을 통해 잠재 거래 파트너 목록을 반환합니다. 현재는 메모리 내에 정의된 예제 프로필로 매칭을 수행합니다.

## 구조

```
export_intelligence/
├── README.md                    프로젝트 소개
├── requirements.txt             필요한 파이썬 패키지 목록
└── backend/
    ├── main.py                 FastAPI 엔트리포인트
    ├── routers/
    │   ├── __init__.py
    │   ├── recommendation.py   추천 API 라우터
    │   ├── simulation.py       시뮬레이션 API 라우터
    │   └── matching.py         매칭 API 라우터
    ├── services/
    │   ├── __init__.py
    │   ├── recommendation_service.py
    │   ├── simulation_service.py
    │   └── matching_service.py
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py          Pydantic 데이터 모델 정의
    └── database/
        ├── __init__.py
        └── database.py         (예제용) 간단한 데이터 저장소
```

## 실행 방법

1. 저장소 루트에서 가상 환경을 생성하고 필요한 패키지를 설치합니다.

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2. 서버를 실행합니다.

    ```bash
    uvicorn backend.main:app --reload
    ```

3. 브라우저에서 `http://localhost:8000/docs`로 접속하면 Swagger UI를 통해 각 API를 테스트할 수 있습니다.

## 참고사항

* 현재 구현은 **예제 데이터**와 **단순 규칙**을 기반으로 동작합니다. 실제 데이터 연동(KOTRA API, 기업 DB 등)을 위해서는 `services/` 디렉터리의 함수들을 수정해야 합니다.
* 예측 모델링은 복잡한 AI 모델 대신 간단한 선형 식을 사용하여 예측 범위를 제공합니다. 데이터가 확보되면 `simulation_service.py`의 로직을 교체하여 발전시킬 수 있습니다.
* 매칭 엔진은 적합도 계산을 위한 가중치와 기준을 `matching_service.py`에서 정의합니다. 필요에 따라 점수 산정 방식을 커스터마이즈할 수 있습니다.
