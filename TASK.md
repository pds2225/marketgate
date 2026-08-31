# marketgate

> 이 파일은 이 GitHub 레포의 유일한 AI 작업지시 기준이다.
> Google Tasks와는 완전히 별개이며 Google Tasks의 항목을 조회·복사·동기화하지 않는다.

---

# 0. TASK LIST

<!--
비개발자가 이 부분만 보고도 현재 작업을 이해·수정·삭제할 수 있어야 한다.
상태: 대기 / 진행 중 / 완료 / 막힘 / 취소 는 아래 기호만 사용한다.
TASK 1개 = 반드시 1줄. LIST의 TASK_ID와 DETAILS의 TASK_ID는 반드시 1:1.
사용자가 "삭제"하면 LIST + DETAILS 모두 삭제. "취소"하면 취소 상태로 보존 가능.
REQUEST_SOLVED=YES가 아닌 작업은 완료 표시 금지.
-->

[x] MG-001 | 해외기업 기본검증 상태값을 맞추고 다른 사용자 결과가 보이지 않게 한다
[x] MG-002 | 바이어가 60개까지만 보이는 원인을 찾아 고친다
[x] MG-003 | 기업검증 화면을 실제 조회 결과와 연결한다
[!] MG-004 | 로그인부터 기업검증까지 실제 사용 흐름으로 확인한다
[x] MG-005 | 랜딩에서 입력한 HS로 구매신호를 바로 보게 한다
[ ] MG-006 | 연락처가 실제 수신자 소유인지 확인하는 절차를 만든다
[ ] MG-007 | 인콰이어리를 고객이 제출한 뒤 실제 발송까지 이어지게 한다
[ ] MG-008 | P2 바이어 소스를 CSV로 넣어 실제 검색에 쓰이게 한다
[x] T-20260814-01 | 코드 머지 전에 제품 테스트가 통과해야 한다


---

# 1. REPOSITORY

REPO: pds2225/marketgate
BASE: main
REMOTE: https://github.com/pds2225/marketgate

## 작업지시 파일

실행 기준은 이 파일 하나뿐이다.

- `TASK.md`만 작업지시 파일로 사용한다.
- `NEXT_TASK.md`는 없다. 실행 기준은 TASK.md만.
- 별도의 CURRENT_TASK.md / NEW_TASK.md / NEXT_TASK.md를 만들지 않는다.
- 다른 레포 TASK, Google Tasks, 과거 채팅 내용을 임의 실행하지 않는다.
- 사용자의 새 요청은 이 TASK.md에 새로운 TASK 항목으로 등록한다.

---

# 2. GOOGLE TASKS 완전 분리

Google Tasks는 이 개발 TASK 시스템과 무관하다.

금지:

- Google Tasks 조회
- Google Tasks 항목 가져오기
- Google Tasks → TASK.md 자동등록
- TASK.md → Google Tasks 등록
- 상태/제목/완료 여부 동기화
- Google Tasks 내용을 개발 우선순위 판단에 사용

---

# 3. GIT 안전 동기화

원칙: 작업은 로컬에서 한다. 기준과 병합은 원격이다.
로컬이 원격보다 **앞서기만** 하면(갈라지지 않음) 막지 않는다. 커밋된 내용을 **push한 뒤 원격에서 머지**해서 로컬=원격을 맞춘다.

작업 시작 전 반드시:

1. `git fetch --all --prune`
2. `git remote get-url origin` — 이 파일 `# 1. REPOSITORY`의 REPO와 일치하는지 확인
3. `git branch --show-current`
4. `git status --short`
5. ahead / behind / diverged 확인:

`git rev-list --left-right --count HEAD...origin/main`

왼쪽 숫자 = 로컬이 앞선 커밋(ahead). 오른쪽 = 로컬이 뒤처진 커밋(behind).
둘 다 0보다 크면 diverged(갈라짐). 둘 다 0이면 동기화됨.

쉬운 말:

- 나만 앞이면 → 올려서 맞춘다. 막지 않는다.
- 나만 뒤면 → 받아서 맞춘다.
- 서로 갈라졌으면 → 강제로 덮지 말고 합친다. 못 합치면 멈춘다.
- 저장 안 한 수정이 있으면 → 지우지 않는다.
- 남이 같은 브랜치에 올렸으면 → 덮어쓰지 말고 먼저 받고 합친다.

## 판정 (fetch 후, AI가 그대로 실행)

`<BASE>`는 `# 1. REPOSITORY`의 BASE다. 이 레포는 `main`.

동기화됨(ahead=0, behind=0, clean)이면 그대로 작업을 시작한다.

### 1. behind only

조건: 현재 브랜치가 BASE, working tree clean, ahead=0, behind>0.

실행: `git merge --ff-only origin/main`

실패하면 `BLOCKED`. `reset --hard`로 맞추지 않는다.

### 2. ahead only

조건: ahead>0, behind=0 (diverged 아님). **ahead only는 BLOCKED가 아니다.**

실행:

1. 미커밋 변경이 있으면 **이번 작업 파일만** 커밋한다. `git add -A` 금지. 사용자 쓰레기 파일을 올리지 않는다.
2. `git push` (force 금지).
3. 현재가 작업 브랜치면 PR을 만든다. 충돌 없음 + GitHub Checks 초록일 때만 머지한다. 실패 체크를 무시하는 `gh pr merge --admin`은 금지한다.
4. 이미 BASE면 push로 원격을 로컬에 맞춘다. 보호 규칙으로 push가 거절되면 PR로 올린다.
5. 이후 `git fetch`로 로컬=원격을 확인한다.

### 3. diverged

조건: ahead>0 그리고 behind>0. 양쪽이 다 앞선 상태다.

force push 금지.

`git fetch` 후 안전하게 합칠 수 있으면 합친다 (`git merge origin/<현재브랜치>` 또는 해당 원격 브랜치). 충돌을 무조건 ours/theirs로 해결하지 않는다.

합친 뒤 `git push` (force 금지).

안전하게 합칠 수 없으면 `BLOCKED`.

### 4. dirty uncommitted

사용자 변경 삭제 금지. `git reset --hard` / `git clean -fd` / stash drop 금지.

선택:

- 이번 작업 파일이면 커밋한 뒤 **2. ahead only** 경로로 간다.
- 이번 작업이 아니거나 BASE를 더럽히면, 별도 worktree에서 `origin/main` 최신으로 작업한다.

안전하게 분리하지 못하면 `BLOCKED`.

### 5. 남이 같은 브랜치에 올린 뒤

로컬 push 전에 다시 `git fetch`.

behind가 생겼으면 force로 덮지 말고 먼저 받고 합친다. 그다음 push.

## 절대 금지

