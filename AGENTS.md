# Codex Working Rules

## 절대 원칙
- 전체 프로젝트를 탐색하지 마라.
- Explore 사용 금지.
- 디렉토리 전체 읽기 금지.
- 요청받은 파일 외 접근 금지.
- 3개 파일 이상 읽기 금지.
- 필요 없는 파일 열지 마라.
- 작업 전에 수정 대상 파일을 먼저 명시하라.
- 수정 전후 변경 요약을 짧게 출력하라.

## 읽기 제한
- 기본적으로 사용자가 지정한 파일만 읽는다.
- 파일이 지정되지 않았으면 먼저 사용자에게 대상 파일명을 요청한다.
- 임의로 프로젝트 구조를 파악하려고 하지 않는다.
- 한 번에 200줄 이상 읽지 않는다.

## 수정 제한
- 기존 구조 최대한 유지.
- 최소 변경 원칙.
- 큰 리팩토링 금지.
- 새 라이브러리 추가 금지.
- API 응답 구조 변경 금지.
- 테스트/문서가 있으면 필요한 범위에서만 업데이트.

## 동시작업 규칙
- Codex가 작업 중인 파일은 수정하지 않는다.
- 같은 파일을 동시에 수정하지 않는다.
- 새 파일 생성 작업은 tools/, docs/처럼 충돌 적은 위치에서만 수행한다.

## 출력 제한
- 최대 300줄 이하.
- 요약 중심.
- 불필요한 코드베이스 설명 금지.
- 작업 결과는 아래 형식으로만 출력한다.

## 출력 형식
1. 읽은 파일 목록
2. 수정 파일 목록
3. 변경 요약
4. 실행 명령
5. 테스트 결과
6. 충돌 가능성
7. 다음 프롬프트 1개

## Cursor Cloud specific instructions

### Services overview

| Service | Location | Start command |
|---|---|---|
| **p1-export-fit-api** (FastAPI) | `services/p1-export-fit-api/` | `uvicorn main:app --reload --port 8000` |
| **frontend-react** (Vite + React 19) | `apps/frontend-react/` | `npm run dev` (requires Node 20.x via nvm) |
| **cosmetics_mvp_preprocess** | `services/cosmetics_mvp_preprocess/` | Scripts only — no long-running server |

### Running services

- **Backend API** must start from `services/p1-export-fit-api/` directory (it loads CSV files via relative paths).
- **Frontend** runs on port 5173 and expects the API at `localhost:8000`. CORS is configured for `localhost:5173`.
- Node.js 20.x is installed via nvm. Source nvm before running node/npm: `export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"`

### Lint / Test / Build

- **Frontend lint**: `cd apps/frontend-react && npx eslint .` (pre-existing lint errors exist in the codebase)
- **Frontend build**: `cd apps/frontend-react && npm run build`
- **API tests**: `cd services/p1-export-fit-api && python3 -m pytest tests/ -v` (13/14 pass; 1 pre-existing failure in `test_build_buyer_shortlist_merges_top_three_countries`)
- **Preprocess tests**: `cd services/cosmetics_mvp_preprocess && python3 -m pytest tests/ -v` (98/101 pass; 3 pre-existing failures due to missing `python` symlink and subprocess calls)

### Gotchas

- The `python` command is not available by default (only `python3`). Some subprocess calls in `cosmetics_mvp_preprocess` tests fail because of this.
- The frontend uses client-side state routing (not URL routing). All navigation is via button clicks from the landing page.
- The export recommendation flow is accessed via "수출 플로우 시작" button on the landing page, not the chat mode.
