<!-- BEGIN OPS HEADER: 실행 게이트. 본문보다 우선. -->

# TASK.md — 이 레포 실행 단일 기준

```text
REPO:   pds2225/marketgate
REMOTE: https://github.com/pds2225/marketgate.git
BASE:   main
```

## 0. STOP 게이트 (하나라도 실패 → 코드 수정 금지, 즉시 중단)

아래를 **맨 처음** 실행한다. 실패하면 구현하지 않는다.

1. `git fetch --all --prune`  
   - 실패 → **STOP**. 로컬에 있는 옛 TASK로 진행 금지.
2. `git remote get-url origin`  
   - 위 `REMOTE`와 **문자 완전 일치**가 아니면 **STOP**. (다른 레포/worktree 오실행 방지)
3. 실행 파일은 **이 `TASK.md`만**.  
   - `NEXT_TASK.md` / 다른 레포 TASK / 옛 채팅 / AGENTS 외 지시서로 구현 시작 → **STOP** 로그 남기고 중단.  
   - `NEXT_TASK.md`는 큐·참고다. TASK가 “읽어라”고 쓰지 않으면 열지 마라.
4. 허용 범위: 이 파일 + 이 파일이 지명한 코드/테스트/문서.  
   - 지명되지 않은 레포·폴더를 고치기 시작하면 **STOP**.
5. Must 순서: 아래 TRACK에 `depends_on`이 있으면 **선행 TRACK이 DONE일 때만** 후속 TRACK 착수.  
   - 선행 미완료인데 후속 파일을 열면 **STOP**.
6. DONE 금지 (하나라도 해당하면 FAIL, 머지 금지):  
   - 구현 코드 diff 없이 **테스트/픽스처만** 변경  
   - 지정 **smoke 산출물 파일** 없음  
   - 보고에 **커밋 SHA + 실행한 명령 + 테스트 요약 원문(10줄 이내)** 없음
7. `AGENTS.md`와 이 TASK가 충돌:  
   - 코드 수정 중단. `BLOCKED_WITH_EVIDENCE`만 남긴다.  
   - 사용자에게 선택지 3개만: `예외 승인` / `우회(다른 파일)` / `보류`. 선택 전 코드 금지.
8. 머지: 이 TASK 본문이 머지를 **명시**한 경우에만. 그래도 아래 아니면 merge 명령 실행 금지.  
   - GitHub Checks **초록**  
   - 필수 테스트 job 통과  
   - 6번 DONE 금지 항목 없음  
   - 충돌 미해결이면 머지 금지
9. 로컬 dirty / 다른 브랜치: 기본 브랜치(`BASE`)에서 직접 수정 금지. **새 브랜치**에서만 작업.
10. 시크릿: 값은 `D:\_secure\.env.shared`만. TASK에는 키 이름만.  
    시작 시 `D:\_secure\sync.ps1 check` (원격이 앞설 때만 pull). 키를 바꿨으면 `push`.

## 우선순위

1. 사용자 요청  
2. 그중 **가장 최신** 요청  
3. 데드라인 / 막힘 / 버그  

Must = 지금 안 하면 막히거나, 데드라인이거나, 버그이거나, **사용자 요청**인 것.

## 하다 만 작업

브랜치 유지 + 이 파일에 체크포인트 한 줄 (`어디까지 했는지`). 기본 브랜치에 미완성 커밋 금지.

## 최종 보고 최소 항목

```text
REPO: (origin URL)
SHA: (구현 커밋)
CMD: (테스트/smoke 명령)
SMOKE: (산출물 경로 또는 N/A 이유)
TEST: (요약 원문 10줄 이내 붙여넣기)
DIFF: (구현 파일 목록 — 테스트만이면 FAIL)
STATUS: DONE | BLOCKED_WITH_EVIDENCE | FAIL
```

<!-- END OPS HEADER -->


---

# TRACK 순서 (marketgate)

