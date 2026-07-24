# PRD: E1 - 채팅 UI 제거 및 위자드/폼 UI 통일

## 1. 목적

React 프론트(`apps/frontend-react`)에서 **채팅형 UX(`ChatModePage`)를 제거**하고, 수출·바이어 발굴 진입을 **구조화된 폼/위자드·수출 플로우**로만 제공한다.

- 사용자 혼란 감소: "뭘 입력해야 하는지" 불명확한 자유 채팅 제거
- 제품 포지셔닝: 무역/수출 전문 도구 톤 유지 (대화형 SaaS 느낌 축소)
- 유지보수: `page === 'chat'` 분기·채팅 전용 CSS·이중 API 호출 경로 정리

## 2. 배경 (로컬 현황, 2026-05-25 기준)

| 구분 | 상태 |
|------|------|
| **프론트 코드** | `ChatModePage.jsx`, `App.jsx`의 `chat` 라우팅, `LandingPage`의 `onStartChat` **그대로 존재** |
| **Git main** | 채팅 제거 커밋 없음. 과거는 `unify to chat mode` 등 **채팅 강화** 이력 |
| **PRD (`docs/prd/`)** | E1 없음 → **본 문서가 최초 PRD** |
| **설계 문서 (`docs/design/`)** | `product_search_wizard_design.md` — **설계 단계 (미반영)** |
| | `product_search_wizard_design_v4.md` — ChatMode 기준 부분 반영 설계, **코드 미완** |

**관련 설계 (구현 시 참고만, PRD 범위는 아래 Phase 정의 따름):**

- `docs/design/product_search_wizard_design.md`
- `docs/design/product_search_wizard_design_v4.md`
- `docs/design/ui_design_proposal_blue.md`

## 3. MVP 범위 (Phase 1 — 이번 개발 1차 목표)

백엔드·API 스키마 변경 없음. 신규 npm 패키지 없음.

### 3.1 제거

- `apps/frontend-react/src/ChatModePage.jsx` 삭제
- `App.jsx`: `ChatModePage` import, `page === 'chat'`, `chatPreset` 이름 정리(→ `analysisPreset` 등)
- `LandingPage.jsx`: `onStartChat` prop 및 채팅 진입 CTA → **분석/위자드 또는 수출 플로우**로 연결
- `App.css`: `.chat-mode-*`, `.chat-bubble-*` 등 **미사용 채팅 블록** 삭제 (다른 화면에서 쓰이지 않는 것만)

### 3.2 유지·대체 진입

| 기존 채팅 동작 | 대체 |
|----------------|------|
| 랜딩 Quick Start 칩 (K-뷰티 등) | `navigate('analysis', { hsCode, category })` — `AnalysisPage` + `preset` |
| 채팅 자유 입력 후 predict | `AnalysisPage` 기존 폼/분석 요청 (`ENDPOINTS.predict` / `buildP1Url`) |
| 채팅 → "폼 모드" 전환 | **불필요** (채팅 자체 제거) |
| "수출 플로우 시작" | `ExportFlowPage` — **변경 없음** (메인 CTA 유지) |

### 3.3 Phase 1에서 하지 않음 (Phase 2)

- `ProductSelector` / `ConditionBuilder` / `ResultsDashboard` **3단계 신규 위자드** 전면 구현 (`docs/design/product_search_wizard_design.md` §11)
- Framer Motion 등 **새 라이브러리**
- API 엔드포인트·응답 필드 변경

## 4. 사용자 시나리오 (Phase 1)

1. 로그인 후 랜딩 → **"바이어 분석"** 또는 Quick Start 카드 클릭 → `AnalysisPage` (HS 프리셋 반영)
2. 랜딩 → **"수출 플로우 시작"** → `ExportFlowPage` (기존과 동일)
3. 어디에서도 **채팅 화면·말풍선·채팅 입력창** 노출 없음

## 5. 화면·라우팅 요구사항

### 5.1 `App.jsx` 상태

- 허용 `page` 값에서 `'chat'` 제거
- 프리셋: `analysis` 진입 시에만 사용 (`preset: { hsCode?, category? }`)

### 5.2 `LandingPage.jsx`

