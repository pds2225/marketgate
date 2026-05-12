# PRD: A2 - 구독 플랜 관리

## 1. 목적
Basic/Pro/Advanced 플랜별 기능 접근 권한을 제어하고 구독 상태를 관리.

## 2. MVP 구현 범위
- 플랜 정보 저장 (JSON 기반)
- 플랜별 기능 접근 제어 미들웨어
- 플랜 전환 API

## 3. 주요 기능
| 플랜 | 월 구독료 | 크레딧 포함 | 주요 기능 |
|------|-----------|-------------|-----------|
| Basic | 무료 | 0C | 수출국 탐색, BEP 계산 |
| Pro | 9,900원 | 월 5C | Buyer Fit Lite, 수익분석 |
| Advanced | 29,000원 | 월 15C | Buyer Fit Pro, 컨택, 리포트 |

## 4. 필요한 데이터
- `data/subscriptions.json`: `{user_id: {plan, started_at, expires_at}}`
- 플랜별 권한 매핑 상수

## 5. API/화면 요구사항
```
GET  /v1/subscription             → {user_id, plan, expires_at}
POST /v1/subscription/upgrade     → {user_id, plan} → {plan, credits_added}
POST /v1/subscription/downgrade   → {user_id, plan}
```
- 프론트: 마이페이지 플랜 표시 및 업그레이드 버튼

## 6. 예외처리
- 만료된 플랜 → Basic으로 자동 다운그레이드
- 결제 실패 시 플랜 전환 차단 (A3 연동 후)
- 동일 플랜 재신청 → 400 Bad Request

## 7. 테스트 기준
- Basic 사용자가 Pro 전용 기능 호출 시 403 반환
- 플랜 업그레이드 후 크레딧 자동 추가 확인
- 만료 후 Basic 자동 전환 확인

## 8. 개발 TASK
- A2-01: 구독 저장소 + 플랜 상수 정의
- A2-02: GET/POST /v1/subscription 엔드포인트
- A2-03: 플랜별 기능 접근 제어 미들웨어
- A2-04: 플랜 업그레이드 시 크레딧 자동 추가 (A1 연동)
- A2-05: 프론트 플랜 표시 UI

## 9. 우선순위
**2순위** — A1 완료 후 진행

## 10. PR 제목 추천
`feat(subscription): A2 구독 플랜 관리 구현 (Basic/Pro/Advanced)`