| TRACK | 상태 | 내용 | 착수 조건 |
|-------|------|------|-----------|
| A | Must | 야간 브랜치 검수·선별병합·CV-04 | 즉시 |
| — | 참고 | `NEXT_TASK.md` | **실행 금지.** 큐/참고만. |

TRACK A smoke: 각 병합 후보 테스트 로그 + CV-04 회귀 로그 파일.
머지는 TASK 본문 순서(CV-05 → BUYER-60 → CV-02 → CV-03 → CV-04) + STOP 게이트 8번을 모두 통과할 때만.

---

# MarketGate TASK — 야간 병렬개발 검수·수정·선별병합·CV-04 통합검증

## 목적

어젯밤 생성된 night 브랜치들을 원격 GitHub 기준으로 검수하고, 필요한 최소 수정 후 **통과한 작업만 main에 병합**한다.

이번 TASK는 단순 보고가 아니라 아래까지 한 번에 수행한다.

```text
원격 검수
→ BLOCKER 수정
→ 각 브랜치 재테스트
→ 통과 브랜치만 선별 병합
→ 충돌 해결
→ main 통합 회귀검증(CV-04)
→ TASKS.md 상태 정리
→ 최종 보고
→ STOP
```

기존 구조를 최대한 유지하고 최소 변경한다.

---

# 0. 현재 원격 기준 사실

기준 저장소:

```text
pds2225/marketgate
```

검수 당시 main 기준점:

```text
8e953b78d166865e86ecc9ed9ea4f3463b795b6a
```

야간 브랜치 상태:

```text
A. night/cv02-opencorporates-mock
   commit: cbb049e
   main 대비 실제 변경 있음

B. night/cv03-company-verification-ui
   commit: a8dc892
   main 대비 실제 변경 있음

C. night/cv05-prd-correction
   commit: 54bb709
   main 대비 실제 변경 있음

D. night/buyer-60-limit
   commit: 2292305
   main 대비 실제 변경 있음

E. night/page-code-splitting
   main과 identical
   실제 변경 없음

F. night/css-deslop-pass3
   commit은 있으나 main compare 기준 files=[]
   실제 병합할 파일 없음
```

## 핵심 원칙

실제 병합 후보는 우선 아래 4개만 본다.

```text
CV-05
BUYER-60
CV-02
CV-03
```

다음 2개는 **병합하지 않는다.**

```text
night/page-code-splitting
night/css-deslop-pass3
```

두 브랜치는 삭제하지 말고 그대로 보존한다.
사용자 검수 전 임의 branch cleanup 금지.

---

# 1. 작업 원칙

- 1기능 = 1검수 = 1결론을 유지한다.
- 원격 `main`과 각 night 브랜치를 source of truth로 사용한다.
- 보고된 테스트 결과만 믿지 말고 필요한 부분을 직접 재검증한다.
- 기존 구조 최대 유지, 최소 수정.
- unrelated refactor 금지.
- synthetic/random buyer metric 추가 금지.
- 신용점수·안전점수·위험점수 생성 금지.
- 실제 OpenCorporates/D&B/K-SURE API 호출 금지.
- 기존 인증·결제·크레딧·Vault 구조를 임의 변경하지 않는다.
- 기존 migration `0001~0004` 수정 금지.
- main 병합 중 conflict가 발생하면 어느 한쪽을 통째로 덮어쓰지 않는다.
- 충돌 파일의 양쪽 의도를 보존하고 관련 테스트로 검증한다.
- 실패한 작업은 main에 넣지 않는다.
- 미검증 항목을 PASS라고 보고하지 않는다.
- 이번 TASK 종료 후 Campaign/Send/Credit/Compliance 신규개발로 넘어가지 않는다.

---

# 2. 시작 전 Git 기준점 확인

먼저 아래를 수행한다.

```text
git fetch origin
git status
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
```

확인:

- 현재 브랜치
- working tree clean 여부
- origin/main 최신 SHA
- 위 6개 night 브랜치 존재 여부
- 각 브랜치가 main 대비 ahead/behind/diverged인지

