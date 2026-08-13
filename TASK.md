# TASK.md — 이 레포 실행 단일 기준

```text
REPO: pds2225/marketgate
BASE: main
```

## 0. Git 동기화·STOP 게이트
1. `git fetch --all --prune`.
2. `git remote get-url origin`, `git branch --show-current`, `git status --short` 확인.
3. `git rev-list --left-right --count HEAD...origin/main`으로 ahead/behind/diverged 확인.
4. 현재 `main`이 clean이고 `ahead=0, behind>0`일 때만 `git merge --ff-only origin/main`으로 최신화.
5. dirty/ahead/diverged/다른 브랜치의 로컬 전용 변경은 보존한다. 삭제·덮어쓰기·자동 reset 금지.
6. `git reset --hard`, force push, `git clean -fd`, 임의 stash/drop 금지.
7. 로컬 변경이 있으면 건드리지 말고 최신 `origin/main` 기준 별도 branch/worktree에서 작업한다. 안전 분리 불가 시 `BLOCKED`.
8. 실행 지시는 이 `TASK.md`만 사용한다. 다른 레포 TASK/NEXT_TASK/옛 채팅 과업 금지.
9. 각 작업은 구현 → 테스트 → commit → push. 아래에서 명시적으로 허용한 검증 통과 브랜치만 main 병합 가능.

# CURRENT TASK — 야간 병렬개발 검수·수정·선별병합·CV-04 통합검증

## 목표
야간 브랜치를 원격 코드 기준으로 다시 검수하고 BLOCKER를 최소 수정한 뒤, 통과한 브랜치만 main에 병합하고 CV-04 통합 회귀검증까지 완료한다.

## 현재상태
검수 대상:
- `night/cv02-opencorporates-mock` — commit `cbb049e`
- `night/cv03-company-verification-ui` — commit `a8dc892`
- `night/cv05-prd-correction` — commit `54bb709`
- `night/buyer-60-limit` — commit `2292305`
- `night/page-code-splitting` — main과 동일, 병합 불필요
- `night/css-deslop-pass3` — 실질 변경 없음, 병합 불필요

확인된 CV-02 BLOCKER:
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

BUYER-60 현재 확인사항:
- main: `_DEFAULT_BUYER_LIMIT = 60`, `_MAX_BUYER_LIMIT = 200`
- night branch는 기본값을 200으로 올림.
- 단순 숫자 변경이 아니라 60 제한의 실제 원인/의도가 demo sample limit인지 실제 검색 제한인지 확인해야 함.

## 구현범위
### TRACK A — CV-02 수정
- DB enum을 확정 5개 값으로 통일.
- API/store/test fixture 상태값도 동일 계약 사용.
- `GET /v1/company-verifications/{verification_id}`는 현재 로그인 사용자 소유 record만 조회 가능하게 `user_id` 조건 적용.
- 타 사용자 ID는 정보 노출 없이 404 처리.
- POST/GET 인증 유지.
- 결과없음/provider 오류/timeout/DB 오류 등 기존 TASKS.md 요구가 구현됐는지 확인하고 누락만 최소 보완.
- 실제 PostgreSQL에서 0005 적용/재실행 정책 검증.

### TRACK B — BUYER-60 원인 수정
- demo snapshot, API query, frontend caller를 추적하여 60개의 실제 원인을 기록.
- 공개 demo 샘플 수 제한과 실제 buyer 검색 결과 제한을 혼동하지 않는다.
- 제품 의도상 200이 맞으면 상수/기본값/호출 계약을 일관되게 수정하고 테스트.
- 단순 `60 → 200` 하드코딩만으로 root cause 해결 처리 금지.

### TRACK C — CV-05 문서
- K-SURE/D&B는 현재 MVP에서 공식 외부 조회 링크만 제공.
- 검증되지 않은 API·신용등급 자동조회 가정 제거 여부 확인.

### TRACK D — CV-03 UI
- TRACK A API 계약이 확정된 뒤 검수/보완.
- 기존 `BuyerSearch/index.tsx` 상세 흐름 안에 유지.
- 새 Router/전역 페이지 금지.
- `registryCheckStatus`를 `contactStatus/tradeStatus/creditStatus`와 혼합 금지.

