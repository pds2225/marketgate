# MarketGate Development Tasks & PRD

> **기준 버전**: GitHub `pds2225/marketgate` (main branch)  
> **작성일**: 2026-04-25  
> **작성자**: AI Assistant  
> **형식**: 각 TASK 별 PRD (Product Requirements Document) 포함

---

## 개요 (Overview)

현재 MarketGate 프로젝트는 폴터 구조 정리는 완료되었으나, **데이터 품질 문제**로 인해 핵심 기능인 P1 수출 유망국 추천 API가 `0건` 결과를 반환하는 상태입니다.  
본 문서는 현재 개발 현황을 기준으로 10개의 TASK를 정의하고, 각 TASK별 상세 PRD를 제공합니다.

---

## 현재 개발 현황 요약

| 구성요소 | 상태 | 핵심 이슈 |
|---------|------|----------|
| `apps/frontend-react` | 🟡 구조 정리 완료 | P1 API와 미연동 |
| `services/p1-export-fit-api` | 🟡 실행 가능 | `trade_data.csv` 부족 → 추천 0건 |
| `services/ml-export-engine` | 🟢 MVP 동작 | 더미 데이터 기반, 실데이터 전환 필요 |
| `ops/monitoring` | 🟢 설정 파일 존재 | 미연동 |

### Blocker 리스트
1. `trade_data.csv`에 국가별 거래 상대국 정보 부족
2. CSV 인코딩 깨짐 이슈
3. 제재국 패널티 데이터 미수령
4. HS Code ↔ 품목명 매핑 데이터 미수령
5. CSV 직접 로드 방식 (DB 미도입)

---

## TASK 우선순위 로드맵

```
Phase 1 (P0 - 데이터 품질):  TASK 1 → TASK 2
Phase 2 (P1 - 기능 완성):   TASK 3 → TASK 4 → TASK 5 → TASK 6
Phase 3 (P2 - 인프라 고도화): TASK 7 → TASK 8 → TASK 9
Phase 4 (P3 - 보안/확장):   TASK 10
```

---

# TASK 1: trade_data.csv 실데이터 교체

## 1.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-001 |
| **제목** | trade_data.csv 실데이터 교체 및 품질 보강 |
| **우선순위** | 🔴 P0 (Critical) |
| **담당 영역** | `services/p1-export-fit-api/csv/` |
| **예상 소요** | 2~3일 |

현재 `p1-export-fit-api`는 실행되지만, `trade_data.csv`에 국가별 거래 상대국(partner country) 정보가 부족하여 **모든 추천 결과가 0건**으로 반환됩니다. 본 TASK는 실제 무역 데이터를 수집·가공하여 해당 CSV를 교체하고, API가 의미 있는 추천 결과를 반환하도록 합니다.

## 1.2 배경 및 목적 (Background & Purpose)

- **문제 상황**: `trade_data.csv`의 컬럼/행 구조가 추천 알고리즘이 기대하는 파트너 국별 무역량 데이터를 포함하지 않음
- **영향 범위**: `POST /v1/predict` 호출 시 `results` 배열이 항상 빈 값
- **성공 기준**: KOR → USA, KOR → VNM 등 실제 무역 관계가 있는 국가 쌍에 대해 0이 아닌 점수 반환

## 1.3 요구사항 (Requirements)

### 기능적 요구사항 (Functional)

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-1.1 | CSV는 `reporter_country`, `partner_country`, `hs_code`, `trade_value_usd`, `year` 컬럼을 포함해야 함 | 필수 |
| FR-1.2 | 최소 2020~2024년 데이터를 포함해야 함 | 필수 |
| FR-1.3 | HS Code는 6자리 기준으로 통일해야 함 | 필수 |
| FR-1.4 | 국가 코드는 ISO 3166-1 alpha-3 (예: KOR, USA, CHN) 사용 | 필수 |
| FR-1.5 | `data_loaders.py`가 새 CSV 구조를 정상 로드해야 함 | 필수 |
| FR-1.6 | NULL/결측치는 0 또는 적절한 대체값으로 처리 | 필수 |

