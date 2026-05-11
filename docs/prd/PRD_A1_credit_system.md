# PRD: A1 - 크레딧 시스템

## 1. 목적
유료 기능(바이어 조회·컨택 등) 사용 시 크레딧을 차감하는 과금 단위 시스템 구현.

## 2. MVP 구현 범위
- JSON 파일 기반 크레딧 저장소 (DB 없이 운영)
- user_id 고정("default") → A4 인증 완료 후 교체
- 충전/차감/잔액조회/이력조회 API

## 3. 주요 기능
| 기능 | 상품명 | 차감 |
|------|--------|------|
| 바이어 상세정보 열람 | Buyer Fit Lite | 3C |
| 바이어 신용레포트 | Buyer Fit Pro | 25C |
| 바이어 컨택 발송 | Buyer Contact 발송 | 5C |
| 바이어 컨택 응답 | Buyer Contact 응답 | 13C |

## 4. 필요한 데이터
- `data/credits.json`: `{user_id: {balance, history[]}}`
- 1C = 2,000원 (A3 결제 연동 후 적용)

## 5. API/화면 요구사항
```
GET  /v1/credits/balance          → {user_id, balance}
POST /v1/credits/charge           → {user_id, amount} → {balance}
POST /v1/credits/deduct           → {user_id, action} → {balance, deducted}
GET  /v1/credits/history          → [{action, amount, balance, timestamp}]
```
- 프론트: 헤더 잔액 badge, 차감 후 실시간 갱신

## 6. 예외처리
- 잔액 부족 → `402 Payment Required` + `"insufficient_credits"`
- JSON 파일 깨짐 → 빈 dict 복구 후 재생성
- 잔액 음수 방지 (deduct 전 검증)
- amount <= 0 입력 → 400 Bad Request

## 7. 테스트 기준
- `get_balance()` → 100 반환
- `charge(50)` → 150 반환
- `deduct(10)` → 140 반환
- `deduct(9999)` → `insufficient_credits` 에러

## 8. 개발 TASK
- A1-01: credit_store.py + credits.json 생성 ✅
- A1-02: GET /v1/credits/balance 엔드포인트
- A1-03: POST /v1/credits/charge 엔드포인트
- A1-04: POST /v1/credits/deduct + 기존 API 트리거 연결
- A1-05: GET /v1/credits/history + 프론트 잔액 표시

## 9. 우선순위
**1순위** — 모든 유료 기능의 선행 조건

## 10. PR 제목 추천
`feat(credits): A1 크레딧 시스템 구현 (잔액/충전/차감/이력)`
