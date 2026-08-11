# MarketGate NEXT TASK — CV-02 OpenCorporates Mock 기본검증 API

## 실행 조건

이 파일은 현재 CV-01 작업이 끝난 뒤에만 실행한다.

- CV-01 STATUS = DONE 인 경우에만 진행
- CV-01 STATUS = BLOCKED / FAILED / 미검증이면 즉시 중단
- CV-01 결과가 원격 브랜치에 push되지 않았으면 진행 금지
- 시작 전 원격 main 최신화 및 현재 브랜치 상태 확인

---

## 작업 원칙

- 1기능 = 1작업 = 1검증
- 기존 구조 최대 유지, 최소 변경
- Windows 기준
- 이번 작업은 CV-02 하나만 수행
- 다음 CV-03 작업은 자동 실행 금지
- 예외처리, 입력검증, 오류상태, 빈상태 반영
- README/TASKS.md는 실제 변경이 필요한 범위만 최소 업데이트

---

## 목표

OpenCorporates 연동 전 단계로, 실제 외부 API를 호출하지 않는 **Mock Adapter 기반 해외기업 기본검증 API**를 구현한다.

목표는 바이어/해외기업의 기본 실체 확인 결과를 표준 상태로 반환하는 것이다.

확정 상태값은 아래 5개만 사용한다.

```text
BASIC_CONFIRMED
BASIC_PARTIAL
DATA_MISMATCH
INACTIVE_ENTITY
CREDIT_CHECK_REQUIRED
```

다른 상태명은 만들지 않는다.

---

## 입력

최소 입력값:

- company_name
- country_iso3
- registration_number (optional)

입력검증:

- company_name 빈값 금지
- country_iso3는 ISO3 3자리 대문자 기준 검증
- registration_number는 선택값
- 잘못된 JSON / 타입 오류 처리

---

## Mock Adapter 요구사항

실제 OpenCorporates API 호출 금지.

Mock Adapter는 테스트 가능한 고정 fixture 또는 deterministic mock 데이터만 사용한다.

최소 시나리오:

1. 회사명/국가 일치 + active → BASIC_CONFIRMED
2. 회사명/국가 일부만 일치 또는 registration_number 부재 → BASIC_PARTIAL
3. 회사명/국가/등록번호 충돌 → DATA_MISMATCH
4. inactive/dissolved 상태 → INACTIVE_ENTITY
5. 기본 실체는 확인되지만 신용도 판단 불가/별도 신용조사 필요 → CREDIT_CHECK_REQUIRED
6. 검색결과 없음 → BASIC_PARTIAL 또는 명확한 no-result 응답 정책을 기존 문서와 맞춰 처리
7. provider timeout/error → 정상 상태로 위장하지 말고 오류 응답

주의:
- 신용점수, 자체 등급, 위험점수 생성 금지
- OpenCorporates mock 결과를 실제 신용정보처럼 표시 금지

---

## DB 저장

CV-01에서 생성한 `core.company_registry_checks`를 사용한다.

저장 필드 최소 확인:

- user_id
- company_name
- country_iso3
- registration_number
- provider = `opencorporates_mock`
- registry_check_status
- result_json
- provider_ref
- requested_at
- completed_at
- error_code
- error_message

DB 스키마를 다시 변경하지 않는다.
CV-01 migration 수정 금지.

---

## API

기존 FastAPI 구조에 맞춰 최소 endpoint를 추가한다.

예시 경로는 기존 라우팅 규칙을 우선한다.
새 경로를 임의로 만들기 전에 유사 endpoint 구조를 확인한다.

응답에는 최소 다음을 포함한다.

```json
{
  "company_name": "...",
  "country_iso3": "USA",
  "provider": "opencorporates_mock",
  "registry_check_status": "BASIC_CONFIRMED",
  "provider_ref": "...",
  "checked_at": "..."
}
```

result_json 전체 원본을 프론트에 무조건 노출하지 않는다.
기존 API 응답 정책에 맞춰 필요한 필드만 반환한다.

---

## 인증 / 권한

- 기존 인증 구조를 그대로 사용
- user_id는 클라이언트 입력을 신뢰하지 말고 기존 auth context에서 확보
- 다른 사용자 결과 조회/덮어쓰기 금지
- 기존 38개 endpoint 보안 정책을 깨지 않는다

---

## 오류 / 빈 상태

반드시 처리:

- company_name 빈값
- 잘못된 country_iso3
- 검색결과 없음
- mock provider error
- mock provider timeout
- DB insert 실패
- 인증 없음
- 잘못된 registration_number 타입

실패를 `BASIC_CONFIRMED` 등 정상 상태로 변환하지 않는다.

---

## 테스트

최소 테스트:

1. BASIC_CONFIRMED
2. BASIC_PARTIAL
3. DATA_MISMATCH
4. INACTIVE_ENTITY
5. CREDIT_CHECK_REQUIRED
6. 검색결과 없음
7. provider error
8. provider timeout
9. 인증 없음
10. 잘못된 입력
11. DB 저장 확인
12. 다른 사용자 격리
13. 기존 backend regression

가능하면 실제 PostgreSQL 테스트 환경을 사용하고,
불가능하면 그 한계를 명확히 보고한다.

---

## 수정 금지

- D&B API 실제 연동
- K-SURE API 실제 연동
- 외부 조회 링크 UI
- 프론트 화면 구현
- Compliance Engine
- Credit Ledger
- Buyer Contact
- Send Adapter
- CSS
- 코드스플리팅
- 기존 migration 수정
- 임의 risk score 생성

---

## 문서 업데이트

작업 완료 시 `TASKS.md` 또는 현재 개발현황 문서에 CV-02 결과만 반영한다.

기록:

- endpoint
- adapter 위치
- 상태 5종
- 테스트 결과
- mock임을 명확히 표기

README는 API 사용법이 실제 사용자/개발자에게 필요한 경우에만 최소 수정한다.

---

## 완료 조건

아래를 모두 만족할 때만 CV-02 = DONE.

- Mock Adapter 구현
- 5개 상태 정확히 사용
- 인증/사용자 격리 유지
- DB 저장 성공
- 오류/timeout/no-result 처리
- 관련 테스트 통과
- 기존 backend regression 통과
- 변경사항 commit + 원격 branch push

하나라도 실패하면 CV-02 = BLOCKED.

---

## 최종 보고 형식

```text
[CV-01 PRECONDITION]
DONE / BLOCKED

[BRANCH]
...

[COMMIT]
...

[PUSH]
...

[ENDPOINT]
...

[ADAPTER]
...

[STATUS CASES]
BASIC_CONFIRMED: ...
BASIC_PARTIAL: ...
DATA_MISMATCH: ...
INACTIVE_ENTITY: ...
CREDIT_CHECK_REQUIRED: ...

[ERROR CASES]
...

[DB]
...

[TEST]
...

[REGRESSION]
...

[CV-02 STATUS]
DONE / BLOCKED

[NEXT]
다음 작업 1개만 추천하고 실행하지 마라.
```

---

# MiMo 실행 지시

**현재 작업(CV-01)을 먼저 끝낸다. CV-01 STATUS가 DONE일 때만 원격 main 최신화 후 이 `NEXT_TASK.md`를 처음부터 끝까지 읽고 CV-02 한 작업만 수행한다. CV-01이 BLOCKED/FAILED이면 CV-02를 실행하지 말고 중단한다.**
