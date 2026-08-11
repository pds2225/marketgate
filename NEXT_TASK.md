# MarketGate NIGHT QUEUE — CV-02 → CV-05

## 실행 조건

- 시작 전 원격 `main` 최신화
- CV-01이 실제 코드/테스트 기준으로 완료되고 원격에 push된 경우에만 시작
- 각 작업은 **1기능 = 1작업 = 1검증 = 1커밋 = 1push**
- 각 단계가 `DONE`일 때만 다음 단계 진행
- `BLOCKED` / `FAILED` / 테스트 실패 / push 실패가 하나라도 발생하면 즉시 중단
- 사용자 승인이나 추가 결정이 필요한 상황에서는 추측하지 말고 중단
- 기존 구조 최대 유지, 최소 변경
- Windows 기준

---

# CV-02 — OpenCorporates Mock 기본검증 API

`TASKS.md`의 CV-02 정의를 source of truth로 사용한다.

구현:
- `POST /v1/company-verifications`
- `GET /v1/company-verifications/{verification_id}`
- 실제 OpenCorporates API 호출 금지, deterministic Mock Adapter 사용
- 상태값은 아래 5개만 사용
  - `BASIC_CONFIRMED`
  - `BASIC_PARTIAL`
  - `DATA_MISMATCH`
  - `INACTIVE_ENTITY`
  - `CREDIT_CHECK_REQUIRED`
- `get_current_user` 인증 적용
- `core.company_registry_checks` 저장
- 정상/일부정보/불일치/비활성/신용조사 필요/결과없음/provider 오류/timeout 처리
- 400/404/502/504/500 및 DB 저장/사용자 격리 테스트
- 신용점수·자체 위험점수 생성 금지

완료 시:
- 관련 테스트 + 전체 backend regression 실행
- `TASKS.md` CV-02 `[x]`
- 커밋 + push
- 전부 성공해야 `CV-02 = DONE`

---

# CV-03 — BuyerSearch 기본검증 카드

CV-02가 `DONE`일 때만 실행.
`TASKS.md`의 CV-03 정의를 source of truth로 사용한다.

구현:
- 새 전역 페이지/Router 생성 금지
- `apps/frontend-react/src/pages/BuyerSearch/index.tsx` 상세 단계에 `CompanyBasicVerificationCard` 추가
- 기존 바이어명·국가 자동입력
- CV-02 API 연결
- 상태 5종을 사용자에게 신용등급처럼 오인되지 않게 표시
- 빈값/로딩/결과없음/API 오류/timeout 처리
- D&B·K-SURE는 **공식 외부 조회 링크만 제공**
- 기존 `contactStatus / tradeStatus / creditStatus`와 `registryCheckStatus` 혼합 금지
- 기존 바이어 검색 흐름 회귀 금지

완료 시:
- 관련 frontend test/lint/build 실행
- 기존 바이어 검색 회귀 확인
- `TASKS.md` CV-03 `[x]`
- 커밋 + push
- 전부 성공해야 `CV-03 = DONE`

---

# CV-04 — 기본검증 테스트·회귀검증

CV-03이 `DONE`일 때만 실행.
`TASKS.md`의 CV-04 정의를 source of truth로 사용한다.

검증/보강:
- DB migration
- Mock Adapter
- API
- 화면 단위테스트
- 로그인 → 바이어검색 → 상세 → 기본검증 E2E
- 신용점수/안전점수/지급능력 판정/임의 데이터가 노출되지 않는지 확인
- 인증·사용자 격리 회귀
- 기존 결제·크레딧·바이어 검색 회귀

완료 기준:
- backend pytest 통과
- frontend unit 통과
- lint 통과
- build 통과
- E2E smoke 통과
- `TASKS.md` CV-04 `[x]`
- 커밋 + push
- 하나라도 실패하면 `BLOCKED` 후 중단

---

# CV-05 — K-SURE·D&B PRD 정정

CV-04가 `DONE`일 때만 실행.
`TASKS.md`의 CV-05 정의를 source of truth로 사용한다.

문서만 수정:
- `PRD_C1_ksure_api.md`
- `PRD_C3_dnb_api.md`
- 검증되지 않은 API/자동 등급조회 가정 제거
- 현재 MVP는 공식 외부 조회 링크로 한정
- 실제 API 연동은 계약·비용·저장·표시·재이용 권한 확인 후 별도 PRD로 명시
- 코드 기능 확장 금지

완료 기준:
- 관련 문서 간 상태/용어/범위 일치
- `TASKS.md` CV-05 `[x]`
- 커밋 + push
- `CV-05 = DONE`

---

# 절대 금지

야간 큐 동안 아래 작업은 하지 않는다.

- CSS deslop
- 코드스플리팅
- Campaign Orchestrator
- Matching & Slot
- Credit Ledger 신규개발
- Send Adapter
- 실제 이메일 발송
- 실제 OpenCorporates/D&B/K-SURE API 계약 없는 연동
- DB migration 기존 파일 임의 수정
- 임의 데이터/합성 점수 추가
- CV-05 이후 다른 작업 자동 시작

---

# 최종 보고

각 작업마다 아래를 기록한다.

```text
[STEP] CV-0X
[STATUS] DONE / BLOCKED
[CHANGED]
[TEST]
[COMMIT]
[PUSH]
```

마지막에는 전체를 요약한다.

```text
[NIGHT RESULT]
CV-02: DONE/BLOCKED/NOT_STARTED
CV-03: DONE/BLOCKED/NOT_STARTED
CV-04: DONE/BLOCKED/NOT_STARTED
CV-05: DONE/BLOCKED/NOT_STARTED
STOPPED_AT: ...
```

# MiMo 실행 지시

**CV-01 완료 확인 후 이 파일을 처음부터 끝까지 읽고 CV-02→CV-05를 순서대로 수행한다. 각 단계가 DONE일 때만 다음 단계로 진행하고, 실패·BLOCKED·push 실패가 발생하면 즉시 중단한다. CV-05 후 종료한다.**