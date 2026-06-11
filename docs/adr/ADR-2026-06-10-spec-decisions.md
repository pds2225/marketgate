# ADR: SPEC 결함 해소 결정 (M1/M6) 및 미정의 산식 보류

- 날짜: 2026-06-10
- 상태: 채택 (자동승인 모드 — 사용자 "머지까지 자동승인" 지시에 따른 보수적 기본값. 사후 검토·번복 가능)
- 근거: 갭 진단 리포트 2026-06-10 (SPEC R1~R66 vs 구현 교차비교), ralplan 합의(Architect→Critic APPROVE)

## 배경

구현 전 결정이 필요한 SPEC 자체의 결함이 진단에서 확인됐다. 코드가 추측으로
수식을 발명하면 테스트가 "추측을 진실로 고정"하므로, 코드 작업 전에 결정을
문서로 남긴다.

## 결정 1 — M1: fit_score 이중 체계

**문제:** REQUIREMENTS.md의 fit_score(국가 추천: 가중치 4종×100 + soft 감점)와
RULES_SPEC.md §4의 fit_score(바이어 매칭: base 50 + 보너스/패널티)가 같은 이름의
다른 공식. 현재 코드의 바이어 점수는 둘 다 아닌 제3의 체계(fit_score_v0:
country20/hs35/contact15/activity15/signal15).

**결정:**
- 두 fit_score는 대상이 다르다(국가 vs 바이어). 충돌이 아니라 별개 엔진으로 해석한다.
- RULES_SPEC §4 엔진은 **별도 모듈로 구현하되, 바이어 데이터에 moq/certification/
  mov_usd/buyer_budget 컬럼이 없는 동안 fit_score_v0가 랭킹을 유지**한다.
- RULES 엔진의 게이트·점수는 응답에 **추가 정보 필드로만** 노출한다
  (`not_evaluated` 포함). **랭킹(정렬 순서)은 변경하지 않는다** — 해석 A 고정.
- 데이터 컬럼이 확보되면 fit_score_v0 교체 여부를 그때 재논의한다.

## 결정 2 — M6: restricted 감점 단위 충돌

**문제:** SIMULATION_SPEC §2.3은 compliance_penalty=-10(점수),
§4.2 calculation_breakdown은 -0.10(확률)을 사용.

**결정:** SPEC이 두 값을 서로 다른 양에 동시에 적용하라고 명시한 것으로 해석한다
(Critic 검증: SPEC 59-65, 504-512행에 둘 다 명시 — 충돌이 아니라 병행 적용).
- 점수 체계: restricted 국가 **-10점** (REQUIREMENTS Soft Rule R10 / SIM §2.3)
- 성공확률: `max(0.05, success_probability - 0.10)` (해당 기능 구현 시)
- calculation_breakdown 표기: 확률 단위(-0.10)

## 결정 3 — 제재 게이트 즉시 적용 (이전 보류 결정 번복)

**문제:** config.py의 주석은 과거 합의(2/3)로 제재국 반영을 보류한다고 기록.
그러나 blocked 국가(KP/IR/SY/CU)가 추천·시뮬레이션에 노출되는 것은 법적 리스크.

**결정:** 2026-06-10 사용자 지시("실사용 기준 갭 자동개발, 머지까지 자동승인")에
따라 보류를 해제한다.
- blocked: 진입점 HTTP 400 차단 + 추천 결과에서 제외 (B0, `app/services/compliance.py`)
- restricted: 점수 -10 적용 (B1)
- 제재 목록의 단일 진실 출처는 `app/services/compliance.py` 하나로 한다.

## 결정 4 — 미정의 산식 보류 (발명 금지)

다음은 SPEC에 산식이 없어 **구현하지 않고 보류**한다. SPEC 보완 후 구현한다.
- M2: fraud_penalty(-25~0) 계산식
- M4: success_probability 일반식 (base_probability, components 산출법)
- M5: economic_indicators.risk_grade(A~D) 등급 기준
- M7: estimated_revenue / market_share min/max 산식
- M8: hs_similarity 0.6 판정용 산업군 매핑 테이블

## 결정 5 — B2 데이터 계약 (unknown-data contract)

바이어 CSV에 moq/certification/mov_usd/buyer_budget 컬럼이 실재하지 않음이
확인됐다(헤더 검증). RULES 엔진은 입력을 전부 Optional로 받고:
- 데이터 부재 시: `gate: not_evaluated`, `score: null`, `data_status: unknown`
- 통과/탈락을 침묵으로 가장하지 않는다.
- 컬럼 채우기(데이터 소싱)는 별도 후속 과제 — 본 배치의 전제 조건이 아니다.

## 결과

- B1 테스트 acceptance 값이 확정됨: -10점, max(0.05, p-0.10), confidence 경계
  0.8/0.6/0.4.
- B2는 데이터 없이도 출고 가능(정직한 unknown), 데이터 도착 시 즉시 동작.
- 후속 과제: 데이터 소싱, M2/M4/M5/M7/M8 SPEC 보완, JSON 스토어·sys.path 구조 부채.