working tree가 dirty하면 기존 사용자 작업을 삭제하거나 덮어쓰지 않는다.

---

# 3. BLOCKER A — CV-02 DB ENUM 불일치 수정

대상:

```text
night/cv02-opencorporates-mock
```

현재 원격 코드에서 `db/migrations/0005_company_registry_checks.sql`의 실제 ENUM이 다음 구형 값으로 작성된 것이 확인됐다.

```text
VERIFIED
PARTIAL_MATCH
MISMATCH
INACTIVE
CREDIT_CHECK_REQUIRED
```

하지만 API Router는 다음 값을 반환한다.

```text
BASIC_CONFIRMED
BASIC_PARTIAL
DATA_MISMATCH
INACTIVE_ENTITY
CREDIT_CHECK_REQUIRED
```

이 상태는 PostgreSQL 실제 INSERT 시 실패할 수 있으므로 **병합 BLOCKER**다.

## 수정

`core.registry_check_status`는 정확히 다음 5개로 통일한다.

```text
BASIC_CONFIRMED
BASIC_PARTIAL
DATA_MISMATCH
INACTIVE_ENTITY
CREDIT_CHECK_REQUIRED
```

다른 상태명 사용 금지.

`registry_check_status` 컬럼의 NULL 허용은 유지한다.

## 확인 범위

아래 모든 계층에서 상태명이 동일해야 한다.

```text
0005 migration
→ store
→ API router
→ API response
→ frontend mapping
→ tests
```

API/Frontend/DB 사이에 불필요한 상태명 변환 계층을 만들지 않는다.

---

# 4. BLOCKER B — CV-02 사용자 격리 수정

현재 원격 CV-02 코드에서 GET 조회는 인증 dependency를 사용하지만 실제 DB 조회는:

```text
WHERE check_id = %s
```

만 사용하고 `user_id`를 조건에 포함하지 않는다.

즉 인증된 사용자라면 다른 사용자의 `verification_id`를 알 경우 조회할 가능성이 있다.

이 상태는 **병합 BLOCKER**다.

## 수정 요구

GET:

```text
GET /v1/company-verifications/{verification_id}
```

는 현재 로그인 사용자의 결과만 조회해야 한다.

store 조회를 최소한 다음 의미로 변경한다.

```text
WHERE check_id = ? AND user_id = current_user
```

구체적 함수 시그니처는 기존 코드 스타일에 맞춘다.

예:

```text
get_verification(check_id, user_id)
```

다른 사용자의 record는 정보노출을 막기 위해 기존 API 정책에 맞게 404 또는 허용된 안전 응답으로 처리한다.

403/404 중 임의로 새 정책을 만들지 말고 저장소의 유사 리소스 조회 패턴을 우선한다.

## 필수 테스트

반드시 추가:

```text
user A가 생성
→ user B가 같은 verification_id GET
→ 데이터 노출 안 됨
```

단순히 `get_current_user` dependency가 있다는 이유만으로 사용자 격리 PASS 처리하지 않는다.

---

# 5. CV-02 Mock 시나리오 완성도 재검수

현재 night 브랜치 테스트는 11개이며, 기존 CV-02 요구사항 전부를 검증하지 못한 상태로 보인다.

최소 아래를 다시 확인한다.

## 정상 상태 5종

```text
BASIC_CONFIRMED
BASIC_PARTIAL
DATA_MISMATCH
INACTIVE_ENTITY
CREDIT_CHECK_REQUIRED
```

## 예외 상태

반드시 검증:

```text
검색결과 없음
provider error
provider timeout
DB insert 실패
인증 없음
잘못된 company_name
잘못된 country_iso3
잘못된 registration_number 타입
다른 사용자 격리
없는 verification_id
```

Provider timeout/error를 정상 verification status로 위장하지 않는다.

HTTP 상태는 기존 TASKS.md/CV 정책과 맞춰:

```text
400/422 계열 입력오류
404 결과없음
502 provider error
504 provider timeout
500 DB/internal error
```

