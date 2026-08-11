# MarketGate TASK — CV-01 재검증 및 수정

## 작업 원칙

- 이번 작업은 **CV-01 하나만** 수행한다.
- **1기능 = 1작업 = 1검증** 원칙을 지킨다.
- 기존 구조를 최대한 유지하고 최소 변경만 한다.
- CV-02 OpenCorporates Mock 구현으로 넘어가지 않는다.
- 다른 기능, CSS, 리팩터링, 결제, 크레딧, 캠페인, 컴플라이언스 확장 작업을 하지 않는다.
- 기존 migration 파일 `0001~0004`는 수정하지 않는다.
- 작업 종료 후 다음 작업을 자동 실행하지 않는다.

---

## 배경

CV-01 완료 보고에는 다음 변경이 있다고 되어 있었다.

- `db/migrations/0005_company_registry_checks.sql` 신규 생성
- `services/p1-export-fit-api/app/run_migrations.py` 수정
- pytest `224 passed`
- frontend build 통과

하지만 원격 `main` 기준으로는 해당 CV-01 변경을 확인할 수 없었고, 보고된 ENUM 값도 기존 확정 상태값과 불일치했다.

따라서 이번 작업의 목표는 **CV-01을 원격 기준으로 재현 가능하고 검증 가능한 상태로 바로잡는 것**이다.

---

# 목표

1. 현재 로컬 작업과 원격 `pds2225/marketgate` 최신 `main`을 비교한다.
2. CV-01 변경사항이 실제 어느 브랜치/커밋/로컬 변경에 있는지 확인한다.
3. `0005_company_registry_checks.sql`의 상태 ENUM을 확정값으로 맞춘다.
4. `run_migrations.py`가 기존 책임범위를 유지하면서 `0005`를 정상 실행하도록 검증한다.
5. 실제 PostgreSQL에서 migration chain과 재실행 동작을 검증한다.
6. 관련 backend 테스트 및 frontend build를 다시 수행한다.
7. 모든 검증이 통과한 경우에만 commit + push 한다.

---

# STEP 1 — Git 기준점 확인

작업 시작 시 반드시 아래를 확인하고 기록한다.

```text
git status
git branch --show-current
git rev-parse HEAD
git fetch origin
git rev-parse origin/main
```

그리고 아래를 명확히 판정한다.

- 현재 브랜치
- 현재 HEAD
- origin/main HEAD
- working tree dirty 여부
- CV-01 변경파일 존재 여부
- CV-01 변경이 아직 미커밋인지, 다른 브랜치에 커밋됐는지, 이미 원격에 있는지

원격 최신 기준을 확인하기 전 코드를 수정하지 않는다.

---

# STEP 2 — CV-01 변경파일 확인

대상 파일:

```text
db/migrations/0005_company_registry_checks.sql
services/p1-export-fit-api/app/run_migrations.py
```

`0005_company_registry_checks.sql`이 없다면 기존 작업 흔적을 먼저 확인한다.

무작정 새로 만들기 전에 다음을 확인한다.

- git log
- 다른 현재 작업 브랜치
- git status의 untracked/modified 파일

기존 CV-01 작업이 발견되면 그것을 기준으로 최소 수정한다.

---

# STEP 3 — ENUM 확정값 수정

`core.registry_check_status`의 값은 정확히 아래 5개를 사용한다.

```text
BASIC_CONFIRMED
BASIC_PARTIAL
DATA_MISMATCH
INACTIVE_ENTITY
CREDIT_CHECK_REQUIRED
```

다음 값은 사용하지 않는다.

```text
VERIFIED
PARTIAL_MATCH
MISMATCH
INACTIVE
```

`registry_check_status` 컬럼은 **NULL 허용**을 유지한다.

이유:
- 요청 직후 아직 검증 결과가 없는 상태를 표현할 수 있어야 한다.
- API/Frontend/DB 상태명을 하나의 계약으로 유지한다.

---

# STEP 4 — 테이블 스키마 검증

`core.company_registry_checks`가 최소 아래 필드를 유지하는지 확인한다.

```text
check_id uuid PK
user_id
company_name
country_iso3
registration_number
provider
registry_check_status
result_json jsonb
provider_ref
requested_at
completed_at
error_code
error_message
```

필수 인덱스:

```text
(user_id, requested_at DESC)
(company_name, country_iso3)
```

기존 인증·결제·크레딧·Vault 관련 테이블은 변경하지 않는다.

---

# STEP 5 — migration runner 검증

`services/p1-export-fit-api/app/run_migrations.py`의 기존 책임범위를 먼저 확인한다.

주의:

- 신규 DB 전체 `0001→0005`를 원래 이 runner가 담당하는 구조인지 확인한다.
- 원래 특정 migration부터 실행하는 runner였다면 책임범위를 임의로 확대하지 않는다.
- 단순히 배열에 `0005`를 넣었다는 이유만으로 완료 처리하지 않는다.
- 파일 실행 순서가 deterministic 해야 한다.
- 파일 누락 시 조용히 성공 처리하지 않는다.

