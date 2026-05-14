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

# MarketGate React/Vercel 작업 고정 규칙

이번 프로젝트의 웹사이트 개선 대상은 Vercel에 배포되는 React 프론트엔드다.

작업 기준:
- 작업 대상 폴더: apps/frontend-react
- 로컬 확인 URL: http://localhost:5173/
- 배포 확인 URL: https://marketgate.vercel.app
- Streamlit localhost:8503은 이번 웹사이트 개선 대상이 아니다.
- services/p1-export-fit-api/streamlit_app.py 수정 금지

주요 파일:
- apps/frontend-react/src/LandingPage.jsx
- apps/frontend-react/src/AnalysisPage.jsx
- apps/frontend-react/src/App.css
- apps/frontend-react/src/App.jsx

필수 제한:
- 백엔드 수정 금지
- API 응답 구조 변경 금지
- 새 라이브러리 추가 금지
- 대규모 리팩토링 금지
- 기존 구조 유지
- 최소 변경 패치
- TASKS.md와 auto_prompt_*.md는 건드리지 말 것

검증 기준:
1. apps/frontend-react에서 npm run build 성공
2. npm run dev 실행 후 http://localhost:5173/ 확인
3. 화면 잘림 여부 확인
4. 문제 없으면 GitHub main에 push
5. Vercel https://marketgate.vercel.app 에서 최종 확인

응답 시 항상 구분:
- localhost:5173 = React 로컬 개발 화면
- marketgate.vercel.app = React Vercel 배포 화면
- localhost:8503 = Streamlit 로컬 화면, 이번 작업 대상 아님

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

## 프로젝트별 한 줄 지침

- React/Vercel 앱, FastAPI 서비스, Streamlit 실험 화면을 혼동하지 않는다.
- 로컬 React는 `localhost:5173`, 배포 React는 `marketgate.vercel.app`, 별도 Streamlit은 `localhost:8503` 기준으로 구분한다.
- `credits.json` 같은 런타임 데이터는 기능 코드와 분리하고, 사용자가 명시하지 않으면 커밋하지 않는다.
## 프로젝트별 작업 지침

### 1. 프로젝트 목적

- 이 프로젝트는 MarketGate의 React/Vercel 화면, FastAPI 서비스, 전처리 도구를 함께 관리하는 저장소다.
- AI는 React 로컬 화면, Vercel 배포 화면, Streamlit 실험 화면을 항상 구분한다.
- 요구사항이 애매하면 새 기능을 만들지 말고, 기존 React/API 흐름을 깨지 않는 최소 수정으로 처리한다.

### 2. 절대 수정 금지

- `.env`, `.env.*` 파일은 절대 수정하거나 내용을 출력하지 않는다.
- `.github/workflows/*`는 사용자가 명시적으로 요청하지 않으면 수정하지 않는다.
- `credits.json` 같은 런타임 데이터는 사용자가 명시하지 않으면 커밋하지 않는다.
- API Key, Token, 비밀번호, 쿠키 값은 답변이나 로그에 출력하지 않는다.

### 3. 수정 허용 범위

- 요청과 직접 관련된 파일만 수정한다.
- React 화면 작업은 기본적으로 `apps/frontend-react` 안에서 처리한다.
- API 응답 구조, DB 구조, 새 라이브러리는 사용자가 명시하지 않으면 변경하지 않는다.
- 단순 버그 수정에서 전면 리팩토링을 하지 않는다.

### 4. 실행/검증 기준

```powershell
cd D:\marketgate\apps\frontend-react
npm run build
```

- FastAPI 검증이 필요할 때만 해당 서비스 폴더에서 Python 테스트를 실행한다.
- 실행 확인을 못 했으면 "미검증"이라고 명확히 말한다.

### 5. Git 규칙

- 사용자가 요청하지 않으면 커밋하지 않는다.
- 사용자가 요청하지 않으면 push하지 않는다.
- 커밋 전에는 `git status --short`로 포함 파일을 확인한다.
- 런타임 데이터, 캐시, 로그, `.env`, 개인 설정 파일은 커밋하지 않는다.

### 6. 보고 형식

```text
상태: 정상 실행 확인됨 / 수정만 완료 / 미검증 / 실행 막힘

수정 파일:
- D:\path\file.py: 수정 이유

검증:
- 실행 명령어:
- 결과:

주의:
- 남은 리스크 또는 사람이 확인할 항목
```

### 7. 자주 하는 실수 방지

- `localhost:5173`은 React 로컬 화면, `marketgate.vercel.app`은 React 배포 화면, `localhost:8503`은 Streamlit 화면이다.
- `TASKS.md`와 `auto_prompt_*.md`는 작업 요청이 없으면 건드리지 않는다.
- Windows에서는 Bash 명령어 대신 PowerShell 명령어를 쓴다.
- 포트가 열렸다는 것과 앱이 정상 동작한다는 것을 구분한다.