### TRACK E — 선별병합
권장 순서:
```text
CV-05 → BUYER-60 → CV-02 → CV-03
```
각 브랜치는 merge 전 자체 테스트 통과 필수. `main.py` 충돌은 ours/theirs로 기계 처리하지 말고 양쪽 의도를 수동 합성 후 재테스트.

### TRACK F — CV-04 통합검증
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

## 금지사항
- 실제 OpenCorporates/D&B/K-SURE 유료·계약 API 호출.
- 신용점수/안전점수/지급능력 점수 생성.
- 근거 없는 buyer/trade/import 수치 생성.
- 기존 0001~0004 migration 임의 수정.
- CODE-SPLIT/CSS empty/identical branch 병합.
- unrelated refactor, Campaign/Send Adapter/Credit Ledger 신규 확장.

## 입력검증
- company_name 공백 금지.
- country ISO3 3자리 검증·정규화.
- verification_id 형식/존재 여부 검증.
- 모든 조회에서 현재 user 소유권 검증.

## 빈상태
- registry 결과 없음 → `확인 결과 없음` 계열 명시 상태.
- buyer 정보/API에 없는 값 → `자료 내 확인 불가` 또는 기존 정책의 명시적 빈값.
- 빈 결과를 임의 점수/추정값으로 채우지 않는다.

## 로딩상태
- 기본검증 요청 중 중복 제출 방지.
- BuyerSearch 기존 로딩 흐름을 깨지 않고 verification loading을 분리.

## 오류상태
- 400/404/401·403/500/502/504를 구분.
- provider timeout과 내부 DB 오류를 같은 성공/빈값으로 처리하지 않는다.
- 화면은 재시도 가능 상태를 제공하고 기존 검색 결과를 날리지 않는다.

## 테스트
최소:
- CV-02 targeted tests
- user isolation negative test
- DB enum/status 저장 test
- migration PostgreSQL 검증
- BUYER-60 limit/root-cause regression
- CV-03 frontend build 및 관련 unit
- 전체 backend pytest
- frontend lint/build
- CV-04 E2E/smoke

## 회귀검증
- buyer 검색/상세 흐름
- auth
- payment/credit
- 기존 contact/trade/credit 상태
- demo snapshot API
- 기존 migration chain

## 문서동기화
- `TASKS.md` CV-02~05 상태를 실제 원격 main 결과와 동기화.
- CV-05 PRD 2개 상태/용어 통일.
- README/ARCHITECTURE를 실제 구현과 불일치할 때만 최소 수정.

## Git 규칙
- 수정은 기존 night branch 또는 최신 origin/main 기반 안전 브랜치에서 수행.
- 작업별 테스트 통과 후 commit/push.
- 선별병합은 TRACK E 조건을 모두 통과한 경우에만 허용.
- 병합 후 main 전체 회귀검증 실패 시 추가 기능 진행 금지.

## DONE/BLOCKED
DONE 조건:
- CV-02 enum/status/user isolation 정합성 PASS.
- BUYER-60 root cause가 설명되고 수정/비수정 결정에 테스트 근거 존재.
- CV-03/CV-05 검수 PASS.
- 필요한 4개 브랜치만 선별병합.
- CV-04 통합검증 PASS.
- TASKS.md 동기화 완료.

BLOCKED 조건:
- 실제 PostgreSQL 검증 불가.
- merge conflict를 안전하게 해결할 수 없음.
- 필수 test/CI 실패.
- 사용자 결정이 필요한 제품 정책 충돌 발견.

## 최종보고
```text
REPO: pds2225/marketgate
BASE_SYNC: CLEAN_CURRENT | FAST_FORWARDED | LOCAL_CHANGES_PRESERVED | DIVERGED | BLOCKED
CV-02: DONE | BLOCKED
BUYER-60: DONE | BLOCKED
CV-05: DONE | BLOCKED
CV-03: DONE | BLOCKED
MERGED:
NOT_MERGED:
CV-04:
TEST:
REGRESSION:
MAIN_SHA:
STATUS: DONE | BLOCKED | FAIL
```

## 실행지시
원격 상태를 안전하게 확인·동기화한 뒤 이 `TASK.md`만 처음부터 끝까지 읽고 그대로 실행한다. 실패/BLOCKED 항목은 근거를 남기고, 안전한 독립 항목은 계속 진행하되 검증되지 않은 브랜치는 main에 병합하지 않는다.
