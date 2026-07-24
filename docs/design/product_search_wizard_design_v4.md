# MarketGate 프론트엔드 설계 문서 v4.0
# — ChatModePage.jsx 실제 구현 기준 반영

> **프로젝트:** MarketGate (AI 기반 글로벌 수출 거래 마켓플레이스)
> **버전:** v4.0 — ChatModePage.jsx 실제 구현 반영
> **기준 코드:** `ChatModePage.jsx` (실제 수정분 기준)
> **상태:** 설계 단계 (미반영)
> **작성일:** 2026-05-03

---

## 1. Executive Summary

### 1.1 v3 → v4 핵심 변경

| 항목 | v3 | v4 (실제 구현 기준) |
|------|-----|-------------------|
| **Step 1 UI** | 위자드 단계 | **챗모드 ↔ 폼모드 듀얼** |
| **카테고리** | HS 코드 카드 | **quickStartItems 배열 기반** |
| **준비중 표시** | 미표시 | **`available` + `status` 필드 + `chat-chip--soon`** |
| **챗 흐름** | 단순 입력 | **handleChipClick → available 분기 → 메시지 주입** |
| **모드 전환** | 없음 | **챗모드(aria-current) ↔ 폼모드(LayoutTemplate 아이콘)** |
| **입력창** | 기본 | **placeholder: "예: K-뷰티 독일 바이어 찾아줘"** |

### 1.2 실제 코드 기준 데이터 구조

```typescript
// ChatModePage.jsx — quickStartItems
const quickStartItems = [
  {
    id: "kbeauty",
    label: "K-뷰티",
    hsCode: "330499",
    available: true,
    status: "지금 시작",
  },
  {
    id: "health",
    label: "건강식품",
    hsCode: "210690",
    available: false,
    status: "Coming Soon",
  },
  {
    id: "kfashion",
    label: "K-패션",
    hsCode: "611030",
    available: false,
    status: "Coming Soon",
  },
];

// 더미 메시지 초기화
const dummyMessages = [
  {
    id: 1,
    role: "assistant",
    text: "안녕하세요. 어떤 제품의 해외 바이어를 찾아드릴까요? 아래 GTM Pack에서 바로 시작하거나, 직접 입력해 주세요.",
  },
];
```

---

## 2. 전체 플로우 (실제 구현 기준)

```
[랜딩] → [챗모드/폼모드 선택] → [카테고리 선택 또는 자연어 입력]
           ↓
    ┌──────┴──────┐
    ↓             ↓
[챗모드]      [폼모드]
(현재)        (미래 확장)
    ↓
[available 분기]
    ├── true → [API 호출 → 바이어 검증 플로우]
    └── false → [준비중 메시지 주입]
```

---

## 3. 챗모드 화면 구조 (ChatModePage.jsx 기준)