을 기존 FastAPI 정책과 대조해 적용한다.

## Mock 방식

실제 OpenCorporates 호출 금지.

Mock은 deterministic fixture/scenario여야 한다.

단순히 회사명을 SHA256으로 해시해 5개 상태 중 무작위처럼 분산시키는 방식만으로는 아래 시나리오를 표현하기 어렵다.

```text
no-result
provider-error
provider-timeout
```

기존 테스트가 재현 가능한 명시적 fixture/scenario를 사용할 수 있게 최소 수정한다.

실행 때마다 달라지는 random 사용 금지.

## Provider 명칭

Mock임을 실제 연동과 혼동하지 않도록 기존 제품 문서/TASKS 정책을 확인한다.

현재 MVP 정책이 `opencorporates_mock`을 요구하면 DB/provider 응답을 그 값으로 통일한다.

실제 연동이 아닌데 실제 production provider처럼 오인되는 값은 사용하지 않는다.

---

# 6. CV-02 실제 PostgreSQL 검증

문자열 기반 테스트만으로 완료하지 않는다.

가능한 실제 PostgreSQL 테스트 환경에서:

```text
0004 → 0005
```

적용 후 CV-02 POST를 실행해 실제 INSERT가 성공하는지 확인한다.

특히 수정된 enum 상태가 실제 INSERT 가능한지 확인한다.

확인:

```text
BASIC_CONFIRMED INSERT
BASIC_PARTIAL INSERT
DATA_MISMATCH INSERT
INACTIVE_ENTITY INSERT
CREDIT_CHECK_REQUIRED INSERT
NULL 허용
```

실제 PostgreSQL 실행이 불가능하면 `NOT RUN`이라고 보고하고 이유를 명시한다.

`NOT RUN`을 PASS로 바꾸지 않는다.

---

# 7. BUYER-60 재검수

대상:

```text
night/buyer-60-limit
```

원격 diff 기준 실제 변경은 최소 다음이다.

```text
services/p1-export-fit-api/app/services/demo_snapshot.py
services/p1-export-fit-api/main.py
```

`demo_snapshot.py`의 main 기존 값:

```text
_DEFAULT_BUYER_LIMIT = 60
_MAX_BUYER_LIMIT = 200
```

night branch 변경:

```text
_DEFAULT_BUYER_LIMIT = 200
_MAX_BUYER_LIMIT = 200
```

즉 `_MAX_BUYER_LIMIT=200`은 원래부터 존재했고, 야간 수정의 핵심은 **기본값 60 → 200**이다.

## 검수 목표

먼저 실제 Root Cause를 명확하게 기록한다.

확인 흐름:

```text
HTTP endpoint
→ endpoint 기본 limit
→ get_demo_buyers/get_demo_snapshot
→ _DEFAULT_BUYER_LIMIT
→ _MAX_BUYER_LIMIT
→ _build_buyers
→ dedupe
→ 최종 response
```

## 판정

다음이 사실이면 현재 최소 수정은 허용 가능하다.

```text
- 60건 제한의 직접 원인이 default limit 60
- max 200은 기존부터 의도적으로 존재
- explicit limit 파라미터 계약은 유지
- 1~200 범위 validation 유지
- 200건 초과 무제한 반환을 요구하는 endpoint가 아님
- 공개 demo endpoint의 안전한 sample cap이라는 기존 목적과 일치
```

이 경우 단순히 `60→200`이라는 이유로 다시 뜯지 말고 Root Cause와 API 계약을 테스트로 고정한다.

반대로 `demo/buyers`가 실제 전체 바이어 조회 기능이고 200 cap도 근거 없는 제한이라면 임의로 500/1000/무제한으로 바꾸지 말고 BLOCKED 처리하고 근거를 보고한다.

## 필수 테스트

```text
기본 호출 → 의도된 기본 건수
explicit limit=1
explicit limit=60
explicit limit=200
limit>200 → 기존 정책대로 clamp/reject 확인
빈 결과
dedupe 유지
민감 연락처 plaintext 비노출
기존 demo endpoint regression
```

