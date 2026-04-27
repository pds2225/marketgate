# MarketGate 프론트엔드 심화 기획안 — 컨셉 A: 수출 비서 (Export Assistant)

> 대상 프로젝트: `D:\marketgate\apps\frontend-react`  
> 기준 시안: 기존 AnalysisPage.jsx 유지 + 챗 인터페이스 병행 구조  
> 경쟁사 참고: [Rinda](https://www.rinda.ai/) — GTM 팩, 캠페인 시퀀스, 팀 워크스페이스  
> 작성일: 2026-04-27 (v2)

---

## 1. 개요

**컨셉**: 사용자가 복잡한 폼을 채우는 대신, 챗봇 인터페이스를 통해 자연스럽게 수출 분석을 시작합니다.  
**핵심 가치**: "수출 경험이 없어도 대화하듯 시작해서, 적합한 바이어를 찾고 인콰이어리까지 발송한다"

**서비스 방향**: MarketGate의 핵심은 **바이어 매칭**이다. P1 수출 유망국 추천은 "어느 나라에서 바이어를 찾아볼까"를 결정하는 보조 도구이며, 최종 목표는 항상 바이어 발굴과 인콰이어리 발송이다.

**Rinda 시사점 반영**:
- **GTM 팩 마켓플레이스**: 산업×국가별 시작 프레임. HS 코드와 타겟 국가를 미리 결정해주어 초보자의 진입장벽을 제거 (ex. "독일 스킨케어 시작하기")
- **적합도 기반 발굴**: 바이어 카드에 "우리 제품과의 적합도" 점수 노출 (수입 이력 기반)
- **캠페인 시퀀스**: 단발성 인콰이어리가 아닌, 1차→2차→3차 자동 후속 메일 시퀀스
- **팀 워크스페이스**: 바이어 리스트 공유, 중복 컨택 방지 (중장기 로드맵)

기존 `AnalysisPage`의 카드 기반 결과 UI는 그대로 유지하되, 진입점을 챗 인터페이스로 교체합니다.  
사용자가 원할 경우 기존 폼 모드로 전환할 수 있는 **듀얼 모드**를 제공합니다.

---

## 2. 화면 구조

### 2.1 전체 화면 흐름

```
[랜딩 페이지] → [챗 모드] → [결과 A: 바이어 발굴] → [인콰이어리/캠페인]
                     ↓
              [결과 B: 0건 폰백] → [P1 국가 추천] → [다른 국가 바이어 검색]
                     ↓
              [폼 모드 전환] → [기존 AnalysisPage]
```

---

### 화면 ① 랜딩 페이지 (LandingPage.jsx — 기존 유지)

```
┌────────────────────────────────────────────┐
│                                            │
│           [MarketGate 로고]                │
│                                            │
│      "AI로 해외 바이어를 찾고               │
│       인콰이어리까지 발송하세요"            │
│                                            │
│         [  🚀 분석 시작  ]                 │
│                                            │
│   ────────  또는 아래에서 선택  ────────    │
│                                            │
│   ┌────────────────┐ ┌────────────────┐    │
│   │    🧴 화장품    │ │   🍵 건강식품   │    │
│   │   지금 시작     │ │   곧 만나요     │    │
│   │  HS 330499     │ │  Coming Soon   │    │
│   └────────────────┘ └────────────────┘    │
│                                            │
│         ┌────────────────┐                 │
│         │   🚗 자동차부품  │                 │
│         │   곧 만나요      │                 │
│         │  Coming Soon    │                 │
│         └────────────────┘                 │
│                                            │
│   💡 새로운 품목이 계속 추가됩니다          │
│   [  🔔 오픈 알림 신청하기  ]               │
│                                            │
│   [관리자 모드 →]                          │
│                                            │
└────────────────────────────────────────────┘
```

**구성 요소 상세**:

| 영역 | 컴포넌트 | 상태 | 동작 |
|------|---------|------|------|
| 메인 CTA | `StartButton` | 활성 | 클릭 → 챗 모드 진입 |
| 퀵스타트 칩 1 | `QuickStartChip` | **사용 가능** | 화장품(스킨케어) — HS 330499. 클릭 시 챗 모드 + 해당 코드 프리셋 |
| 퀵스타트 칩 2 | `QuickStartChip` | **오픈 예정** | 건강기능식품 — HS 210690. 클릭 시 토스트 노출 |
| 퀵스타트 칩 3 | `QuickStartChip` | **오픈 예정** | 자동차 부품 — HS 870899. 클릭 시 토스트 노출 |
| 알림 배너 | `ComingSoonBanner` | — | 이메일 입력 → 오픈 알림 신청 (향신 API 연동) |

**오픈 예정 상태 디자인**:
- 오픈 예정 칩: 배경색 흐리게 (opacity 0.6), "Coming Soon" 배지 우상단
- 호버/클릭 시: `🚧 아직 준비 중이에요. 오픈되면 가장 먼저 알려드릴게요.` 토스트
- 화장품 칩: 정상 배경색, "지금 시작" 라벨

**오픈 알림 신청 흐름**:
```
사용자: [🍵 건강식품] 클릭
비서:   🚧 "아직 준비 중이에요. 오픈되면 가장 먼저 알려드릴게요."
        [🔔 오픈 알림 신청하기] 버튼 노출

사용자: [🔔 오픈 알림 신청하기] 클릭
       → 이메일 입력 필드 + 품목 체크박스 노출
       → "어떤 품목이 궁금하신가요? [🍵건강식품] [🚗자동차부품] [모두]"
       → 이메일 제출 → "오픈 소식을 전해드릴게요! 🎉"
```

---

### 화면 ② 챗 모드 — 진입 (ChatModePage.jsx 신규)

```
┌─────────────────────────────────────────────────────────────┐
│  🏠  MarketGate          [챗 💬 | 폼 📝]        [관리자 👤]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│              🤖 MarketGate 비서                             │
│                                                             │
│     "안녕하세요! 어떤 제품의 해외 바이어를 찾아드릴까요?      │
│      아래에서 바로 시작하거나, 직접 입력해 주세요."          │
│                                                             │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│   │ 🧴 화장품   │  │ 🍵 건강식품  │  │ 🚗 자동차부품│           │
│   │   지금 시작 │  │   곧 만나요  │  │   곧 만나요  │           │
│   │  HS 330499 │  │  HS 210690 │  │  HS 870899 │           │
│   └────────────┘  └────────────┘  └────────────┘           │
│                                                             │
│   ─────────────────────────────────────────────────────     │
│                                                             │
│   💬 사용자                                                 │
│   "화장품 수출하고 싶어요"                                  │
│                                                             │
│   🤖 비서                                                   │
│   "어떤 화장품인지 알려주시면 정확한 HS 코드를              │
│    찾아드릴게요. 스킨케어, 메이크업 중 어떤 제품인가요?"    │
│                                                             │
│   💬 사용자                                                 │
│   "스킨케어 세럼"                                          │
│                                                             │
│   🤖 비서                                                   │
│   [스피너] 분석 중...                                       │
│                                                             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [🎤]  "메시지를 입력하세요..."              [전송 ➤]       │
└─────────────────────────────────────────────────────────────┘
```

**구성 요소**:
| 영역 | 컴포넌트 | 설명 |
|------|---------|------|
| 상단 네비 | `ModeToggle` | 챗/폼 전환. 현재 "챗" 활성 |
| 중앙 | `ChatHistory` | 메시지 버블 리스트. 사용자(오른쪽) / 비서(왼쪽) |
| 중앙 | `GtmPackStrip` | 진입 시 1회 노출. 클릭 시 해당 프리셋 로드 |
| 하단 | `ChatInput` | 텍스트 입력 + 전송 버튼 + 음성(Phase 4) |

---

### 화면 ③ 챗 모드 — 바이어 발굴 성공 (결과 A)

```
┌─────────────────────────────────────────────────────────────┐
│  🏠  MarketGate          [챗 💬 | 폼 📝]        [관리자 👤]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   💬 사용자                                                 │
│   "스킨케어 세럼 독일 바이어 찾아줘"                        │
│                                                             │
│   🤖 비서                                                   │
│   "독일 스킨케어 바이어를 검색했습니다.                     │
│    적합도 기준 상위 결과입니다."                            │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ 🇩🇪 독일 — 스킨케어 세럼 (HS 330499)                 │   │
│   │ 검색 조건: 독일 + 뷰티 유통사                         │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ 1️⃣ Beauty Wholesale GmbH                            │   │
│   │    🏷️ 뷰티 유통사  📍 함부르크                        │   │
│   │    [적합도 92% 🟢]  수입 이력: 스킨케어 3건           │   │
│   │    📧 contact@beauty-wholesale.de                     │   │
│   │    [인콰이어리 작성]  [상세 정보]                     │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ 2️⃣ Euro Cosmetics AG                                │   │
│   │    🏷️ 화장품 수입사  📍 뮌헨                          │   │
│   │    [적합도 85% 🟡]  수입 이력: 세럼 1건               │   │
│   │    📧 info@euro-cosmetics.de                          │   │
│   │    [인콰이어리 작성]  [상세 정보]                     │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   🤖 비서                                                   │
│   "2건의 바이어를 찾았습니다. 인콰이어리를 작성하시려면     │
│    '1번' 또는 '2번'이라고 말씀해 주세요.                    │
│    다른 국가도 검색해 볼까요?"                              │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [🎤]  "메시지를 입력하세요..."              [전송 ➤]       │
└─────────────────────────────────────────────────────────────┘
```

**구성 요소**:
| 영역 | 컴포넌트 | 설명 |
|------|---------|------|
| 결과 헤더 | `SearchResultHeader` | 국기 + 국가명 + HS 코드 + 검색 조건 요약 |
| 바이어 카드 | `BuyerCard` (기존 수정) | `FitScoreBadge` 추가. 적합도 % + 색상 뱃지 |
| 액션 버튼 | `ChatMessage` 내 버튼 | "인콰이어리 작성" 클릭 → 모달 오픈 |

---

### 화면 ④ 챗 모드 — 0건 폴백 (결과 B)

```
┌─────────────────────────────────────────────────────────────┐
│  🏠  MarketGate          [챗 💬 | 폼 📝]        [관리자 👤]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   💬 사용자                                                 │
│   "화장품 독일 바이어"                                      │
│                                                             │
│   🤖 비서                                                   │
│   "현재 독일 화장품 바이어 데이터를 확보 중입니다.          │
│    대신, 어느 국가를 먼저 타겟팅할지 분석해 드릴게요."      │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ 📊 수출 유망국 분석 (P1)                            │   │
│   │                                                     │   │
│   │ 1위 🇺🇸 미국        78.5점  ━━━━━━━━━━━━━━━━        │   │
│   │    무역 실적 92% · 성장률 65% · GDP 88%             │   │
│   │    [미국 바이어 검색]                                 │   │
│   │                                                     │   │
│   │ 2위 🇯🇵 일본        72.1점  ━━━━━━━━━━━━━━          │   │
│   │    [일본 바이어 검색]                                 │   │
│   │                                                     │   │
│   │ 3위 🇭🇰 홍콩        68.3점  ━━━━━━━━━━━━            │   │
│   │    [홍콩 바이어 검색]                                 │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   🤖 비서                                                   │
│   "미국은 현재 바이어 데이터가 가장 많습니다.              │
│    검색해 보시겠어요? 아니면 데이터 추가 알림을            │
│    설정해 두실 수도 있습니다."                             │
│                                                             │
│   [🔔 독일 데이터 알림 설정]  [🇺🇸 미국 바이어 검색]        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [🎤]  "메시지를 입력하세요..."              [전송 ➤]       │
└─────────────────────────────────────────────────────────────┘
```

**구성 요소**:
| 영역 | 컴포넌트 | 설명 |
|------|---------|------|
| 안내 메시지 | `ChatMessage` | "데이터 확보 중" 안내 |
| P1 카드 | `CountryRecommendationCard` (기존 재사용) | 순위 + 점수 + 주요 지표 |
| 액션 버튼 | `ChatMessage` 내 버튼 | "바이어 검색" → 해당 국가로 즉시 검색 |
| 알림 버튼 | `ChatMessage` 내 버튼 | "알림 설정" → 이메일 수집 (향신 기능) |

---

### 화면 ⑤ 인콰이어리 모달 + 캠페인 시퀀스

```
┌─────────────────────────────────────────────────────────────┐
│  🏠  MarketGate          [챗 💬 | 폼 📝]        [관리자 👤]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [모달 오버레이]                                           │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  ✉️ 인콰이어리 작성 — Beauty Wholesale GmbH         │   │
│   │                                                     │   │
│   │  받는 사람: contact@beauty-wholesale.de             │   │
│   │  제품: 스킨케어 세럼 (HS 330499)                    │   │
│   │                                                     │   │
│   │  ───── 캠페인 시퀀스 설정 ─────                     │   │
│   │  [✅] 1차: 즉시 발송                                │   │
│   │  [✅] 2차: 3일 후 (미응답 시)  [수정]               │   │
│   │  [✅] 3차: 7일 후 (미응답 시)  [수정]               │   │
│   │  [+] 후속 메일 추가                                 │   │
│   │                                                     │   │
│   │  ───── 1차 메일 초안 ─────                          │   │
│   │  Subject: Partnership Inquiry — Korean Skincare     │   │
│   │  ─────────────────────────────────────────────      │   │
│   │  Dear Beauty Wholesale Team,                        │   │
│   │                                                     │   │
│   │  We are a Korean skincare manufacturer...           │   │
│   │  [편집 가능한 textarea]                             │   │
│   │                                                     │   │
│   │  [취소]  [💾 초안 저장]  [🚀 1차 발송]              │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [🎤]  "메시지를 입력하세요..."              [전송 ➤]       │
└─────────────────────────────────────────────────────────────┘
```

**구성 요소**:
| 영역 | 컴포넌트 | 설명 |
|------|---------|------|
| 모달 | `InquiryModal` (기존 M08 확장) | 바이어 정보 + 발송 폼 |
| 시퀀스 | `CampaignSequence` (신규) | 1차/2차/3차 체크박스 + 간격 설정 |
| 초안 | `DraftEditor` | draft_en 표시 + 편집 가능 |
| 버튼 | — | 취소 / 저장 / 발송 (발송 시 캠페인 생성 API 호출) |

---

### 화면 ⑥ 폼 모드 (AnalysisPage.jsx — 기존 유지)

```
┌─────────────────────────────────────────────────────────────┐
│  🏠  MarketGate          [챗 💬 | 폼 📝]        [관리자 👤]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [← 뒤로가기]                                              │
│                                                             │
│   HS 코드 입력                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  330499                    [🔍 검색]                │   │
│   └─────────────────────────────────────────────────────┘   │
│   추천: 화장품 · 반도체 · 리튬전지 · 즉석면                │
│                                                             │
│   수출국                                                    │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  🇰🇷 대한민국 (KOR)                                  │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   [고급 필터 ▼]                                             │
│   ─────────────────────────────────────────────────────     │
│                                                             │
│   [📊 분석 시작]                                            │
│                                                             │
│   === 분석 결과 ===                                         │
│   [국가 추천 카드] [바이어 리스트] ...                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- **변경 없음**: 기존 AnalysisPage 완전 유지
- **진입 경로**: 상단 `ModeToggle` "폼" 클릭 시 전환

---

### 2.2 모바일 대응

```
모바일 (375px 기준):
┌─────────────────────────┐
│  MarketGate   [챗|폼]   │
├─────────────────────────┤
│                         │
│  [💬 챗 영역]            │
│                         │
│  ← 스크롤 →             │
│  [🧴화장품][🔋리튬][💻반]│  ← GTM 팩 가로 스크롤
│                         │
│  💬 사용자               │
│  "화장품 수출"           │
│                         │
│  🤖 비서                 │
│  "독일 바이어 N건..."    │
│                         │
│  [바이어 카드]           │
│  ┌─────────────────┐    │
│  │ Beauty GmbH     │    │
│  │ 적합도 92% 🟢    │    │
│  │ [인콰이어리]     │    │
│  └─────────────────┘    │
│                         │
├─────────────────────────┤
│ [🎤] "입력하세요..." [➤]│
└─────────────────────────┘
```

- GTM 팩: 가로 스크롤 (scroll-snap)
- 바이어 카드: 전체 너비, 세로 스택
- 인콰이어리 모달: 전체 화면 바텀 시트로 변경

### 2.2 GTM 팩 (Go-To-Market Pack) — Rinda 대응 전략

**정의**: 업종×목표국가별로 HS 코드와 기본 설정을 미리 결정한 **시작 프레임**. 초보자가 "뭘 입력해야 할지 모르겠다"는 상황을 해결한다.

| 팩 이름 | 프리셋 구성 | 사용자가 얻는 것 |
|--------|------------|----------------|
| 독일 스킨케어 시작하기 | HS 330499 + 독일 | 해당 업종/국가로 바이어 검색 시작 |
| 미국 의료기기 시작하기 | HS 901890 + 미국 | 해당 업종/국가로 바이어 검색 시작 |
| 일본 식품 시작하기 | HS 190230 + 일본 | 해당 업종/국가로 바이어 검색 시작 |

> **주의**: GTM 팩은 "바이어 N건을 보장"하는 것이 아니다. "이 설정으로 바이어 검색을 시작할 수 있다"는 프레임을 제공한다. 실제 바이어 수는 데이터 상태에 따라 다르며, 0건일 때도 적절한 안내 메시지를 출력한다.

**진입 흐름**:
1. 사용자가 랜딩 페이지 "분석 시작" 클릭
2. 챗 모드 진입 + 동시에 GTM 팩 퀵액션 노출
3. 사용자가 팩 클릭 → 해당 HS 코드/국가로 즉시 바이어 검색 API 호출
4. 결과: "해당 조건으로 바이어를 검색 중입니다" → 결과 카드 또는 "데이터 확보 중" 안내
5. 또는 자유 입력으로 직접 분석 진행

### 2.3 모드 전환 규칙

| 조건 | 동작 |
|------|------|
| 랜딩 페이지 "분석 시작" 클릭 | 챗 모드로 진입 + GTM 팩 노출 |
| GTM 팩 클릭 | 해당 팩 설정으로 즉시 분석 실행 |
| 상단 토글 "폼" 클릭 | 기존 AnalysisPage 렌더링 |
| 챗에서 "고급 설정 열어줘" 입력 | 자동으로 폼 모드 전환 + 해당 필드 포커스 |
| 모바일 환경 | 챗 모드만 제공 (GTM 팩 퀵액션은 가로 스크롤) |

---

## 3. 사용자 시나리오

### 시나리오 1: 완전 초보자의 즉시 시작 (GTM 팩 활용) — Rinda 대응

```
[랜딩 페이지] → "분석 시작" 클릭

비서:   "안녕하세요! 어떤 제품을 수출하실 계획인가요? 
         아래에서 바로 시작할 수 있는 조합을 준비했어요. 👇"
         → [🎁 GTM 팩 퀵액션 렌더링]

사용자: ["독일 스킨케어 시작하기" 클릭]

비서:   → GET /v1/buyers?hs_code=330499&country=DEU
         → "독일 스킨케어 바이어를 검색했습니다."

[결과 A — 바이어 발굴 성공]
         → "적합도 기준 상위 바이어 N건을 찾았습니다."
         → [바이어 리스트(적합도 배지 포함) 렌더링]
         → "바로 인콰이어리를 보내볼까요?"

[결과 B — 바이어 데이터 부족]
         → "현재 해당 조건의 바이어 데이터를 확보 중입니다. 
            대신 '수출 유망국 분석'으로 어느 국가를 먼저 타겟팅할지 확인해 보시겠어요?"
         → [P1 국가 추천 카드 렌더링 — "독일 외에도 프랑스 82점, 네덜란드 76점"]
         → "다른 국가로 바이어를 검색하거나, 알림을 설정해 두시면 
            해당 업종 바이어 데이터가 추가될 때 연락드립니다."
```

### 시나리오 2: HS 코드를 아는 실무자 (바이어 매칭 중심)

```
사용자: "330499 KOR USA"
비서:   → GET /v1/buyers?hs_code=330499&country=USA
         → "미국 화장품 바이어를 검색했습니다. 적합도 기준 상위 결과입니다."
         → [바이어 카드 리스트 렌더링 — 적합도 95%, 88%, 72% 배지 표시]
         → "인콰이어리를 작성하시려면 바이어를 선택해 주세요."

[사용자가 다른 국가도 궁금해할 경우 — P1 보조 기능]
사용자: "다른 나라는?"
비서:   → POST /v1/predict {hs_code:"330499", exporter_country_iso3:"KOR"}
         → "미국 외에는 일본(72.1점), 홍콩(68.3점)이 추천됩니다. 
            해당 국가 바이어도 검색해 볼까요?"
```

### 시나리오 3: 캠페인 시퀀스 설정 — Rinda "캠페인 시퀀스" 대응

```
사용자: "2번 바이어한테 메일 보내고 싶어"
비서:   → 해당 바이어 카드 하이라이트
         → "한 번에 보내실 건가요, 아니면 후속 메일도 준비할까요?"
사용자: "후속도 준비해줘"
비서:   → [캠페인 시퀀스 설정 카드 렌더링]
         → "1차: 오늘 / 2차: 3일 후(미응답 시) / 3차: 7일 후(미응답 시) 
             이렇게 설정했습니다. 변경하시겠어요?"
사용자: "응 좋아"
비서:   → 인콰이어리 모달 오픈 → draft_en 생성
         → POST /v1/campaigns {buyer_id, sequence:[{day:0}, {day:3}, {day:7}],
                               drafts:[draft_1, draft_2, draft_3]}
         → "캠페인이 저장됐습니다. 1차 메일은 즉시 발송됩니다. 
             진행 상황은 '캠페인 관리'에서 확인하세요."
```

### 시나리오 4: 고급 필터링 요청

```
사용자: "리튬전지 수출할 건데 GDP 큰 나라 위주로, 성장률 3% 이상인 곳만"
비서:   "조건에 맞는 국가를 먼저 찾아볼까요?"
         → POST /v1/predict {hs_code:"850650", exporter_country_iso3:"KOR",
                           filters:{min_gdp_growth_pct:3}}
         → "조건에 맞는 상위 국가입니다. 어느 나라 바이어를 검색해 볼까요?"
         → [국가 추천 카드 렌더링]
         
[사용자가 폼 모드 선호 시]
사용자: "고급 설정 화면으로 보여줘"
비서:   → 폼 모드 전환 + HS 코드 "850650" 자동 입력 + GDP/성장률 필터 하이라이트
```

### 시나리오 5: 히스토리 기반 재분석 + 캠페인 이어하기

```
사용자: "아까 분석한 거 다시 보여줘"
비서:   → 로컬 스토리지 세션 ID 조회
         → "가장 최근: 330499 화장품 / 미국 추천. 불러올까요?"
사용자: "응"
비서:   → 캐시된 API 응답 재렌더링 (재호출 없음, < 500ms)
         → "이 캠페인은 2차 메일이 1일 후 예정되어 있습니다. 
             미리 보기를 확인하시겠어요?"
```

### 시나리오 6: 팀 공유 — Rinda "워크스페이스" 대응 (중장기)

```
사용자: "이 바이어 리스트 팀원한테 공유하고 싶어"
비서:   → "팀 워크스페이스에 저장할까요? 링크를 생성할까요?"
사용자: "링크로 줘"
비서:   → 세션 데이터를 base64 인코딩 → 공유 URL 생성
         → "https://marketgate.ai/share/{token} 
             이 링크를 팀원에게 보내세요. 중복 컨택 방지를 위해 
             내가 컨택한 바이어는 자동으로 표시됩니다."
```

---

## 4. 컴포넌트 설계

### 4.1 신규 컴포넌트

| 컴포넌트 | 경로 | 역할 |
|---------|------|------|
| `ChatModePage` | `src/ChatModePage.jsx` | 챗 모드 메인 컨테이너 |
| `ChatSidebar` | `src/components/ChatSidebar.jsx` | 좌측 비서 프로필 + 히스토리 목록 |
| `ChatHistory` | `src/components/ChatHistory.jsx` | 챗 메시지 리스트 |
| `ChatInput` | `src/components/ChatInput.jsx` | 하단 입력창 + 전송 + 음성(선택) |
| `ChatMessage` | `src/components/ChatMessage.jsx` | 단일 메시지 버블 (텍스트/카드/로딩) |
| `SessionCard` | `src/components/SessionCard.jsx` | 히스토리 목록의 개별 세션 아이템 |
| `ModeToggle` | `src/components/ModeToggle.jsx` | 상단 챗/폼 전환 스위치 |
| `GtmPackStrip` | `src/components/GtmPackStrip.jsx` | **Rinda 대응** — GTM 팩 가로 스크롤 퀵액션 |
| `GtmPackCard` | `src/components/GtmPackCard.jsx` | **Rinda 대응** — 개별 GTM 팩 카드 (아이콘+제목+설명) |
| `FitScoreBadge` | `src/components/FitScoreBadge.jsx` | **Rinda 대응** — 바이어 적합도 배지 (0~100%) |
| `CampaignSequence` | `src/components/CampaignSequence.jsx` | **Rinda 대응** — 1차/2차/3차 메일 시퀀스 설정 UI |
| `CampaignPreview` | `src/components/CampaignPreview.jsx` | **Rinda 대응** — 시퀀스별 draft 미리보기 |
| `useChatSession` | `src/hooks/useChatSession.js` | 세션 CRUD + localStorage 관리 |
| `useNlpParser` | `src/hooks/useNlpParser.js` | 자연어 → HS 코드/국가/의도 파싱 |
| `useGtmPacks` | `src/hooks/useGtmPacks.js` | **Rinda 대응** — GTM 팩 목록 조회 (정적 JSON or API) |

### 4.2 기존 컴포넌트 수정

| 컴포넌트 | 수정 내용 |
|---------|----------|
| `App.jsx` | `page` 상태에 `'chat'` 추가, `ModeToggle` 삽입, `GtmPackStrip` 조건부 노출 |
| `AnalysisPage.jsx` | 폼 모드로 재명명, 진입점에서만 사용 |
| `config.js` | `ENDPOINTS`에 `/v1/buyers`, `/v1/inquiry`, `/v1/campaigns`, `/v1/gtm-packs` 추가 |

### 4.3 컴포넌트 의존성 그래프

```
App.jsx
├── ModeToggle
├── GtmPackStrip (신규)
│   └── GtmPackCard (신규)
│       └── useGtmPacks (신규)
├── ChatModePage (신규)
│   ├── ChatSidebar
│   │   ├── SessionCard (신규)
│   │   └── useChatSession (신규)
│   ├── ChatHistory (신규)
│   │   └── ChatMessage (신규)
│   │       ├── [기존 CountryCard 재사용]
│   │       ├── [기존 BuyerCard + FitScoreBadge 재사용/수정]
│   │       ├── [기존 InquiryModal + CampaignSequence 재사용/수정]
│   │       └── CampaignPreview (신규)
│   └── ChatInput (신규)
└── AnalysisPage (기존, 폼 모드)
```

---

## 5. 상태 관리 설계

### 5.1 로컬 상태 (useState)

| 상태 | 위치 | 설명 |
|------|------|------|
| `page` | `App.jsx` | `'landing' \| 'chat' \| 'analysis' \| 'admin'` |
| `mode` | `App.jsx` | `'chat' \| 'form'` (현재 활성 모드) |
| `messages` | `ChatModePage.jsx` | 챗 메시지 배열 |
| `inputText` | `ChatInput.jsx` | 입력창 텍스트 |
| `isLoading` | `ChatModePage.jsx` | API 호출 중 여부 |
| `activeSessionId` | `ChatModePage.jsx` | 현재 세션 UUID |
| `gtmPacks` | `GtmPackStrip.jsx` | GTM 팩 목록 (정적 or API) |
| `activeCampaign` | `ChatModePage.jsx` | 현재 설정 중인 캠페인 정보 |

### 5.2 지속 상태 (localStorage)

```typescript
interface ChatSession {
  id: string;
  title: string;        // "330499 화장품 — 미국" (자동 생성)
  createdAt: ISOString;
  updatedAt: ISOString;
  messages: Message[];
  lastSnapshot?: PredictResponse;
  linkedCampaignId?: string; // 연결된 캠페인 ID
}

interface CampaignDraft {
  id: string;
  sessionId: string;
  buyerId: string;
  buyerName: string;
  sequence: Array<{ day: number; sent: boolean; draft: string }>;
  createdAt: ISOString;
  status: 'draft' | 'active' | 'paused' | 'completed';
}

// 키: `mg:sessions:v1` — 최대 50개 세션, LRU 삭제
// 키: `mg:campaigns:v1` — 캠페인 임시 저장 (로그인 전)
```

### 5.3 메시지 타입 정의

```typescript
type MessageRole = 'user' | 'assistant' | 'system';
type MessageType = 
  | 'text' 
  | 'country_recommendation' 
  | 'buyer_list' 
  | 'inquiry_draft' 
  | 'campaign_sequence'   // 신규: 캠페인 시퀀스 설정 카드
  | 'gtm_pack_suggestion' // 신규: GTM 팩 추천 카드
  | 'loading' 
  | 'error';

interface Message {
  id: string;
  role: MessageRole;
  type: MessageType;
  content: string;
  payload?: unknown;
  timestamp: ISOString;
}
```

---

## 6. API 연동 설계

### 6.1 신규 엔드포인트 (config.js 추가)

```javascript
export const ENDPOINTS = {
  health: buildApiUrl("/v1/health"),
  predict: buildApiUrl("/v1/predict"),
  legacyPredict: buildApiUrl("/predict"),
  snapshot: buildApiUrl("/v1/snapshot"),
  buyers: buildApiUrl("/v1/buyers"),
  inquiry: buildApiUrl("/v1/inquiry"),
  campaigns: buildApiUrl("/v1/campaigns"),     // Rinda 대응: 캠페인 CRUD
  gtmPacks: buildApiUrl("/v1/gtm-packs"),      // Rinda 대응: GTM 팩 목록
};
```

### 6.2 GTM 팩 데이터 구조 (정적 JSON or API)

```typescript
interface GtmPack {
  id: string;
  name: string;              // "독일 스킨케어 시작하기"
  category: string;          // "뷰티/화장품"
  targetCountry: string;     // "DEU"
  hsCode: string;            // "330499"
  description: string;       // "스킨케어 제품의 독일 바이어 검색을 시작합니다"
  icon: string;              // Lucide 아이콘명 or 이모지
  presetFilters: {
    min_trade_value_usd?: number;
    min_gdp_growth_pct?: number;
  };
  // 제거: estimatedBuyers, buyerType
  // 이 팩은 시작 프레임이며, 바이어 수를 약속하지 않는다
}
```

> **MVP 단계**: `src/data/gtm-packs.json` 정적 파일로 관리, 백엔드 없이 프론트에서 로드

### 6.3 챗 명령 → API 매핑

| 사용자 의도 | 파싱 결과 | 호출 API | 렌더링 타입 |
|-----------|----------|---------|-----------|
| GTM 팩 선택 | `{pack_id}` | — (프리셋 로드) | `gtm_pack_suggestion` + 자동 `country_recommendation` |
| 국가 추천 요청 | `{hs_code, exporter_iso3}` | POST /v1/predict | `country_recommendation` |
| 특정 국가 바이어 조회 | `{hs_code, country_iso3}` | GET /v1/buyers | `buyer_list` |
| 인콰이어리 작성 | `{buyer_idx, sender_info}` | POST /v1/inquiry | `inquiry_draft` |
| 캠페인 시퀀스 설정 | `{buyer_id, sequence}` | POST /v1/campaigns | `campaign_sequence` |
| 세션 불러오기 | `{session_id}` | localStorage | 이전 메시지 복원 |
| 고급 필터 요청 | `{intent: "advanced_filter"}` | — | 폼 모드 전환 트리거 |

### 6.4 의도 파싱 로직 (프론트엔드 단순 룰 기반)

```javascript
// useNlpParser.js — MVP 단계 정규식 기반
function parseIntent(text, gtmPacks = []) {
  const normalized = text.trim().toLowerCase();
  
  // HS 코드 추출
  const hsMatch = normalized.match(/\b(\d{6})\b/);
  
  // 국가 코드 추출
  const countryMatch = normalized.match(/\b(KOR|USA|JPN|CHN|DEU|GBR|FRA|...|[가-힣]{2,4})\b/);
  
  // GTM 팩 매칭: "독일 화장품" → 해당 팩 ID 반환
  const matchedPack = gtmPacks.find(pack => 
    normalized.includes(pack.category.toLowerCase()) &&
    normalized.includes(countryInfo[pack.targetCountry]?.name)
  );
  if (matchedPack) return { intent: 'GTM_PACK', packId: matchedPack.id };
  
  // 캠페인/시퀀스 관련
  if (normalized.includes('후속') || normalized.includes('시퀀스') || 
      normalized.includes('캠페인') || normalized.includes('자동 발송'))
    return { intent: 'CAMPAIGN_SEQUENCE', hsCode: hsMatch?.[1] };
  
  // 기존 의도들...
  if (normalized.includes('바이어') || normalized.includes('buyer')) 
    return { intent: 'BUYER_SEARCH', hsCode: hsMatch?.[1], country: countryMatch?.[1] };
  if (normalized.includes('추천') || normalized.includes('점수') || normalized.includes('어때'))
    return { intent: 'COUNTRY_RECOMMEND', hsCode: hsMatch?.[1] };
  if (normalized.includes('메일') || normalized.includes('인콰이어리') || normalized.includes('보내'))
    return { intent: 'INQUIRY_DRAFT' };
  if (normalized.includes('고급') || normalized.includes('필터') || normalized.includes('설정'))
    return { intent: 'ADVANCED_FILTER' };
  
  return { intent: 'GENERAL', hsCode: hsMatch?.[1] };
}
```

---

## 7. 구현 로드맵

### Phase 1: 챗 골격 + GTM 팩 온보딩 (1주)
- [ ] `ChatModePage` + `ChatHistory` + `ChatInput` 신규 작성
- [ ] `ModeToggle` 추가, `App.jsx` 라우팅 수정
- [ ] `useChatSession` + localStorage CRUD 구현
- [ ] `GtmPackStrip` + `GtmPackCard` + 정적 `gtm-packs.json` 작성
- [ ] 더미 메시지로 GTM 팩 클릭 → **바이어 검색 흐름** 검증
- [ ] **0건 결과 처리**: "데이터 확보 중" 안내 → P1 국가 추천 폴백 흐름

### Phase 2: API 연동 + 적합도 배지 (1주)
- [ ] `useNlpParser` 룰 기반 구현 (GTM 팩 매칭 포함)
- [ ] 의도 → API 매핑 + 로딩/에러 상태 처리
- [ ] 기존 `CountryCard`, `BuyerCard`를 `ChatMessage` 내에 임베드
- [ ] `FitScoreBadge` 추가 — 바이어 적합도 시각화 (Rinda 대응)
- [ ] `SessionCard` 히스토리 목록 구현

### Phase 3: 캠페인 시퀀스 + 인콰이어리 통합 (3일)
- [ ] `CampaignSequence` 컴포넌트 신규 작성 — 1차/2차/3차 설정 UI
- [ ] `CampaignPreview` — 시퀀스별 draft 미리보기
- [ ] 기존 `InquiryModal`을 챗 컨텍스트 + 캠페인 흐름에 연결
- [ ] 모바일 반응형 최적화

### Phase 4: 고도화 (2주, 선택)
- [ ] 백엔드 LLM 파서 `/v1/chat/parse` 연동
- [ ] 음성 입력 (Web Speech API)
- [ ] 키보드 단축키 (`/` 포커스, `Esc` 취소)
- [ ] **팀 워크스페이스** — 세션 공유 링크, 중복 컨택 방지 (Rinda 대응)
- [ ] **인박스 기능** — 발송 메일 관리, 응답 확인 UI

---

## 8. 기술 스택 및 의존성

### 기존 유지
- React 19 + Vite
- Framer Motion (애니메이션)
- Lucide React (아이콘)

### 신규 추가 (필요 시)
| 패키지 | 버전 | 용도 |
|--------|------|------|
| `uuid` | ^9.0 | 메시지/세션 ID 생성 |
| `date-fns` | ^3.0 | 상대 시간 표시 ("3분 전") |

> **권장**: `crypto.randomUUID()` + `Intl.RelativeTimeFormat` 네이티브 API 사용으로 대체 가능

---

## 9. 위험도 및 대응

| 위험 | 가능성 | 영향 | 대응 |
|------|--------|------|------|
| NLP 파서 정확도 낮음 | 높음 | 사용자 혼란 | GTM 팩 퀵액션 + 버튼형 퀵액션 병행 제공 |
| 메시지 배열 과대 성장 | 중간 | 렉 | 최대 100개 메시지, 이전 메시지는 "더보기"로 접기 |
| 모바일 키보드 가림 | 높음 | 입력 불편 | `visualViewport` API로 입력창 위치 동 조정 |
| localStorage 용량 초과 | 낮음 | 세션 유실 | 5MB 한도 모니터링, 오래된 세션 자동 정리 |
| 캠페인 시퀀스 복잡도 | 중간 | UX 혼란 | 기본값 제공 (1차:즉시/2차:3일/3차:7일), 변경은 선택사항 |

---

## 10. Rinda 대비 차별화 전략

| 영역 | Rinda | MarketGate (기획 방향) | 차별화 포인트 |
|------|-------|----------------------|-------------|
| **진입점** | 필터 기반 검색 | **챗 + GTM 팩 퀵액션** | 대화하듯 시작, 초보자 친화 |
| **국가 추천** | 없음 (직접 국가 선택) | **AI 수출 유망국 추천 (P1)** | "왜 이 국가인가" 데이터 기반 설명 |
| **바이어 적합도** | 수입 이력 + 채용 공고 | **수출 적합도 점수 + 무역 데이터** | 한국 수출 관점의 맞춤 점수 |
| **캠페인** | 이메일 시퀀스 자동화 | **인콰이어리 초안 + 시퀀스** | draft_en/draft_ko 자동 생성 |
| **팀 기능** | 워크스페이스 + 중복 방지 | **세션 공유 링크 + 캠페인 공유** | 링크 하나로 즉시 공유, 진입장벽 최소화 |
| **언어** | 20개 언어 지원 | **한국어 중심 + 영어 draft** | 한국 수출 기업 맞춤 |

---

## 11. 다음 프롬프트 제안

```
"Phase 1 구현 시작: 
1. ChatModePage.jsx + ChatHistory.jsx + ChatInput.jsx 신규 작성
2. App.jsx에 'chat' 페이지 추가, 기존 AnalysisPage는 건드리지 말기
3. GtmPackStrip.jsx + GtmPackCard.jsx 신규 작성, src/data/gtm-packs.json 정적 데이터 생성
4. ModeToggle로 chat/analysis 전환만 가능하게 구현"
```
