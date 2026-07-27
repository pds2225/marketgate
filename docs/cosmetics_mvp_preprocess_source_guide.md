# MarketGate `cosmetics_mvp_preprocess` 원본 소스코드 설명서

> 작성 기준: `services/cosmetics_mvp_preprocess` 내 핵심 파일 3개  
> (`preprocess_cosmetics.py`, `shortlist_service.py`, `task05_shortlist.py`)

---

## 1. 개요

`cosmetics_mvp_preprocess`는 **화장품 수출 타겟 바이어·수요 신호를 수집·정제·정규화·필터링**하는 전처리 파이프라인이다.

- **입력**: 여러 정부·공공기관 원본 CSV(인콰이어리, 구매오퍼, SNS 바이어 등)
- **출력**: `output/buyer_candidate.csv`, `output/opportunity_item.csv`
- **후속 사용**: `shortlist_service.py`가 출력 CSV를 읽어 공급자 프로필과 매칭 → 적합도 점수 → 추천 생성

이 설명서는 전처리 파이프라인의 핵심 3개 파일을 중심으로 구조, 데이터 흐름, 주요 함수, 정규화/게이트 정책을 정리한다.

---

## 2. 디렉터리 구조 (핵심 파일 위주)

```text
services/cosmetics_mvp_preprocess/
├── preprocess_cosmetics.py      # 메인 수집·정규화 파이프라인
├── shortlist_service.py         # 매칭·숏리스트·추천 서비스
├── task05_shortlist.py          # 바이어/기회 정규화 & 하드 게이트
├── task06_fit_score.py          # 적합도 점수 (shortlist_service import)
├── task08_recommendation.py     # 추천 문구 생성 (shortlist_service import)
├── validate_cosmetics_outputs.py
├── diagnose_shortlist.py
├── scripts/
│   ├── auto_filter_cosmetics.py
│   ├── enrich_emails.py
│   ├── fetch_buykorea_inquiry.py
│   ├── fetch_govdata_api.py
│   └── nice_dnb_poc.py
├── tests/
│   ├── test_preprocess_cosmetics.py
│   ├── test_task05_shortlist.py
│   ├── test_task06_fit_score.py
│   ├── test_task07_shortlist_api.py
│   ├── test_task08_recommendation.py
│   ├── test_task09_validate_top20.py
│   └── test_task10_run_checks.py
├── input/                       # 원본 CSV (런타임 입력)
├── sample_input/                # 개발용 샘플
├── output/                      # 산출물
│   ├── buyer_candidate.csv
│   └── opportunity_item.csv
└── docs/
    ├── DATA_COLLECTION_GUIDE.md
    └── ...
```

---

## 3. 데이터 흐름

```text
[원본 CSV (input/)]
       ↓
preprocess_cosmetics.py  ──→  buyer_candidate.csv
       │                        opportunity_item.csv
       │
       ↓
task05_shortlist.py      ──→  opportunity_item.csv 정제
       │
       ↓
shortlist_service.py     ──→  공급자 프로필 기반 매칭
       │
       ├── task05_shortlist.match_hs_or_keywords()
       ├── task06_fit_score.score_buyers()
       └── task08_recommendation.build_recommendation_lines()
       ↓
[추천 결과]
```

---

## 4. 핵심 파일 상세

### 4.1 `preprocess_cosmetics.py` (1,337줄)

**역할**: 다양한 소스의 원본 CSV를 통일된 스키마로 읽고 정규화·중복 제거·노이즈 필터링 후 `buyer_candidate.csv` / `opportunity_item.csv`를 생성한다.

#### 주요 상수/별칭 테이블

| 상수/테이블 | 용도 |
|---|---|
| `COMMON_OUTPUT_COLUMNS` | 통일 출력 컬럼 18개 (`record_type`, `source_dataset`, `source_file`, `source_row_no`, `title`, `normalized_name`, `country_raw`, `country_norm`, `country_iso3`, `hs_code_raw`, `hs_code_norm`, `keywords_raw`, `keywords_norm`, `has_contact`, `contact_*`, `valid_until`) |
| `TITLE_ALIASES` | 제목 컬럼 한글/영문 별칭 |
| `COMPANY_ALIASES` | 기업명 컬럼 별칭 |
| `COUNTRY_ALIASES` | 국가 컬럼 별칭 |
| `HS_ALIASES` | HS 코드 컬럼 별칭 |
| `KEYWORD_ALIASES` | 키워드/품목 컬럼 별칭 |
| `CONTACT_*_ALIASES` | 담당자·이메일·전화·웹사이트 컬럼 별칭 |
| `VALID_UNTIL_ALIASES` | 유효기간/마감일 컬럼 별칭 |
| `MANUAL_COUNTRY_ALIASES` | 영문 국가명 → 한국명 매핑 |
| `ENCODING_FALLBACKS` | `utf-8-sig`, `utf-8`, `cp949`, `euc-kr` |
| `DELIMITER_CANDIDATES` | `,`, `;`, `\t`, `\|` |

