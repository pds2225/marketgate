# PRD: B4 - 바이어 컨택 응답 추적

## 1. 목적
인콰이어리 발송 후 발송/열람/응답 상태를 추적하여 후속 행동 지원.

## 2. MVP 구현 범위
- 인콰이어리 발송 이력 저장
- 상태 관리: 발송됨 → 열람됨 → 응답됨
- 응답 수신 시 13C 차감

## 3. 주요 기능
- 컨택 발송 시 이력 생성 (5C 차감)
- 바이어 응답 수신 시 상태 업데이트 (13C 차감)
- 발송 목록 조회 및 상태 필터

## 4. 필요한 데이터
- `data/contacts.json`: `{contact_id, buyer_id, user_id, status, sent_at, replied_at}`
- 상태값: `sent | opened | replied`

## 5. API/화면 요구사항
```
GET  /v1/contacts                 → 발송 이력 목록
GET  /v1/contacts/{id}            → 단건 상태 조회
POST /v1/contacts/{id}/reply      → 응답 수신 처리 + 13C 차감
PATCH /v1/contacts/{id}/status    → 상태 수동 업데이트
```
- 프론트: 컨택 현황 탭, 상태 badge 표시

## 6. 예외처리
- 이미 응답된 컨택 재응답 → 409 Conflict (중복 차감 방지)
- 잔액 부족 상태에서 응답 수신 → 이력은 저장, 크레딧 별도 청구 안내

## 7. 테스트 기준
- 인콰이어리 발송 → contacts에 sent 상태 생성
- 응답 수신 → replied 상태 + 13C 차감 확인
- 중복 응답 → 409 반환

## 8. 개발 TASK
- B4-01: contacts 저장소 생성
- B4-02: 발송 시 이력 자동 생성 (inquiry_service 연동)
- B4-03: GET /v1/contacts 엔드포인트
- B4-04: POST /v1/contacts/{id}/reply + 13C 차감
- B4-05: 프론트 컨택 현황 UI

## 9. 우선순위
**8순위** — A1·B3 완료 후 진행

## 10. PR 제목 추천
`feat(contact): B4 바이어 컨택 응답 추적 시스템 구현`