### 3.1 전체 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 MarketGate                    💎 350  🔔 3  👤 프로필   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ 챗 모드 / 폼 모드 전환 ──────────────────────────────┐ │
│  │                                                          │ │
│  │  [챗 모드  ●]  [폼 모드 ○]  ← 버튼 그룹               │ │
│  │   aria-current="page"       onClick={onSwitchToForm}   │ │
│  │                                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ 채팅 히스토리 ─────────────────────────────────────────┐ │
│  │                                                          │ │
│  │  🤖 안녕하세요. 어떤 제품의 해외 바이어를 찾아드릴까요?  │ │
│  │     아래 GTM Pack에서 바로 시작하거나, 직접 입력해 주세요.│ │
│  │                                                          │ │
│  │  ─────────────────────────────────────────────────────  │ │
│  │                                                          │ │
│  │  💬 "K-뷰티 독일 바이어 찾아줘"                          │ │
│  │  🤖 "분석 중..."                                       │ │
│  │                                                          │ │
│  │  💬 "건강식품" ← 사용자 클릭                             │ │
│  │  🤖 "건강식품 GTM Pack은 아직 준비 중입니다.            │ │
│  │     지금은 K-뷰티(HS 330499)로 먼저 시작할 수 있습니다." │ │
│  │                                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ GTM Pack 퀵 칩 ───────────────────────────────────────┐ │
│  │                                                          │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │ │
│  │  │ ✨         │  │ 💊         │  │ 👕         │          │ │
│  │  │ K-뷰티     │  │ 건강식품     │  │ K-패션     │          │ │
│  │  │ HS 330499  │  │ HS 210690  │  │ HS 611030  │          │ │
│  │  │ [지금 시작]│  │ [Coming    │  │ [Coming    │          │ │
│  │  │            │  │  Soon]     │  │  Soon]     │          │ │
│  │  │ clickable  │  │ disabled   │  │ disabled   │          │ │
│  │  └────────────┘  └────────────┘  └────────────┘          │ │
│  │                                                          │ │
│  │  클래스: chat-chip (기본) / chat-chip--soon (준비중)     │ │
│  │  뱃지:  chat-chip-badge (status 표시)                    │ │
│  │                                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ 입력 영역 ──────────────────────────────────────────────┐ │
│  │                                                          │ │
│  │  [  예: K-뷰티 독일 바이어 찾아줘           ] [보내기]   │ │
│  │                                                          │ │
│  │  placeholder: "예: K-뷰티 독일 바이어 찾아줘"            │ │
│  │  onKeyDown: Enter → handleSend()                       │ │
│  │                                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 컴포넌트 상세 — 실제 코드 기준

### 4.1 `<ChatModePage />` Props

```typescript
interface ChatModePageProps {
  onSwitchToForm: () => void;  // 폼모드 전환 콜백
}
```

### 4.2 State 구조

```typescript
interface ChatModeState {
  messages: {
    id: number;           // Date.now() 기반
    role: "user" | "assistant";
    text: string;
  }[];
  input: string;          // 입력창 value
  isAnalyzing: boolean;   // AI 분석 중 상태
}
```

### 4.3 핸들러 로직 — 실제 코드 기준

```typescript
// 준비중 항목 클릭
const handleUnavailableChip = (item: QuickStartItem) => {
  setMessages((prev) => [
    ...prev,
    {
      id: Date.now(),
      role: "assistant",
      text: `${item.label} GTM Pack은 아직 준비 중입니다. 지금은 K-뷰티(HS ${quickStartItems[0].hsCode})로 먼저 시작할 수 있습니다.`,
    },
  ]);
};

// 칩 클릭 분기
const handleChipClick = async (item: QuickStartItem) => {
  if (!item.available) {
    handleUnavailableChip(item);
    return;
  }
  // 기존 available 처리 로직 유지
  // → API 호출 → 바이어 검증 플로우 진행
};
```

---

## 5. 스타일 시스템 — CSS 클래스 기준

### 5.1 chat-chip 관련 클래스

```css
/* 기본 칩 */
.chat-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 16px;
  border: 2px solid var(--color-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chat-chip:hover {
  border-color: var(--color-primary);
  transform: scale(1.02);
}

/* 준비중 상태 */
.chat-chip--soon {
  opacity: 0.6;
  cursor: not-allowed;
  background: var(--color-surface-muted);
}

.chat-chip--soon:hover {
  border-color: var(--color-border);
  transform: none;
}

/* 뱃지 */
.chat-chip-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-top: 4px;
}

/* 사용 가능 */
.chat-chip .chat-chip-badge {
  background: var(--color-success-bg);
  color: var(--color-success);
}

/* 준비중 */
.chat-chip--soon .chat-chip-badge {
  background: var(--color-muted-bg);
  color: var(--color-muted);
}
```

### 5.2 모드 전환 버튼

```css
.chat-mode-actions {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}

.chat-mode-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
}

/* 현재 활성화된 모드 */
.chat-mode-toggle[aria-current="page"] {
  background: var(--color-primary);
  color: white;
}

/* 비활성 모드 */
.chat-mode-toggle:not([aria-current]) {
  background: var(--color-surface);
  color: var(--color-text);
}
```

---

## 6. 챗모드 → 4단계 플로우 연결

