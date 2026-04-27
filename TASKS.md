# TASKS.md — MarketGate MVP (인콰이어리 E2E)

**목표:** 사용자가 HS코드 입력 → 바이어 조회 → 인콰이어리 발송까지 오류 없이 실행 가능한 MVP
**테스트 경로:** `services/p1-export-fit-api/`
**실행 명령:** `cd services/p1-export-fit-api && python -m pytest --tb=short -q`

---

## Active

### 📬 Phase 2 — 인콰이어리 기능 구현

- [x] **[M04] inquiry_service.py 생성** — services/p1-export-fit-api/app/services/inquiry_service.py 신규 작성. 입력: buyer_name, contact_email, hs_code, sender_company, sender_name, message(optional). 출력: inquiry_id(uuid4), draft_ko(한국어 템플릿), draft_en(영어 템플릿), created_at. 완료 기준: tests/test_inquiry_service.py PASS
- [x] **[M05] POST /v1/inquiry 엔드포인트 구현** — services/p1-export-fit-api/main.py에 POST /v1/inquiry 추가. inquiry_service.build_draft() 호출 후 결과 반환. 응답: {inquiry_id, draft_ko, draft_en, status: "draft_ready"}. 완료 기준: tests/test_inquiry_endpoint.py PASS
- [x] **[M06] 인콰이어리 템플릿 한/영 완성** — inquiry_service.py의 draft_ko/draft_en에 buyer_name, hs_code, sender_company, sender_name 치환 정상 동작. 빈값 입력 시 "Unknown" fallback 처리. 완료 기준: test_inquiry_template_substitution PASS

### 🖥️ Phase 3 — 프론트엔드 연결

- [x] **[M07] 바이어 카드 contact 정보 표시** — apps/frontend-react/src/AnalysisPage.jsx 바이어 카드에 contact_email, contact_phone, contact_website 렌더링 추가. contact 없으면 "연락처 미제공" badge 표시. 완료 기준: JSX에 contact 블록 및 null 분기 처리 코드 존재
- [x] **[M08] 인콰이어리 모달 UI 구현** — AnalysisPage.jsx에 바이어 카드별 "인콰이어리 보내기" 버튼 추가. 클릭 시 모달: sender_company, sender_name, message 입력 폼 → POST /v1/inquiry 호출. 성공 시 draft_en 표시, 실패 시 에러 메시지. 완료 기준: InquiryModal 컴포넌트 및 handleSubmit 함수 존재
- [x] **[M09] 오류/빈/로딩 3종 상태 처리** — AnalysisPage.jsx에서 (1) API 호출 중 LoaderCircle 스피너, (2) buyers.items 길이 0일 때 "조건에 맞는 바이어를 찾지 못했습니다" 안내, (3) 인콰이어리 POST 실패 시 "잠시 후 다시 시도해 주세요" 메시지. 완료 기준: 3가지 분기 코드 존재

### ✅ Phase 4 — E2E 검증

- [x] **[M10] E2E 스모크 테스트 작성** — services/p1-export-fit-api/tests/test_e2e_smoke.py 신규 작성. (1) GET /health 200, (2) GET /v1/buyers?hs_code=330499&country=USA items>=1 + has_contact True 항목 존재, (3) POST /v1/inquiry {buyer_name, contact_email, hs_code, sender_company, sender_name} → draft_en 비어있지 않음. 완료 기준: 3개 테스트 PASS
- [x] **[M11] CORS 설정 검증** — services/p1-export-fit-api/main.py CORS origins에 http://localhost:5173 포함 확인 및 누락 시 추가. 완료 기준: test_cors_origins_include_frontend PASS
- [x] **[M12] 전체 pytest 회귀 통과** — services/p1-export-fit-api/ 전체 pytest 0 failed. 완료 기준: pytest --tb=short -q exit code 0

---

## Done

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
