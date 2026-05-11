# PRD: D2 - 계약 중개 수수료 처리

## 1. 목적
바이어-셀러 계약 성사 시 거래액의 2% 중개 수수료를 자동 정산.

## 2. MVP 구현 범위
- 계약 성사 이벤트 등록
- 거래액 2% 수수료 계산 및 청구
- 바이어 결제 링크 생성 포함

## 3. 주요 기능
- 계약 성사 등록 (수동 또는 D1 주문서 연동)
- 수수료 = 거래액 × 2% 자동 계산
- 수수료 청구서 생성 및 발송
- 바이어 측 결제 수단 연동 (토스페이먼츠 A3 연동)

## 4. 필요한 데이터
- `data/contracts.json`: `{contract_id, buyer_id, seller_id, amount, fee, status, created_at}`
- 결제 연동: 토스페이먼츠 (A3 연동)

## 5. API/화면 요구사항
```
POST /v1/contracts                → {buyer_id, seller_id, trade_amount} → {contract_id, fee, payment_url}
GET  /v1/contracts                → 계약 목록
PATCH /v1/contracts/{id}/paid     → 수수료 납부 완료 처리
```
- 바이어 결제 링크 → 토스페이먼츠 결제창 연동 (A3)

## 6. 예외처리
- 수수료 결제 실패 → 계약 상태 "fee_pending" 유지
- 중복 등록 방지 → contract_id 기반 idempotency
- 거래액 0원 → 400 Bad Request

## 7. 테스트 기준
- 거래액 5,000만원 → 수수료 100만원 계산 확인
- 결제 성공 → 상태 "completed" 변경 확인
- 중복 등록 → 409 반환

## 8. 개발 TASK
- D2-01: contracts 저장소 생성
- D2-02: 수수료 계산 서비스
- D2-03: POST /v1/contracts 엔드포인트
- D2-04: 바이어 결제 링크 생성 (토스페이먼츠, A3 연동)
- D2-05: 수수료 청구서 PDF 생성 (D1 템플릿 재활용)

## 9. 우선순위
**13순위** — D1·A3 완료 후 진행

## 10. PR 제목 추천
`feat(contract): D2 계약 중개 수수료 2% 정산 구현`