`_MAX_BUYER_LIMIT=200`을 임의 제거하지 않는다.

---

# 8. CV-03 재검수

대상:

```text
night/cv03-company-verification-ui
```

CV-03은 CV-02의 API 계약이 확정된 뒤에만 최종 승인한다.

확인:

```text
CompanyBasicVerificationCard
기존 바이어명 자동입력
기존 국가 자동입력
POST /v1/company-verifications
GET 필요 시 현재 사용자 결과만 조회
상태 5종 표시
빈값
로딩
결과없음
API 오류
provider timeout
D&B 외부 공식 링크
K-SURE 외부 공식 링크
```

금지:

```text
신용등급처럼 보이는 자체 점수
안전점수
지급능력 판정
가짜 기업정보
임의 검증결과
contactStatus/tradeStatus/creditStatus와 registryCheckStatus 혼합
```

CV-02 수정으로 response contract가 바뀌면 CV-03을 그 계약에 최소 동기화한다.

새 전역 Router/Page 생성 금지.

Frontend build만으로 충분하다고 보지 말고 가능한 관련 unit/static test를 추가 또는 실행한다.

---

# 9. CV-05 검수

대상:

```text
night/cv05-prd-correction
```

변경 대상 문서만 확인한다.

```text
docs/prd/PRD_C1_ksure_api.md
docs/prd/PRD_C3_dnb_api.md
```

확인:

- 검증되지 않은 API 연동 가정 제거
- 자동 신용등급 조회 가정 제거
- 현재 MVP는 공식 외부 조회 링크로 한정
- 실제 API 연동은 계약/비용/저장/표시/재이용 권한 확인 후 별도 진행
- 코드 기능 범위를 문서가 과장하지 않음

문서 외 코드 변경이 있으면 이유를 확인하고 불필요하면 제거한다.

---

# 10. CODE-SPLIT / CSS-PASS3 처리

다음 브랜치는 이번 작업에서 병합하지 않는다.

```text
night/page-code-splitting
night/css-deslop-pass3
```

이유:

```text
CODE-SPLIT: main과 identical
CSS-PASS3: main compare 기준 실질 변경 파일 없음
```

따라서 merge commit을 만들어 이력을 더럽히지 않는다.

브랜치 삭제도 하지 않는다.

최종 보고에:

```text
NO_MERGE_ALREADY_PRESENT
```

또는 적절한 동일 의미 상태로 표시한다.

---

# 11. 브랜치별 수정 및 재테스트

main 병합 전에 필요한 수정은 **각 기존 night 브랜치에서** 수행한다.

새로운 중복 night 브랜치를 만들지 않는다.

## CV-02

```text
night/cv02-opencorporates-mock
```

수정 → 관련 테스트 → backend 전체 pytest → commit → push.

## BUYER-60

```text
night/buyer-60-limit
```

재검수 후 수정이 필요하면 최소 수정 → 관련 테스트 → backend regression → commit → push.

수정이 필요 없으면 새 empty commit을 만들지 않는다.

## CV-03

CV-02 최종 API 계약에 맞춰 수정 필요 시:

```text
night/cv03-company-verification-ui
```

에서 최소 수정 → build/test → commit → push.

## CV-05

문제 없으면 추가 수정 없이 기존 commit을 그대로 사용한다.

---

# 12. 병합 Gate

다음 조건을 모두 만족한 브랜치만 main 병합 후보가 된다.

```text
검수 PASS
관련 테스트 PASS
전체 regression PASS 또는 해당 작업에서 요구한 회귀 PASS
원격 branch push 완료
BLOCKER 없음
```

하나라도 실패하면 해당 브랜치는 main에 병합하지 않는다.

다른 독립 브랜치는 계속 검수 가능하되, 의존성이 있는 CV-03은 CV-02 실패 시 병합하지 않는다.

---

# 13. 권장 병합 순서

검수 통과 시 아래 순서로 main에 병합한다.