#### 주요 클래스

| 클래스 | 설명 |
|---|---|
| `CountryLookup` | 국가명/ISO3 조회 테이블. 외부 country code 파일을 읽어 구축 |
| `SourceSpec` | 소스별 CSV 처리 규칙(파일 패턴, record_type, 필드 그룹, 기본값 등) |
| `LoadResult` | 로드 결과 메타데이터(원본 행 수, 정제 후 행 수, 노이즈 제거 수 등) |

#### 주요 함수

| 함수 | 시그니처 | 설명 |
|---|---|---|
| `transform_source_dataframe` | `(df, spec, source_file, country_lookup)` | SourceSpec에 따라 컬럼 매핑, 정규화, HS/국가/키워드 추출, `has_contact` 계산 |
| `process_pipeline` | `(input_dir, output_dir, country_code_file, allow_sample_fallback)` | 전체 파이프라인 실행: 파일 탐색 → 로드 → 변환 → 중복 제거 → 저장 |
| `_read_csv_with_fallback` | `(path)` | 인코딩/구분자를 후보로 시도하며 CSV 읽기 |
| `_discover_source_file` | `(spec, input_dir, allow_sample_fallback, sample_dir)` | 소스별 파일 탐색, 개발 시 `sample_input` 폼백 허용 |
| `_filter_noise_rows` | `(df)` | test/sample/dummy 등 노이즈 행 필터링 |
| `_deduplicate_target` | `(df, target)` | target(`buyer_candidate`/`opportunity_item`)별 중복 제거 |
| `main` | `(argv)` | CLI 진입점 |

#### CLI 예시

```bash
python preprocess_cosmetics.py \
  --input-dir ./input \
  --output-dir ./output \
  --country-code-file ./country_codes.csv
```

---

### 4.2 `task05_shortlist.py` (1,089줄)

**역할**: 바이어/기회 레코드의 **정규화**, **HS/키워드 매칭**, **하드 게이트**를 담당. `preprocess_cosmetics.py`와 `shortlist_service.py` 양쪽에서 재사용된다.

#### 주요 Enum/상수

| 상수 | 설명 |
|---|---|
| `GateReason` | `COUNTRY_MISMATCH`, `HS_MISMATCH`, `BANNED_COUNTRY`, `CAPACITY_FAIL`, `SIGNAL_TYPE_INVALID`, `EXPIRED`, `AMBIGUOUS_PRODUCT` |
| `ALLOWED_SIGNAL_TYPES` | `{"inquiry", "offer", "consultation"}` |
| `DATE_WINDOW_DAYS` | 183일(6개월) |
| `DEFAULT_BANNED_COUNTRY_KEYS` | 한국(`KOR`, `대한민국` 등) — 국내 바이어 필터링 |
| `GENERIC_TITLE_TOKENS` | test, sample, product, 문의 등 범용/더미 제목 필터 |
| `KEYWORD_MATCH_STOPWORDS` | skin, care, beauty, 제품, 문의 등 의미 없는 일반 토큰 |
| `STRONG_COSMETICS_KEYWORDS` | skincare, serum, ampoule, 세럼, 앰플, 마스크팩 등 |
| `WEAK_COSMETICS_KEYWORDS` | beauty, cosmetic, cream, 화장품, 메이크업 등 |
| `BLOCKED_NON_COSMETICS_KEYWORDS` | equipment, medical, pharma, food 등 화장품 외 품목 차단 |

#### 정규화 함수

| 함수 | 설명 |
|---|---|
| `normalize_text(value)` | NFKC, 소문자, 공백 정리 |
| `normalize_country(value)` | 국가명 정규화 |
| `normalize_hs_code(value)` | 숫자 이외 제거, 6~10자리 정리 |
| `infer_hs_code_from_texts(*values)` / `infer_hs_code_with_score(*values)` | 텍스트에서 HS 코드 추론 및 신뢰도 반환 |
| `normalize_keywords(value)` | 키워드 분리·정규화·중복 제거 |
| `parse_date(value)` | 다양한 날짜 문자열 파싱 |
| `normalize_signal_type(value)` / `derive_signal_type(record)` | 신호 유형 정규화 및 유도 |