확인할 것:

```text
기존 실행 시작 migration
실행 순서
실패 시 exit 동작
중간 migration 실패 시 후속 실행 여부
재실행 시 기대 동작
```

---

# STEP 6 — 실제 PostgreSQL migration 검증

SQL 문자열 검사만으로 완료 처리하지 않는다.

가능한 실제 PostgreSQL에서 아래를 수행한다.

## A. 기존 DB 업그레이드 경로

```text
0004까지 적용된 상태
→ 0005 적용
→ 성공
```

## B. 신규 DB 정상 migration chain

현재 프로젝트의 공식 migration 실행 경로를 사용하여 새 DB에서 `0005`까지 정상 도달하는지 확인한다.

예상 경로가 `0001→0005`라면 전부 실행한다.

## C. 재실행 검증

migration runner 또는 공식 재실행 경로를 한 번 더 실행해 예상한 동작인지 확인한다.

특히 PostgreSQL ENUM의 `CREATE TYPE` 재실행 충돌 여부를 실제로 확인한다.

재실행이 "성공해야 하는 구조"인지 "이미 적용된 migration을 건너뛰는 구조"인지 기존 migration 정책을 기준으로 판단한다.

억지로 모든 SQL을 idempotent하게 바꾸지 않는다.

---

# STEP 7 — DB 결과 검증

실제 DB에서 다음을 확인한다.

### ENUM 값

정확히 5개:

```text
BASIC_CONFIRMED
BASIC_PARTIAL
DATA_MISMATCH
INACTIVE_ENTITY
CREDIT_CHECK_REQUIRED
```

### 테이블

```text
core.company_registry_checks
```

### 인덱스

```text
user_id + requested_at DESC
company_name + country_iso3
```

### NULL

`registry_check_status IS NULL`인 row가 스키마상 허용되는지 확인한다.

---

# STEP 8 — 테스트

최소 다음을 실행한다.

## Backend

기존 p1-export-fit-api 전체 pytest.

완료 기준:

```text
0 failed
```

기존 보고의 `224 passed`와 숫자가 달라도, 테스트 추가/삭제가 있었으면 실제 현재 개수를 보고한다.

## Frontend

```text
npm run build
```

통과해야 한다.

## Migration 검증

별도로 다음 결과를 보고한다.

- 기존 DB `0004→0005`
- 신규 DB 공식 migration chain
- 재실행

---

# STEP 9 — Commit / Push

다음 조건을 모두 만족할 때만 commit + push 한다.

- ENUM 확정값 일치
- PostgreSQL migration 성공
- migration runner 정상
- backend pytest 0 failed
- frontend build 성공
- 기존 핵심 테이블 비침범

가능하면 현재 CV-01 작업 브랜치를 사용한다.

`main`에 직접 push하지 말고, 이미 사용 중인 안전한 작업 브랜치가 있다면 해당 브랜치에 push한다.

현재 작업 방식이 main 직접 push가 명시적으로 허용된 구조라면 기존 저장소 관행을 확인하고 따른다.

새 브랜치를 임의로 여러 개 만들지 않는다.

---

# 수정 금지

- CV-02 OpenCorporates Mock adapter/API 구현
- UI 구현
- D&B/K-SURE 외부 링크 구현
- CSS
- code splitting
- Campaign Orchestrator
- Credit Ledger
- Send Adapter
- Response Relay
- 다른 migration 수정
- unrelated cleanup/refactor
- 기존 인증/결제/크레딧/Vault 스키마 변경

---

# 최종 출력 형식

## [BRANCH]

작업 브랜치와 origin/main 기준 상태

## [COMMIT]

커밋 SHA. 커밋하지 않았다면 이유.

## [PUSH]

원격 push 여부와 원격 브랜치명

## [FILES]

실제 수정 파일

## [ENUM]

최종 ENUM 5개

## [MIGRATION TEST]

```text
0004 → 0005: PASS/FAIL
신규 DB 공식 migration chain: PASS/FAIL
재실행: PASS/FAIL
```

실제 PostgreSQL을 실행하지 못했다면 PASS라고 쓰지 말고 `NOT RUN`과 이유를 명시한다.

## [TEST]

```text
backend pytest: N passed / N failed
frontend build: PASS/FAIL
```

## [REGRESSION]

기존 인증·결제·크레딧·Vault 등에 영향 여부

## [CV-01 STATUS]

모든 필수 검증 통과 시에만:

```text
DONE
```

하나라도 확인하지 못했거나 실패하면:

```text
BLOCKED
```

그리고 정확한 blocker를 적는다.

## [NEXT]

다음 작업은 1개만 제안한다.
실행하지 않는다.

---

# MiMo 실행 지시

**원격 `main`을 기준점으로 확인한 뒤 이 `TASK.md`를 처음부터 끝까지 읽고, CV-01 재검증/수정 작업 1개만 수행해라. CV-02는 실행하지 말고 결과 보고 후 멈춰라.**
