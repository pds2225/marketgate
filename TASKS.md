# TASKS.md — MarketGate MVP (인콰이어리 E2E)

**목표:** 사용자가 HS코드 입력 → 바이어 조회 → 인콰이어리 발송까지 오류 없이 실행 가능한 MVP
**테스트 경로:** `services/p1-export-fit-api/`
**실행 명령:** `cd services/p1-export-fit-api && python -m pytest --tb=short -q`
**개발현황 기준 시트:** [MarketGate 개발현황 모니터링 v3](https://docs.google.com/spreadsheets/d/1lmzSGu0fPYwVaoP82n-9tbMGtUmzE_G1j2wcblZldQg/edit)
**동기화 규칙:** GitHub의 WBS 상태가 변경되면 같은 작업 내에서 기준 시트의 상태도 갱신하고 재읽기 검증한다.

---

## Phase 0 체크포인트 — 2026-07-25

- **재개 기준:** `main@d1a564994c6d1b3acdcfdd86a549f1546fc0676f` ([PR #68](https://github.com/pds2225/marketgate/pull/68))
- **완료 WBS 14건:** `W-001`, `W-008`~`W-020`
- **완료 산출물:** 17테이블 DDL·ERD·데이터 사전, Vault Access Broker, Vault 키 레지스트리·회전 경계, PostgreSQL 16 회귀 CI
- **검증 결과:** Phase 0 스키마 5/5, Vault Broker 7/7, PostgreSQL 16.14에서 `0001→0003`·`pgcrypto`·키 회전·롤백·권한 경계 통과 ([Actions run](https://github.com/pds2225/marketgate/actions/runs/30149928926))
- **다음 개발 순서:** `W-003` 컴플라이언스 정책표 → `W-021` Source Rights Registry → `W-022` Legal Basis Ledger → `W-023` Suppression Registry → `W-024` Compliance Decision Engine
- **운영 배포 조건:** 실제 KMS·Secrets 어댑터가 키 값을 DB 외부에서 주입하도록 연결하고 운영 키·권한을 분리
- **재검증 보류:** SQL 보안 독립 리뷰 1회

---

## Active

### 🏢 CV — 해외기업 기본검증

> 무료 기본검증은 법인 실체·등록상태·입력정보 일치 여부까지만 제공한다. `fitScore`, 기존 `creditStatus`, `core.buyers.verification_status`와 신규 `registryCheckStatus`를 혼합하지 않는다. OpenCorporates는 Mock Adapter부터 구현하고 D&B·K-SURE는 공식 외부 링크만 제공한다.

- [ ] **[CV-01] 해외기업 기본검증 DB 마이그레이션** — `db/migrations/0005_company_registry_checks.sql` 추가. 재실행 가능한 SQL, 5개 `registry_check_status`, 선택값 NULL, 기존 인증·결제·크레딧 테이블 비변경. `run_migrations.py`를 `0004→0005` 순차 실행으로 수정. 완료 기준: 최초 실행·재실행·제약조건 테스트 통과.
- [ ] **[CV-02] OpenCorporates Mock 기본검증 API** — `POST /v1/company-verifications`, `GET /v1/company-verifications/{verification_id}` 구현. 정상·일부정보·불일치·비활성·신용조사 필요·결과없음·Provider 오류·타임아웃의 결정적 Mock 시나리오 제공. `get_current_user` 인증 적용. 완료 기준: 400·404·502·504·500 및 DB 저장 테스트 통과.
- [ ] **[CV-03] BuyerSearch 기본검증 카드** — 새 전역 페이지나 Router를 만들지 않고 `apps/frontend-react/src/pages/BuyerSearch/index.tsx` 상세 단계에 `CompanyBasicVerificationCard` 추가. 기존 바이어명·국가 자동입력, 빈값·로딩·결과없음·오류·타임아웃 처리, D&B·K-SURE 외부 링크 제공. 완료 기준: 기존 바이어 검색 흐름과 `contactStatus / tradeStatus / creditStatus` 회귀 없음.
- [ ] **[CV-04] 기본검증 테스트·회귀검증** — DB·Adapter·API·화면 단위테스트와 로그인→바이어검색→상세→기본검증 E2E 작성. 신용점수·안전점수·지급능력 판정·임의 데이터 미노출 확인. 완료 기준: 백엔드 pytest, 프론트 unit·lint·build·E2E smoke 통과.
- [ ] **[CV-05] K-SURE·D&B PRD 정정** — `PRD_C1_ksure_api.md`, `PRD_C3_dnb_api.md`에서 검증되지 않은 API·등급 자동조회 가정을 제거하고 현재 MVP를 외부 공식 조회 링크로 한정. 실제 API 연동은 계약·비용·저장·표시·재이용 권한 확인 후 별도 PRD로 진행. 완료 기준: 문서 간 상태·용어·범위 일치.

### 🧭 A-MVP — Landing 진입 경로

- [x] **[A-001] Landing CTA 연결** — `LandingPage.jsx` 하단 CTA에서 유망국 분석(`AnalysisPage`), 수출 플로우(`ExportFlowPage`), 바이어 검색(`BuyerSearchPage`)으로 진입 가능. 기존 `App.jsx` 상태 라우팅 재사용, 새 라이브러리·백엔드 변경 없음. 검증: CTA/라우트 6/6 정적 연결 확인, `npm run build` 통과.

### 📬 Phase 2 — 인콰이어리 기능 구현

- [x] **[M04] inquiry_service.py 생성** — services/p1-export-fit-api/app/services/inquiry_service.py 신규 작성. 입력: buyer_name, contact_email, hs_code, sender_company, sender_name, message(optional). 출력: inquiry_id(uuid4), draft_ko(한국어 템플릿), draft_en(영어 템플릿), created_at. 완료 기준: tests/test_inquiry_service.py PASS
- [x] **[M05] POST /v1/inquiry 엔드포인트 구현** — services/p1-export-fit-api/main.py에 POST /v1/inquiry 추가. inquiry_service.build_draft() 호출 후 결과 반환. 응답: {inquiry_id, draft_ko, draft_en, status: "draft_ready"}. 완료 기준: tests/test_inquiry_endpoint.py PASS
- [x] **[M06] 인콰이어리 템플릿 한/영 완성** — inquiry_service.py의 draft_ko/draft_en에 buyer_name, hs_code, sender_company, sender_name 치환 정상 동작. 빈값 입력 시 "Unknown" fallback 처리. 완료 기준: test_inquiry_template_substitution PASS

### 🖥️ Phase 3 — 프론트엔드 연결

- [x] **[M07] 바이어 카드 contact 정보 표시** — apps/frontend-react/src/AnalysisPage.jsx 바이어 카드에 contact_email, contact_phone, contact_website 렌더링 추가. contact 없으면 "연락처 미제공" badge 표시. 완료 기준: JSX에 contact 블록 및 null 분기 처리 코드 존재
- [x] **[M08] 인콰이어리 모달 UI 구현** — AnalysisPage.jsx에 바이어 카드별 "인콰이어리 보내기" 버튼 추가. 클릭 시 모달: sender_company, sender_name, message 입력 폼 → POST /v1/inquiry 호출. 성공 시 draft_en 표시, 실패 시 에러 메시지. 완료 기준: InquiryModal 컴포넌트 및 handleSubmit 함수 존재
- [x] **[M09] 오류/빈/로딩 3종 상태 처리** — AnalysisPage.jsx에서 (1) API 호출 중 LoaderCircle 스피너, (2) buyers.items 길이 0일 때 "조건에 맞는 바이어를 찾지 못했습니다" 안내, (3) 인콰이어리 POST 실패 시 "잠시 후 다시 시도해 주세요" 메시지. 완료 기준: 3가지 분기 코드 존재

### ✅ Phase 4 — E2E 검증

- [x] **[M10] E2E 스모크 테스트 작성** — services/p1-export-fit-api/tests/test_e2e_smoke.py. (1) GET /health 200, (2) conftest 목 인증을 걷어낸 진짜 경로: register → login → Bearer 토큰, 무인증 호출은 401/403, (3) POST /v1/predict {hs_code 330499} → results 비어있지 않음 + buyers.items 중 contact_email 보유 1건 이상, (4) POST /v1/inquiries → draft_en 비어있지 않음 → /v1/inquiries/{id}/submit → review_required. 완료 기준: test_e2e_smoke.py 전체 PASS (2026-07-28 실물 테스트로 대체 검증)
- [x] **[M11] CORS 설정 검증** — services/p1-export-fit-api/main.py CORS origins에 http://localhost:5173 및 https://marketgate.vercel.app 포함. 설정 문자열이 아니라 실제 응답 헤더로 확인하고, 미허용 출처는 반사되지 않음을 함께 검증. 완료 기준: tests/test_e2e_smoke.py::test_cors_origins_include_frontend PASS (2026-07-28 실물 테스트로 대체 검증)
- [x] **[M12] 전체 pytest 회귀 통과** — services/p1-export-fit-api/ 전체 pytest 0 failed. 완료 기준: pytest --tb=short -q exit code 0

---

- [x] [TASK-08] 콘텐츠 크기 통일 작업
  - 원본 태스크: TASK-08
  - 의존성: 없음
  - 검증: UI 리뷰 및 QA 테스트 수행

- [x] [TASK-09] 페이지 이동 경로 통합
  - 원본 태스크: TASK-09
  - 의존성: 없음
  - 검증: 사용자 테스트를 통한 기능 검증

- [x] [TASK-10] 콘텐츠 크기 통일 및 일관성 수정
  - 원본 태스크: TASK-10
  - 의존성: 없음
  - 검증: 디자인 프로토타입 또는 화면 스크린샷 비교 검토

- [x] [TASK-11] 단일 루트 페이지 이동 경로 설정
  - 원본 태스크: TASK-11
  - 의존성: 없음
  - 검증: 이동 경로 시나리오 테스트 및 사용자 피드백 확인

## Done

- [x] [A1-02] GET /v1/credits/balance 엔드포인트 구현 (2026-05-21)
- [x] [B3-01] 바이어 DB MOQ 필드 확인 및 보완 (2026-05-13)
- [x] [B1-01] 관세율·물류비 데이터 로더 구현 (2026-05-13)
- [x] [A2-02] GET/POST /v1/subscription 엔드포인트 구현 (2026-05-13)
- [x] [A2-01] 구독 저장소와 플랜 상수 정의 (2026-05-13)
- [x] [A1-05] GET /v1/credits/history 엔드포인트와 프론트 잔액 표시 (2026-05-13)
- [x] [A1-04] POST /v1/credits/deduct 엔드포인트와 유료 기능 차감 연결 (2026-05-13)
- [x] [A1-03] POST /v1/credits/charge 엔드포인트 구현 (2026-05-13)
- [x] TASK-00: 통합 작업본 기준 폴더 정리
- [x] TASK-01: P1 추천 API 기본 엔드포인트 구현
- [x] TASK-02: CSV 로더, ISO3 정규화, 거리/무역/WB 조회 구현
- [x] TASK-03: 프론트 분석 화면에서 P1 결과 렌더링 구현
- [x] TASK-04: trade fallback self-test 및 pytest 통과
- [x] TASK-05: 추천 결과 0건/저품질 원인 API 응답 포함
- [x] TASK-06: 프론트 API 베이스 URL 환경변수 공통화
- [x] TASK-07: KOR + 330499 스모크 테스트 및 회귀 테스트
- [x] M01: data_loaders.py 절대경로 수정 (이미 구현됨)
- [x] M02: blocked buyer 필터 구현 (이미 구현됨)
- [x] M03: 전체 109 테스트 통과 확인
