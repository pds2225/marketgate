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
