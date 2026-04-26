# TASK.md — valueup-mvp

> 대상 프로젝트: D:/valueup-mvp/unified_workspace_20260418
> 생성일: 2026-04-23
> 목표: 가장 빠르게 실제로 사용 가능한 MVP 만들기

---

## Active

### 실제 사용 가능 MVP (P1)

- [x] [TASK-01] selected opportunity가 사용자 입력 HS코드와 키워드를 최우선으로 반영하도록 최소 변경 패치하고 `/v1/predict` buyers 품질과 건수를 before/after로 비교하기
- [x] [TASK-02] 입력한 값에 맞는 적합한 바이어가 더 많이 나오도록 shortlist 필터와 점수 규칙을 최소 변경으로 보강하기
- [ ] [TASK-03] 분석 화면에서 입력, 로딩, 빈 상태, 오류 상태, 결과 상태를 비개발자 기준으로 바로 이해되게 고정하기
- [ ] [TASK-04] `/v1/predict` 핵심 스모크 입력과 buyers 결과 품질 회귀 테스트를 고정하기

### 문서와 실행 정리 (P2)

- [ ] [TASK-05] README와 TASK 문서를 현재 MVP 실행 기준과 검증 기준으로 짧게 업데이트하기

## Done

- [x] [TASK-00] opportunity_item의 빈 `hs_code_norm`을 화장품 키워드 기준으로 보강하기

---

## 태스크 상세

### TASK-01 — opportunity 선택 정확도 우선

**심각도:** P1
**파일:** `services/cosmetics_mvp_preprocess/shortlist_service.py`, `services/cosmetics_mvp_preprocess/task05_shortlist.py`, `services/p1-export-fit-api/app/services/buyer_shortlist.py`
**의존성:** TASK-00

**문제:**
현재는 `opportunity_item`에 일부 `hs_code_norm`이 채워져도, 실제 선택된 opportunity가 사용자 입력 HS/키워드와 안 맞는 경우가 남아 있다.

**수정 방향:**
- opportunity 선택에서 `target_hs_code_norm`, `target_keywords_norm` 일치도를 우선 반영한다
- 기존 구조는 유지하고 선택 기준만 최소 변경으로 보강한다
- `/v1/predict` 기준으로 buyers 결과를 before/after 비교한다

**수락 기준:**
- [ ] 선택된 opportunity가 입력 품목과 더 직접적으로 연결된다
- [ ] `/v1/predict` buyers 결과의 엉뚱한 케이스가 줄어든다
- [ ] before/after 비교 결과가 로그나 테스트로 남는다

---

### TASK-02 — 적합한 바이어 더 많이 나오게 보강

**심각도:** P1
**파일:** `services/cosmetics_mvp_preprocess/task06_fit_score.py`, `services/cosmetics_mvp_preprocess/shortlist_service.py`, `services/p1-export-fit-api/app/services/buyer_shortlist.py`
**의존성:** TASK-01

**문제:**
입력값과 맞는 바이어가 충분히 있더라도, 현재 shortlist 규칙 때문에 실제 노출 수와 적합도가 기대보다 낮을 수 있다.

**수정 방향:**
- hard gate, keyword match, contact signal, score threshold를 최소 변경으로 조정한다
- 입력값과 맞는 바이어가 더 많이 보이게 하되 엉뚱한 결과는 늘리지 않는다
- buyers 품질과 건수를 함께 비교한다

**수락 기준:**
- [ ] 입력값과 맞는 바이어가 더 많이 나온다
- [ ] 품질이 낮은 바이어가 무분별하게 늘지 않는다
- [ ] 핵심 스모크 입력에서 결과 품질이 유지되거나 개선된다

---

### TASK-03 — 화면 상태 고정

**심각도:** P1
**파일:** `apps/frontend-react/src/AnalysisPage.jsx`, `services/p1-export-fit-api/main.py`, `services/p1-export-fit-api/app/models.py`
**의존성:** TASK-01, TASK-02

**문제:**
실제 사용 가능한 MVP는 결과만이 아니라, 입력/로딩/빈/오류 상태가 명확해야 한다.

**수정 방향:**
- 로딩, 빈 결과, 오류, 정상 결과를 비개발자가 바로 이해할 문구로 고정한다
- 입력값이 잘못되면 즉시 안내한다
- 화면이 깨지지 않게 유지한다

**수락 기준:**
- [ ] 입력 검증이 있다
- [ ] 로딩, 오류, 빈 상태가 분리된다
- [ ] 정상 결과가 한 번에 읽힌다

---

### TASK-04 — 회귀 테스트 고정

**심각도:** P1
**파일:** `services/p1-export-fit-api/tests/test_trade_fallback.py`, `services/cosmetics_mvp_preprocess/tests`
**의존성:** TASK-01, TASK-02

**문제:**
핵심 입력 조합에서 결과가 흔들리면 MVP를 계속 믿고 쓸 수 없다.

**수정 방향:**
- `KOR + 330499 + 2023`을 기본 스모크로 유지한다
- buyers 품질/건수 비교가 자동으로 다시 확인되게 한다
- 정상, 빈 결과, 오류 케이스를 묶는다

**수락 기준:**
- [ ] 핵심 스모크 테스트가 자동으로 돈다
- [ ] buyers 결과 회귀가 있으면 바로 드러난다
- [ ] 오류/빈 상태 케이스도 검증된다

---

### TASK-05 — README와 실행 기준 정리

**심각도:** P2
**파일:** `README.md`, `TASK.md`
**의존성:** TASK-03, TASK-04

**문제:**
실행 경로와 검증 기준이 문서에 남지 않으면 비개발자가 다시 쓰기 어렵다.

**수정 방향:**
- Windows 기준 실행법을 가장 짧게 정리한다
- 현재 MVP에서 확인할 입력값과 기대 결과를 문서에 남긴다

**수락 기준:**
- [ ] 실행 명령어가 짧게 정리된다
- [ ] 핵심 검증 입력이 문서에 남는다
- [ ] 현재 작업 기준이 TASK와 README에 반영된다
