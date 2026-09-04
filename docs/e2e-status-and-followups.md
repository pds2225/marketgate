# marketgate E2E — 상태와 남은 일 (2026-09-04)

> 이 브랜치(`chore/e2e-followups`)는 **지금 main에 넣지 않고 나중에 반영할** 것들을
> 모아둔 곳이다. 사용자 지시: "나중에 반영하게 브랜치에 저장하고 읽을 수 있게 메모 남겨".
> main에 이미 들어간 것은 아래 "완료" 참고.

---

## 지금 어디까지 됐나 (비개발자용)

**로그인 → 바이어 검색 → 상세 → 인콰이어리 초안 → 관리자 검토 요청까지, 실제로 다
동작한다.** 로컬(내 PC)에서 자동 테스트로 전 과정을 5개 항목 전부 통과 확인했다.
데이터도 진짜다 — 바이어 36,241건이 `buyer_candidate.csv`에서 나온다.

`localhost:5173/demo.html` 은 로그인 없이 실데이터를 보여주는 화면인데, 이것도 정상.

**아직 안 되는 것:**
- 회사(기업) 검증이 **운영 사이트(marketgate.vercel.app)** 에서는 실패 — MG-004.
  운영 백엔드(Render)가 2026-07-28 코드에 멈춰 있어서 그렇다. Render 관리자
  화면에서 수동으로 한 번 배포해야 한다. (아래 "MG-004" 참고)
- 인콰이어리 **실제 메일 발송** — MG-007. 코드는 됐고 dry-run(모의 발송)은 테스트됨.
  진짜 발송은 운영 메일 계정(SMTP) 설정이 있어야 한다.
- P2 바이어 데이터 추가 — MG-008. 넣을 CSV 파일이 있어야 진행.

---

## main에 이미 반영됨 (PR #146, `e2d1ed4`)

- `tools/e2e-local.mjs` — 로컬 스택에 대고 E2E 전체를 돌리는 러너
- `apps/frontend-react/tests/e2e/deployed.spec.js` — `@smoke` 화면 판별 버그 수정 (L026)
- `docs/LESSONS.md` — L026
- 결과: 로컬 E2E 5/5, 백엔드 pytest 267 pass / 1 skip, 프론트 unit 28 pass
- **부수효과**: main의 `Deployed E2E` 워크플로가 몇 주 만에 처음 GREEN. (smoke 판별
  버그가 원인이었음. 단, 이게 MG-004를 푸는 건 아님 — smoke는 health 체크만 하고,
  write journey는 기업검증을 안 건드리고, company-verification 스펙은 CV-02를 mock함)

Codex가 같은 밤에 병합: MG-006(`/v1/contact-verifications`), MG-007(dry-run dispatch),
MG-008 preflight(`tools/validate_p2_dropins.py`).

---

## 이 브랜치에 담긴 것

### 1. `tools/mg004-live-e2e.mjs` (이전 세션에서 만든 untracked 파일 — 여기 저장)

운영 사이트(`marketgate.vercel.app`)에 실제로 접속해서 로그인→검색→상세→기업검증까지
훑는 스크립트. Render가 재배포되기 전엔 기업검증 단계에서 FAIL 난다.
**나중에 할 일**: `tools/e2e-local.mjs`에 `--target=prod` 모드로 흡수하고 이 파일은 삭제.
지금은 그냥 잃어버리지 않게 커밋만 해둠.

### 2. 이 문서

---

## MG-004 — 2026-09-04 재조사 (블로커가 바뀜)

**옛 블로커(Render가 2026-07-28 코드에 멈춤) 해소됨.** `marketgate.onrender.com`
이 최근 코드로 재배포됨 — `/v1/company-verifications`, `/v1/contact-verifications`,
`/v1/admin/inquiries/{id}/dispatch-dry-run` 전부 라이브(전엔 404). 로그인 →
바이어검색 → 상세 → 기업검증 탭까지 운영에서 실제 동작 확인
(`tests/e2e/mg004-prod-verification.spec.js`).

**새 블로커:** 기업검증 POST가 **503 `verification_store_unavailable`**.
- `company_verification_store.py` 는 의도적으로 **"DB-only, no file fallback"**
  (docstring·router 주석·`#119`부터). `test_post_db_unavailable_returns_503` 가드 존재.
- `render.yaml` 에 `DATABASE_URL`/DB 리소스 없음 → 운영에 Postgres 없음 →
  `get_conn()` None → `RuntimeError` → 503.
- 다른 store(inquiry/credit/auth/subscription)는 전부 파일 폴백이 있는데 CV-02만 없음.

