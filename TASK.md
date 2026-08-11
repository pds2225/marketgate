# MarketGate TASK — demo/buyers 60명 제한 원인 규명 및 최소 수정

## 작업 원칙
- 이번 작업은 **1기능 = 1작업 = 1검증**으로 수행한다.
- 기존 구조를 최대한 유지하고 최소 변경만 한다.
- 다른 기능으로 범위를 확장하지 않는다.
- 작업 종료 후 다음 작업을 자동 실행하지 않는다.
- Windows 기준으로 작업한다.

## 목표
현재 `demo/buyers` 엔드포인트가 최대 60명만 반환하는 원인을 정확히 찾아 수정한다.

실제 후보 데이터가 60건 이상 존재하는 경우에도 결과가 60건에서 강제로 잘리는 원인을 추적하고, **불필요한 하드 limit인 경우에만 최소 수정으로 제거한다.**

추측으로 `60 → 500`, `60 → 1000` 같은 숫자 변경을 하지 않는다.

## 이번 작업에서 수정 금지
- CSS deslop Pass 3
- Landing CSS
- App.jsx 코드스플리팅
- React.lazy / Suspense
- Campaign Orchestrator
- Matching & Slot Service 신규 구현
- Credit & Entitlement Ledger 신규 구현
- Compliance 신규 구현
- Send Adapter
- Response Relay
- Attribution / Deal Workspace
- unrelated refactor
- unrelated cleanup
- 임의 데이터 생성
- fake buyer 추가
- 랜덤/합성 지표 추가

# STEP 1 — 변경 전 원인 조사
`demo/buyers` 요청부터 최종 response까지 데이터 흐름을 끝까지 추적한다.

조사 순서:

```text
HTTP endpoint
→ router/controller
→ service
→ repository/query
→ CSV/data loader
→ normalization
→ dedupe
→ filter
→ pagination/limit
→ response serializer
```

관련 범위 안에서 아래 패턴을 조사한다.

```text
limit=60
LIMIT 60
head(60)
[:60]
max_results
page_size
default_limit
max_buyers
demo limit
```

주의:
- 저장소 전체의 숫자 `60`을 무작정 변경하지 않는다.
- `demo/buyers`와 실제 호출 경로에 연결된 코드만 우선 조사한다.
- 프론트에서 잘리는 것인지 백엔드에서 잘리는 것인지 구분한다.
- CSV 또는 DB 로딩 단계에서 이미 60개만 읽는지도 확인한다.

# STEP 2 — 데이터 흐름 수치 측정
코드 수정 전에 다음 수치를 실제 실행 결과로 확인한다.

```text
원본 후보 건수
→ 국가 필터 후 건수
→ HS/품목 필터 후 건수
→ 중복 제거 후 건수
→ 기타 Hard Gate 후 건수
→ API 반환 직전 건수
→ 최종 HTTP response 건수
```

반드시 실제 값으로 기록한다.

# STEP 3 — Root Cause 판정
60건 제한의 원인을 아래 중 하나로 명확히 분류한다.

- A. DB query
- B. CSV/data loader
- C. service
- D. pagination
- E. frontend
- F. 실제 필터링 결과가 60건 이하
- G. 기타

원인이 여러 단계에 존재하면 각각 기록하되, 실제 최종 60건 제한을 발생시키는 직접 원인을 구분한다.

# STEP 4 — 수정 조건

## 수정하는 경우
원인이 **불필요한 고정 limit**으로 확인된 경우에만 최소 수정한다.

반드시 유지:
- 기존 API 계약
- 기존 pagination 구조가 있다면 유지
- 명시적 `limit` 파라미터가 있으면 유지
- limit 입력값 validation
- 잘못된 country 입력 처리
- 잘못된 HS/product 입력 처리
- 빈 결과 상태
- 데이터 로딩 오류 상태
- API 오류 상태
- 기존 정상 필터
- 기존 정렬 기준

## 수정하지 않는 경우
다음 경우 코드를 억지로 바꾸지 않는다.
- 실제 데이터가 60건 이하
- 정상 pagination의 첫 페이지가 60건인 것뿐인 경우
- 60건 제한이 명시된 제품 요구사항인 경우
- 원인이 데이터 품질/중복 제거 때문인 경우

이 경우 Root Cause와 다음 대응만 보고한다.

# STEP 5 — 테스트
최소 다음 케이스를 검증한다.

1. 후보가 60건 이하인 경우
2. 후보가 60건 초과인 경우
3. 결과가 0건인 경우
4. 잘못된 filter 입력
5. explicit `limit` 전달
6. 기존 `demo/buyers` endpoint regression

가능하면 기존 관련 테스트를 먼저 실행하고, 필요한 테스트만 최소 추가한다.

# STEP 6 — 검증 기준
완료 조건:
- 60건 제한의 정확한 위치가 확인됨
- 수정 전/후 데이터 건수 비교 가능
- 실제 데이터가 60건 이상이면 의도된 방식으로 접근 가능
- 기존 필터 결과가 변형되지 않음
- 기존 pagination/API contract가 깨지지 않음
- 빈 상태 처리 정상
- 오류 처리 정상
- 관련 테스트 통과

테스트 실패 상태로 완료 처리하지 않는다.

# STEP 7 — 문서 업데이트
원인이 확인되고 작업이 끝난 경우 기존 `TASKS.md`에 아래만 추가 또는 갱신한다.

- Root Cause
- 수정 파일
- 검증 결과
- 테스트 결과

주의:
- 기존 `TASKS.md` 구조를 최대한 유지한다.
- 다른 WBS 상태를 임의로 변경하지 않는다.
- README는 **실제 사용자 동작 또는 API 사용 방법이 달라지는 경우에만** 수정한다.

# 최종 보고 형식

## [ROOT CAUSE]
60건 제한의 정확한 원인과 발생 위치

## [DATA FLOW]
```text
원본 N
→ country filter N
→ HS/product filter N
→ dedupe N
→ hard gate N
→ API 직전 N
→ HTTP response N
```

수정 전/후가 다르면 둘 다 표시한다.

## [CHANGED]
- 수정 파일
- 각 파일의 수정 이유

수정이 필요 없었다면 `코드 수정 없음`이라고 명시한다.

## [TEST]
- 실행 명령
- passed / failed
- 테스트 개수

## [REGRESSION]
기존 기능 영향 여부

## [TASK]
`TASKS.md` 갱신 내용

## [NEXT]
다음 작업 **1개만** 추천한다.
다음 작업을 실제로 실행하지 않는다.

# MiMo 실행 지시

**이 `TASK.md`를 처음부터 끝까지 읽고, 적힌 작업 1개만 수행한 뒤 멈춰라.**
