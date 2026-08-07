# 작업 진행 현황 — 2026-08-06

## 완료

- [x] **DATABASE_URL 설정** — Neon PostgreSQL 연결 문자열 `.env` + Render 대시보드 반영
- [x] **SQL 인젝션 방어** — `auth_store.py` `_db_update_user`에 컬럼 화이트리스트 적용
- [x] **CSS deslop Pass 1** — dead landing-hero grid, `.analysis-detail-row` 충돌 제거
- [x] **CSS deslop Pass 2** — `#3b82f6` → `--landing-blue` 색상 통일 (quickstart, chat mode)
- [x] **성능 최적화 1차** — `score_buyers()` target context/opportunity 캐싱, opportunity 2회→1회 순회
- [x] **성능 최적화 2차** — pandas 벡터 프리필터 (HS prefix + keyword overlap), target_terms 사전 계산
- [x] **벤치마크** — 3,552행 기준 1.78초→0.28초 (6.2x 향상)
- [x] **회원가입 UX** — 가입 완료 메시지 표시 (자동 로그인 제거)
- [x] **PricingPage 글씨체** — DM Sans/Bebas Neue/DM Mono → Pretendard 통일
- [x] **SimulationPage 다크테마 제거** — GitHub dark(#0d1117) → 앱 디자인 시스템(밝은 배경) 통일
- [x] **E2E 검증** — 회원가입→로그인→바이어검색→인콰이어리 생성/제출 전체 통과

## 진행 중

- [ ] **커밋 미완료** — SimulationPage 다크테마 수정 커밋 필요
- [ ] **바이어 검색 속도** — Render 서버에서 predict 엔드포인트 응답 시간 최적화

## 대기

- [ ] **CSS deslop Pass 3** — remaining zombie 스타일 정리 (추가 분석 필요)
- [ ] **국가 수 제한** — predict 추천 국가 10개→3개로 줄이기
- [ ] **바이어 수 확대** — demo/buyers 60명 제한 해제 또는 predict 결과 바이어 수 확인