#### 매칭 및 게이트 함수

| 함수 | 설명 |
|---|---|
| `match_hs_or_keywords(buyer, opportunity)` | HS 코드 정확/접두 매칭 또는 키워드 오버랩 판정 |
| `buyer_hard_gate(...)` | 국가/HS/금지국/생산능력 기준으로 바이어 통과/거부 판정 |
| `opportunity_hard_gate(opportunity, reference_date)` | 신호 유형/만료/모호 제목 기준으로 기회 필터 |
| `is_signal_usable(...)` | 허용 신호 유형 + 유효기간 + 모호성 종합 판단 |
| `normalize_opportunity_record(...)` | 기회 레코드 전체 정규화 및 게이트 분류 추가 |
| `transform_opportunity_csv(...)` | 입력 CSV → 정규화된 opportunity CSV 변환 |

#### CLI 예시

```bash
python task05_shortlist.py \
  --input ./output/opportunity_item.csv \
  --output ./output/opportunity_item_cleaned.csv \
  --reference-date 2026-07-26
```

---

### 4.3 `shortlist_service.py` (402줄)

**역할**: 전처리 산출물을 바탕으로 **공급자(supplier) 프로필**을 받아 최적의 기회를 선택하고, 바이어 숏리스트를 작성한 뒤 추천 문구를 생성한다.

#### 의존성

```python
from task05_shortlist import (...)   # 정규화·매칭·게이트
from task06_fit_score import score_buyers
from task08_recommendation import build_recommendation_lines
```

#### 주요 함수

| 함수 | 시그니처 | 설명 |
|---|---|---|
| `load_buyer_frame(output_dir)` | `→ pd.DataFrame` | `output/buyer_candidate.csv` 로드 (LRU 캐싱) |
| `load_opportunity_frame(output_dir)` | `→ pd.DataFrame` | `output/opportunity_item.csv` 로드 (LRU 캐싱) |
| `clear_shortlist_cache()` | | 프레임 캐시 초기화 |
| `build_supplier_profile(...)` | `*` 키워드 인자 | 공급자명, 타겟 국가/HS/키워드/생산능력/금지국 등 입력 → 프로필 딕셔너리 |
| `_build_target_match_record(profile)` | `→ dict` | 타겟 HS/키워드/제목 매칭용 레코드 구성 |
| `_opportunity_fit_score(opportunity, supplier_profile)` | `→ int` | 기회별 적합도 점수 계산(HS exact 70, inferred 50, prefix 40/30/20, 키워드 25/30+) |
| `_select_opportunity(opportunities, ...)` | `→ dict | None` | 필터(제목/국가) + 적합도 + 신호 사용 가능 + 유효기간 기준으로 최적 기회 선택 |
| `shortlist_buyers(...)` | `*` 키워드 인자 | 바이어 하드 게이트 → 적합도 점수 → limit 개수로 숏리스트 작성 |
| `validate_shortlist_quality(result)` | | 숏리스트 품질 검증(soft penalty 분포 등) |

#### 사용 예시

```python
from shortlist_service import build_supplier_profile, shortlist_buyers

profile = build_supplier_profile(
    supplier_name="ABC 화장품",
    target_country_norm="미국",
    target_hs_code_norm="330499",
    target_keywords_norm="serum | ampoule | mask pack",
    required_capacity=10000,
)

result = shortlist_buyers(
    output_dir=Path("./output"),
    supplier_profile=profile,
    reference_date=date.today(),
    limit=20,
)
```

---

## 5. 공통 데이터 모델

### 5.1 출력 CSV 공통 컬럼 (`COMMON_OUTPUT_COLUMNS`)

| 컬럼 | 의미 |
|---|---|
| `record_type` | `buyer_candidate` 또는 `opportunity_item` |
| `source_dataset` | 데이터셋 식별자 |
| `source_file` | 원본 파일명 |
| `source_row_no` | 원본 행 번호 |
| `title` | 제목/문의 제목 |
| `normalized_name` | 정규화된 기업명 |
| `country_raw` / `country_norm` / `country_iso3` | 국가 원본/정규/ISO3 |
| `hs_code_raw` / `hs_code_norm` | HS 코드 원본/정규 |
| `keywords_raw` / `keywords_norm` | 키워드 원본/정규 |
| `has_contact` | 연락처 존재 여부(0/1) |
| `contact_name/email/phone/website` | 연락처 정보 |
| `valid_until` | 유효기간/마감일 |