### 비기능적 요구사항 (Non-Functional)

| ID | 요구사항 |
|----|---------|
| NFR-1.1 | 파일 크기는 100MB 이하로 유지 (Git LFS 고려) |
| NFR-1.2 | 로드 시간은 5초 이내 |
| NFR-1.3 | 데이터 출처는 문서화되어야 함 |

## 1.4 데이터 소스 제안 (Data Sources)

| 소스 | URL/방법 | 데이터 내용 |
|------|---------|------------|
| UN Comtrade API | `https://comtrade.un.org/api/` | 국가별 HS Code별 수출입 데이터 |
| KITA (한국무역협회) | `https://www.kita.net/` | 한국 수출입 통계 |
| World Bank WITS | `https://wits.worldbank.org/` | 세계 통합 무역 데이터 |

## 1.5 수락 기준 (Acceptance Criteria)

- [ ] `POST /v1/predict` 호출 시 `results` 배열에 1개 이상의 추천 국가 반환
- [ ] `fit_score`가 0이 아닌 값으로 계산됨
- [ ] `score_components.trade_volume_score`가 0보다 큼
- [ ] `csv/README.md`에 데이터 출처, 기준 연도, 컬럼 설명 기재
- [ ] `data_loaders.py`에서 새 CSV를 오류 없이 로드

## 1.6 기술 스택 및 의존성

- Python 3.12
- pandas (CSV 처리)
- requests (API 수집 시)

## 1.7 리스크 및 완화 방안

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| UN Comtrade API Rate Limit | 데이터 수집 지연 | 캐싱, 배치 처리, 오프라인 샘플 준비 |
| 데이터 라이선스 제약 | 법적 이슈 | 오픈 데이터만 사용, 출처 명시 |
| 파일 크기 증가 | Git 저장소 부담 | Git LFS 사용 또는 외부 다운로드 스크립트 |

## 1.8 산출물 (Deliverables)

- `services/p1-export-fit-api/csv/trade_data.csv` (교체)
- `services/p1-export-fit-api/csv/trade_data_sample.csv` (테스트용 샘플)
- `services/p1-export-fit-api/csv/README.md` (데이터 사양 문서)
- 데이터 수집 스크립트 (선택): `scripts/fetch_trade_data.py`

---

# TASK 2: CSV → JSON 포맷 변환 및 인코딩 수정

## 2.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-002 |
| **제목** | CSV → JSON 포맷 변환 및 인코딩 이슈 해결 |
| **우선순위** | 🔴 P0 (Critical) |
| **담당 영역** | `services/p1-export-fit-api/app/services/data_loaders.py` |
| **예상 소요** | 1~2일 |

현재 `data_loaders.py`에서 `trade_data.csv` 로드 시 인코딩 깨짐 이슈가 발생합니다. 개발자 인수인계 메모에 따른 JSON 포맷 변환을 검증하고, 인코딩 문제를 해결합니다.

## 2.2 배경 및 목적

- **문제 상황**: CSV 파일의 문자 인코딩(UTF-8 vs CP949) 불일치로 한글/특수문자 깨짐
- **영향 범위**: 데이터 로드 실패 또는 오염된 데이터로 인한 잘못된 점수 계산
- **성공 기준**: 모든 데이터 파일이 UTF-8로 통일되고, JSON 포맷 지원 추가

## 2.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-2.1 | `data_loaders.py`가 UTF-8 인코딩 CSV를 정상 로드 | 필수 |
| FR-2.2 | JSON 포맷 데이터 로드 기능 추가 | 필수 |
| FR-2.3 | CSV/JSON 자동 감지 로직 구현 | 필수 |
| FR-2.4 | 인코딩 감지 및 변환 유틸리티 추가 | 필수 |
| FR-2.5 | 기존 CSV와의 하위호환성 유지 | 필수 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-2.1 | JSON 로드 시 CSV 대비 성능 저하 20% 이내 |
| NFR-2.2 | 인코딩 오류 발생 시 명확한 예외 메시지 출력 |

