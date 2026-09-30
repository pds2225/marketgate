# marketgate E2E — 상태와 남은 일 (2026-09-04)

> 이 브랜치(`chore/e2e-followups`)는 **지금 main에 넣지 않고 나중에 반영할** 것들을
> 모아둔 곳이다. MG-004는 이후 진행돼 main에 이미 병합·완료됐다 — 아래 "완료" 참고.

---

## 지금 어디까지 됐나 (비개발자용)

**로그인 → 바이어 검색 → 상세 → 기업검증 → 인콰이어리 초안 → 관리자 검토 요청까지,
로컬과 운영(marketgate.vercel.app) 양쪽 다 실제로 동작한다.** 데이터도 진짜다 —
바이어 36,241건이 `buyer_candidate.csv`에서 나온다.

`localhost:5173/demo.html` 은 로그인 없이 실데이터를 보여주는 화면, 이것도 정상.

**아직 안 되는 것:**
- 인콰이어리 **실제 메일 발송** — MG-007. 코드는 됐고 dry-run(모의 발송)은 테스트됨.
  진짜 발송은 provider 어댑터 구현 + 운영 메일 계정(SMTP) 설정이 있어야 한다.
- P2 바이어 데이터 추가 — MG-008. 넣을 CSV 파일이 있어야 진행.

---

## main에 이미 반영됨

**PR #146 (`e2d1ed4`)** — `tools/e2e-local.mjs`(로컬 E2E 러너), `deployed.spec.js`
`@smoke` 화면판별 버그 수정(L026). 로컬 E2E 5/5, 백엔드 pytest 267 pass/1 skip.
부수효과로 main `Deployed E2E` 워크플로가 몇 주 만에 GREEN.

**PR #148 (`5a288e7`) — MG-004 본체 수정** — `company_verification_store.py`에
`inquiry_store` 패턴(원자적 JSON 파일 폴백 + `user_id` 격리)을 추가해, Render 운영에
Postgres가 없어도(`DATABASE_URL` 미설정) 기업검증이 동작하게 함. `docs/LESSONS.md` L027.
backend pytest 271 pass/1 skip.

**PR #149 (`483c2fa`) — MG-004 종료** — 운영(`marketgate.onrender.com`)에 배포 확인 후
`tests/e2e/mg004-prod-verification.spec.js`(비mock, 실제 운영 API)로 로그인→검색→상세→
기업검증 전 과정 PASS 확인. `TASK.md` `MG-004 [!]`→`[x]`, `REQUEST_SOLVED=YES`.
`marketgate-e2e.onrender.com`(격리 e2e 서비스)은 아직 이 fix가 안 올라가 있어 그
서비스에 대고 도는 CI(`Preview deployed E2E`)는 계속 503으로 실패함 — AC-7(SHOULD)
후속 과제로 남음, MG-004 자체를 막지는 않음(운영이 기준).

Codex가 같은 밤에 병합: MG-006(`/v1/contact-verifications`), MG-007(dry-run dispatch),
MG-008 preflight(`tools/validate_p2_dropins.py`).

**결과: MG-001~006 전부 `[x]`. 남은 건 MG-007·MG-008뿐, 둘 다 아래처럼 100% 사용자
제공(자격증명/데이터) 대기.**

---

## 이 브랜치에 담긴 것

### `tools/mg004-live-e2e.mjs` (이전 세션에서 만든 untracked 파일 — 여기 저장)

운영 사이트에 실제 접속해 로그인→검색→상세→기업검증을 훑는 초기 스크립트.
`tests/e2e/mg004-prod-verification.spec.js`(이제 main에 있고 green)로 사실상
대체됐다. **나중에 할 일**: 필요 없으면 삭제, 필요하면 `e2e-local.mjs`에
`--target=prod` 모드로 흡수.

### 이 문서

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
