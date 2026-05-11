# PRD: C2 - Hunter.io 이메일 검증 연동

## 1. 목적
바이어 이메일 발송 전 Hunter.io API로 실시간 유효성 검증하여 반송률 감소.

## 2. MVP 구현 범위
- 인콰이어리 발송 전 이메일 유효성 자동 검증
- 유효하지 않은 이메일 → 발송 차단 + 사용자 안내

## 3. 주요 기능
- 이메일 형식·도메인·MX레코드 검증
- 검증 결과: valid / risky / invalid
- invalid 시 발송 차단

## 4. 필요한 데이터
- Hunter.io API Key (환경변수: `HUNTER_API_KEY`)
- 엔드포인트: `GET https://api.hunter.io/v2/email-verifier?email={email}&api_key={key}`

## 5. API/화면 요구사항
- 기존 POST /v1/inquiry 내부에서 자동 호출 (별도 엔드포인트 불필요)
- invalid → 422 Unprocessable + "유효하지 않은 이메일" 메시지
- risky → 경고 표시 후 발송 허용

## 6. 예외처리
- Hunter.io API 실패 → 검증 스킵 후 발송 허용 (서비스 중단 방지)
- API Rate limit → 캐싱 (이메일별 TTL 7일)
- 개인정보: 이메일 로그 저장 최소화

## 7. 테스트 기준
- 유효 이메일 → 인콰이어리 정상 발송
- invalid 이메일 → 422 반환 + 발송 차단
- Hunter.io 장애 → 발송 허용 (fallback 동작)

## 8. 개발 TASK
- C2-01: Hunter.io API 클라이언트
- C2-02: 이메일 캐시 레이어
- C2-03: inquiry_service.py에 검증 로직 삽입
- C2-04: 테스트 케이스 (valid/invalid/risky/장애)

## 9. 우선순위
**10순위** — B4 완료 후 진행

## 10. PR 제목 추천
`feat(email): C2 Hunter.io 이메일 유효성 검증 연동`
