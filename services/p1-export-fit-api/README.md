# Export Fit Score API (P1)

수출 대상 국가 추천 시스템 — HS 코드(6자리)와 수출국 정보를 입력받아 적합한 수출 대상 국가를 점수화하여 출력하는 FastAPI 기반 서비스.

---

## 프로젝트 구조

```
export-fit-score-api/
├── app/
│   ├── config.py           # 파일 경로, 가중치 등 설정값
│   ├── models.py           # Pydantic 입출력 스키마
│   ├── utils.py            # 공통 유틸리티
│   └── services/
│       ├── data_loaders.py # CSV 데이터 로드 및 조회
│       └── scoring.py      # 점수 계산 로직
├── csv/                    # 데이터 파일 (README 참조)
├── main.py                 # FastAPI 엔트리포인트
├── streamlit_app.py        # 데모용 Streamlit UI (임시)
└── requirements.txt
```

---

## 실행 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. CSV 데이터 준비
`csv/README.md` 참조 — 별도 준비 필요한 파일 2종 확인 후 `csv/` 폴더에 배치

### 3. API 서버 실행
```bash
uvicorn main:app --reload
```

### 4. (선택) Streamlit 데모 실행
```bash
streamlit run streamlit_app.py
```

---

## API 명세

### `GET /v1/health`
서버 상태 확인

### `POST /v1/predict`
수출 추천국 반환

**요청 예시:**
```json
{
  "hs_code": "330499",
  "exporter_country_iso3": "KOR",
  "top_n": 10,
  "year": 2023,
  "filters": {
    "exclude_countries_iso3": ["PRK", "IRN"],
    "min_trade_value_usd": 0
  }
}
```

**응답 구조:**
```json
{
  "request_id": "uuid",
  "status": "ok",
  "timestamp": "2025-xx-xxTxx:xx:xx+09:00",
  "data": {
    "input": { ... },
    "results": [
      {
        "rank": 1,
        "partner_country_iso3": "USA",
        "fit_score": 78.5,
        "score_components": {
          "trade_volume_score": 0.92,
          "growth_score": 0.65,
          "gdp_score": 0.88,
          "distance_score": 0.41,
          "soft_adjustment": 0.0
        },
        "explanation": { ... }
      }
    ]
  }
}
```

---

## 점수 계산 로직

| 요소 | 가중치 |
|------|--------|
| trade_volume_score | 0.40 |
| growth_score | 0.25 |
| gdp_score | 0.20 |
| distance_score | 0.15 |

- 정규화: Min-Max (max==min이면 0.5 반환)
- 거리: 역수 적용 (가까울수록 고점)
- Soft Penalty: 무역량 하위 30% → -5, 거리 상위 70% → -5, GDP 성장률 음수 → -3
- 최종 점수: `clamp(base_score × 100 + soft_adjustment, 0, 100)`

---

## Hard Filter

| 조건 | 코드 |
|------|------|
| 사용자 제외 국가 | USER_EXCLUDED |
| 무역 데이터 없음 | NO_TRADE_DATA |
| 최소 무역액 미달 | MIN_TRADE_VALUE |
| 거리 데이터 없음 | NO_DISTANCE_DATA |

---

## Python 버전
Python 3.12

## 미완성/TODO 사항 (개발자 인수인계 메모)
- `trade_data.csv` 인코딩 깨짐 이슈 → JSON 포맷 변환 테스트 필요 (`data_loaders.py` 주석 참조)
- 제재국(restricted) 패널티 데이터 미수령 → `scoring.py` TODO 주석 확인
- 추후 HS Code 입력 → 텍스트 매핑 데이터 수령 후 연결 필요
- DB화 예정 (현재 CSV 파일 직접 로드 방식)
