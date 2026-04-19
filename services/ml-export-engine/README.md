# VALUE-UP AI 수출 유망국 추천 백엔드 엔진 (MVP)

중력모형 + XGBoost 하이브리드 구조의 수출 유망국 추천 시스템

## 📁 프로젝트 구조

```
backend/
├── api.py                 # FastAPI 서버 (메인 실행 파일)
├── gravity_model.py       # 중력모형 구현
├── xgb_model.py          # XGBoost 보정 모델
├── data_generator.py     # 더미 데이터 생성
├── requirements.txt      # Python 의존성
├── models/               # 학습된 모델 저장 (자동 생성)
│   ├── gravity_model.pkl
│   └── xgboost_model.pkl
└── README.md            # 이 파일
```

## 🚀 빠른 시작

### 1. Python 환경 설정 (Python 3.9 이상 권장)

```bash
# 가상환경 생성 (선택사항)
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 2. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

### 3. API 서버 실행

```bash
python api.py
```

또는

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

서버가 시작되면 자동으로:
- 더미 데이터 생성 (5000 샘플)
- 중력모형 학습
- XGBoost 모델 학습
- 모델 저장

최초 실행시 약 10-30초 소요됩니다.

### 4. API 테스트

브라우저에서 접속:
- API 문서: http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/health

또는 curl 사용:

```bash
# 헬스 체크
curl http://localhost:8000/health

# 수출 유망국 추천
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"hs_code": "33", "exporter_country": "KOR", "top_n": 10}'
```

## 📊 API 엔드포인트

### POST /predict
수출 유망국 추천

**요청 예시:**
```json
{
  "hs_code": "33",
  "exporter_country": "KOR",
  "top_n": 10
}
```

**응답 예시:**
```json
{
  "top_countries": [
    {
      "country": "VNM",
      "score": 0.87,
      "expected_export_usd": 12500000,
      "explanation": {
        "gravity_baseline": 0.42,
        "growth_potential": 0.21,
        "culture_fit": 0.18,
        "regulation_ease": 0.08,
        "logistics": 0.05,
        "tariff_impact": -0.11
      }
    }
  ]
}
```

### GET /health
서버 상태 확인

### POST /retrain
모델 재학습 (관리자용)

## 🧪 개별 모듈 테스트

각 모듈은 독립적으로 실행 가능합니다:

### 더미 데이터 생성 테스트
```bash
python data_generator.py
```

### 중력모형 단독 테스트
```bash
python gravity_model.py
```

### XGBoost 모델 단독 테스트
```bash
python xgb_model.py
```

## 🏗️ 모델 아키텍처

### 1단계: 중력모형 (Gravity Model)
국제무역의 기본 패턴을 학습하는 베이스라인 모델

**수식:**
```
log(export_value) = β₀ + β₁·log(GDP_target) - β₂·log(distance)
                    + β₃·FTA + β₄·LPI + β₅·tariff + ε
```

**특성:**
- log_gdp_target: 목표 국가 GDP (로그)
- log_distance_km: 거리 (로그)
- fta: FTA 체결 여부 (0/1)
- lpi_score: 물류성과지수
- tariff_rate: 관세율

### 2단계: XGBoost 보정 모델
중력모형의 예측을 기반으로 추가 특성을 활용하여 정확도를 높임

**입력 특성:**
- gravity_pred: 중력모형 예측값
- gdp_growth: GDP 성장률
- lpi_score: 물류성과지수
- tariff_rate: 관세율
- culture_index: 문화적 유사성
- regulation_index: 규제 편의성

**출력:**
- 최종 수출액 예측 (USD)

## 📈 평가 지표

모델 성능은 다음 지표로 평가됩니다:
- **R² (결정계수)**: 모델 설명력
- **RMSE (평균 제곱근 오차)**: 예측 오차

학습 로그에서 확인 가능합니다.

## 🔄 실데이터 전환 가이드

현재는 더미 데이터를 사용하지만, UN Comtrade 실데이터로 전환 가능한 구조입니다.

### 데이터 교체 방법:

1. **data_generator.py 수정**
   - `generate_dummy_data()` 함수를 UN Comtrade API 호출로 대체
   - 동일한 컬럼명 유지:
     ```python
     ['exporter_country', 'target_country', 'hs_code',
      'gdp_target', 'gdp_growth', 'distance_km',
      'lpi_score', 'fta', 'tariff_rate',
      'culture_index', 'regulation_index', 'export_value_usd']
     ```

2. **외부 데이터 소스 통합**
   - UN Comtrade API: 실제 무역 데이터
   - World Bank API: GDP, 성장률
   - WTO API: 관세율
   - World Bank LPI: 물류성과지수

3. **API 수정 없음**
   - 데이터만 교체하면 API는 그대로 작동합니다.

## 🛠️ 트러블슈팅

### 모델 파일이 없다는 에러
```bash
# 모델 재학습 실행
python -c "from api import train_models; train_models()"
```

### 포트 충돌
```bash
# 다른 포트 사용
uvicorn api:app --port 8001
```

### 의존성 설치 오류
```bash
# pip 업그레이드 후 재시도
pip install --upgrade pip
pip install -r requirements.txt
```

## 📝 다음 단계

MVP 이후 개선 사항:
1. ✅ UN Comtrade 실데이터 연동
2. ✅ 데이터베이스 연동 (PostgreSQL 등)
3. ✅ 모델 재학습 스케줄러
4. ✅ 캐싱 시스템 (Redis)
5. ✅ 인증/권한 시스템
6. ✅ 모니터링 및 로깅
7. ✅ Docker 컨테이너화

## 📞 문의

프로젝트 관련 문의사항이 있으시면 이슈를 등록해주세요.

---

**VALUE-UP AI** | 수출 유망국 추천 시스템 MVP v1.0
