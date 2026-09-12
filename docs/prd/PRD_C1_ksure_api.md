# PRD: C1 - K-SURE 외부 신용조사 연계

## 1. 목적
MarketGate의 해외기업 기본검증 결과에서 K-SURE K-Sight 및 국외기업 신용조사 신청 페이지로 연결한다.

무료 기본검증은 법인 실체와 등록정보 확인까지만 제공하며, 재무상태·결제이력·신용등급·지급능력 판단은 K-SURE의 별도 신용조사 영역으로 분리한다.

## 2. 현재 MVP 구현 범위
- K-SURE K-Sight 외부 조회 링크 제공
- K-SURE 국외기업 신용조사 신청 링크 제공
- 기본검증 결과에 `신용조사 필요` 안내 표시
- 링크는 새 창에서 열고 `noopener noreferrer` 적용

## 3. 현재 MVP 제외 범위
- `KSURE_API_KEY` 환경변수 추가
- K-SURE 비공개 또는 확인되지 않은 API 호출
- A~D 등급·위험등급 자동 표시
- 무역보험 상품 자동 추천
- K-SURE 데이터 스크래핑·저장·재판매
- 무료 제공 건수 하드코딩

K-SURE 무료 혜택과 수수료는 변경될 수 있으므로 화면에는 대상여부 조회 링크와 확인일만 표시한다.

## 4. 화면 요구사항
바이어 상세의 `법인등록 기본검증` 영역에 다음 버튼을 제공한다.

```text
K-SURE 기업 조회
K-SURE 신용조사 신청
```

기본 안내문:

```text
현재 결과는 법적 실체와 등록정보에 대한 기본확인입니다.
재무상태, 결제이력, 신용등급 및 지급능력 확인은 별도의 신용조사가 필요합니다.
```

## 5. 상태 정책
기존 신용조사 진행상태를 유지한다.

```text
not_requested
pending
report_received
expired
```

신규 법인등록 기본검증 상태(`registry_check_status`)와 기존 신용조사 상태(`creditStatus`)를 합치지 않는다.

`registry_check_status` enum 값은 정확히 아래 5개만 사용한다:

| 값 | 의미 |
|---|---|
| `BASIC_CONFIRMED` | 기본 확인 완료 |
| `BASIC_PARTIAL` | 부분 확인 |
| `DATA_MISMATCH` | 데이터 불일치 |
| `INACTIVE_ENTITY` | 비활성 법인 |
| `CREDIT_CHECK_REQUIRED` | 신용조사 필요 |

`fitScore`, 기존 `creditStatus`, `core.buyers.verification_status`와 혼합하지 않는다.

## 6. 예외처리
- 외부 링크 설정 누락: 버튼 비활성화 + `외부 조회 링크 준비 중` 표시
- 새 창 차단: 같은 링크를 복사할 수 있도록 제공
- 외부 서비스 장애: MarketGate 기본검증 결과는 그대로 유지
- K-SURE 결과 미확인: 임의로 `안전`, `우수`, `거래 가능` 판정 금지

## 7. 테스트 기준
- K-SURE 외부 링크가 새 창으로 열림
- `noopener noreferrer` 적용
- 기본검증 결과와 `creditStatus`가 서로 덮어쓰지 않음
- 링크 누락 시 오류 없이 빈상태 표시
- 신용등급·위험등급·보험상품이 임의 생성되지 않음

## 8. 개발 TASK
- C1-01: 공식 K-SURE 링크를 설정파일 또는 환경변수로 관리
- C1-02: BuyerSearch 기본검증 카드에 외부 링크 추가
- C1-03: 링크 누락·외부 장애 안내상태 구현
- C1-04: 기존 `creditStatus`와 기본검증 상태 분리 테스트
- C1-05: 실제 API 제공범위와 이용조건 확인 후 별도 PRD 작성

## 9. 우선순위
**현재 MVP 포함:** 외부 링크 연계

**후순위:** 실제 API 연동은 아래 5가지가 모두 확인된 후 별도 PRD로 진행한다:
1. K-SURE 공식 API 제공 여부 및 상품계약
2. 호출비용 및 과금구조 확인
3. 데이터 저장 권리
4. 화면 표시 권리
5. 재이용(재판매) 권리

## 10. PR 제목 추천
`docs(ksure): scope MVP to external credit-check links`
