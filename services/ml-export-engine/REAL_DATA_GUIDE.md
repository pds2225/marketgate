# 실데이터 연동 가이드

VALUE-UP AI 백엔드 엔진의 실데이터 연동 방법을 설명합니다.

## 📊 지원하는 데이터 소스

### 1. UN Comtrade API
**실제 국제 무역 데이터**

- 제공 데이터: 국가별, HS 코드별 수출입액
- API 문서: https://comtradeplus.un.org/
- 필요사항: API 키 (무료 티어 사용 가능)

### 2. World Bank API
**경제 지표 데이터**

- 제공 데이터:
  - GDP (현재 가격 USD)
  - GDP 성장률 (연간 %)
  - LPI (물류성과지수)
- API 문서: https://datahelpdesk.worldbank.org/
- 필요사항: 없음 (무료 오픈 API)

### 3. 보조 데이터
**기타 필수 데이터**

- 거리: Haversine 공식 기반 계산
- FTA: 한국 기준 FTA 체결 국가 리스트
- 관세율: 더미 데이터 (실제 연동 준비됨)
- 문화 유사성: 지역 기반 더미 데이터
- 규제 지수: 더미 데이터

## 🚀 빠른 시작

### 1. 환경 설정

```bash
cd backend

# .env 파일 생성
cp .env.example .env
```

### 2. .env 파일 편집

```bash
# 더미 데이터 모드 (기본)
USE_REAL_DATA=false

# 또는 실데이터 모드
USE_REAL_DATA=true
UN_COMTRADE_API_KEY=your_api_key_here

# 캐시 설정
ENABLE_CACHE=true
CACHE_EXPIRY_HOURS=24
```

### 3. API 서버 실행

```bash
# v2 API (실데이터 지원)
python api_v2.py
```

## 📖 사용 방법

### Python 코드에서 직접 사용

#### 더미 데이터 모드
```python
from real_data_collector import RealDataCollector

# 더미 데이터로 수집
collector = RealDataCollector(use_real_data=False)

df = collector.collect_training_data(
    exporter="KOR",
    hs_codes=['33', '84'],
    year=2023
)

print(df.head())
```

#### 실데이터 모드
```python
import os
from real_data_collector import RealDataCollector

# API 키 로드
comtrade_key = os.getenv('UN_COMTRADE_API_KEY')

# 실데이터로 수집
collector = RealDataCollector(
    use_real_data=True,
    comtrade_api_key=comtrade_key
)

df = collector.collect_training_data(
    exporter="KOR",
    hs_codes=['33'],
    year=2023
)
```

### API 호출

```bash
# 설정 확인
curl http://localhost:8000/config

# 예측 (더미 데이터)
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"hs_code": "33", "use_real_data": false}'

# 예측 (실데이터)
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"hs_code": "33", "use_real_data": true}'
```

## 🔧 개별 데이터 소스 사용

### UN Comtrade

```python
from data_sources.un_comtrade import ComtradeDataFetcher

fetcher = ComtradeDataFetcher(
    api_key="your_key",
    use_real_data=True
)

# 특정 국가별 수출액
export_values = fetcher.get_export_values(
    reporter="KOR",
    partners=['USA', 'CHN', 'JPN'],
    hs_code="33",
    year=2023
)

for country, value in export_values.items():
    print(f"{country}: ${value:,.0f}")
```

### World Bank

```python
from data_sources.world_bank import WorldBankDataFetcher

fetcher = WorldBankDataFetcher(use_real_data=True)

# GDP 조회
gdp = fetcher.get_gdp(['KOR', 'USA', 'CHN'], 2023)
print(gdp)

# GDP 성장률
growth = fetcher.get_gdp_growth(['KOR', 'USA'], 2023)
print(growth)

# LPI
lpi = fetcher.get_lpi(['KOR', 'SGP'], 2023)
print(lpi)
```

### 보조 데이터

```python
from data_sources.supplementary_data import SupplementaryDataProvider

provider = SupplementaryDataProvider()

# 거리
distance = provider.get_distance(['USA', 'CHN', 'JPN'])
print(distance)

# FTA 체결 여부
fta = provider.get_fta_status(['USA', 'VNM'])
print(fta)

# 관세율
tariff = provider.get_tariff_rates(['USA', 'CHN'], hs_code="33")
print(tariff)
```

## 💾 캐싱

데이터 수집 결과는 자동으로 캐싱됩니다.

