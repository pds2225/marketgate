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
- [x] **Vercel API 프록시** — `vercel.json`에 `/api/*` → Render rewrite 추가 (세션 만료 해결)
- [x] **데이터스토어 최적화** — `_build_mofa_lookup` 캐시, `pd.Series` 생성 제거
- [x] **국가 수 제한** — top_n 기본값 10→3으로 변경
- [x] **E2E 검증** — 회원가입→로그인→바이어검색→인콰이어리 생성/제출 전체 통과

## 커밋 이력

```
a05dcf5 feat: reduce default top_n from 10 to 3 countries
8c73bdd fix: Vercel API proxy + cache mofa_lookup in DataStore
818c47a fix: SimulationPage dark theme to match app design system
29d8cee perf: vectorized pre-filter in score_buyers + auth/pricing fixes
9e2b310 perf: cache target context in score_buyers + merge opportunity passes
5427ec6 fix(security): whitelist SQL column names in auth_store + deslop CSS
```

## 남은 작업

- [ ] **CSS deslop Pass 3** — remaining zombie 스타일 정리 (추가 분석 필요)
- [ ] **바이어 수 확인** — demo/buyers 60명 제한 원인 파악
