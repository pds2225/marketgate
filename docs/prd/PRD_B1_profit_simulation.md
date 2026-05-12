# PRD: B1 - 수익성 시뮬레이션

## 1. 목적
관세·물류비를 반영한 Landed Cost 기반 수익성 계산으로 수출 전 손익 검증 제공.

## 2. MVP 구현 범위
- Landed Cost 계산 (제품단가 + 관세 + 물류비 + 보험료)
- BEP(손익분기점) 및 마진율 산출
- 기본 계산은 무료, 상세 시뮬레이션은 크레딧 차감 없음(A2 Basic 제공)

## 3. 주요 기능
- 입력: 제품단가, HS코드, 목표국가, 수량, 물류방식(항공/해운)
- 출력: Landed Cost, BEP 수량, 예상 마진율, 수익성 등급

## 4. 필요한 데이터
- 관세율 데이터 (KOTRA API 또는 정적 CSV)
- 물류비 기준표 (항공/해운 단가, 가정값 허용)
- 환율 (World Bank API 또는 고정값)

## 5. API/화면 요구사항
```
POST /v1/simulation/landed-cost   → {hs_code, country, unit_price, qty, logistics} → {landed_cost, margin_rate, bep_qty}
POST /v1/simulation/bep           → {price, fixed_cost, variable_cost} → {bep_qty, bep_revenue}
```
- 프론트: 수치 입력 폼 + 결과 차트(선택)

## 6. 예외처리
- 관세율 데이터 없는 국가 → 가정값(5%) + 경고 표시
- 음수 마진율 → "적자 수출 구조" 경고
- HS코드 불일치 → 400 Bad Request

## 7. 테스트 기준
- HS코드 330499, 미국, 단가 $10 → Landed Cost 정상 계산
- BEP 계산 입력값 검증 테스트
- 관세율 없는 국가 → fallback 동작 확인

## 8. 개발 TASK
- B1-01: 관세율·물류비 데이터 로더
- B1-02: Landed Cost 계산 서비스
- B1-03: BEP·마진율 계산 서비스
- B1-04: POST /v1/simulation 엔드포인트
- B1-05: 프론트 시뮬레이션 입력/결과 화면

## 9. 우선순위
**5순위** — A1 완료 후 독립 진행 가능

## 10. PR 제목 추천
`feat(simulation): B1 Landed Cost·BEP 수익성 시뮬레이션 구현`
