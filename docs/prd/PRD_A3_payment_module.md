# PRD: A3 - 결제 모듈 연동

## 1. 목적
구독료 자동결제 및 크레딧 충전을 위한 PG사 연동 구현.

## 2. MVP 구현 범위
- 국내 PG사: **토스페이먼츠** 확정
- 구독료 정기결제 + 크레딧 단건 결제
- 결제 성공/실패 webhook 처리

## 3. 주요 기능
- 구독료 자동결제 (월간)
- 크레딧 충전 (1C = 2,000원, 패키지 할인 가능)
- 결제 이력 조회
- 환불 처리 (관리자)

### 크레딧 충전 패키지
| 패키지 | 크레딧 | 가격 | 단가 |
|--------|--------|------|------|
| 소형 | 10C | 20,000원 | 2,000원/C |
| 중형 | 30C | 54,000원 | 1,800원/C (10% 할인) |
| 대형 | 100C | 160,000원 | 1,600원/C (20% 할인) |

## 4. 필요한 데이터
- `data/payments.json`: 결제 이력
- PG사 API Key (환경변수: `PG_SECRET_KEY`, `PG_CLIENT_KEY`)

## 5. API/화면 요구사항
```
POST /v1/payment/checkout         → {user_id, product_type, amount} → {payment_url}
POST /v1/payment/webhook          → PG사 결제 결과 수신
GET  /v1/payment/history          → [{payment_id, amount, status, timestamp}]
POST /v1/payment/refund           → {payment_id} (관리자 전용)
```

### 결제 플로우
```
프론트 → POST /checkout → 서버가 토스페이먼츠 결제창 URL 생성
→ 프론트 리다이렉트 → 토스페이먼츠 결제창 → 사용자 결제
→ 토스페이먼츠 → POST /webhook (서버) → 크레딧/플랜 반영
→ 프론트 콜백 페이지 도착 (성공/실패)
```

### Webhook 페이로드 구조 (토스페이먼츠)
```json
{
  "paymentKey": "toss_pk_xxxx",
  "orderId": "order_20260514_abc123",
  "status": "DONE",
  "totalAmount": 20000,
  "method": "카드",
  "requestedAt": "2026-05-14T10:00:00+09:00",
  "approvedAt": "2026-05-14T10:00:05+09:00"
}
```
- `orderId` 형식: `{product_type}_{user_id}_{timestamp}`
- `status`: `DONE`(성공), `CANCELED`(취소), `ABORTED`(실패)

### 환경변수
| 변수명 | 설명 |
|--------|------|
| `TOSS_SECRET_KEY` | 토스페이먼츠 시크릿 키 (서버 전용) |
| `TOSS_CLIENT_KEY` | 토스페이먼츠 클라이언트 키 (프론트용) |
| `TOSS_WEBHOOK_SECRET` | Webhook HMAC 서명 검증 키 |

## 6. 예외처리
- 결제 실패 → 크레딧/플랜 미변경, 에러 메시지 반환
- Webhook 위변조 방지 → HMAC 서명 검증 필수
- 중복 결제 방지 → idempotency key 사용
- 네트워크 타임아웃 → 결제 상태 재조회 로직

## 7. 테스트 기준
- 테스트 결제 성공 → 크레딧 충전 확인
- Webhook 위변조 → 400 반환 확인
- 결제 실패 → 잔액 변동 없음 확인

## 8. 개발 TASK
- A3-01: 토스페이먼츠 SDK 설치 및 환경변수 설정
- A3-02: 결제창 연동 (프론트 → PG → Webhook)
- A3-03: Webhook 수신 및 크레딧/플랜 반영 (A1·A2 연동)
- A3-04: 결제 이력 API
- A3-05: 프론트 결제 UI (충전 모달)

## 9. 우선순위
**3순위** — A1·A2 완료 후 진행. 보안 리스크 최고 단계

## 10. PR 제목 추천
`feat(payment): A3 PG사 결제 모듈 연동 (구독/크레딧 충전)`
