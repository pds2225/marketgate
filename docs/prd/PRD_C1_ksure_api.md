# PRD: C1 - K-SURE API 연동

## 1. 목적
K-SURE 바이어 신용 조회 및 무역보험 추천/가입 안내 기능 제공.

## 2. MVP 구현 범위
- K-SURE API로 바이어 신용등급 조회
- 신용도 기반 무역보험 상품 추천
- 가입 안내 링크 제공

## 3. 주요 기능
- 바이어 국가·기업명으로 신용 조회
- 신용등급 표시 (A~D, Unknown)
- 추천 보험 상품 안내

## 4. 필요한 데이터
- K-SURE API Key (환경변수: `KSURE_API_KEY`)
- 가정: `GET /ksure/credit?company={name}&country={iso3}` → `{grade, risk_level}`

## 5. API/화면 요구사항
```
GET /v1/buyers/{buyer_id}/credit  → {grade, risk_level, insurance_products[]}
```
- 프론트: 바이어 카드에 신용등급 badge

## 6. 예외처리
- K-SURE 조회 실패 → "신용정보 조회 불가" 표시, 서비스 중단 없음
- API 타임아웃 (3초) → fallback: Unknown 표시
- Rate limit → 캐싱 (TTL 24시간)

## 7. 테스트 기준
- 정상 바이어 → 신용등급 반환
- K-SURE 응답 없음 → Unknown + 서비스 정상 동작
- 캐시 히트 확인

## 8. 개발 TASK
- C1-01: K-SURE API 클라이언트 (mock 우선)
- C1-02: 캐싱 레이어 (TTL 24h)
- C1-03: GET /v1/buyers/{id}/credit 엔드포인트
- C1-04: 무역보험 상품 추천 로직
- C1-05: 프론트 신용등급 표시

## 9. 우선순위
**9순위** — B2·B3 완료 후 진행

## 10. PR 제목 추천
`feat(ksure): C1 K-SURE 바이어 신용 조회 연동`