## 2.4 수락 기준

- [ ] 한글 국가명이 포함된 CSV를 오류 없이 로드
- [ ] JSON 파일(`trade_data.json`)을 동일 인터페이스로 로드 가능
- [ ] 잘못된 인코딩 파일 입력 시 `UnicodeDecodeError` 대신 사용자 친화적 메시지 반환
- [ ] 단위 테스트: UTF-8, CP949, ASCII 인코딩 파일 각각 로드 테스트 통과
- [ ] 기존 API 엔드포인트 동작에 영향 없음

## 2.5 기술 스택

- Python 3.12
- pandas (encoding 파라미터 활용)
- chardet (인코딩 자동 감지, 선택)

## 2.6 산출물

- `services/p1-export-fit-api/app/services/data_loaders.py` (수정)
- `services/p1-export-fit-api/app/utils/encoding_utils.py` (신규)
- `services/p1-export-fit-api/csv/trade_data.json` (TASK-001 데이터 기반 변환)
- 단위 테스트 파일

---

# TASK 3: 제재국(Restricted) 패널티 데이터 수집 및 로직 구현

## 3.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-003 |
| **제목** | 제재국 패널티 데이터 수집 및 점수 계산 로직 구현 |
| **우선순위** | 🟡 P1 (High) |
| **담당 영역** | `services/p1-export-fit-api/app/services/scoring.py` |
| **예상 소요** | 1~2일 |

`scoring.py`에 TODO 주석으로 남아있는 제재국(restricted countries) 패널티 로직을 구현합니다. UN, 미국, EU 등의 제재국 리스트를 데이터화하고, 추천 점수에 패널티를 적용합니다.

## 3.2 배경 및 목적

- **문제 상황**: 제재국에 대한 수출 추천 시 법적/정책적 리스크가 있으나, 현재 시스템은 이를 고려하지 않음
- **영향 범위**: 추천 결과의 신뢰성 및 법적 안전성
- **성공 기준**: 제재국이 추천 목록 하위로 배치되거나 필터링됨

## 3.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-3.1 | 제재국 리스트 데이터 파일 생성 | 필수 |
| FR-3.2 | 제재국에 대해 `soft_adjustment`에 -20점 패널티 적용 | 필수 |
| FR-3.3 | 제재국은 Hard Filter로 완전 제외 옵션 제공 | 필수 |
| FR-3.4 | 제재 유형(무역금지/제한/감시)별 차등 패널티 | 선택 |
| FR-3.5 | API 요청 시 `filters.include_restricted` 파라미터로 옵션 제어 | 선택 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-3.1 | 제재국 리스트는 외부 파일로 관리 (코드 재배포 없이 업데이트) |
| NFR-3.2 | 제재국 리스트 업데이트 주기: 월 1회 |

## 3.4 데이터 소스 제안

| 소스 | 내용 |
|------|------|
| UN Security Council Sanctions | `https://www.un.org/securitycouncil/content/un-sc-consolidated-list` |
| US OFAC SDN List | `https://sanctionssearch.ofac.treas.gov/` |
| EU Consolidated Financial Sanctions | `https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions` |

## 3.5 수락 기준

- [ ] PRK(북한), IRN(이란) 등 제재국이 추천 시 점수에 패널티 적용
- [ ] `filters.exclude_countries_iso3`와 별개로 제재국 필터링 가능
- [ ] `score_components.soft_adjustment`에 제재국 패널티 값이 포함됨
- [ ] 제재국 리스트 JSON 파일이 외부에서 수정 가능
- [ ] `POST /v1/predict` 응답에 `explanation.restricted_penalty` 필드 추가

## 3.6 산출물

- `services/p1-export-fit-api/csv/restricted_countries.json`
- `services/p1-export-fit-api/app/services/scoring.py` (수정)
- `services/p1-export-fit-api/app/models.py` (응답 스키마 확장)

---

# TASK 4: HS Code ↔ 품목명 매핑 데이터 연결