```python
from cache_manager import CacheManager, cached

# 캐시 매니저 생성
cache = CacheManager(
    cache_dir="backend/cache",
    expiry_hours=24
)

# 수동 캐싱
cache.set("my_key", {"data": [1, 2, 3]})
result = cache.get("my_key")

# 데코레이터 사용
@cached(cache)
def expensive_api_call(country):
    # API 호출...
    return data

# 자동으로 캐싱됨
result = expensive_api_call("USA")
```

캐시 관리:

```python
# 만료된 캐시 정리
cache.clear_expired()

# 모든 캐시 삭제
cache.clear()
```

## 🧪 테스트

```bash
# 전체 통합 테스트
python test_real_data_integration.py

# 개별 모듈 테스트
python data_sources/un_comtrade.py
python data_sources/world_bank.py
python data_sources/supplementary_data.py
python real_data_collector.py
python cache_manager.py
```

## 📁 파일 구조

```
backend/
├── data_sources/              # 데이터 소스 모듈
│   ├── __init__.py
│   ├── un_comtrade.py        # UN Comtrade API
│   ├── world_bank.py         # World Bank API
│   └── supplementary_data.py # 보조 데이터
│
├── real_data_collector.py    # 통합 데이터 수집기
├── cache_manager.py          # 캐시 관리
├── api_v2.py                 # 실데이터 지원 API
│
├── .env.example              # 환경 변수 예시
├── .env                      # 실제 환경 변수 (생성 필요)
│
└── cache/                    # 캐시 저장 디렉토리
```

## 🔑 API 키 발급

### UN Comtrade API 키 발급 (선택)

1. https://comtradeplus.un.org/ 접속
2. 회원 가입
3. API Keys 메뉴에서 키 생성
4. `.env` 파일에 추가:
   ```
   UN_COMTRADE_API_KEY=your_api_key_here
   ```

**참고:**
- API 키 없이도 사용 가능 (제한적)
- API 키가 있으면 호출 제한이 완화됨

### World Bank API

별도의 API 키가 필요 없습니다.

## ⚠️ 주의사항

### API 호출 제한

**UN Comtrade:**
- 무료 (키 없음): 분당 1회
- 무료 (키 있음): 분당 10회
- 유료: 제한 없음

**World Bank:**
- 제한 없음 (합리적 사용)

### Rate Limiting

코드에 자동 Rate Limiting이 구현되어 있습니다:

```python
# UN Comtrade
rate_limit_delay = 1.0 if api_key else 6.0  # 초

# World Bank
rate_limit_delay = 0.5  # 초
```

### 캐시 활용

- 동일한 요청은 캐시에서 즉시 반환
- 기본 캐시 유효 기간: 24시간
- API 비용 절감 및 성능 향상

## 🔄 실데이터 vs 더미 데이터 비교

| 특성 | 더미 데이터 | 실데이터 |
|------|------------|---------|
| 속도 | 빠름 (즉시) | 느림 (API 호출) |
| 정확도 | 낮음 (랜덤) | 높음 (실제 데이터) |
| 비용 | 무료 | API 제한 (무료/유료) |
| 사용 목적 | 개발, 테스트 | 프로덕션 |
| 설정 | 불필요 | API 키 필요 |

## 🎯 권장 사용 시나리오

### 개발/테스트 단계
```python
collector = RealDataCollector(use_real_data=False)
```

- 빠른 개발
- 무제한 테스트
- API 비용 없음

### 프로덕션 배포
```python
collector = RealDataCollector(
    use_real_data=True,
    comtrade_api_key=api_key
)
```

- 실제 데이터 기반 예측
- 높은 정확도
- 캐싱으로 성능 최적화

## 🚧 향후 확장

### 추가 예정 데이터 소스

1. **WTO Tariff Database**
   - 실제 관세율 데이터
   - 현재: 더미 데이터

2. **Hofstede Insights**
   - 문화적 거리 측정
   - 현재: 지역 기반 추정

3. **World Bank Doing Business**
   - 규제 편의성 지수
   - 현재: 더미 데이터

4. **UNCTAD**
   - 추가 무역 통계

### 확장 방법

`data_sources/` 디렉토리에 새 모듈 추가:

```python
# data_sources/new_source.py
class NewDataSource:
    def get_data(self, countries):
        # API 호출 구현
        pass
```

`real_data_collector.py`에 통합:

```python
self.new_source = NewDataSource()
new_data = self.new_source.get_data(countries)
```

---

**작성일:** 2026-01-11
**버전:** 2.0
**다음 업데이트:** 실제 API 키 확보 후 프로덕션 테스트
