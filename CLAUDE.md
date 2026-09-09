# Claude Code Working Rules

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

## E2E 요청 예외
사용자가 `E2E`, `실사용 검증`, `브라우저 검증`, `로그인부터 끝까지 확인`을 요청하면 파일명을 다시 묻지 않는다.

이 경우 아래 기존 진입점만 사용한다.

1. `apps/frontend-react/playwright.config.js`
2. 요청과 직접 관련된 `apps/frontend-react/tests/e2e/*.spec.js` 1개
3. 필요할 때만 해당 기능 파일 1개

MarketGate 운영 MG-004 흐름 검증은 이미 있는 아래 테스트를 우선 실행한다.

`apps/frontend-react/tests/e2e/mg004-prod-verification.spec.js`

Windows MCP에서 PowerShell/터미널을 사용할 수 있으면 브라우저를 손으로 클릭하기 전에 기존 Playwright를 먼저 실행한다.

```powershell
cd apps/frontend-react
$env:E2E_BASE_URL="https://marketgate.vercel.app"
$env:E2E_API_BASE_URL="https://marketgate.onrender.com"
$env:E2E_WRITE_ENABLED="true"
npx playwright test tests/e2e/mg004-prod-verification.spec.js --project=chromium
```

이 테스트는 사용자의 GitHub 비밀번호를 요구하지 않는다. 임시 E2E 계정을 API로 생성하고 로그인 토큰을 브라우저에 주입해 실제 화면을 검증한다.

Playwright 실행이 브라우저 실행파일 부재로만 실패하면 그때만 아래를 1회 실행한다.

```powershell
npx playwright install chromium
```

Playwright가 기능 오류로 실패하면:
- Browser 연결로 `https://marketgate.vercel.app`에서 같은 실패 지점을 재현한다.
- 실패 화면/응답 상태를 확인한다.
- 테스트를 건너뛰거나 mock으로 대체하지 않는다.
- 사용자에게 로그인 비밀번호 입력을 요구하지 않는다.
- 실패 원인과 실제 사용자 영향만 짧게 보고한다.

E2E PASS 기준:
- 실제 배포 화면 사용
- 실제 Render API 사용
- 로그인 또는 인증 상태 확인
- 요청한 사용자 흐름을 처음부터 끝까지 완료
- 최종 화면 결과 확인

단위 테스트/build 성공만으로 E2E PASS라고 하지 않는다.

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