## 4.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-004 |
| **제목** | HS Code ↔ 품목명 매핑 데이터 연결 |
| **우선순위** | 🟡 P1 (High) |
| **담당 영역** | `services/p1-export-fit-api/` (API 입력 확장) |
| **예상 소요** | 1~2일 |

현재 API는 HS 코드(6자리 숫자)만 입력받습니다. 사용자가 "화장품"과 같은 품목명을 입력하면 해당 HS 코드로 매핑하여 처리하도록 합니다.

## 4.2 배경 및 목적

- **문제 상황**: 비개발자/일반 사용자는 HS 코드를 모름
- **영향 범위**: API 사용성 및 frontend 사용자 경험
- **성공 기준**: 품목명 입력 시 정확한 HS 코드로 매핑되어 추천 수행

## 4.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-4.1 | HS Code → 품목명(한글/영문) 매핑 테이블 생성 | 필수 |
| FR-4.2 | 품목명 → HS Code 역매핑 기능 | 필수 |
| FR-4.3 | API 요청에 `hs_code` 대신 `product_name` 입력 지원 | 필수 |
| FR-4.4 | 부분 일치 검색 (fuzzy matching) 지원 | 선택 |
| FR-4.5 | 매핑 결과가 여러 개일 때 후보 리스트 반환 | 선택 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-4.1 | 매핑 테이블은 메모리에 캐싱 (응답 지연 50ms 이내) |
| NFR-4.2 | HS Code Rev. 2022 기준 |

## 4.4 수락 기준

- [ ] "330499" 입력 시 "Beauty or make-up preparations" 반환
- [ ] "화장품" 입력 시 "330499" 등 관련 HS 코드 반환
- [ ] `POST /v1/predict`에 `product_name` 파라미터 추가
- [ ] `hs_code`와 `product_name` 중 하나는 필수, 둘 다 제공 시 `hs_code` 우선
- [ ] 존재하지 않는 품목명 입력 시 400 에러 + 후보 리스트 반환

## 4.5 산출물

- `services/p1-export-fit-api/csv/hs_code_mapping.json`
- `services/p1-export-fit-api/app/services/hs_mapper.py` (신규)
- `services/p1-export-fit-api/app/models.py` (입력 스키마 확장)
- `services/p1-export-fit-api/main.py` (라우터 수정)

---

# TASK 5: PostgreSQL DB 도입 (CSV → DB 마이그레이션)

## 5.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-005 |
| **제목** | PostgreSQL DB 도입 및 CSV → DB 마이그레이션 |
| **우선순위** | 🟡 P1 (High) |
| **담당 영역** | `services/p1-export-fit-api/` (전체 아키텍처) |
| **예상 소요** | 3~5일 |

현재 CSV 파일을 직접 로드하는 방식은 확장성과 성능에 한계가 있습니다. PostgreSQL을 도입하여 데이터를 DB화하고, SQLAlchemy ORM으로 조회합니다.

## 5.2 배경 및 목적

- **문제 상황**: CSV 직접 로드 → 메모리 사용량 증가, 동시 요청 처리 한계
- **영향 범위**: 서버 확장성, 데이터 업데이트 주기
- **성공 기준**: API가 DB에서 데이터를 조회하고, CSV 의존성 제거

## 5.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-5.1 | PostgreSQL 15+ 스키마 설계 | 필수 |
| FR-5.2 | SQLAlchemy 2.0 ORM 모델 정의 | 필수 |
| FR-5.3 | CSV → DB 마이그레이션 스크립트 | 필수 |
| FR-5.4 | Alembic 마이그레이션 관리 | 필수 |
| FR-5.5 | DB 연결 풀 설정 | 필수 |
| FR-5.6 | `data_loaders.py`가 DB 조회 모드 지원 | 필수 |
| FR-5.7 | CSV 폴백(fallback) 모드 유지 | 선택 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-5.1 | DB 쿼리 응답 시간 100ms 이내 (인덱스 포함) |
| NFR-5.2 | 동시 접속 100개 처리 가능 |
| NFR-5.3 | DB 커넥션 풀: 최소 5, 최대 20 |