```text
1. CV-05
2. BUYER-60
3. CV-02
4. CV-03
```

브랜치:

```text
1. night/cv05-prd-correction
2. night/buyer-60-limit
3. night/cv02-opencorporates-mock
4. night/cv03-company-verification-ui
```

## 이유

```text
문서
→ 독립 버그수정
→ Backend 기능
→ Backend 의존 Frontend
```

의 순서로 충돌과 의존성을 최소화한다.

---

# 14. main.py 충돌 처리

다음 두 브랜치가 모두 `services/p1-export-fit-api/main.py`를 수정한다.

```text
BUYER-60
CV-02
```

따라서 충돌 가능성이 있다.

충돌 시 어느 한쪽 파일을 통째로 선택하지 않는다.

최종 main에는 양쪽 의도가 모두 남아야 한다.

예:

```text
BUYER-60의 demo buyers limit 계약
+
CV-02의 company verification router 등록
```

충돌 해결 후 최소 다음을 다시 확인한다.

```text
기존 demo endpoint 정상
company verification endpoint 등록 정상
기존 router 누락 없음
앱 import/startup 오류 없음
```

---

# 15. 각 merge 후 검증

각 merge 직후 최소 smoke 검증을 한다.

## CV-05 후

- 문서 diff 확인
- 코드 파일 변화 없음 확인

## BUYER-60 후

- demo buyer 관련 테스트
- backend regression

## CV-02 후

- company verification 테스트
- cross-user isolation
- provider error/timeout/no-result
- DB 저장
- backend regression

## CV-03 후

- frontend 관련 test
- lint 가능 시 실행
- `npm run build`
- 기존 BuyerSearch 회귀

merge 실패/충돌 미해결/테스트 실패 상태에서 다음 merge로 넘어가지 않는다.

---

# 16. CV-04 통합검증

4개 병합이 모두 성공한 경우 main에서 CV-04를 수행한다.

CV-04는 신규 기능을 크게 추가하는 작업이 아니라 **통합 테스트·회귀검증 보강**이다.

## Backend

실행:

```text
services/p1-export-fit-api 전체 pytest
```

완료 기준:

```text
0 failed
```

## Frontend

가능한 현재 프로젝트 명령을 확인해 실행한다.

최소:

```text
unit test (존재 시)
lint
npm run build
```

없는 script를 억지로 만들지 않는다.

## E2E 핵심 흐름

가능한 기존 테스트 인프라에서:

```text
로그인
→ 바이어 검색
→ 바이어 상세
→ 기본검증 요청
→ 결과 표시
```

을 검증한다.

## 보안/정확성

반드시 확인:

```text
무인증 company verification 호출 차단
다른 사용자 verification 조회 차단
신용점수 미생성
안전점수 미생성
지급능력 임의 판정 없음
임의 기업 데이터 없음
registryCheckStatus와 기존 creditStatus 혼합 없음
```

## 예외상태

```text
빈 company_name
잘못된 ISO3
결과없음
provider error
provider timeout
DB 오류
404 verification
frontend loading
frontend empty
frontend error
```

## CV-04 완료 조건

모두 실제로 검증된 경우에만 DONE.

실행하지 못한 E2E가 있으면 `NOT RUN`으로 기록하고, 해당 항목이 CV-04 완료 필수조건이면 CV-04를 BLOCKED로 둔다.

---

# 17. TASKS.md 정리

모든 검수/병합 결과가 결정된 후 `TASKS.md`를 실제 상태에 맞게 업데이트한다.

임의로 미완료 작업을 `[x]` 처리하지 않는다.

원칙:

```text
CV-01: 실제 main에 migration 기반이 정상 존재하고 검증됐으면 [x]
CV-02: 수정+병합+검증 완료 시 [x]
CV-03: 병합+frontend 검증 완료 시 [x]
CV-04: 통합검증 완료 시 [x]
CV-05: 문서 병합 완료 시 [x]
```

실패/BLOCKED면 `[ ]` 유지하고 바로 아래에 blocker를 짧게 기록한다.