### 5.2 정규화 규칙

1. **텍스트**: Unicode NFKC → 소문자 → 특수문자/공백 정리
2. **기업명**: 숫자·한글·영문 외 문자 제거, 반복 공백 제거
3. **HS 코드**: 숫자만 남기고 6자리 이상 보정, 2/4/6자리 prefix 매칭
4. **키워드**: 구분자(`|`, `,`, `/`) 기준 분리 → stopword 제거 → 중복 제거
5. **국가**: `MANUAL_COUNTRY_ALIASES` 및 외부 country code 파일 기반 매핑
6. **날짜**: `parse_date()`에서 여러 포맷 파싱 시도

---

## 6. 하드 게이트 정책

### 6.1 바이어 하드 게이트 (`buyer_hard_gate`)

| 거부 사유 | 조건 |
|---|---|
| `COUNTRY_MISMATCH` | 타겟 국가와 바이어 국가 불일치 |
| `HS_MISMATCH` | 타겟 HS/키워드와 바이어 HS/키워드 불일치 |
| `BANNED_COUNTRY` | 금지국(기본 한국)에 해당 |
| `CAPACITY_FAIL` | 생산능력 요건 미달 |

### 6.2 기회 하드 게이트 (`opportunity_hard_gate`)

| 거부 사유 | 조건 |
|---|---|
| `SIGNAL_TYPE_INVALID` | `inquiry/offer/consultation` 외 신호 유형 |
| `EXPIRED` | `valid_until` 또는 `created_at`이 6개월 이전 |
| `AMBIGUOUS_PRODUCT` | 제목/품목이 너무 모호하거나 제네릭 토큰만 존재 |

### 6.3 HS/키워드 매칭 우선순위 (`match_hs_or_keywords`)

| 매칭 모드 | 점수 |
|---|---|
| `hs_exact` | 70 |
| `hs_inferred` | 50 |
| `hs_prefix_4` | 40 |
| `hs_inferred_prefix_4` | 30 |
| `hs_prefix_2` | 20 |
| `keyword` | 25 + 중첩 본너스 |

---

## 7. 테스트

```bash
cd services/cosmetics_mvp_preprocess
python3 -m pytest tests/ -v
```

- `test_preprocess_cosmetics.py`: 전처리 파이프라인 검증
- `test_task05_shortlist.py`: 정규화·게이트·매칭 검증
- `test_task06_fit_score.py` ~ `test_task10_run_checks.py`: 적합도·API·추천·검증 검증

> 현재 98/101 통과, 3개는 `python` 명령어 부재로 인한 서브프로세스 호출 실패가 사전에 기록되어 있다.

---

## 8. 연계 및 확장

- `shortlist_service.py`는 `task05_shortlist`(정규화/매칭), `task06_fit_score`(적합도), `task08_recommendation`(추천 문구)를 조합하여 사용한다.
- `task07_shortlist_api.py`, `task09_validate_top20.py`, `task10_run_checks.py`는 API 노출·검증·통합 체크 역할을 수행한다.
- `scripts/` 하위 모듈은 공공데이터·BuyKorea·K-SURE·SBC 등 외부 데이터를 수집한다.

---

## 9. 주의사항

1. **인코딩**: 원본 CSV가 `cp949`/`euc-kr`인 경우가 많으므로 `ENCODING_FALLBACKS` 순서로 시도한다.
2. **샘플 폼백**: `allow_sample_fallback=True`는 개발/테스트용이며, 운영 환경에서는 사용하지 않는다.
3. **금지국**: 기본적으로 한국(`KOR`)을 금지국으로 설정하여 국내 바이어가 추천되지 않도록 한다.
4. **연락처**: `has_contact`는 전처리 단계에서 이메일/전화/웹사이트 존재 여부로 계산된다.
5. **신호 유효성**: 6개월 이상 경과하거나 모호한 제목의 신호는 `opportunity_hard_gate`에서 제외된다.

---

## 10. 참고 파일

- `services/cosmetics_mvp_preprocess/preprocess_cosmetics.py`
- `services/cosmetics_mvp_preprocess/shortlist_service.py`
- `services/cosmetics_mvp_preprocess/task05_shortlist.py`
- `docs/ARCHITECTURE.md` (상위 시스템 설계)
- `docs/PRODUCT.md` (상품/가격 설계)