## 5.4 DB 스키마 제안

```sql
-- trade_data 테이블
CREATE TABLE trade_data (
    id SERIAL PRIMARY KEY,
    reporter_country_iso3 CHAR(3) NOT NULL,
    partner_country_iso3 CHAR(3) NOT NULL,
    hs_code VARCHAR(6) NOT NULL,
    trade_value_usd BIGINT,
    year INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trade_reporter ON trade_data(reporter_country_iso3);
CREATE INDEX idx_trade_partner ON trade_data(partner_country_iso3);
CREATE INDEX idx_trade_hs ON trade_data(hs_code);
CREATE INDEX idx_trade_year ON trade_data(year);
```

## 5.5 수락 기준

- [ ] `docker-compose up db`로 PostgreSQL 컨테이너 실행 가능
- [ ] `python scripts/migrate_csv_to_db.py` 실행 시 CSV 데이터가 DB에 적재
- [ ] API가 CSV 없이 DB에서 데이터 조회하여 정상 동작
- [ ] Alembic으로 스키마 버전 관리 가능
- [ ] 기존 API 응답 형식 변경 없음

## 5.6 산출물

- `services/p1-export-fit-api/app/db/` (DB 설정, 모델, 세션)
- `services/p1-export-fit-api/alembic/` (마이그레이션)
- `services/p1-export-fit-api/scripts/migrate_csv_to_db.py`
- `docker-compose.yml` (DB 서비스 추가)

---

# TASK 6: frontend-react ↔ p1-export-fit-api 연동

## 6.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-006 |
| **제목** | React Frontend ↔ P1 API 연동 |
| **우선순위** | 🟡 P1 (High) |
| **담당 영역** | `apps/frontend-react/` ↔ `services/p1-export-fit-api/` |
| **예상 소요** | 2~3일 |

현재 React 화면은 P1 API와 연결되지 않은 상태입니다. API 클라이언트를 구축하고, 실제 추천 결과를 화면에 표시합니다.

## 6.2 배경 및 목적

- **문제 상황**: frontend가 정적 데이터 또는 목업 데이터를 사용 중
- **영향 범위**: 사용자가 실제 추천 결과를 볼 수 없음
- **성공 기준**: 화면에서 HS 코드/국가 입력 → API 호출 → 결과 표시

## 6.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-6.1 | API Base URL 환경변수로 관리 | 필수 |
| FR-6.2 | `POST /v1/predict` 호출 클라이언트 구현 | 필수 |
| FR-6.3 | 로딩 상태 및 에러 핸들링 UI | 필수 |
| FR-6.4 | 추천 결과를 테이블/차트로 시각화 | 필수 |
| FR-6.5 | CORS 설정 (API 측) | 필수 |
| FR-6.6 | `GET /v1/health` 연동 → 서버 상태 표시 | 선택 |
| FR-6.7 | 결과 다운로드 (CSV/Excel) | 선택 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-6.1 | API 타임아웃: 10초 |
| NFR-6.2 | 에러 발생 시 사용자 친화적 메시지 |
| NFR-6.3 | 모바일 반응형 대응 |

## 6.4 수락 기준

- [ ] React 화면에서 HS 코드와 수출국 입력 후 "분석" 버튼 클릭 시 API 호출
- [ ] API 응답 결과가 화면에 rank, country, fit_score로 표시
- [ ] API 서버 다운 시 "서버 연결 불가" 메시지 표시
- [ ] CORS 에러 없이 cross-origin 요청 성공
- [ ] `npm run dev`와 `uvicorn main:app` 동시 실행 시 정상 동작

## 6.5 산출물

- `apps/frontend-react/src/api/client.ts` (신규)
- `apps/frontend-react/src/api/predict.ts` (신규)
- `apps/frontend-react/src/components/RecommendationResult.tsx` (신규/수정)
- `apps/frontend-react/.env` (환경변수)
- `services/p1-export-fit-api/main.py` (CORS 설정 추가)

---

# TASK 7: ml-export-engine 실데이터 전환