```
┌─────────────────────────────────────────────────────────────┐
│  챗모드 시작 → 카테고리 선택 또는 자연어 입력                  │
│                                                             │
│  [K-뷰티 클릭]                                              │
│     ↓                                                       │
│  [Step 1: 품목 검색] — HS 330499 자동 설정                   │
│     ↓                                                       │
│  [Step 2: 바이어 검증] — Lite 20💎 / Pro 50💎 선택            │
│     ↓                                                       │
│  [Step 3: 검증 결과] — Verified Leads 3~5/5~8개             │
│     ↓                                                       │
│  [Step 4: 발송+완료] — SMTP 발송 + 주문 내역                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**챗모드에서 v3 4단계로 진입하는 방법:**
- K-뷰티 칩 클릭 → `available: true` → `handleChipClick` → `App.jsx`에서 `page` 상태를 `wizard`로 변경 → Step 1 진입 (HS 코드 자동 채움)

---

## 7. 폼모드 확장 설계 (미구현)

### 7.1 폼모드 — v3 스텝 위자드와 동일

```
┌─────────────────────────────────────────────────────────────┐
│  폼 모드 — 단계별 위자드                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1/4 품목] → [2/4 검증] → [3/4 결과] → [4/4 발송]          │
│                                                             │
│  Step 1: 자연어입력 → HS추천 → MOQ → 인증 → [검색]          │
│  Step 2: Lite(20💎) / Pro(50💎) 선택 → 결제                   │
│  Step 3: 검증 결과 + D&B 리포트                              │
│  Step 4: SMTP 발송 + 큐 트래킹 + 주문 완료                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**구현 방향:**
- 현재는 `onSwitchToForm` prop만 있고 폼모드 컴포넌트는 별도 구현 필요
- v3 설계의 전체 4단계 위자드를 `FormModePage.jsx`로 분리
- `App.jsx`에서 `page` 상태로 챗/폼 전환

---

## 8. 구현 체크리스트 (실제 코드 기준)

### ChatModePage.jsx (이미 수정됨)
- [x] `quickStartItems` 배열 — id/label/hsCode/available/status
- [x] `dummyMessages` — 초기 assistant 메시지
- [x] `handleUnavailableChip` — 준비중 항목 클릭 시 메시지 주입
- [x] `handleChipClick` — available 분기
- [x] 모드 전환 버튼 — `chat-mode-actions` / `chat-mode-toggle`
- [x] `chat-chip--soon` 클래스 — 준비중 스타일
- [x] `chat-chip-badge` — status 뱃지
- [x] 입력창 placeholder — "예: K-뷰티 독일 바이어 찾아줘"

### 추가 구현 필요
- [ ] 폼모드 컴포넌트 (`FormModePage.jsx`) — v3 4단계 위자드
- [ ] 챗모드 → 위자드 전환 브리지 (K-뷰티 클릭 → Step 1 진입)
- [ ] 준비중 상태 서버 연동 (추후 available 토글 API)
- [ ] 건강식품/K-패션 `available: true` 전환 시 자동 활성화

---

## 9. 기존 v3 설계와의 관계

| v3 설계 | v4 실제 구현 | 비고 |
|--------|-------------|------|
| 랜딩 페이지 | 유지 | 그대로 사용 |
| 4단계 플로우 (Step 1~4) | 유지 | 폼모드로 분리 예정 |
| 구독/결제 시스템 | 유지 | BM1 그대로 적용 |
| 파트너 마켓플레이스 | 유지 | BM2~BM4 그대로 적용 |
| D&B 리포트 UI | 유지 | Step 3에 그대로 사용 |
| **Step 1 UI** | **챗모드로 대체** | 자연어 입력 + quickStartItems |
| **반도체 카테고리** | **제거됨** | K-뷰티/건강식품/K-패션만 |
| **준비중 상태** | **available/status 추가** | chat-chip--soon 클래스 |
| **모드 전환** | **신규** | 챗모드 ↔ 폼모드 |

---

**문서 종료. 코드 미반영.**
