# PRD: D1 - 주문서/계약서 자동생성 (RPA)

## 1. 목적
기존 입력값(바이어 정보, 제품, 단가 등)으로 주문서와 계약서를 자동 생성. Alibaba.com 방식 벤치마킹.

## 2. MVP 구현 범위
- 표준 계약서 템플릿 기반 자동 생성
- PDF 다운로드 제공
- 바이어 결제 링크 삽입 가능

## 3. 주요 기능
- 입력: 바이어 정보, 제품명, HS코드, 수량, 단가, 결제 조건
- 출력: 주문서 PDF + 계약서 PDF
- 바이어에게 이메일로 발송 옵션 (선택)
- 바이어 결제 링크 포함 (D2 연동)

## 4. 필요한 데이터
- 계약서 템플릿 (Jinja2 HTML → PDF)
- 결제 링크 생성 로직 (A3/D2 연동)

## 5. API/화면 요구사항
```
POST /v1/orders/generate          → {buyer_id, product, qty, unit_price, payment_terms} → {order_pdf_url, contract_pdf_url}
POST /v1/orders/{id}/send         → 바이어에게 이메일 발송
GET  /v1/orders                   → 생성된 주문서 목록
```

## 6. 예외처리
- 필수 입력값 누락 → 422 Unprocessable
- PDF 생성 실패 → 재시도 1회 후 에러 반환
- 이메일 발송 실패 → 주문서 생성은 유지, 발송만 실패 처리

## 7. 테스트 기준
- 필수 입력값 → PDF URL 반환 확인
- 생성된 PDF 내 바이어 이름·단가 정확히 치환 확인
- 이메일 발송 실패 → 주문서 삭제 없음 확인

## 8. 개발 TASK
- D1-01: 계약서/주문서 Jinja2 템플릿 작성
- D1-02: PDF 생성 서비스 (WeasyPrint)
- D1-03: POST /v1/orders/generate 엔드포인트
- D1-04: 이메일 발송 연동 (SMTP)
- D1-05: 프론트 주문서 생성 폼 + 다운로드

## 9. 우선순위
**12순위** — A3·B4 완료 후 진행

## 10. PR 제목 추천
`feat(rpa): D1 주문서·계약서 자동생성 구현`