## 7.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-007 |
| **제목** | ML Export Engine 실데이터 전환 |
| **우선순위** | 🟢 P2 (Medium) |
| **담당 영역** | `services/ml-export-engine/` |
| **예상 소요** | 3~5일 |

현재 ML 엔진은 더미 데이터를 사용합니다. UN Comtrade, World Bank, WTO 등의 실제 데이터로 전환하여 예측 정확도를 높입니다.

## 7.2 배경 및 목적

- **문제 상황**: `data_generator.py`의 더미 데이터는 실제 무역 패턴을 반영하지 못함
- **영향 범위**: ML 모델의 예측 신뢰도
- **성공 기준**: 실데이터 학습 후 R², RMSE 지표가 더미 데이터 대비 개선

## 7.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-7.1 | `data_generator.py`의 `generate_dummy_data()`를 실데이터 수집 함수로 대체 | 필수 |
| FR-7.2 | UN Comtrade API 연동 | 필수 |
| FR-7.3 | World Bank API (GDP, 성장률) 연동 | 필수 |
| FR-7.4 | WTO API (관세율) 연동 | 선택 |
| FR-7.5 | World Bank LPI (물류성과지수) 연동 | 선택 |
| FR-7.6 | 동일 컬럼명 유지 (하위호환) | 필수 |
| FR-7.7 | 데이터 캐싱 (API 호출 최소화) | 필수 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-7.1 | 데이터 수집은 배치 작업으로 분리 |
| NFR-7.2 | API Rate Limit 대응 (재시도, 지수 백오프) |
| NFR-7.3 | 실데이터 누적 저장 (매일 증분 업데이트) |

## 7.4 수락 기준

- [ ] `python data_generator.py` 실행 시 실제 데이터로 `training_data.csv` 생성
- [ ] 중력모형 + XGBoost 학습 후 R² > 0.6 달성
- [ ] `POST /predict`가 실데이터 기반 예측값 반환
- [ ] API 인터페이스(`hs_code`, `exporter_country`, `top_n`) 변경 없음
- [ ] 데이터 수집 로그 파일 생성

## 7.5 산출물

- `services/ml-export-engine/data_fetcher.py` (신규)
- `services/ml-export-engine/data_generator.py` (수정)
- `services/ml-export-engine/config.py` (API 키, 엔드포인트 설정)
- `services/ml-export-engine/data/raw/` (수집된 원본 데이터)

---

# TASK 8: Docker 컨테이너화

## 8.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-008 |
| **제목** | Docker 컨테이너화 (Frontend + API + ML) |
| **우선순위** | 🟢 P2 (Medium) |
| **담당 영역** | 프로젝트 루트 |
| **예상 소요** | 2~3일 |

전체 서비스(React Frontend, P1 API, ML Engine, PostgreSQL)를 Docker 컨테이너로 패키징하여 `docker-compose up` 하나로 실행 가능하게 합니다.

## 8.2 배경 및 목적

- **문제 상황**: 로컬 개발 환경 의존성, 배포 복잡성
- **영향 범위**: 개발 환경 통일, 배포 자동화
- **성공 기준**: 클린 환경에서 `docker-compose up`만으로 전체 서비스 기동

## 8.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-8.1 | `Dockerfile` (Frontend - Node.js 20) | 필수 |
| FR-8.2 | `Dockerfile` (P1 API - Python 3.12) | 필수 |
| FR-8.3 | `Dockerfile` (ML Engine - Python 3.12) | 필수 |
| FR-8.4 | `docker-compose.yml` (전체 오케스트레이션) | 필수 |
| FR-8.5 | PostgreSQL 서비스 포함 | 필수 |
| FR-8.6 | 볼륨 마운트 (데이터, 로그) | 필수 |
| FR-8.7 | 네트워크 분리 (frontend-network, backend-network) | 선택 |
| FR-8.8 | 헬스체크 엔드포인트 연동 | 선택 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-8.1 | 컨테이너 시작 시간: 30초 이내 (DB 제외) |
| NFR-8.2 | 이미지 크기: Python < 500MB, Node < 200MB |
| NFR-8.3 | 멀티스테이지 빌드 적용 |