- `onStartChat` 제거 → `onStartAnalysis(preset?)` 또는 기존 `onStartAnalysis`만 사용
- Quick Start 카드 클릭: 채팅이 아닌 **분석 페이지 + preset**
- 문구: "채팅", "AI와 대화" 등 **CTA 카피 제거** (제품 톤에 맞게 "분석 시작", "바이어 찾기" 등)

### 5.3 `AnalysisPage.jsx`

- `ChatModePage`에서 넘기던 `preset` / HS 칩 동작 **유지**
- 채팅 전용 API 호출 경로가 `ChatModePage`에만 있었다면 **`AnalysisPage` 단일 경로**로 통합 (중복 `fetchPredict` 제거)

## 6. API / 데이터

- **변경 없음.** 기존 P1 `/v1/predict` (로컬·배포 시 `buildP1Url` / `/api/v1/...` 프록시 규칙 유지)
- `config.js`, `vercel.json`, `api/proxy.js` — E1에서 **수정 금지** (별도 버그 티켓)

## 7. 예외·엣지 케이스

| 케이스 | 처리 |
|--------|------|
| 북마크/내부 링크로 `chat` 상태 복원 불가 | 클라이언트 라우팅만 사용 중이므로 해당 없음. 혹시 localStorage 키 있으면 제거 |
| 준비중 카테고리 (건강식품 등) | 채팅 칩 대신 랜딩/분석에서 **disabled + 툴팁** (기존 `available: false` 패턴 유지) |
| 모바일 | 채팅 2열 레이아웃 제거로 **분석 단일 컬럼**만 검증 |

## 8. 수용 기준 (Acceptance)

- [ ] `ChatModePage.jsx` 파일 없음
- [ ] `grep -r "ChatModePage\|page === 'chat'\|onStartChat" apps/frontend-react/src` → **0건** (주석 제외)
- [ ] 랜딩 Quick Start → 분석 화면, HS 코드 프리셋 적용
- [ ] `npm run build` 성공 (`apps/frontend-react`)
- [ ] `localhost:5173` 수동: 랜딩 → 분석 → 결과, 수출 플로우 진입, **채팅 UI 없음**
- [ ] `marketgate.vercel.app` 배포 후 동일 (배포는 별도 push)

## 9. 개발 TASK (Phase 1)

| ID | 작업 | 파일 | 상태 |
|----|------|------|------|
| E1-01 | PRD 확정 및 INDEX 반영 | `docs/prd/` | ⬜ |
| E1-02 | `ChatModePage` 삭제, `App.jsx` 라우팅 정리 | `App.jsx` | ⬜ |
| E1-03 | `LandingPage` CTA·prop 정리 | `LandingPage.jsx` | ⬜ |
| E1-04 | `AnalysisPage` preset·predict 경로 단일화 | `AnalysisPage.jsx` | ⬜ |
| E1-05 | 미사용 `.chat-*` CSS 제거 | `App.css` | ⬜ |
| E1-06 | 빌드·로컬 스모크 테스트 | — | ⬜ |

## 10. Phase 2 (후속 — 별도 PRD 개정 가능)

`docs/design/product_search_wizard_design.md` 기준 3단계 위자드:

1. 품목 선택 (`ProductSelector`)
2. 조건 설정 (`ConditionBuilder`)
3. 결과 대시보드 (`ResultsDashboard`)

Phase 1 완료 후 착수. API 변경 없이 프론트 컴포넌트 분리·`useReducer` 스텝 머신.

## 11. 우선순위

**프론트 UX 1순위 (A 시리즈와 독립)** — 채팅 제거는 배포 혼선·이중 진입 제거에 즉시 효과.

## 12. PR 제목 추천

- `feat(frontend): remove ChatModePage and route Quick Start to AnalysisPage (E1)`
- `chore(ui): drop chat-mode CSS and unify landing CTAs (E1)`

## 13. 검증 명령

```powershell
cd D:\marketgate\apps\frontend-react
npm run build
npm run dev
```

## 14. 충돌·주의

- Codex/다른 에이전트가 `ChatModePage.jsx`, `LandingPage.jsx`, `App.jsx` 동시 수정 중이면 **한 명만 E1 담당**
- `TASKS.md`, `auto_prompt_*.md` 수정 금지 (프로젝트 규칙)
- Streamlit `localhost:8503` **범위 외**

---

**문서 상태:** 초안 (개발 전) · **다음 액션:** E1-02부터 Phase 1 구현
