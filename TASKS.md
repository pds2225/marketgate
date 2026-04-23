# TASKS.md

## Active
- TASK-13: 실제 거래 데이터 보강 및 0건 원인 제거
- TASK-14: 분석 화면 MVP 기본 흐름 고정
- TASK-15: 오류/빈/로딩 상태와 예외 메시지 정리
- TASK-16: `KOR + 330499 + 2023` 스모크 및 회귀 테스트 강화
- TASK-17: 상태 카드, 로그, 산출물 정리

---

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

### TASK-13 — 실제 거래 데이터 보강 및 0건 원인 제거

**심각도:** P1
**파일:** `services/p1-export-fit-api/app/services/data_loaders.py`, `services/p1-export-fit-api/app/services/scoring.py`, `services/p1-export-fit-api/csv/*`
**의존성:** TASK-05, TASK-10

**문제:**
현재 `trade_data.csv`가 세계 합계 중심이라 국가별 추천 결과가 `0건`으로 떨어지는 경우가 남아 있다. 실제 사용성 기준에서는 가장 먼저 해결해야 하는 데이터 문제다.

**수정 방향:**
- 국가별 파트너 거래 데이터를 보강한다
- `0건`이 나오는 원인을 `diagnostics`에서 더 분명하게 구분한다
- 샘플 입력 `KOR + 330499 + 2023`이 실제 결과를 반환하도록 데이터 경로를 정리한다

**수락 기준:**
- [ ] 핵심 스모크 입력에서 추천 결과가 `0건`으로만 떨어지지 않는다
- [ ] `zero_result_reasons`가 실제 원인별로 구분된다
- [ ] `diagnostics`에 데이터 부족과 필터 제외가 구분되어 보인다

---

### TASK-14 — 분석 화면 MVP 기본 흐름 고정

**심각도:** P1
**파일:** `apps/frontend-react/src/AnalysisPage.jsx`, `apps/frontend-react/src/ValueUpAIMvp.jsx`
**의존성:** TASK-13

**문제:**
화면은 존재하지만, 실제 사용자는 입력-실행-결과 확인의 기본 흐름을 가장 짧게 끝내야 한다.

**수정 방향:**
- 기본 입력값과 샘플 입력을 더 전면에 둔다
- 분석 시작에서 결과 확인까지의 흐름을 한 번에 끝내게 한다
- MVP에서 불필요한 설명보다 실행 경로를 먼저 보여준다

**수락 기준:**
- [ ] 사용자가 샘플 입력으로 바로 실행할 수 있다
- [ ] 결과 카드와 요약 정보가 한 번에 보인다
- [ ] 첫 화면에서 핵심 기능을 찾는 데 오래 걸리지 않는다

---

### TASK-15 — 오류/빈/로딩 상태와 예외 메시지 정리

**심각도:** P1
**파일:** `services/p1-export-fit-api/main.py`, `services/p1-export-fit-api/app/services/scoring.py`, `apps/frontend-react/src/AnalysisPage.jsx`, `apps/frontend-react/src/AdminDashboard.jsx`
**의존성:** TASK-13, TASK-14

**문제:**
실사용 MVP는 잘 되는 경우보다, 실패했을 때 앱이 안 죽고 다음 행동을 알려주는지가 중요하다.

**수정 방향:**
- API와 프론트 모두에서 빈 상태, 로딩 상태, 오류 상태를 일관되게 보여준다
- 예외 메시지를 사용자 친화적으로 정리한다
- 실패했을 때도 화면이 깨지지 않게 한다

**수락 기준:**
- [ ] 예외 상황에서도 앱이 종료되지 않는다
- [ ] 빈 상태와 로딩 상태가 명확히 구분된다
- [ ] 사용자가 다음에 무엇을 해야 하는지 알 수 있다

---

### TASK-16 — `KOR + 330499 + 2023` 스모크 및 회귀 테스트 강화

**심각도:** P1
**파일:** `services/p1-export-fit-api/tests/test_trade_fallback.py`, `services/p1-export-fit-api/tests`
**의존성:** TASK-13, TASK-15

**문제:**
실제 사용 가능한 상태를 유지하려면, 핵심 입력 조합이 매번 같은 방식으로 검증되어야 한다.

**수정 방향:**
- `KOR + 330499 + 2023`을 고정 스모크로 둔다
- `/v1/predict`와 legacy `/predict` 응답 계약을 함께 점검한다
- 0건, 정상, 경계 케이스를 모두 묶는다

**수락 기준:**
- [ ] 스모크 테스트가 자동으로 통과한다
- [ ] `/v1/predict` 계약이 깨지면 바로 잡힌다
- [ ] 0건과 정상 결과가 모두 검증된다

---

### TASK-17 — 상태 카드, 로그, 산출물 정리

**심각도:** P2
**파일:** `dashboard/server.py`, `dashboard/streamlit_app.py`, `dashboard/project_snapshot.py`, `.gitignore`
**의존성:** TASK-14, TASK-15

**문제:**
프로젝트가 실제로 쓰이려면, 화면과 로그에서 지금 상태를 바로 알아야 한다.

**수정 방향:**
- 상태 카드 문구를 한 가지 기준으로 맞춘다
- 실행 산출물과 런타임 파일이 저장소를 오염시키지 않게 한다
- Git 상태와 실행 상태를 사람이 바로 읽을 수 있게 정리한다

**수락 기준:**
- [ ] 상태 문구가 화면마다 다르지 않다
- [ ] 런타임 산출물이 저장소를 더럽히지 않는다
- [ ] Git 비저장소 상태에서도 화면이 깨지지 않는다