## 8.4 수락 기준

- [ ] `docker-compose up --build` 실행 시 4개 서비스 모두 기동
- [ ] `http://localhost:3000`에서 React 화면 접속
- [ ] `http://localhost:8000/docs`에서 P1 API Swagger 접속
- [ ] `http://localhost:8001/docs`에서 ML API Swagger 접속
- [ ] `docker-compose down`으로 깔끔하게 종료
- [ ] `.dockerignore`로 불필요한 파일 제외

## 8.5 산출물

- `apps/frontend-react/Dockerfile`
- `services/p1-export-fit-api/Dockerfile`
- `services/ml-export-engine/Dockerfile`
- `docker-compose.yml` (루트)
- `.dockerignore` (각 서비스별)

---

# TASK 9: Prometheus/Alertmanager 모니터링 연동

## 9.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-009 |
| **제목** | Prometheus/Alertmanager 모니터링 연동 |
| **우선순위** | 🟢 P2 (Medium) |
| **담당 영역** | `ops/monitoring/` + 각 서비스 |
| **예상 소요** | 1~2일 |

`ops/monitoring/`에 이미 설정 파일이 존재하지만, 실제 서비스와 연동되지 않은 상태입니다. FastAPI에 `/metrics` 엔드포인트를 추가하고 Prometheus가 스크래핑하도록 연동합니다.

## 9.2 배경 및 목적

- **문제 상황**: 모니터링 설정 파일만 존재, 실제 메트릭 미노출
- **영향 범위**: 운영 환경 가시성, 장애 감지
- **성공 기준**: Prometheus UI에서 API 요청 수, 응답 시간, 에러율 확인 가능

## 9.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-9.1 | P1 API에 `/metrics` 엔드포인트 추가 (Prometheus Client) | 필수 |
| FR-9.2 | ML Engine에 `/metrics` 엔드포인트 추가 | 필수 |
| FR-9.3 | Prometheus 설정 파일에 scrape target 등록 | 필수 |
| FR-9.4 | API 요청 수 카운터 (`http_requests_total`) | 필수 |
| FR-9.5 | API 응답 시간 히스토그램 (`http_request_duration_seconds`) | 필수 |
| FR-9.6 | 에러율 게이지 (`http_requests_failed_total`) | 필수 |
| FR-9.7 | Alertmanager 규칙: 5xx 에러율 > 5% 시 알림 | 선택 |
| FR-9.8 | Grafana 대시보드 JSON 제공 | 선택 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-9.1 | 메트릭 수집은 API 성능에 영향 최소화 |
| NFR-9.2 | 메트릭 데이터 보관: 15일 |

## 9.4 수락 기준

- [ ] `http://localhost:8000/metrics` 접속 시 Prometheus 포맷 메트릭 출력
- [ ] Prometheus UI(`http://localhost:9090`)에서 `http_requests_total` 쿼리 가능
- [ ] API 호출 후 메트릭 값 증가 확인
- [ ] Alertmanager가 설정된 조건에서 알림 발생 (Webhook/Email 테스트)

## 9.5 산출물

- `services/p1-export-fit-api/app/middleware/metrics.py` (신규)
- `services/ml-export-engine/metrics.py` (신규)
- `ops/monitoring/prometheus.yml` (수정)
- `ops/monitoring/alert_rules.yml` (신규)
- `ops/monitoring/grafana-dashboard.json` (선택)

---

# TASK 10: 인증/권한 시스템 추가 (JWT)

## 10.1 개요 (Overview)

| 항목 | 내용 |
|------|------|
| **TASK ID** | TASK-010 |
| **제목** | 인증/권한 시스템 추가 (JWT 기반) |
| **우선순위** | 🔵 P3 (Low) |
| **담당 영역** | `services/p1-export-fit-api/` + `services/ml-export-engine/` |
| **예상 소요** | 2~3일 |

