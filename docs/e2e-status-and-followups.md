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

## MG-004 — Render 수동 배포 절차 (사용자 액션)

이 세션들엔 Render API key / CLI / 브라우저 확장이 없어서 자동화 불가.
TASK.md §8-4에 원문 있음. 요약:

1. Render Dashboard → `marketgate` 서비스 → Settings → Build & Deploy
   → **Auto-Deploy = Yes**, Branch = `main` 확인/복구
2. Manual Deploy → **Deploy latest commit** 1회 실행
3. `marketgate-e2e` 서비스도 똑같이
4. 확인: `curl -s https://marketgate.onrender.com/openapi.json | grep company-verifications`
   → 결과가 나오면 성공
5. 그 다음 기업검증 E2E를 운영에 대고 재실행 → BASIC_* 표시되면 `MG-004 [!]` → `[x]`

**Render 배포가 끝나면 나한테 알려주세요.** 내가 운영 기업검증 E2E를 돌려서
결과 보고하고, 통과하면 TASK.md MG-004도 `[x]`로 바꿉니다. (AskUserQuestion
3번 질문에 4번 = "나중에 브랜치+메모"로 답해서, 그 지시를 여기 기록해 둠)

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
