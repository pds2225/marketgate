# PRD: B3 - MOQ 필터링 고도화

## 1. 목적
셀러 MOQ와 바이어 MOQ를 자동 비교하여 거래 가능한 바이어만 필터링.

## 2. MVP 구현 범위
- 셀러 MOQ 입력 → 바이어 MOQ와 자동 비교
- MOQ 조건 불일치 바이어 제외
- 기존 /v1/buyers 엔드포인트에 파라미터 추가

## 3. 주요 기능
- 입력: 셀러 MOQ (수량)
- 비교: 셀러 MOQ ≥ 바이어 요구 MOQ
- 결과: 거래 가능 바이어만 반환, 제외 사유 표시

## 4. 필요한 데이터
- 바이어 DB에 `moq_required` 필드 존재 여부 확인 필요
- 없으면 null 처리 → 조건 미적용

## 5. API/화면 요구사항
```
GET /v1/buyers?hs_code=330499&country=USA&seller_moq=100
→ moq_required <= 100 인 바이어만 반환
```
- 프론트: MOQ 입력 필드 추가 (선택사항)

## 6. 예외처리
- 바이어 MOQ 데이터 없음 → 조건 미적용 (포함 유지)
- seller_moq = 0 → 필터 미적용
- 음수 입력 → 400 Bad Request

## 7. 테스트 기준
- seller_moq=100, buyer moq=200 → 해당 바이어 제외
- seller_moq=0 → 전체 반환
- MOQ 없는 바이어 → 포함 확인

## 8. 개발 TASK
- B3-01: 바이어 DB MOQ 필드 확인 및 보완
- B3-02: MOQ 비교 필터 로직 (scoring.py 또는 data_loaders.py)
- B3-03: /v1/buyers에 seller_moq 파라미터 추가
- B3-04: 테스트 케이스 추가

## 9. 우선순위
**6순위** — A1 완료 후 독립 진행 가능

## 10. PR 제목 추천
`feat(filter): B3 MOQ 기반 바이어 필터링 고도화`