관리자용 엔드포인트(`/retrain` 등)와 일반 사용자용 엔드포인트를 분리하고, JWT 기반 인증을 도입합니다.

## 10.2 배경 및 목적

- **문제 상황**: 모든 API가 인증 없이 공개됨
- **영향 범위**: 보안, 남용 방지, 사용자별 추적
- **성공 기준**: JWT 토큰 없이는 관리자 엔드포인트 접근 불가

## 10.3 요구사항

### 기능적 요구사항

| ID | 요구사항 | 필수/선택 |
|----|---------|----------|
| FR-10.1 | JWT 토큰 발급 엔드포인트 (`POST /auth/login`) | 필수 |
| FR-10.2 | JWT 토큰 검증 미들웨어 | 필수 |
| FR-10.3 | 관리자/일반 사용자 역할(Role) 구분 | 필수 |
| FR-10.4 | `/retrain` 등 관리자 엔드포인트 보호 | 필수 |
| FR-10.5 | 토큰 만료 시간: Access 1시간, Refresh 7일 | 필수 |
| FR-10.6 | 사용자 DB 테이블 생성 | 필수 |
| FR-10.7 | Rate Limiting (사용자별 100req/min) | 선택 |

### 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NFR-10.1 | JWT Secret Key는 환경변수로 관리 |
| NFR-10.2 | 비밀번호는 bcrypt로 해싱 |
| NFR-10.3 | 인증 실패 시 401, 권한 부족 시 403 반환 |

## 10.4 수락 기준

- [ ] 토큰 없이 `POST /retrain` 호출 시 401 반환
- [ ] 올바른 JWT로 `POST /retrain` 호출 시 200 반환
- [ ] 일반 사용자 토큰으로 관리자 엔드포인트 호출 시 403 반환
- [ ] 토큰 만료 후 재발급(Refresh) 동작
- [ ] 비밀번호는 평문 저장되지 않음

## 10.5 산출물

- `services/p1-export-fit-api/app/auth/` (인증 모듈)
- `services/p1-export-fit-api/app/models/user.py` (User ORM)
- `services/p1-export-fit-api/app/routers/auth.py` (로그인/회원가입)
- `services/p1-export-fit-api/app/middleware/auth.py` (JWT 검증)
- DB 마이그레이션 파일 (users 테이블)

---

# 부록 A: 전체 의존성 맵

```
TASK-001 (실데이터) ─┬─→ TASK-002 (JSON 변환)
                    ├─→ TASK-005 (DB 도입)
                    └─→ TASK-007 (ML 실데이터)

TASK-003 (제재국) ───→ TASK-001 완료 후 실행 가능

TASK-004 (HS 매핑) ──→ TASK-006 (Frontend 연동)과 병행 가능

TASK-005 (DB) ───────→ TASK-010 (인증)의 사용자 테이블과 통합 고려

TASK-006 (Frontend) ──→ TASK-001, TASK-004 완료 권장

TASK-008 (Docker) ───→ TASK-005 완료 후 통합 권장

TASK-009 (모니터링) ──→ TASK-008 완료 후 컨테이너 내 통합 권장
```

# 부록 B: Git 브랜치 전략 제안

```
main (배포 브랜치)
  ├── feature/TASK-001-trade-data
  ├── feature/TASK-002-json-encoding
  ├── feature/TASK-003-restricted-countries
  ├── feature/TASK-004-hs-mapping
  ├── feature/TASK-005-postgresql
  ├── feature/TASK-006-frontend-api
  ├── feature/TASK-007-ml-real-data
  ├── feature/TASK-008-docker
  ├── feature/TASK-009-monitoring
  └── feature/TASK-010-jwt-auth
```

# 부록 C: 체크리스트 템플릿

각 TASK 완료 시 아래 체크리스트를 PR에 포함:

- [ ] 코드 리뷰 완료
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 문서 업데이트 (README, API 문서)
- [ ] CHANGELOG.md 업데이트
- [ ] Docker 빌드 확인 (해당 시)
- [ ] 성능/보안 검토 완료

---

*문서 끝*
