# MarketGate NIGHT PARALLEL TASKS

## 목적
오늘 밤 사용자 승인 없이 서로 독립 가능한 작업을 병렬 개발한다.
각 작업은 별도 branch/worktree에서 구현·테스트·commit·push까지만 수행하고 **main에는 병합하지 않는다.**
내일 사용자가 한 번에 검수·병합한다.

## 공통 원칙
- 시작 전 `origin/main` 최신 상태를 기준점으로 사용
- 가능하면 subagent/worktree로 병렬 실행
- 각 작업 = 별도 branch
- 한 작업 실패가 다른 독립 작업을 중단시키지 않음
- 해당 작업 테스트 실패 시 DONE 처리 금지
- 기존 구조 최대 유지, 최소 변경
- 입력검증·빈상태·오류상태·로딩상태 유지
- unrelated refactor 금지
- 임의 데이터·합성 지표 금지
- `main` merge/push 금지
- 각 작업 완료 시 branch + commit SHA + test 결과 기록
- 여러 branch가 `TASKS.md`를 각각 수정해 충돌시키지 말 것. 야간 branch에서는 `TASKS.md` 체크 변경을 생략하고 최종 보고에 상태만 기록

---

# A — CV-02 OpenCorporates Mock 기본검증 API
branch: `night/cv02-opencorporates-mock`

- `POST /v1/company-verifications`
- `GET /v1/company-verifications/{verification_id}`
- 실제 OpenCorporates 호출 금지, deterministic Mock Adapter
- CV-01의 `core.company_registry_checks` 사용
- `get_current_user` 인증 및 사용자 격리
- 상태값은 `BASIC_CONFIRMED`, `BASIC_PARTIAL`, `DATA_MISMATCH`, `INACTIVE_ENTITY`, `CREDIT_CHECK_REQUIRED` 5개만 사용
- 정상/일부일치/불일치/inactive/신용조사필요/결과없음/provider error/timeout/DB실패/무인증/잘못된입력 처리
- 자체 신용점수·위험점수 생성 금지
- 관련 신규 테스트 + backend 전체 regression
- 성공 시 commit + push

---

# B — CV-03 BuyerSearch 기본검증 카드
branch: `night/cv03-company-verification-ui`

CV-02의 확정 API contract와 현재 `TASKS.md` 명세만 기준으로 frontend를 독립 구현한다.

- 새 전역 페이지/Router 금지
- `apps/frontend-react/src/pages/BuyerSearch/index.tsx` 상세 단계에 `CompanyBasicVerificationCard` 추가
- 바이어명·국가 자동입력
- loading / empty / no-result / error / timeout 처리
- 상태 5종을 신용등급처럼 오인되지 않게 표시
- D&B/K-SURE는 공식 외부 조회 링크 UI만 제공
- 기존 `contactStatus`, `tradeStatus`, `creditStatus`와 혼합 금지
- frontend unit/lint/build 및 BuyerSearch 회귀 확인
- 성공 시 commit + push

---

# C — CV-05 K-SURE·D&B PRD 정정
branch: `night/cv05-prd-correction`

대상 문서를 찾아 다음만 수정한다.
- `PRD_C1_ksure_api.md`
- `PRD_C3_dnb_api.md`
- 검증되지 않은 API 자동조회 가정 제거
- 신용등급 자동수집/자동판정 가정 제거
- 현재 MVP는 공식 외부 조회 링크까지만으로 한정
- 실제 API 연동은 계약·비용·저장·표시·재이용 권한 확인 후 별도 단계로 명시
- CV 상태명/용어를 `TASKS.md`와 일치
- 코드 수정 금지
- 성공 시 commit + push

---

# D — demo/buyers 60명 제한 원인 규명·최소 수정
branch: `night/buyer-60-limit`

목표: `demo/buyers`가 최대 60건만 반환되는 직접 원인을 찾고, 불필요한 고정 limit인 경우에만 최소 수정한다.

추적:
HTTP endpoint → service → query/repository → CSV/data loader → normalization → dedupe → filter → pagination/limit → response

검색:
`limit=60`, `LIMIT 60`, `head(60)`, `[:60]`, `page_size`, `max_results`, `default_limit`

수정 전 실제 건수 기록:
원본 → country → HS/product → dedupe → hard gate → API 직전 → response

금지:
- 단순 60→500/1000 변경
- 실제 데이터가 60 이하인데 억지 수정
- 기존 pagination 계약 파괴

검증:
- 60 이하
- 60 초과
- 0건
- 잘못된 filter
- explicit limit
- 기존 endpoint regression

성공 시 commit + push

---

# E — 페이지 코드스플리팅
branch: `night/page-code-splitting`

- `App.jsx`의 정적 page import를 `React.lazy()` + `Suspense` 기반 page-level code splitting으로 최소 변경
- 기존 라우팅/상태 라우팅 유지
- 새 라우터 라이브러리 도입 금지
- loading fallback 제공
- 페이지 기능 변경 금지
- `npm run build`
- build chunk 결과와 초기 main bundle 전/후 수치 보고
- 주요 진입 경로 smoke 가능한 범위 확인
- 성공 시 commit + push

---

# F — CSS deslop Pass 3
branch: `night/css-deslop-pass3`

- Pass 1/2 이후 남은 명백한 dead/zombie CSS만 제거
- 시각 디자인 재설계 금지
- class rename 금지
- 사용 여부 불확실 selector 삭제 금지
- JS/JSX 기능 변경 금지
- 기존 CSS 변수 체계 유지
- 중복 선언/도달 불가 selector/완전 미사용 selector 위주
- 삭제 후보마다 실제 참조 검색
- `npm run build`
- 가능하면 주요 화면 smoke
- 제거 selector/라인 수 보고
- 성공 시 commit + push

---

# 야간 병렬 작업에서 제외
통합 의존성이 크므로 오늘 밤에는 실행하지 않는다.

- CV-04 통합 E2E/회귀검증
- Campaign Orchestrator
- Matching & Slot Service
- Credit Ledger 확장
- Compliance Engine
- 실제 Send Adapter
- 실제 OpenCorporates/D&B/K-SURE API
- 실제 결제/에스크로
- main 병합

---

# 최종 보고 형식

```text
[NIGHT-A CV-02]
STATUS: DONE / BLOCKED
BRANCH:
COMMIT:
PUSH:
FILES:
TEST:
RISKS:

[NIGHT-B CV-03]
...
[NIGHT-C CV-05]
...
[NIGHT-D BUYER-60]
...
[NIGHT-E CODE-SPLIT]
...
[NIGHT-F CSS-PASS3]
...

[MERGE]
main 병합: 0건
내일 검수 필요 branch 목록:
충돌 예상 파일:
권장 병합 순서:
```

# MiMo 실행 지시

**원격 main 최신화 후 이 `NEXT_TASK.md`를 읽고 A~F 독립 작업을 가능한 한 병렬 실행해라. 각 작업은 별도 branch/worktree에서 테스트·commit·push까지만 하고 main에는 병합하지 마라. 실패한 작업만 BLOCKED로 남기고 다른 독립 작업은 계속 진행한 뒤 최종 보고하고 종료해라.**