**끝내려면 둘 중 하나 (팀 결정 필요 — 야간 자동처리 부적절):**
1. **운영에 Postgres 붙이기** (Render Blueprint에 free Postgres + `DATABASE_URL`).
   부작용: payment/credit/subscription store도 DB 경로로 전환 → L013–L027 멱등·잠금
   로직이 DB 기준으로 바뀜, `UVICORN_WORKERS:1` 근거 재검토, free Postgres 30일 만료.
   payment 회귀 검증 선행 필요.
2. **CV-02에 파일 폴백 추가** (`inquiry_store` 패턴 미러, `os.replace` 원자쓰기,
   `owner user_id` 격리 유지). "DB-only" 명시 결정을 되돌림 + 가드 테스트 2건 갱신.
   CV-02 provider가 결정론적 mock이라 "가짜 성공 은폐" 우려는 약함.

내 판단: **2번(파일 폴백)** 이 범위 작고 운영 현실과 일치. 단 명시적 반대 결정을
뒤집는 거라 사용자/Codex 승인 후. `mg004-prod-verification.spec.js` 는 고쳐지면
바로 green으로 AC-4/5/6 증명하도록 이미 작성됨.

## MG-007 — 2026-09-04 재조사

- 고객 상태 조회: My Inquiries + `history` 로 이미 보임 (deployed write journey가
  "검토 대기" 확인). MUST #1은 사실상 충족.
- 실발송: `inquiry_delivery.py` 에 **dry-run 어댑터만** 있음. 파일 헤더 명시:
  "A real provider must implement the same result contract in a later, explicitly
  authorised task." `dry_run_enabled()` 은 `APP_ENV=production` 이거나 `RENDER`
  set이면 False → 운영에서 dispatch-dry-run은 409(fail-closed, 의도됨).
- **블로커: 실제 provider 어댑터 미구현 + SMTP 자격증명 없음.** 별도 승인된 작업 필요.

## MG-008 — 2026-09-04 재조사

- `services/cosmetics_mvp_preprocess/input/p2_optional/` 에 `.csv.example` 템플릿 +
  README만. 실데이터 0.
- README: "TradeKorea / KITA / KOTRA 무역관은 **공개 일괄 CSV가 없습니다**
  (ACCESS_GATED, L002)." — 회원·무역관에서 **합법 수령한** 목록만 넣을 수 있음.
- FORBIDDEN: 스크래핑, 가짜 바이어, 라이선스 없는 데이터 커밋.
- **블로커: 100% 사용자 제공.** 우회 불가(L002). 파일을 위 폴더에 넣고
  `python3 tools/merge_p1_p2_buyer_sources.py` 실행하면 검색에 반영됨.

---

## 로컬에서 E2E 돌리는 법

두 서버를 먼저 띄운다 (venv에 fastapi/uvicorn/pandas/pytest 다 있음):

```bash
# 1. 백엔드
cd services/p1-export-fit-api
APP_ENV=e2e E2E_ADMIN_TOKEN=local-e2e-admin-token-0123456789abcdef INQUIRY_DELIVERY_DRY_RUN=true \
  .venv/Scripts/python -m uvicorn main:app --host 127.0.0.1 --port 8000
# 2. 프론트
cd apps/frontend-react && npm run dev      # :5173
# 3. 테스트
node tools/e2e-local.mjs                    # 전체 (write journey 포함)
node tools/e2e-local.mjs --grep @smoke      # 빠른 것만
```

로컬 테스트 계정: `local-test@marketgate.dev` / `Test1234!local`

### 지금 켜져 있는 서버 (Claude가 밤에 띄워둠)

- FastAPI `127.0.0.1:8000` (APP_ENV=e2e), 로그 `/tmp/mg-backend.log`
- Vite `127.0.0.1:5173`, 로그 `/tmp/mg-frontend.log`
- 끄려면: `pkill -f "uvicorn main:app"` / `pkill -f vite` (또는 taskkill //F //PID)
- 그냥 둬도 됨 — 다음에 열어서 바로 확인 가능하라고 켜뒀음

---

## 나중에 할 만한 코드 작업 (전부 선택)

1. **CI에 `lint` + `test:unit` job 추가** — 지금 둘 다 CI에서 안 돈다.
2. **`apps/frontend-react/src/main.jsx` 에 전역 React ErrorBoundary** — 렌더 에러 1개에
   전체가 white screen 되는 구조. 에러 화면이라도 뜨게.
3. **`ComparePage.jsx` / `demo.jsx` 린트 2건** (`react-refresh/only-export-components`)
   — #133 이전부터 있던 기존 부채, CI 게이트 아님. 정리하려면 상수/컴포넌트 파일 분리.
4. `tools/mg004-live-e2e.mjs` → `e2e-local.mjs --target=prod` 흡수 (Render 배포 후).