- `git reset --hard`
- force push (`--force`, `--force-with-lease` 포함)
- `git clean -fd`
- 사용자 변경 삭제
- 임의 stash/drop
- 충돌을 무조건 ours/theirs로 해결
- 로컬 파일을 원격 상태에 강제로 덮어쓰기
- `git add -A`

---

# 4. TASK 실행 계약 고정 — TASK PINNING

AI가 TASK를 시작할 때 반드시 아래 값을 기록한다.

TASK_ID: <현재 [~] TASK ID>
TASK_START_SHA: <작업 시작 시 origin/base commit SHA>
TASK_BLOB_SHA: <그 시점 TASK.md blob SHA>
WORK_BRANCH: <task/TASK-ID 등>

## 목적

작업 도중 `TASK.md`가 새 요청으로 변경되더라도,
이미 시작한 일반 TASK는 최초 실행 계약을 기준으로 완료한다.

필요하면 최초 TASK는:

`git show <TASK_START_SHA>:TASK.md`

로 다시 확인한다.

## 작업 중 TASK.md 변경 감지

새 TASK가 일반적인 후속 요청:

- 현재 ACTIVE TASK에 섞지 않는다.
- 현재 TASK를 최초 TASK_ID 기준으로 계속 수행한다.
- 새 TASK는 다음 실행에서 수행한다.

새 TASK가 아래에 해당:

- STOP
- CANCEL
- 기존 작업 즉시 중단 요청
- 보안 긴급지시
- 데이터 손실 방지 지시

→ 현재 TASK를 즉시 중단하고 상태를 기록한다.

---

# 5. TASK 선택 규칙

기본적으로 `[~]` 상태의 TASK 1개를 ACTIVE TASK로 실행한다.

`[~]`가 없으면 실행 가능한 `[ ]` TASK 중 우선순위가 가장 높은 작업을 선택한다.

## TASK 상태

- `[ ]` READY / 대기
- `[~]` ACTIVE / 진행 중
- `[x]` DONE / 실제 요청 해결 완료
- `[!]` BLOCKED / 현재 진행 불가능
- `[-]` CANCELLED / 사용자 취소

## 동시에 ACTIVE

같은 파일·API·DB·entrypoint를 수정하지 않는 독립 작업만 여러 `[~]` 허용.

---

# 6. TASK 우선순위

상충 시 아래 순서로 판단한다.

1. 데이터 손실 방지 / 보안 / Git 안전규칙
2. 가장 최신 사용자의 명시적 요청
3. 현재 ACTIVE TASK
4. ACTIVE TASK 수행에 필수인 선행조건
5. repo의 필수 보호규칙 / architecture contract
6. 기존 대기 TASK
7. backlog
8. 리팩터링 / 고도화 / 미관 개선

판단할 수 없는 충돌은 임의 선택하지 않는다.

→ `BLOCKED`

---

# 7. TASK 간 충돌·의존성

## 병렬 가능

다음을 모두 만족하면 병렬 가능:

- 수정 파일군이 다름
- 같은 public API를 변경하지 않음
- 같은 DB schema/migration을 변경하지 않음
- 같은 runtime entrypoint를 변경하지 않음
- TASK A 결과가 TASK B의 입력이 아님

## 순차 필수

하나라도 해당하면 순차:

- 같은 파일 수정
- 같은 API contract 변경
- 같은 DB migration 변경
- 같은 entrypoint 변경
- 한 TASK가 다른 TASK의 선행조건

순차 예:

TASK-A
→ 실사용 검증
→ 최신 코드 기준 TASK-B
→ 통합 E2E

---

# 8. TASK DETAILS

<!--
TASK LIST 한 줄 요약과 아래 상세 TASK는 TASK_ID로 연결한다.
새 사용자 요청을 TASK로 만들 때 반드시 MUST / KEEP / REMOVE / FORBIDDEN / VERIFY / DONE 관점으로 변환한다.
MG-003은 MG-001 API 계약 이후. MG-004는 선별병합 후 통합 E2E.
NEXT_TASK.md 이관(2026-08-13): A→MG-001, B→MG-003, C→MG-003(CV-05), D→MG-002. E/F(code-split/css)는 빈 브랜치라 LIST 미등록. ACTIVE(MG-001)에 내용 합치지 않음. 파일 삭제.
-->

## T-20260814-01

### 8-1. 사용자 원문
marketgate main: required에 제품 test job 추가 (docs-gate만 두지 말 것). 존재하는 job 이름만. mail 건드리지 마. MAIL-002 금지. --admin 금지.

### 최종 결과
marketgate main 머지에 docs-gate뿐 아니라 제품 테스트 job이 필수라서, 코드 테스트가 실패하면 머지되지 않는다.

### MUST
- 기존 CI에 실제로 있는 job 이름만 required에 넣는다
- docs-gate는 유지한다
- docs-gate.yml을 “코드인데 테스트 없으면 fail”로 바꾸지 않는다

### KEEP
- 기존 MG-001~MG-004 과업 내용은 합치지 않는다
- mail은 건드리지 않는다

### REMOVE
- required가 docs-gate만인 상태

### FORBIDDEN
- .env / 비밀값
- 없는 job 이름 만들기
- `gh pr merge --admin`
- mail / MAIL-002

### VERIFY
- required contexts에 docs-gate와 `W-020 / PostgreSQL 16 + pgcrypto`가 함께 있다
- enforce_admins=true, allow_force_pushes=false

### DONE
- REQUEST_SOLVED=YES: 코드 PR은 제품 테스트 job이 실패하면 머지 불가

### 8-4. 현재상태 (ALREADY_DONE 검증 2026-08-17)
- TASK_START_SHA: fa62050
- WORK_BRANCH: task/T-20260814-01
- CI: `.github/workflows/postgresql16-vault-ci.yml` job name `W-020 / PostgreSQL 16 + pgcrypto` (bd8f8c0에서 전 PR 실행)
- Branch protection (`GET /branches/main`): required contexts = `docs-gate`, `W-020 / PostgreSQL 16 + pgcrypto`; `enforcement_level=everyone`
- PR #121 status checks에 두 job 모두 SUCCESS 후 머지됨
- `allow_force_pushes` 상세 API는 integration 토큰 403으로 직접 읽지 못함. required status의 enforcement_level=everyone으로 admin bypass 없는 상태 확인
- REQUEST_SOLVED=YES


## MG-001

### 8-1. 사용자 원문 요청

> 해외기업 기본검증 상태값을 DB·API에서 동일하게 맞추고, 다른 사용자의 검증 결과가 보이지 않게 한다.

확인된 CV-02 BLOCKER (원문 보존):

1. `0005_company_registry_checks.sql` ENUM이 구형 값(`VERIFIED/PARTIAL_MATCH/MISMATCH/INACTIVE/...`)으로 API 계약과 불일치.
2. GET 조회가 `check_id`만 사용하여 `user_id` 격리가 되지 않음.

