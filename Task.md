Task.md

## Active
- 없음

## Done
- TASK-00: 통합 작업본 기준 폴더 정리
- TASK-01: P1 추천 API 기본 엔드포인트 구현
- TASK-02: CSV 로더, ISO3 정규화, 거리/무역/WB 조회 구현
- TASK-03: 프론트 분석 화면에서 P1 결과 렌더링 구현
- TASK-04: trade fallback self-test 및 pytest 통과
- TASK-05: 추천 결과 0건/저품질 데이터의 원인을 API 응답에 포함해 진단 가능하게 만들기
- TASK-06: 프론트 API 베이스 URL을 환경변수로 공통화하고 `AnalysisPage`/`AdminDashboard`의 엔드포인트를 정리하기
- TASK-07: `KOR + 330499` 기준 스모크 테스트와 `/v1/predict` 계약 회귀 테스트를 추가하기
- TASK-08: `AnalysisPage`, `AdminDashboard`, `ValueUpAIMvp`, `streamlit_app.py`의 API 베이스 URL을 환경변수/공통 설정으로 묶기
- TASK-09: `/v1/predict`의 `diagnostics`를 프론트와 관리화면에 노출하고, 0건/저품질 결과를 사람이 읽을 수 있게 보여주기
- TASK-10: `KOR + 330499 + 2023` 기준 스모크 테스트와 `/v1/predict` / `/predict` 계약 회귀 테스트를 추가하기
- TASK-11: 대시보드 프로젝트 상태 카드를 `branch / HEAD / remote / dirty / non-git` 안내 문구로 통일하기
- TASK-12: Windows 로컬 실행 산출물(`__pycache__`, `.pytest_cache`, temp/log 파일)을 `.gitignore`와 테스트 설정에서 계속 분리하기

---

## 태스크 상세

### TASK-08 — 프론트 API 베이스 URL 공통화

**심각도:** P1
**파일:** `apps/frontend-react/src/AnalysisPage.jsx`, `apps/frontend-react/src/AdminDashboard.jsx`, `apps/frontend-react/src/ValueUpAIMvp.jsx`, `services/p1-export-fit-api/streamlit_app.py`
**의존성:** 없음

**문제:**
여러 화면이 `http://localhost:8000`을 직접 박아두고 있어서, 실행 환경이 바뀌면 같은 수정이 여러 파일에 흩어진다.

**수정 방향:**
- API 베이스 URL을 한 곳의 환경변수/공통 상수로 읽는다
- 로컬 개발과 배포용 값을 분리할 수 있게 한다
- 새 화면이 추가돼도 같은 규칙을 재사용한다

**수락 기준:**
- [ ] `localhost:8000` 하드코딩이 한 군데 규칙으로 정리된다
- [ ] `AnalysisPage`, `AdminDashboard`, `ValueUpAIMvp`가 같은 베이스 URL 규칙을 쓴다
- [ ] Streamlit 입력 화면도 같은 규칙을 쓴다

---

### TASK-09 — diagnostics 화면 노출

**심각도:** P1
**파일:** `services/p1-export-fit-api/main.py`, `apps/frontend-react/src/AnalysisPage.jsx`, `apps/frontend-react/src/AdminDashboard.jsx`
**의존성:** TASK-05

**문제:**
API가 진단 정보를 내려줘도, 화면에서 바로 보이지 않으면 사용자는 결과가 왜 나왔는지 알기 어렵다.

**수정 방향:**
- `diagnostics`의 핵심 값만 화면에 보여준다
- 0건일 때 이유와 경고를 사람이 읽기 쉬운 문장으로 바꾼다
- 결과 목록과 진단 메시지를 같이 본다

**수락 기준:**
- [ ] `returned_count`, `candidate_count`, `eligible_count`를 확인할 수 있다
- [ ] `zero_result_reasons`가 0건 상태에서 보인다
- [ ] `quality_warnings`가 경고 문구로 보인다

---

### TASK-10 — 스모크/계약 테스트 추가

**심각도:** P1
**파일:** `services/p1-export-fit-api/tests/test_trade_fallback.py`, `services/p1-export-fit-api/tests`
**의존성:** TASK-05

**문제:**
핵심 추천 흐름이 바뀌면 API 응답 모양이나 330499 케이스가 쉽게 흔들릴 수 있다.

**수정 방향:**
- `KOR + 330499 + 2023`를 기준 스모크로 고정한다
- `/v1/predict`의 응답 구조를 회귀 테스트로 묶는다
- 필요하면 legacy `/predict`와의 차이도 확인한다

**수락 기준:**
- [ ] 330499 스모크 테스트가 자동으로 돈다
- [ ] `diagnostics` 필드가 계약에 포함된다
- [ ] 결과 0건 케이스와 정상 케이스가 둘 다 검증된다

---

### TASK-11 — 프로젝트 상태 문구 통일

**심각도:** P2
**파일:** `dashboard/server.py`, `dashboard/streamlit_app.py`, `dashboard/project_snapshot.py`
**의존성:** 없음

**문제:**
Git 상태가 화면마다 다르게 보이면, 사용자가 지금 저장소가 정상인지 아닌지 판단하기 어렵다.

**수정 방향:**
- 브랜치, HEAD, remote, dirty, non-git 상태를 같은 말로 보여준다
- Flask와 Streamlit에서 안내 문구를 맞춘다

**수락 기준:**
- [ ] 같은 상태에 같은 문구를 쓴다
- [ ] Git 저장소가 아니어도 화면이 깨지지 않는다
- [ ] remote 없음 상태가 별도로 구분된다

---

### TASK-12 — 런타임 산출물 분리

**심각도:** P2
**파일:** `.gitignore`, `tests/conftest.py`
**의존성:** 없음

**문제:**
로컬 실행과 테스트가 만드는 캐시/로그가 저장소에 섞이면, 진짜 코드 변경과 잡파일이 헷갈린다.

**수정 방향:**
- Windows temp, pytest cache, streamlit log를 추적 대상에서 제외한다
- 테스트가 임시 폴더를 안정적으로 쓰게 유지한다

**수락 기준:**
- [ ] `__pycache__`, `.pytest_cache`, temp 산출물이 추적되지 않는다
- [ ] 실행 로그 파일이 커밋 대상이 아니다
- [ ] Windows에서 테스트가 불필요한 권한 문제를 덜 만난다
