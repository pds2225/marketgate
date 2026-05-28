# PRD INDEX — MarketGate

> AI 기반 중소기업 수출 One-Stop 플랫폼. 수출국 추천 → 바이어 매칭 → 수익성 시뮬레이션 → 신용조회 → 컨택 → 주문·결제

---

## 전체 PRD 목록

| ID | 파일 | 설명 | 상태 |
|----|------|------|------|
| A1 | [PRD_A1_credit_system.md](PRD_A1_credit_system.md) | 크레딧 잔액·차감·이력 | 🔨 진행중 |
| A2 | [PRD_A2_subscription_plan.md](PRD_A2_subscription_plan.md) | Basic/Pro/Advanced 플랜 | ⬜ 대기 |
| A3 | [PRD_A3_payment_module.md](PRD_A3_payment_module.md) | PG사 결제 연동 | ⬜ 대기 |
| A4 | [PRD_A4_auth_system.md](PRD_A4_auth_system.md) | JWT 회원 인증 | ⬜ 대기 |
| B1 | [PRD_B1_profit_simulation.md](PRD_B1_profit_simulation.md) | Landed Cost·BEP | ⬜ 대기 |
| B2 | [PRD_B2_buyer_fit_pro.md](PRD_B2_buyer_fit_pro.md) | 신용레포트 PDF | ⬜ 대기 |
| B3 | [PRD_B3_moq_filter.md](PRD_B3_moq_filter.md) | MOQ 필터링 | ⬜ 대기 |
| B4 | [PRD_B4_contact_tracking.md](PRD_B4_contact_tracking.md) | 컨택 응답 추적 | ⬜ 대기 |
| C1 | [PRD_C1_ksure_api.md](PRD_C1_ksure_api.md) | K-SURE 신용조회 | ⬜ 대기 |
| C2 | [PRD_C2_hunter_api.md](PRD_C2_hunter_api.md) | Hunter.io 이메일 검증 | ⬜ 대기 |
| C3 | [PRD_C3_dnb_api.md](PRD_C3_dnb_api.md) | D&B 신용데이터 | ⬜ 대기 |
| D1 | [PRD_D1_order_rpa.md](PRD_D1_order_rpa.md) | 주문서·계약서 자동생성 | ⬜ 대기 |
| D2 | [PRD_D2_brokerage_fee.md](PRD_D2_brokerage_fee.md) | 중개 수수료 2% 정산 | ⬜ 대기 |
| E1 | [PRD_E1_remove_chat_wizard_ui.md](PRD_E1_remove_chat_wizard_ui.md) | 채팅 UI 제거·폼/위자드 통일 (React) | ⬜ 대기 |

---

## Phase별 개발 순서 (의존성 기준)

```
Phase A — 수익화 기반 (필수 선행)
  A1 크레딧 시스템     ← 현재 진행
  A2 구독 플랜         ← A1 완료 후
  A3 결제 모듈         ← A1+A2 완료 후
  A4 회원 인증         ← A1~A3 완료 후

Phase B — 기능 고도화 (A1 완료 후 병행 가능)
  B1 수익성 시뮬레이션 ← A1 완료 후 독립 진행
  B3 MOQ 필터링        ← A1 완료 후 독립 진행
  B2 Buyer Fit Pro     ← A1 + C3 완료 후
  B4 컨택 응답 추적    ← A1 + B3 완료 후

Phase C — 외부 API (B 진행 중 병행)
  C2 Hunter.io         ← B4 완료 후
  C1 K-SURE            ← B2+B3 완료 후
  C3 D&B               ← B2 착수 전 병행

Phase D — RPA·결제 (전체 후반)
  D1 주문서 자동생성   ← A3 + B4 완료 후
  D2 중개 수수료       ← D1 + A3 완료 후

Phase E — 프론트 UX (백엔드 독립, A~D와 병행 가능)
  E1 채팅 제거·위자드 통일 ← design/ 설계 참고, Phase 1은 ChatMode 제거만
```

---

## 선행/후행 관계

| TASK | 선행 조건 | 후행 |
|------|-----------|------|
| A1 | 없음 | A2, B1, B3 |
| A2 | A1 | A3 |
| A3 | A1, A2 | A4, D1, D2 |
| A4 | A1~A3 | 전체 |
| B1 | A1 | - |
| B2 | A1, C3 | - |
| B3 | A1 | B4 |
| B4 | A1, B3 | C2, D1 |
| C1 | B2, B3 | - |
| C2 | B4 | - |
| C3 | B2 착수 전 | B2 |
| D1 | A3, B4 | D2 |
| D2 | D1, A3 | - |

---

## 1순위 추천: A1 (크레딧 시스템)

- A1-01 완료 ✅
- 다음: A1-02 `GET /v1/credits/balance` 엔드포인트
- 완료 후: A2 구독 플랜 또는 B1 수익성 시뮬레이션 병행 가능
