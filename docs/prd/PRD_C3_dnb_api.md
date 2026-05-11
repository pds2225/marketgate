# PRD: C3 - D&B 신용데이터 연동

## 1. 목적
D&B(Dun & Bradstreet) API로 바이어 재무·신용정보를 조회하여 Buyer Fit Pro에 제공.

## 2. MVP 구현 범위
- DUNS 번호 기반 기업 신용정보 조회
- 조회 결과를 B2 PDF 레포트에 연동

## 3. 주요 기능
- 기업명/국가로 DUNS 번호 검색
- 신용등급, 부도위험, 연매출, 직원수 조회
- 조회 결과 캐싱 (TTL 72시간)

## 4. 필요한 데이터
- D&B 해외기업 신용조사보고서 API (PDF/Text/HTML 형식 제공)
- 환경변수: `DNB_APP_KEY`, `DNB_SECRET_KEY` (실제 키는 .env에만 저장)
- 인증방식: App Key (호출용) + Secret Key (인증용)
- 응답 형식: PDF / Text / HTML 선택 가능

## 5. API/화면 요구사항
```
GET /v1/buyers/{buyer_id}/dnb     → {duns, credit_grade, revenue, employees, risk_score}
```
- B2 PDF 생성 시 내부 호출 (직접 노출 없음)

## 6. 예외처리
- D&B 조회 실패 → B2 PDF에 "신용정보 미확인" 섹션으로 대체
- DUNS 없는 기업 → 기업명 검색 fallback
- 비용 과금 주의: 조회당 비용 발생 → 캐싱 필수
- API Key 만료 → 알림 + 서비스 중단 방지

## 7. 테스트 기준
- DUNS 번호로 신용정보 반환 확인
- 캐시 TTL 내 재조회 → API 미호출 확인
- D&B 장애 → PDF 생성 시 fallback 동작

## 8. 개발 TASK
- C3-01: D&B OAuth 인증 클라이언트
- C3-02: DUNS 검색 + 재무정보 조회
- C3-03: 캐싱 레이어 (TTL 72h)
- C3-04: GET /v1/buyers/{id}/dnb 엔드포인트
- C3-05: B2 PDF 연동

## 9. 우선순위
**11순위** — B2 착수 전 병행 진행

## 10. PR 제목 추천
`feat(dnb): C3 D&B 신용데이터 API 연동`
