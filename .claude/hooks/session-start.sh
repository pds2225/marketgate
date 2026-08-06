#!/bin/bash
# Claude Code on the web 세션이 시작될 때 의존성을 설치한다.
# 이 훅이 없으면 원격 세션에서 pytest / npm run lint / npm run test:unit 이
# 모듈 없음으로 바로 실패한다.
set -euo pipefail

# 로컬(개발자 PC) 세션에서는 건드리지 않는다. 웹 세션 전용.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

echo "[session-start] 백엔드 의존성 설치 (services/p1-export-fit-api)"
python3 -m pip install --quiet --disable-pip-version-check \
  -r services/p1-export-fit-api/requirements.txt

# pytest 와 httpx 는 requirements.txt 에 없지만 테스트 실행에 반드시 필요하다.
#   - README 의 `python -m pytest` 가 pytest 를 요구
#   - tests/ 가 쓰는 fastapi.testclient.TestClient 가 내부적으로 httpx 를 요구
# 런타임 의존성이 아니므로 requirements.txt 는 건드리지 않고 여기서만 채운다.
echo "[session-start] 백엔드 테스트 도구 설치 (pytest, httpx)"
python3 -m pip install --quiet --disable-pip-version-check pytest httpx

echo "[session-start] 프론트엔드 의존성 설치 (apps/frontend-react)"
# npm ci 가 아니라 npm install 을 쓴다 — 컨테이너 상태가 캐시되므로
# 이미 설치된 경우 훨씬 빨리 끝난다(멱등).
# Playwright 브라우저는 이미지에 포함돼 있고(PLAYWRIGHT_BROWSERS_PATH),
# PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 이 재다운로드를 막는다. playwright install 금지.
(cd apps/frontend-react && npm install --no-audit --no-fund)

echo "[session-start] 완료"