확정 상태값은 아래 5개만 허용:

```text
BASIC_CONFIRMED
BASIC_PARTIAL
DATA_MISMATCH
INACTIVE_ENTITY
CREDIT_CHECK_REQUIRED
```

원문의 의미를 축약 과정에서 변경하지 않는다.

### 8-2. 비개발자용 1줄 요약

해외기업 기본검증 상태값을 맞추고 다른 사용자 결과가 보이지 않게 한다

이 문장이 상단 TASK LIST에 그대로 표시된다.

### 8-3. 사용자가 원하는 최종 결과

사용자가 실제로 사용했을 때:

- 기본검증 상태가 DB·API·화면에서 같은 5개 값만 사용됨
- 로그인한 사용자는 자기 검증 결과만 볼 수 있음
- 다른 사용자 ID는 정보 노출 없이 404

이 결과가 달성되지 않으면 DONE이 아니다.

### 8-4. 현재상태

- ALREADY_DONE 검증 2026-08-17 (TASK_START_SHA 3c20abf, WORK_BRANCH task/MG-001)
- main에 `0006_company_registry_checks.sql` ENUM 5값 + GET `user_id` 격리 반영됨 (#119)
- 실 PostgreSQL 16에서 0001~0006 적용·0006 재실행 idempotent 확인
- 실 DB E2E: owner GET 200 / other user GET 404(본문 미노출) / country_iso3 정규화
- DB unavailable → POST 503 `verification_store_unavailable` 최소 보완
- REQUEST_SOLVED=YES

문서의 DONE 표시만 믿지 말고 실제 코드/runtime을 확인한다.

### 8-5. MUST — 반드시 구현

- [x] DB enum을 확정 5개 값으로 통일
- [x] API/store/test fixture 상태값도 동일 계약 사용
- [x] `GET /v1/company-verifications/{verification_id}`는 현재 로그인 사용자 소유 record만 조회 (`user_id` 조건)
- [x] 타 사용자 ID는 정보 노출 없이 404
- [x] POST/GET 인증 유지
- [x] 결과없음/provider 오류/timeout/DB 오류 등 기존 요구가 구현됐는지 확인하고 누락만 최소 보완
- [x] 실제 PostgreSQL에서 0005 적용/재실행 정책 검증

### 8-6. KEEP — 유지

- [ ] 기존 0001~0004 migration
- [ ] POST/GET 인증
- [ ] 기존 buyer 검색·상세 흐름
- [ ] 사용자가 변경 요청하지 않은 기존 동작

### 8-7. REMOVE — 제거

- [ ] 구형 ENUM 값(`VERIFIED/PARTIAL_MATCH/MISMATCH/INACTIVE/...`)을 계약에서 제거

### 8-8. FORBIDDEN — 금지

- 사용자 요청에 없는 기능 임의 추가 금지
- 불필요한 대규모 리팩터링 금지
- 관련 없는 DB/API/UI 변경 금지
- 테스트를 통과시키기 위한 기능 삭제 금지
- 기존 실패 테스트 skip 금지
- 근거 없는 값/데이터 생성 금지

TASK별 추가 금지사항:

- 실제 OpenCorporates/D&B/K-SURE 유료·계약 API 호출
- 신용점수/안전점수/지급능력 점수 생성
- 기존 0001~0004 migration 임의 수정

### 8-9. 선행조건·의존성

DEPENDS_ON:

- NONE

### 8-10. 구현범위

수정 가능 범위:

- company verification API/store
- `0005_company_registry_checks.sql` enum
- 관련 test fixture
- 사용자 격리 조회

기존 구조를 최대한 유지하고 최소 변경한다.

검수 대상 브랜치: `night/cv02-opencorporates-mock` (`cbb049e`)

### 8-11. 입력검증

반드시 확인:

- company_name 공백 금지
- country ISO3 3자리 검증·정규화
- verification_id 형식/존재 여부
- 모든 조회에서 현재 user 소유권
- 정상 입력 / 필수값 없음 / 잘못된 형식 / 허용범위 밖 값 / 중복 입력 / 비정상 문자열

해당되지 않는 항목은 N/A 근거를 남긴다.

### 8-12. 빈상태

검증:

- registry 결과 없음 → `확인 결과 없음` 계열 명시 상태
- 빈 결과를 임의 점수/추정값으로 채우지 않는다
- 데이터 0건 / 결과 없음 / 일부 필드 없음 / 최초 사용 상태

### 8-13. 로딩상태

- 기본검증 요청 중 중복 제출 방지
- 비동기 처리/UI 작업인 경우 처리 중 상태, 완료 후 전환, 오래 걸릴 때 기존 화면 손상 방지

### 8-14. 오류상태

필요한 경우:

- 400/404/401·403/500/502/504를 구분
- provider timeout과 내부 DB 오류를 같은 성공/빈값으로 처리하지 않는다
- 외부 API 실패 / DB 실패 / timeout / 네트워크 실패 / 일부 데이터 실패 / 권한 오류 / 잘못된 요청 / 재시도 가능 상태

---

## MG-002

### 8-1. 사용자 원문 요청

> 바이어가 60개까지만 보이는 원인을 찾아 정상화한다.

원문 보존:

- main: `_DEFAULT_BUYER_LIMIT = 60`, `_MAX_BUYER_LIMIT = 200`
- night branch는 기본값을 200으로 올림
- 단순 숫자 변경이 아니라 60 제한의 실제 원인/의도가 demo sample limit인지 실제 검색 제한인지 확인해야 함

원문의 의미를 축약 과정에서 변경하지 않는다.

### 8-2. 비개발자용 1줄 요약

바이어가 60개까지만 보이는 원인을 찾아 고친다

이 문장이 상단 TASK LIST에 그대로 표시된다.

### 8-3. 사용자가 원하는 최종 결과

사용자가 실제로 사용했을 때:

- 60개 제한의 실제 원인이 기록됨
- demo 샘플 수 제한과 실제 검색 제한을 혼동하지 않음
- 제품 의도에 맞게 검색 결과가 보이며, 단순 `60 → 200` 하드코딩만으로 끝난 것처럼 처리하지 않음

이 결과가 달성되지 않으면 DONE이 아니다.

### 8-4. 현재상태

- DONE 검증 2026-08-17 (TASK_START_SHA b055f70, WORK_BRANCH task/MG-002)
- 원인: 공개 데모 `/v1/demo/snapshot|buyers`의 `_DEFAULT_BUYER_LIMIT=60` (MAX는 이미 200). BuyerSearch `/v1/predict` top_n(≤10)과는 무관.
- #118에서 demo default를 200으로 올림. 본 작업에서 원인 기록 + regression 테스트로 demo/search 계약 분리 고정.
- REQUEST_SOLVED=YES

문서의 DONE 표시만 믿지 말고 실제 코드/runtime을 확인한다.

### 8-5. MUST — 반드시 구현

- [x] demo snapshot, API query, frontend caller를 추적하여 60개의 실제 원인을 기록
- [x] 공개 demo 샘플 수 제한과 실제 buyer 검색 결과 제한을 혼동하지 않는다
- [x] 제품 의도상 200이 맞으면 상수/기본값/호출 계약을 일관되게 수정하고 테스트
- [x] 단순 `60 → 200` 하드코딩만으로 root cause 해결 처리 금지

### 8-6. KEEP — 유지

- [ ] 기존 buyer 검색/상세 흐름
- [ ] demo snapshot API의 공개 샘플 의도가 별도라면 그 의도
- [ ] 사용자가 변경 요청하지 않은 기존 동작

### 8-7. REMOVE — 제거

없음 (원인 확인 후 잘못된 제한만 제거)

### 8-8. FORBIDDEN — 금지

- 사용자 요청에 없는 기능 임의 추가 금지
- 불필요한 대규모 리팩터링 금지
- 관련 없는 DB/API/UI 변경 금지
- 테스트를 통과시키기 위한 기능 삭제 금지
- 기존 실패 테스트 skip 금지
- 근거 없는 값/데이터 생성 금지

TASK별 추가 금지사항:

- 근거 없는 buyer/trade/import 수치 생성
- 단순 상수 변경만으로 DONE 처리

### 8-9. 선행조건·의존성

DEPENDS_ON:

- NONE

MG-001과 파일군이 겹치지 않으면 병렬 가능.

### 8-10. 구현범위

수정 가능 범위:

- buyer limit 상수/쿼리/프론트 호출 계약
- 관련 regression test

검수 대상 브랜치: `night/buyer-60-limit` (`2292305`)

기존 구조를 최대한 유지하고 최소 변경한다.

### 8-11. 입력검증

반드시 확인:

- 정상 입력 / 필수값 없음 / 잘못된 형식 / 허용범위 밖 값 / 중복 입력
- limit 호출이 demo와 실검색 중 어디에 적용되는지

해당되지 않는 항목은 N/A 근거를 남긴다.

### 8-12. 빈상태

검증:

- 검색 0건
- 일부 필드 없음
- buyer 정보/API에 없는 값 → `자료 내 확인 불가` 또는 기존 정책의 명시적 빈값

### 8-13. 로딩상태

BuyerSearch 기존 로딩 흐름을 깨지 않는다. 정적 기능이면 N/A 가능.

### 8-14. 오류상태

필요한 경우:

- 외부 API 실패 / DB 실패 / timeout / 잘못된 요청 / 재시도 가능 상태

오류가 없다는 사실 자체는 DONE 기준이 아니다.

---

## MG-003

### 8-1. 사용자 원문 요청

> 기업검증 화면을 실제 조회 결과와 연결한다.

원문 보존 (CV-03 UI + CV-05 문서):

- TRACK A API 계약이 확정된 뒤 검수/보완
- 기존 `BuyerSearch/index.tsx` 상세 흐름 안에 유지
- 새 Router/전역 페이지 금지
- `registryCheckStatus`를 `contactStatus/tradeStatus/creditStatus`와 혼합 금지
- K-SURE/D&B는 현재 MVP에서 공식 외부 조회 링크만 제공
- 검증되지 않은 API·신용등급 자동조회 가정 제거 여부 확인

원문의 의미를 축약 과정에서 변경하지 않는다.

### 8-2. 비개발자용 1줄 요약

기업검증 화면을 실제 조회 결과와 연결한다

이 문장이 상단 TASK LIST에 그대로 표시된다.

### 8-3. 사용자가 원하는 최종 결과

사용자가 실제로 사용했을 때:

- 바이어 상세에서 기본검증 결과가 실제 API와 연결됨
- D&B·K-SURE는 공식 외부 조회 링크로만 제공됨
- 신용등급 자동조회처럼 검증되지 않은 가정이 화면에 없음

이 결과가 달성되지 않으면 DONE이 아니다.

### 8-4. 현재상태

- DONE 검증 2026-08-19 (TASK_START_SHA 984e37c, WORK_BRANCH task/MG-003, PR #126)
- POST then owner-scoped GET `/v1/company-verifications/{id}` in BuyerSearch detail tab
- D-U-N-S lookup / K-Sight find-buyer / K-SURE 신청 (`ksure.or.kr`) only; no auto credit grade
- registry_check_status not mixed with contact/trade/credit; unknown enum → `확인 결과 없음`
- USER_E2E: Playwright CV-04 journey PASS on localhost:5173 (React local)
- REQUEST_SOLVED=YES

문서의 DONE 표시만 믿지 말고 실제 코드/runtime을 확인한다.

### 8-5. MUST — 반드시 구현

- [x] MG-001 API 계약이 확정된 뒤 UI 검수/보완
- [x] 기존 `BuyerSearch/index.tsx` 상세 흐름 안에 유지
- [x] 새 Router/전역 페이지 금지
- [x] `registryCheckStatus`를 `contactStatus/tradeStatus/creditStatus`와 혼합 금지
- [x] K-SURE/D&B는 공식 외부 조회 링크만 제공
- [x] 검증되지 않은 API·신용등급 자동조회 가정 제거 여부 확인

### 8-6. KEEP — 유지

- [ ] 기존 BuyerSearch 상세 흐름
- [ ] 기존 contact/trade/credit 상태
- [ ] 사용자가 변경 요청하지 않은 기존 동작

### 8-7. REMOVE — 제거

- [x] 검증되지 않은 API·신용등급 자동조회 가정 (확인 후)

### 8-8. FORBIDDEN — 금지

- 사용자 요청에 없는 기능 임의 추가 금지
- 불필요한 대규모 리팩터링 금지
- 관련 없는 DB/API/UI 변경 금지
- 테스트를 통과시키기 위한 기능 삭제 금지
- 기존 실패 테스트 skip 금지
- 근거 없는 값/데이터 생성 금지

TASK별 추가 금지사항:

- 실제 OpenCorporates/D&B/K-SURE 유료·계약 API 호출
- 신용점수 생성
- 새 Router/전역 페이지

### 8-9. 선행조건·의존성

DEPENDS_ON:

- MG-001

선행 TASK가 실제로 DONE이 아니면 후속 작업을 완료 처리하지 않는다.

### 8-10. 구현범위

수정 가능 범위:

- BuyerSearch 기업검증 UI
- CV-05 PRD/용어/외부 링크
- 관련 frontend unit/build

기존 구조를 최대한 유지하고 최소 변경한다.

### 8-11. 입력검증

반드시 확인:

- 정상 입력 / 필수값 없음 / 잘못된 형식
- verification_id / 사용자 소유권은 API 계약을 따름

해당되지 않는 항목은 N/A 근거를 남긴다.

### 8-12. 빈상태

검증:

- registry 결과 없음 → 명시 상태
- buyer 정보/API에 없는 값 → `자료 내 확인 불가` 또는 기존 정책
- 빈 결과를 임의 점수로 채우지 않는다

### 8-13. 로딩상태

- BuyerSearch 기존 로딩 흐름을 깨지 않고 verification loading을 분리
- 처리 중 상태, 중복 실행 방지, 완료 후 전환

### 8-14. 오류상태

필요한 경우:

- 화면은 재시도 가능 상태를 제공하고 기존 검색 결과를 날리지 않는다
- 400/404/401·403/500/502/504를 구분
- 외부 API 실패 / timeout / 권한 오류 / 잘못된 요청

---

## MG-004

### 8-1. 사용자 원문 요청

> 로그인부터 기업검증까지 실제 사용 흐름으로 확인하고, 통과한 야간 브랜치만 골라 합친다.

원문 보존 (선별병합 + CV-04):

권장 병합 순서:

```text
CV-05 → BUYER-60 → CV-02 → CV-03
```

각 브랜치는 merge 전 자체 테스트 통과 필수. `main.py` 충돌은 ours/theirs로 기계 처리하지 말고 양쪽 의도를 수동 합성 후 재테스트.

병합 후 main에서:

- DB migration
- Mock Adapter/API
- 로그인→바이어검색→상세→기본검증 E2E/smoke
- 사용자 격리
- 기존 buyer 검색
- 인증
- 결제/크레딧 회귀
- frontend unit/lint/build
- backend pytest

를 검증하고 `TASKS.md` CV 상태를 실제 결과에 맞게 갱신.

병합 불필요: `night/page-code-splitting`(main과 동일), `night/css-deslop-pass3`(실질 변경 없음)

원문의 의미를 축약 과정에서 변경하지 않는다.

### 8-2. 비개발자용 1줄 요약

로그인부터 기업검증까지 실제 사용 흐름으로 확인한다

이 문장이 상단 TASK LIST에 그대로 표시된다.

### 8-3. 사용자가 원하는 최종 결과

사용자가 실제로 사용했을 때:

- 로그인 → 바이어 검색 → 상세 → 기본검증이 실제로 동작
- 통과한 브랜치만 main에 합쳐짐
- 기존 검색·인증·결제가 깨지지 않음

이 결과가 달성되지 않으면 DONE이 아니다.

### 8-4. 현재상태

- TASK_START_SHA c75de1a → live re-verify 2026-08-29 (cloud). WORK_BRANCH cursor/mg-004-skip-backup-preview-fe9c (PR #131 MERGED)
- Vercel Hobby 한도: GitHub commit status on aea06df at 2026-08-29T07:42:23Z `Deployment rate limited — retry in 24 hours` (code api-deployments-free-per-day). Literal +24h would be 2026-08-30 16:42 KST. Actual rolling 86400s window reopened earlier: walk production deploy ~16:54Z, marketgate production `dpl_EuUHKv9w6ZyK2XHAjwei4qE9donD` READY 2026-08-29T17:01:44Z = **2026-08-30 02:01:44 KST**
- Production https://marketgate.vercel.app **now serves 0969cc** (aea06df + #131 backup-preview skip). Previous production was 4bd8f99 (#129)
- #131: `git.deploymentEnabled` / ignoreCommand skips `backup/WIN-K20QOC29TOB` (branch not deleted, no force-push)
- Render FastAPI `https://marketgate.onrender.com` snapshot head **a887da8 (2026-07-28)**, 150 commits behind origin/main. No `/v1/company-verifications`, no #130 warmup. `autoDeploy: true` in render.yaml is not rolling this service
- USER_E2E on marketgate.vercel.app (2026-08-29 17:13–17:41Z):
  - 로그인/회원가입: PASS (로그아웃·100C 확인)
  - HS 330499 검색: PASS — 국가 후보 리스트(미국, 바이어 5) / 첫 요청 구프록시 110s→502, 0969cc 이후 predict 200 in ~174s then ~150s
  - 바이어 상세: PASS — Beauti Control Csmtcs Inc. BUYER DETAIL REPORT
  - 기업검증: FAIL — 탭·D-U-N-S/K-SURE 공식 링크는 있음. POST `/api/v1/company-verifications` 404 `Not Found`. UI `검증 실패 / 검증 결과를 찾을 수 없습니다`. BASIC_* 미표시
- REQUEST_SOLVED=NO until Render production API is on main (or later) and 기업검증 shows BASIC_* (or API statuses) with official lookup links

- **2026-08-31 재진단 (background 세션):**
  - PR #133 (`fix/frontend-hooks-lint`) MERGED → main `1591f6b`. 로컬 검증: backend `pytest` 248 pass / 1 skip, frontend `npm run build` ✓. (`npm run lint` 에 `react-refresh/only-export-components` 2건 — `ComparePage.jsx`/`demo.jsx`, #133 이전부터 존재하는 기존 부채이고 CI 게이트 아님)
  - main 코드에 `POST /v1/company-verifications` 라우터 정상 존재 (`app/routers/company_verification.py`, `main.py` include_router). 빌드/임포트 이상 없음 — 배포만 되면 동작할 상태
  - **Render 두 서비스 모두 미배포.** `marketgate.onrender.com`(prod)·`marketgate-e2e.onrender.com`(e2e) 의 openapi 경로 차이는 `/v1/e2e/*` 뿐 → 둘 다 동일 코드(a887da8, 2026-07-28)에서 멈춤. e2e 서비스에도 CV-02 없음
  - a887da8 이후 backend 커밋 40개가 하나도 롤아웃 안 됨. GitHub commit status 에 Render 항목이 전혀 없음 (`2cf80f8`·`4f5dc77` "재배포 트리거" 커밋 포함 전부 Vercel status 만 존재) → **Render→GitHub auto-deploy 연결이 2026-07-28 즈음부터 끊김/비활성**. `render.yaml` 의 `autoDeploy: true` 는 대시보드에서 만든 서비스에는 무효
  - main push (`1591f6b`, 11:34Z) 후 ~15분 폴링 → prod openapi 40 경로 불변. push-to-main 으로는 안 깨어남
  - migration 리스크 낮음: `app/run_migrations.py` 는 `DATABASE_URL` 미설정 시 skip, 그 외 예외도 WARN 만 (빌드 실패 안 시킴)
  - **남은 유일 차단 — Render 대시보드 수동 조치 (이 세션엔 Render API key/CLI/deploy hook/브라우저 확장 전부 없음):**
    1. Render Dashboard → `marketgate` 서비스 → Settings → Build & Deploy → Auto-Deploy = **Yes**, Branch = `main` 확인/복구
    2. Manual Deploy → **Deploy latest commit** (`1591f6b`) 1회 실행. `marketgate-e2e` 서비스도 동일하게
    3. 빌드 후: `curl -s https://marketgate.onrender.com/openapi.json | grep company-verifications` → 존재 확인
    4. 기업검증 E2E 재수행: 로그인 → HS 검색 → 바이어 상세 → 기업검증 탭 BASIC_* 표시 확인 후 MG-004 `[x]`

문서의 DONE 표시만 믿지 말고 실제 코드/runtime을 확인한다.

### 8-5. MUST — 반드시 구현

- [x] 필요한 브랜치만 선별병합 (CODE-SPLIT/CSS empty/identical 제외) — already on main, not re-merged
- [x] 권장 순서 `CV-05 → BUYER-60 → CV-02 → CV-03` — already on main
- [x] 각 브랜치 merge 전 자체 테스트 통과 — historical, already merged
- [x] `main.py` 충돌은 기계 ours/theirs 금지 — N/A, already merged
- [ ] 병합 후 CV-04 통합검증 (migration, Mock Adapter/API, E2E/smoke, 격리, buyer 검색, 인증, 결제/크레딧, frontend lint/build, backend pytest) — journey+pytest+build done; live PG and Preview E2E pending
- [x] `TASK.md` CV 상태를 실제 결과에 맞게 갱신 (TASKS.md는 역사 문서)

### 8-6. KEEP — 유지

- [ ] 기존 buyer 검색/상세
- [ ] 인증
- [ ] 결제/크레딧
- [ ] 기존 contact/trade/credit 상태
- [ ] demo snapshot API
- [ ] 기존 migration chain

### 8-7. REMOVE — 제거

없음 (병합하지 않을 브랜치는 합치지 않음)

### 8-8. FORBIDDEN — 금지

- 사용자 요청에 없는 기능 임의 추가 금지
- 불필요한 대규모 리팩터링 금지
- 관련 없는 DB/API/UI 변경 금지
- 테스트를 통과시키기 위한 기능 삭제 금지
- 기존 실패 테스트 skip 금지
- 근거 없는 값/데이터 생성 금지

TASK별 추가 금지사항:

- CODE-SPLIT/CSS empty/identical branch 병합
- unrelated refactor, Campaign/Send Adapter/Credit Ledger 신규 확장
- 충돌을 무조건 ours/theirs로 해결
- 실제 유료 외부 API 호출

### 8-9. 선행조건·의존성

DEPENDS_ON:

- MG-001
- MG-002
- MG-003

선행 TASK가 실제로 DONE이 아니면 후속 작업을 완료 처리하지 않는다.

### 8-10. 구현범위

수정 가능 범위:

- 선별병합
- 충돌 합성
- CV-04 E2E/smoke
- TASKS.md 상태 동기화

기존 구조를 최대한 유지하고 최소 변경한다.

### 8-11. 입력검증

반드시 확인:

- 정상 로그인·검색·검증 입력
- 필수값 없음 / 잘못된 형식 / 권한 없는 조회

해당되지 않는 항목은 N/A 근거를 남긴다.

### 8-12. 빈상태

검증:

- 검색 0건
- 검증 결과 없음
- 일부 필드 없음

### 8-13. 로딩상태

실사용 흐름의 기존 로딩을 깨지 않는다.

### 8-14. 오류상태

필요한 경우:

- 인증 실패 / 권한 오류 / DB 실패 / timeout / 재시도 가능 상태

병합 후 main 전체 회귀검증 실패 시 추가 기능 진행 금지.

---

## MG-005

### 8-1. 사용자 원문 요청

> 과거사용자가 요청했ㄷ너것중 미완료된거 task에추가하고 개발

원문 보존 (이전 세션):

- "사용자가 구매신호릉 직접 볼수있게해"
- 랜딩 상단「해외 수요 찾기」는 있으나, 검색창 HS가 구매신호 목록으로 넘어가지 않음
- 하단 CTA에도 구매신호 진입이 없음

원문의 의미를 축약 과정에서 변경하지 않는다.

### 8-2. 비개발자용 1줄 요약

랜딩에서 입력한 HS로 구매신호를 바로 보게 한다

이 문장이 상단 TASK LIST에 그대로 표시된다.

### 8-3. 사용자가 원하는 최종 결과

사용자가 실제로 사용했을 때:

- 랜딩에 제품명/HS를 넣고 구매신호를 누르면 그 조건의 수요 목록이 열린다
- 하단 CTA에서도 같은 화면으로 들어간다
- 새 페이지/라우터를 만들지 않고 기존 `opportunities` 화면을 쓴다

이 결과가 달성되지 않으면 DONE이 아니다.

### 8-4. 현재상태

- TASK_START_SHA: 984e37c1567510fe1e723f99823c57c9d498c9af
- TASK_BLOB_SHA: 91ce2465aefa3678f470f66c2ff1effd5311ffbc
- WORK_BRANCH: cursor/incomplete-user-tasks-23f7
- localhost:5173: HS 330499 입력 → 구매신호 보기 → 로그인 후 해외 수요 화면에 HS 330499 유지 확인
- 목록 API는 `opportunity_item.csv` 부재로 500. 가짜 데이터는 만들지 않음 (MG-008)
- REQUEST_SOLVED=YES (랜딩 HS 진입). 목록 원본 파일은 별도

문서의 DONE 표시만 믿지 말고 실제 코드/runtime을 확인한다.

### 8-5. MUST — 반드시 구현

- [x] 과거 미완료 요청을 TASK LIST에 등록 (MG-005~MG-008)
- [x] 랜딩 검색어에서 HS를 읽어 `onStartOpportunities({ hsCode })`로 전달
- [x] 상단「해외 수요 찾기」와 하단 CTA·검색 보조 버튼이 같은 경로를 탄다
- [x] 기존 `App.jsx` 상태 라우팅 재사용, 새 라이브러리·백엔드 변경 없음

### 8-6. KEEP — 유지

- [ ] 기존 `OpportunityExplorePage`
- [ ] 바이어 검색 기본 제출 동작
- [ ] 사용자가 변경 요청하지 않은 기존 동작

### 8-7. REMOVE — 제거

없음

### 8-8. FORBIDDEN — 금지

- 사용자 요청에 없는 기능 임의 추가 금지
- 불필요한 대규모 리팩터링 금지
- 관련 없는 DB/API/UI 변경 금지
- BuyerSearch/기업검증 파일 수정 (MG-003 동시 작업)
- 새 라이브러리
- 백엔드 수정

### 8-9. 선행조건·의존성

DEPENDS_ON: 없음. MG-003과 파일군이 다름.

### 8-10. 구현범위

- `LandingPage.jsx`
- 필요 시 `App.css` 최소 스타일
- `TASK.md` / `TASKS.md`

### 8-11. VERIFY

- 검색창에 `330499` 입력 후 구매신호 → opportunities 화면이 HS 330499로 열린다
- HS 없이 눌러도 기존 전체 목록 화면이 열린다
- `npm run build` 통과

### DONE

- REQUEST_SOLVED=YES: 랜딩에서 구매신호를 HS와 함께 바로 볼 수 있다

---

## MG-006

### 8-1. 사용자 원문 요청

> 연락처 소유 확인 (이전 세션: "아직 고객사용플로우중 ㄷ안되는것" / 갭 표에서 소유 확인 미구현)

원문 보존: `contactStatus`의 `ownership_verified`는 타입만 있고 절차가 없다. #82는 형식 검증만.

### 8-2. 비개발자용 1줄 요약

연락처가 실제 수신자 소유인지 확인하는 절차를 만든다

### 8-3. 사용자가 원하는 최종 결과

- 이메일이 그 바이어 소유인지 확인된 건만 `ownership_verified`로 표시
- 형식만 맞으면 `format_validated` 유지
- 확인 안 된 연락처로 실발송하지 않음

### 8-4. 현재상태

- UI 라벨은 있음. 부여 로직 없음 (`buyerViewModel.js` 주석: 별도 절차 전까지 부여하지 않음)
- 선행: 확인 채널(메일 링크 등) 설계 필요

### 8-5. MUST

- [ ] 소유 확인 절차와 상태 전이 규칙을 구현
- [ ] 미확인 건을 `ownership_verified`로 올리지 않음

### 8-8. FORBIDDEN

- 근거 없이 소유 확인됨으로 표시
- 실제 유료 외부 API 임의 호출

### 8-9. 선행조건·의존성

DEPENDS_ON: 없음. 발송(MG-007)보다 먼저 하는 것이 안전.

---

## MG-007

### 8-1. 사용자 원문 요청

> 인콰이어리 고객 E2E 실발송 (이전: "이 서비스를 가능하게하라고" / 초안→관리자 큐에서 멈춤)

### 8-2. 비개발자용 1줄 요약

인콰이어리를 고객이 제출한 뒤 실제 발송까지 이어지게 한다

### 8-3. 사용자가 원하는 최종 결과

- 고객이 초안을 제출하면 검토 후 실제 메일 발송까지 이어지거나, 그 상태가 화면에 보임
- 지금은 `review_required`에서 끝남

### 8-4. 현재상태

- POST `/v1/inquiries` + `/submit` → `review_required`
- 관리자 큐는 있음. 고객 E2E 실발송·SMTP 파일럿 미완
- 실 SMTP는 운영 메일함/`ADMIN_EMAILS` 필요

### 8-5. MUST

- [ ] 제출 이후 발송/대기 상태를 고객이 볼 수 있게 함
- [ ] 실발송 경로가 있으면 1건 파일럿 가능해야 함

### 8-8. FORBIDDEN

- 미확인 연락처로 임의 대량 발송
- 운영 비밀값 로그 출력

### 8-9. 선행조건·의존성

DEPENDS_ON: MG-006 권장. 운영 SMTP/`ADMIN_EMAILS`.

---

## MG-008

### 8-1. 사용자 원문 요청

> P2 CSV 드롭인. 실제사용가능하게하라고 / TradeKorea·KITA 등 실제 소스

### 8-2. 비개발자용 1줄 요약

P2 바이어 소스를 CSV로 넣어 실제 검색에 쓰이게 한다

### 8-3. 사용자가 원하는 최종 결과

- 지정 CSV를 넣으면 바이어 검색에 실제로 나온다
- 게이트만 있고 파일이 비어 있지 않음

### 8-4. 현재상태

- P2 경로/`ACCESS_GATED` 흔적. 실 CSV 드롭인 미완
- 원본 파일이 없으면 만들지 않음

### 8-5. MUST

- [ ] 실제 P2 CSV가 있을 때만 로더에 연결
- [ ] 없는 값을 합성하지 않음

### 8-8. FORBIDDEN

- 가짜 바이어 생성
- 라이선스 없는 스크래핑 데이터 커밋

### 8-9. 선행조건·의존성

DEPENDS_ON: 사용자가 넣을 P2 CSV.

---

# 9. 실제사용 시나리오

TASK 완료 전에 반드시 실제 사용자 관점으로 검증한다.

해당 TASK DETAILS의 최종 결과·구현범위와 함께 적용한다.

## USER FLOW

사용자 시작점:
화면 / CLI / 이메일 / API / 파일 등 실제 진입점

사용자 행동:
1. 사용자가 실제로 하는 행동
2. 다음 행동
3. 다음 행동

시스템 처리:
실제 production 경로 (mock-only로 대체하지 않음)

사용자 최종 결과:
사용자가 실제 보게 되는 것

## 핵심 질문

`이 결과가 사용자의 최초 요청을 실제로 해결했는가?`

YES가 아니면 DONE 금지.

---

# 10. VERIFY — 해결 여부 검증

사용자 요청과 결과를 1:1로 대조한다.

| 사용자 요구 | 실제 결과 | 판정 |
|---|---|---|
| DETAILS의 MUST 항목 | 실제 결과 | PASS/FAIL |

하나라도 필수 요구가 FAIL이면:

`REQUEST_SOLVED = NO`

---

# 11. 실사용 E2E

최소 1개의 실제 사용자 흐름을 처음부터 끝까지 실행한다.

원칙:

- 단위 테스트만으로 대체 금지
- mock-only 검증만으로 DONE 금지
- 가능한 실제 runtime/production entrypoint 사용
- 실제 외부 유료 호출이나 위험 작업은 안전한 staging/dry-run/preview 사용

E2E 결과:

USER_E2E: PASS | FAIL | BLOCKED

근거:
명령 / 화면 / 산출물 / preview / API 결과

---

# 12. 테스트

실사용 검증을 보조하는 테스트를 수행한다.

최소:

- 정상경로
- 주요 경계값
- 입력검증
- 빈상태
- 주요 오류
- 변경한 기능 단위 테스트
- 관련 integration test

테스트 PASS만으로 DONE 처리하지 않는다.

---

# 13. 회귀검증

이번 변경 때문에 기존 핵심 기능이 깨지지 않았는지 확인한다.

- [ ] 기존 핵심 사용자 흐름
- [ ] 관련 API
- [ ] 인증/권한
- [ ] DB 계약
- [ ] 기존 사용자 데이터
- [ ] 기존 자동화
- [ ] 기존 주요 테스트

관련 없는 전체 제품 고도화는 하지 않는다.

---

# 14. 문서동기화

실제 구현과 문서가 달라진 경우에만 최소 수정:

- README
- TASK 관련 문서
- ARCHITECTURE
- 운영문서
- 테스트/사용법 문서

거짓 DONE 기록을 남기지 않는다.

---

# 15. DONE 기준 — 실제 사용자 요청 해결 기준

## 절대 원칙

다음은 단독으로 DONE 근거가 아니다.

- 코드 작성 완료
- 테스트 PASS
- build PASS
- 오류 없음
- commit 존재
- PR 생성
- 화면이 열림

## DONE

다음을 모두 만족해야 한다.

- [ ] 사용자의 필수 요청사항 전부 해결
- [ ] `REQUEST_SOLVED = YES`
- [ ] 실제 사용자 E2E PASS
- [ ] 사용자가 원하는 최종 결과 확인
- [ ] 필요한 입력/빈/로딩/오류상태 사용 가능
- [ ] 기존 핵심 기능 회귀 없음
- [ ] 금지사항 위반 없음
- [ ] 필요한 문서 동기화
- [ ] commit 완료
- [ ] push 완료

## ALREADY_DONE

새 코드를 만들지 않아도 이미 요청사항이 해결되어 있고
실제사용 E2E로 이를 확인한 경우.

## PARTIAL

일부 구현했지만:

`REQUEST_SOLVED = NO`

인 경우.

작업량이 많아도 DONE 금지.

## BLOCKED

외부 의존성/권한/정책/Git 충돌/검증환경 때문에
안전하게 사용자의 요청을 해결할 수 없는 경우.

## FAIL

구현을 시도했으나 사용자 요청 해결에 실패한 경우.

---

# 16. 작업 종료 전 Git 최신 상태 재확인

작업 완료 직전 다시:

1. `git fetch --all --prune`
2. 현재 `origin/main` 확인
3. `TASK_START_SHA`와 최신 base 비교

## base가 작업 중 변경된 경우

코드를 최신 base와 안전하게 통합한다.

필요하면:

- conflict 해결
- 관련 test 재실행
- USER E2E 재실행
- regression 재실행

단:

최신 TASK.md의 새로운 일반 작업을 현재 ACTIVE TASK에 섞지 않는다.

코드는 최신화할 수 있지만,
ACTIVE TASK의 목적과 DONE 조건은 최초 TASK snapshot을 유지한다.

---

# 17. 작업 완료 후 Git 동기화

TASK 구현 완료:

1. 변경 파일 확인
2. 필요한 파일만 stage (`git add -A` 금지)
3. commit
4. remote work branch에 push

확인:

WORK_BRANCH_PUSHED: YES | NO

## PR/merge가 TASK 범위인 경우

- 필요한 검사 통과
- PR
- merge

머지는 이 TASK가 허용한 경우만 한다. 명시가 없으면 기본 브랜치 병합 금지.

조건:

- 충돌 없음
- GitHub Checks 초록

실패면 merge 명령 실행 금지.

문제: 머지 규칙이 TASK 글뿐이라 `gh pr merge`로 문서 PR을 Checks 빨강인데도 머지할 수 있었다. 예외 머지는 폐지한다.

머지는 GitHub Checks가 초록일 때만 한다. 문서만(`TASK.md`, `*.md`, `docs/**`) 바뀌면 무거운 테스트 대신 `docs-gate`가 초록이면 된다. `gh pr merge --admin` 및 실패 체크를 무시하는 머지는 금지한다.


merge 후:

1. `git fetch`
2. local base clean 확인
3. `git merge --ff-only origin/main`
4. local base와 remote base 일치 확인

절대 reset --hard로 맞추지 않는다.

---

# 18. TASK LIST 상태 갱신 규칙

TASK LIST의 상태는 실제 결과와 반드시 일치한다.

### `[x]`

다음일 때만:

`REQUEST_SOLVED = YES`

### `[~]`

현재 실행 중.

### `[!]`

BLOCKED.

### `[-]`

사용자가 취소.

### `[ ]`

아직 시작하지 않음.

LIST와 DETAILS가 불일치하면 TASK 파일 오류로 간주한다.

---

# 19. TASK 수정/삭제 규칙

## 사용자가 TASK 설명을 수정

TASK LIST 1줄 요약과 해당 DETAILS를 함께 수정한다.

## 사용자가 "삭제"

- TASK LIST 행 삭제
- TASK DETAILS 전체 삭제

## 사용자가 "취소"

- LIST를 `[-]`로 변경
- 상세에는 취소 이유 최소 기록 가능

## 완료 TASK

사용자가 목록에서 완료 TASK도 계속 보고 싶다면 `[x]` 유지.

별도 요청으로 정리할 때만 제거한다.

---

# 20. 새 사용자 요청 등록 규칙

새 요청:

1. 기존 TASK와 동일한 요청인지 확인
2. 이미 해결됐으면 중복 생성 금지
3. 새 TASK_ID 발급
4. 사용자 원문 보존
5. 비개발자용 1줄 요약 생성
6. TASK LIST에 `[ ]` 추가
7. TASK DETAILS 생성
8. MUST/KEEP/REMOVE/FORBIDDEN/VERIFY/DONE 변환
9. 기존 TASK와 dependency/충돌 검사
10. 실행 순서 결정

기존 ACTIVE TASK에 새 요청을 임의 합치지 않는다.

---

# 21. TASK 완료 후 다음 TASK

현재 TASK가 DONE된 후:

- TASK LIST에서 다음 READY 작업 확인
- dependency가 해결된 작업 우선
- 독립 작업은 병렬 가능
- BLOCKED 작업은 건너뛰되 이유 유지

새 TASK가 없으면:

`NO_ACTIVE_TASK`

를 보고하고 개발을 중단한다.

---

# 22. 최종보고

반드시 아래 형식으로 보고한다.

REPO:
TASK_ID:

USER_REQUEST:
REQUEST_SOLVED: YES | NO

TASK_START_SHA:
TASK_BLOB_SHA:
WORK_BRANCH:

USER_E2E: PASS | FAIL | BLOCKED
USER_RESULT:
VERIFY_RESULT:

TEST:
REGRESSION:

COMMIT:
WORK_BRANCH_PUSHED: YES | NO

PR:
MAIN_MERGED: YES | NO | N/A

REMOTE_BASE_SYNC:
LOCAL_BASE_SYNC:

TASK_STATUS:
DONE | ALREADY_DONE | PARTIAL | BLOCKED | FAIL

NEXT_READY_TASK:
PENDING_TASKS:

---

# 23. 최종 STOP 조건

아래 중 하나면 임의 개발을 계속하지 않는다.

- ACTIVE TASK 없음
- 사용자 요청과 TASK 내용이 명백하게 불일치
- repo/origin 불일치
- 안전한 Git 작업공간 확보 불가
- 사용자 데이터를 잃을 위험
- 최신 CANCEL/STOP 지시 발견
- 해결방법 선택이 제품정책을 바꾸며 사용자의 결정이 반드시 필요함

상태를 `BLOCKED` 또는 `NO_ACTIVE_TASK`로 보고한다.