기존 TASKS.md 구조를 최대한 유지한다.

개발현황 시트 동기화 규칙이 있지만 현재 실행환경에서 외부 시트 접근이 불가능하면 거짓으로 완료 처리하지 말고:

```text
SHEET_SYNC: NOT RUN — 접근수단 없음
```

처럼 최종 보고한다.

---

# 18. 절대 금지

이번 TASK에서 다음은 하지 않는다.

```text
Campaign Orchestrator 신규 구현
Matching & Slot 신규 구현
Credit Ledger 신규 구현
Send Adapter
실제 이메일 발송
실제 OpenCorporates API 호출
실제 D&B API 연동
실제 K-SURE API 연동
새 결제 기능
CSS 추가정리
추가 code splitting
unrelated 리팩터링
DB 0001~0004 수정
가짜 바이어 추가
합성/랜덤 신뢰지표 추가
```

CV-04 이후 다음 제품 기능으로 자동 진행하지 않는다.

---

# 19. 최종 보고 형식

반드시 아래 형식으로 한 번에 보고한다.

```text
[BASELINE]
origin/main before: <sha>
origin/main after: <sha>

[CV-02 REVIEW]
STATUS: PASS / FIXED / BLOCKED
ENUM: ...
USER ISOLATION: ...
ERROR/TIMEOUT/NO-RESULT: ...
POSTGRESQL: PASS / FAIL / NOT RUN
TEST: ...
BRANCH: ...
COMMIT: ...
PUSH: ...

[BUYER-60 REVIEW]
STATUS: PASS / FIXED / BLOCKED
ROOT CAUSE: ...
DEFAULT LIMIT: ...
MAX LIMIT: ...
EXPLICIT LIMIT: ...
TEST: ...
BRANCH: ...
COMMIT: ...
PUSH: ...

[CV-03 REVIEW]
STATUS: PASS / FIXED / BLOCKED
API CONTRACT MATCH: ...
UI STATES: ...
TEST/BUILD: ...
BRANCH: ...
COMMIT: ...
PUSH: ...

[CV-05 REVIEW]
STATUS: PASS / FIXED / BLOCKED
DOCS: ...
BRANCH: ...
COMMIT: ...
PUSH: ...

[NO-MERGE]
page-code-splitting: NO_MERGE_ALREADY_PRESENT
css-deslop-pass3: NO_MERGE_NO_FILE_DIFF

[MERGE]
CV-05: MERGED / SKIPPED / BLOCKED
BUYER-60: MERGED / SKIPPED / BLOCKED
CV-02: MERGED / SKIPPED / BLOCKED
CV-03: MERGED / SKIPPED / BLOCKED
CONFLICTS: ...

[CV-04]
backend pytest: ...
frontend unit: ...
lint: ...
build: ...
E2E: ...
auth isolation: ...
STATUS: DONE / BLOCKED

[TASKS]
CV-01: [x]/[ ]
CV-02: [x]/[ ]
CV-03: [x]/[ ]
CV-04: [x]/[ ]
CV-05: [x]/[ ]
SHEET_SYNC: DONE / NOT RUN / BLOCKED

[FINAL]
main clean: YES/NO
remaining blockers: ...
next recommended task: 1개만 제안
```

---

# 20. 최종 실행 지시

**원격 main 최신화 후 이 `TASK.md`를 처음부터 끝까지 읽고 그대로 수행한다. CV-02와 BUYER-60을 먼저 재검수·필요 시 기존 night 브랜치에서 최소 수정한 뒤, 통과한 브랜치만 `CV-05 → BUYER-60 → CV-02 → CV-03` 순서로 main에 병합한다. CODE-SPLIT/CSS-PASS3는 병합하지 않는다. 병합 후 CV-04 통합검증과 TASKS.md 정리까지 수행하고 결과를 한 번에 보고한 뒤 멈춘다. 실패한 작업은 억지로 병합하지 말고 BLOCKED로 남긴다.**