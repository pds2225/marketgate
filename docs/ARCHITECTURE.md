# MarketGate 목표 아키텍처 v2 (확정본)

> 작성일: 2026-07-22 · 상태: **설계 확정(구현 전 기준 문서)**
> 근거: 사업성·적법성·데이터 전략 평가 세션 + 외부 아키텍처 리뷰 반영 + 쟁점 사실 4건 검증(§2.2)
> 원칙: **화면(AdminDashboard) 개발 전에 본 문서의 상태 머신·스키마·정책표를 먼저 고정한다.**

---

## 1. 유지 확정된 3대 설계 판단

1. 연락처 판매가 아닌 **플랫폼 중개 발송**
2. 스톡형 DB 판매가 아닌 **매칭·슬롯 판매**
3. `Buyer Core DB`와 `Contact Vault`의 **물리적·권한적 분리**

핵심 경쟁력 정의:

> 적법하게 접촉 가능한 바이어를 선별하고, 접촉 기회를 제한적으로 배분하며,
> 연락처를 노출하지 않고 중개하고, 실제 응답·미팅·견적 결과까지 증명하는 **거래 인프라**

---

## 2. 외부 리뷰 반영 내역

### 2.1 전면 수용 (P0 컴포넌트)

| 컴포넌트 | 역할 |
|---|---|
| Consent & Legal Basis Ledger | 연락처별 수집근거·동의·목적·철회 기록 |
| Source Rights Registry | 출처별 권리 8단계 코드 + 권리별 정책 객체(§4.2) |
| Global Suppression Registry | 이메일·도메인·기업 단위 수신거부·민원·차단 통합 |
| Campaign Orchestrator | 캠페인 상태 머신(§5) 관리 |
| Credit & Entitlement Ledger | 슬롯 예약·차감·복원·환불 원장 |
| Audit Log | 관리자 행위 전수 기록 |
| Response Relay | 익명 중계 회신, 상호동의 후 연락처 공개(§5.3) |
| Tenant Isolation / RBAC | 고객사 간 격리, 역할별 권한 |
| Vault Access Broker | 발송워커의 Vault 직접 접속 금지, 토큰·정책 검증 후 일시 복호화 |
| Signal Store 4분리 | Event Store / Engagement Aggregate / Suppression·Frequency Store / Feature Store |
| Regulatory Adapter | 규제DB 국가별 어댑터 + 공통 출력 스키마(§7.3) |
| Deal Workspace | K-SURE 연계를 안내 기능이 아닌 거래 관리 락인으로(§8) |

개발 순서 수정도 수용: **상태 머신·DB 스키마 확정 → API → 화면.**

### 2.2 쟁점 사실 검증 결과 (2026-07-22, 병렬 검증 4건)

| 쟁점 | 판정 | 아키텍처 반영 |
|---|---|---|
| K-SURE "연 10회 무료 신용조사" | **현행 아님.** 2019.10 시행 과거 우대조치. 현행 공식 수수료 페이지에 무료 조항 없음. 현행 공표 혜택은 신규·리턴 고객 한정 **3건 무료**(등록일부터 1년, K-Sight 게시). 정상요금: 중소중견 요약보고서 33,000원 / Full 49,500원(VAT 포함), 후불제 | 혜택 수치 하드코딩 금지. **K-SURE Policy Registry**(§8.2)로 관리, `verified_at` + 대상여부 조회 링크 표시 |
| "DLP B/L 덤프" 정체 | DLP = Data Liberation Project, 실존 단체(오기 아님). 그러나 CBP B/L FOIA 요청(CBP-FO-2023-075587)은 **2023-04-28 거부**("records unavailable via FOIA")됐고 공개된 데이터셋이 없음 | **무료 B/L 경로 삭제.** 대체: 19 CFR 103.31 기반 CBP 유료 구독(견적 요청) 또는 상용 벤더 라이선스 — 계약 시 재판매·기업명 표시·파생 상품화 권리 명시(§7.2) |
| KISA 정보통신망법 안내서 7차 개정본 | 실재(2026-03-04 게시). 광고 수신동의는 '광고성 정보 수신동의' 명칭 명시 필수('혜택 알림' 등 모호 명칭 불인정), 즉시 수신거부 요구 | 옵트인 수집 UI 문구·캠페인 승인 체크리스트에 반영(§6.2) |
| SES/SendGrid = 국외이전 여부 | **해당.** 보호법 §28조의8: 국외이전은 제공·처리위탁·보관 모두 포함. 계약 이행 목적 처리위탁은 별도 동의 대신 처리방침 공개/고지(5개 사항)로 갈음 가능 + 보호조치 필요 | 처리방침에 국외이전 5개 고지사항 공개, 발송업체 리전·위탁계약(DPA) 관리 항목 추가 |

### 2.3 조건부 수용 (경량 구현 노트)

- **Phase 0 17개 테이블(§9.1)**: 스키마는 전부 수용하되, 1인 운영 현실에 맞춰 단일 Postgres 인스턴스 + 일부 통합 허용:
  `buyer_identifiers`·`buyer_signals`는 초기 JSONB 컬럼으로 시작 가능, `approval_tasks`는 `campaigns` 상태 컬럼으로 흡수 가능.
  단 **통합 금지 5종**: `contacts_vault`, `contact_legal_basis`, `suppression_entries`, `credit_ledger`, `audit_logs` — 이 5개는 분리 자체가 통제다.
- **완성도 점수(55점)**: 개념 설계 대비 운영 설계 갭 지적으로 수용. 본 문서가 그 갭을 메우는 확정본이다.

---

## 3. 목표 아키텍처 다이어그램 (v2)

```text
[수집 소스]
 CBP 구독/상용벤더 B/L · 규제DB(국가별 어댑터) · 전시회 · RFQ 인바운드 · 고객 업로드
                  │
                  ▼
[Source Rights & Lineage Registry]
 출처·계약·허용용도·수집일·만료일·원본 레코드 (§4.2, §4.3)
                  │
                  ▼
[정규화 · Entity Resolution · Data Quality]
 기업 식별 / 중복통합 / 필드 신뢰도 / golden_record_rule
                  │
                  ▼
[Compliance Decision Engine]
 ├─ Legal Basis & Consent Ledger (§4.1)
 ├─ Global Suppression Registry
 ├─ Country Rule Matrix (§6)
 ├─ Retention / Delete Policy
 └─ Manual Review Queue
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
 Buyer Core   Contact Vault   Event Store
 기업정보      암호화·격리      불변 발송·응답 이벤트
        │         │             │
        │  Vault Access Broker  │   (+ Engagement Aggregate
        └─────────┼─────────────┘      / Suppression·Frequency Store
                  ▼                    / Feature Store)
[Matching & Slot Service]  ◀── Export Product Passport(판매자 데이터, §7.5)
 Intent Score(§7.1) ≠ Compliance Eligibility / Inventory / Exclusivity
                  │
                  ▼
[Campaign Orchestrator]  ◀ 상태 머신 §5.1
 검수→승인→슬롯예약→크레딧승인→발송→재시도→종료
                  │
                  ▼
[Send Adapter]  SES / SendGrid (국외이전 고지·DPA 관리)
                  │
     ┌────────────┴────────────┐
     ▼                         ▼
Webhook Processor         Response Relay (§5.3)
반송·민원·수신거부          익명회신·상호동의 공개
     │                         │
     └────────────┬────────────┘
                  ▼
[Attribution & Deal Workspace]  ◀ K-SURE Policy Registry §8
 응답→미팅→샘플→견적→계약→신용조사→보험
                  │
                  ▼
[Credit / Billing Ledger]  차감·복원·환불·보상·정산

────────────── 공통 통제 레이어 ──────────────
Tenant Isolation / RBAC / Audit Log / KMS / Secrets /
Monitoring / Backup / Incident Response
```

---

## 4. 데이터 통제 레이어 정의

### 4.1 Consent & Legal Basis Ledger

연락처 레코드별 필수 필드:

```text
contact_id, buyer_id, source_id, collected_at, collection_method,
legal_basis_code, purpose_code, consent_status, consent_scope,
consent_timestamp, consent_evidence_uri, jurisdiction,
valid_from, valid_until, withdrawn_at, suppression_reason
```

법적 상태 코드:

| 상태 | 의미 | 발송 |
|---|---|---|
| `OPTED_IN` | 명시적 마케팅 수신동의 | 가능 |
| `CONTRACT_REQUIRED` | 계약 이행상 필요한 연락 | 해당 목적만 |
| `LEGITIMATE_INTEREST_REVIEW` | 국가별 LI 검토 대상 | Country Rule Matrix 통과 시 |
| `PUBLIC_CORPORATE_CONTACT` | 공개된 기업 대표 연락처 | 국가·목적별 검토(§6) |
| `UNKNOWN_BASIS` | 처리근거 불명확 | 불가 |
| `WITHDRAWN` | 동의 철회 | 불가 |
| `SUPPRESSED` | 민원·반송·차단 | 불가 |

발신자가 한국 기업이므로 **해외 수신자의 개인 식별 가능한 업무용 이메일에도 개인정보보호법이 적용**된다(정보주체 국적 불문 — 검증 확인). 수집·이용 근거를 반드시 이 원장에 기록한다.

### 4.2 Source Rights Registry

권리 코드 8단계(리뷰안 채택):

| 코드 | Core 저장 | Vault 저장 | 발송 | 상품화 |
|---|---|---|---|---|
| `OPEN_REUSE` | 가능 | 조건부 | 조건부 | 가능 |
| `INTERNAL_ANALYTICS` | 가능 | 불가 | 불가 | 결과만 |
| `OUTREACH_ALLOWED` | 가능 | 가능 | 가능 | 슬롯 가능 |
| `CUSTOMER_PROVIDED` | 가능 | 격리 | 고객 범위 내 | 제한 |
| `CONSENTED_INBOUND` | 가능 | 가능 | 가능 | 가능 |
| `CONTRACT_REQUIRED` | 보류 | 보류 | 불가 | 불가 |
| `PROHIBITED` | 통계만 | 불가 | 불가 | 불가 |
| `UNKNOWN` (기본값) | 격리 | 격리 | 불가 | 불가 |

출처별 권리는 단일 태그가 아닌 **정책 객체**로 관리한다:

```json
{
  "store_core": true,
  "store_contact": false,
  "use_for_scoring": true,
  "show_company_to_customer": false,
  "send_outreach": false,
  "commercialize_derived_output": "review_required"
}
```

초기 출처 매핑(세션 적법성 조사 결과):

| 출처 | 초기 코드 | 비고 |
|---|---|---|
| GoBizKorea 인콰이어리·구매오퍼 | `INTERNAL_ANALYTICS` | 약관상 재판매 금지, 원문 직판 불가 |
| KOTRA SNS 수집분 | `UNKNOWN` → 취득 경로·공공누리 유형 확인 후 재분류 | 미부착 자료는 사전 협의 |
| NIPA 글로벌ICT포털 | `INTERNAL_ANALYTICS` + 연락처 `PROHIBITED` | 이메일 자동수집 거부 명시 사이트 |
| CBP 구독/벤더 B/L | `CONTRACT_REQUIRED` → 계약 체결 후 재분류 | 재판매·표시·파생 권리를 계약에 명시 |
| 규제DB(BPOM 등) | 국가별 검토 후 `OPEN_REUSE`/`INTERNAL_ANALYTICS` | 기업 사실정보 위주, robots·약관 확인 |
| RFQ 인바운드 | `CONSENTED_INBOUND` | 유일한 완전 자유 재사용 |
| 고객 업로드 | `CUSTOMER_PROVIDED` | 테넌트 격리 |

**B/L 데이터는 구매의도 신호이지 연락 동의가 아니다.** B/L 출처만으로는 `CONTACTABLE`이 되지 않으며, 발송 가능 여부는 별도 채널의 Legal Basis + Country Rule로 결정한다.

### 4.3 Data Lineage

Buyer Core 주요 필드별 메타데이터: `source_id, source_record_id, observed_at, ingested_at, confidence_score, verification_status, expires_at`. 출처 간 값 충돌은 덮어쓰기 금지, `golden_record_rule`(신선도·신뢰도 가중)로 대표값 결정.

---

## 5. 상태 머신

### 5.1 캠페인 상태

```text
DRAFT → COMPLIANCE_REVIEW → APPROVED → SLOT_RESERVED → CREDIT_AUTHORIZED
      → QUEUED → SENDING → DELIVERED → RESPONDED → QUALIFIED
      → INTRODUCED → CLOSED_WON / CLOSED_LOST

예외: REJECTED_COMPLIANCE, SUPPRESSED, HARD_BOUNCED, SOFT_BOUNCED,
      RETRYING, CANCELLED, CREDIT_RESTORED, REFUNDED, COMPLAINT_RECEIVED
```

### 5.2 발송 이벤트 → 슬롯 소진 규칙

| 이벤트 | 슬롯 소진 | 크레딧 |
|---|---|---|
| `queued` / `sent` | 아니오 | 홀드 |
| `delivered` | **예** | 확정 차감 |
| `soft_bounce` | 재시도 후 판단 | 홀드 유지 |
| `hard_bounce` | 아니오 | **100% 복원** |
| `complaint` / `unsubscribe` | 즉시 차단 | 복원 + Suppression 등록 |
| `reply_positive` | 성과 인정 | — |
| `reply_negative` / `auto_reply` | 응답이나 성과 제외 | — |

### 5.3 응답 이후 흐름 (Response Relay)

```text
바이어 회신 → Response Inbox → 스팸·자동응답 분류 → 관심도 분류
→ 수출기업에 익명 전달 → 수출기업 회신 작성 → 플랫폼 중계 발송
→ 바이어 연락처 공개 동의 → 상호 공개 또는 플랫폼 내 대화 지속
→ 미팅·샘플·견적·계약 상태 추적 (Deal Workspace)
```

연락처 공개는 **양 당사자 동의 시에만** 가능(슬롯 구매·발송 성공·단순 열람으로는 절대 공개 금지).

---

## 6. Country Rule Matrix (초기 확정값, 2026-07-22 검증 기반)

**기본 원칙: default-deny — 미검토 국가는 발송 불가.**

| 관할 | 법제 | B2B 콜드메일 | 핵심 요건 | 초기 정책 |
|---|---|---|---|---|
| 미국 | CAN-SPAM | **옵트아웃으로 적법** | 정확한 헤더·비기만 제목·광고 표시·물리 주소 기재·수신거부 수단 30일 유지·10영업일 내 처리. 위반 건당 최대 $53,088 | `SEND_ALLOWED` (옵트아웃 준수) |
| 캐나다 | CASL | 옵트인(묵시 예외) | 공개 게시 주소 + 직무 관련 + 수신거부 문구 없음 → 묵시적 동의. **증빙(수집 URL·일시) 기록 필수** | `SEND_CONDITIONAL` |
| 프랑스 등 EU 관대국 | GDPR+ePrivacy §13 | LI 기반 가능 | LIA 문서화 + 명확한 옵트아웃 | `SEND_CONDITIONAL` |
| 독일·오스트리아 | UWG §7 등 | 사전동의 필요 | — | `SEND_BLOCKED` (옵트인 확보 전) |
| 영국 | PECR | 법인 주소 제외 | corporate subscriber 여부 확인 | `SEND_CONDITIONAL` |
| 한국 수신자 | 망법 §50 | 옵트인 | KISA 7차: '광고성 정보 수신동의' 명칭 명시, 즉시 수신거부 | `SEND_BLOCKED` (옵트인 전) |
| 기타 전체 | 미검토 | — | 국가별 검토 후 개방 | `SEND_BLOCKED` (기본값) |

한국 망법 §50의 "한국 발신자→해외 수신자" 적용 여부는 해석 미확정(검증 결과 PARTIAL) → **보수적으로 (광고) 표시·수신거부 수단 등 국내 요건을 전 발송에 준용**한다.

### 6.2 발송 공통 체크리스트 (Campaign Orchestrator의 COMPLIANCE_REVIEW 단계)

1. Legal Basis 상태 발송 가능 여부
2. Country Rule Matrix 통과
3. Suppression Registry 무매치
4. 바이어 빈도상한·쿨다운 통과
5. 승인된 템플릿(광고 표시·물리 주소·수신거부 링크 포함)
6. 발송업체 국외이전 고지: 개인정보 처리방침에 §28조의8 5개 고지사항 공개 상태 확인

---

## 7. 매칭·데이터 소스

### 7.1 Intent Score (초기 배점) — Eligibility와 분리

`Intent Score(구매 가능성) ≠ Compliance Eligibility(발송 가능 여부)`

배점: 최근 12개월 수입 이력 25 / 수입 빈도·증가율 15 / HS·카테고리 적합도 15 / 전시회 10 / 규제 등록 10 / 기업 규모 10 / 이메일 반응 10 / 신선도 5 (합 100).
감점: 12개월 미갱신 -10, 도메인 불일치 -20, 담당 기능 미확인 -10, 과거 부정 응답 -30. 수신거부·권리불명은 점수 무관 발송 불가.

바이어 검증 상태: `DISCOVERED → IDENTIFIED → ACTIVE_SIGNAL → CONTACTABLE → VERIFIED → ENGAGED → QUALIFIED → CONVERTED` (+ `SUPPRESSED`, `DORMANT`).
Phase 0 최소 검증 조건: 기업 실재 + 공식 도메인 + 품목 관련성 + 24개월 내 신호 1개 + 발송 금지 아님 + 출처·수집일 추적 가능.

### 7.2 B/L 데이터 소스 (정정)

- ~~Data Liberation Project 무료 덤프~~ → **존재하지 않음** (FOIA 거부, 2023-04-28). 이전 로드맵에서 삭제.
- 경로 1: **CBP 직접 구독** (19 CFR 103.31, AMS manifest 데이터 유료 구독) — Collections Section 견적 요청이 Phase 1 첫 액션
- 경로 2: **상용 벤더 라이선스** — 계약서에 재판매·기업명 표시·파생 점수 상업화·보관 기간 권리를 명시(Source Rights Registry `CONTRACT_REQUIRED` → 계약 후 재분류)
- 타사 가공 사이트(ImportYeti 등) 크롤링은 DB권 침해 구조(잡코리아 판례)로 금지

### 7.3 Regulatory Adapter

```text
Regulatory Adapter Interface
├─ IndonesiaBPOMAdapter   (화장품 notification holder)
├─ PhilippinesFDAAdapter
├─ MalaysiaNPRAAdapter
├─ USFDAAdapter           (MoCRA 시설등록, FOIA 공개 범위 내)
└─ CountryRuleManualAdapter

공통 출력: country_code, regulator_code, product_category,
registration_status, license_holder, registration_number,
valid_from, valid_until, source_url, observed_at, confidence
```

### 7.4 슬롯 정의 (상품)

> 슬롯 = 특정 바이어 기업에 대해, 특정 품목군의 수출기업 1개사가 일정 기간
> 플랫폼 중개 제안을 발송할 수 있는 제한적 권리

식별키: `buyer_id + product_category_id + slot_period + seller_tenant_id`.
초기 파라미터: 기간 30일 / 동일 바이어·품목군 1개사 / 바이어 월 최대 2건 / 쿨다운 30일 / 하드바운스·컴플라이언스 차단 시 크레딧 100% 복원 / 단순 무응답 환불 없음 / 수신거부 누락 발송·기업 실재 오류는 전액 환불 또는 대체 슬롯.

**슬롯은 내부 인벤토리 단위**이며, 고객에게 판매하는 상품 사다리(무료 Export Passport → 소액 체험 → 캠페인 → 구독 → 관리형)는 `docs/PRODUCT.md`에서 정의한다. 모든 고객 상품은 내부적으로 슬롯·크레딧으로 환산되어 본 문서의 빈도상한·배타성 규칙을 따른다.

### 7.5 Export Product Passport (판매자 데이터 레이어)

노크의 무료 브랜드 등록을 벤치마크하되, 목적을 "노출"이 아닌 **매칭 정밀도용 판매자 구조화 데이터 확보**로 재정의한 무료 진입 상품.

- 입력 필드: 기업(기업명·홈페이지·수출국) / 제품(카테고리·HS Code) / 거래(단가·MOQ·리드타임) / 조건(인코텀즈·결제) / 인증(국가별 인증·유효기간) / 콘텐츠(영문 소개서)
- 무료 산출물: 수출준비도 점수, 적합국가 3개, 적합 바이어 유형, 누락자료 체크리스트, 예상 BEP(기존 기능 재사용)
- 권리 처리: `CUSTOMER_PROVIDED` — 테넌트 격리, 매칭·스코어링 사용 동의를 수집 시점에 명시
- 매칭 엔진과의 관계: Intent Score(바이어 측)와 Passport(판매자 측)의 양방향 적합도로 매칭 산출 — 데이터가 쌓일수록 §7.1 플라이휠과 동일하게 정밀도 상승

---

## 8. K-SURE 연계 (Deal Workspace 락인)

### 8.1 기능

안내 배너가 아닌 거래 워크플로: 바이어를 K-SURE 조사 후보로 저장 → 신용조사 신청 체크리스트 → 신청일·결과 기록 → Buyer Risk Profile 반영 → 보험 가입·한도 상태 관리 → 매칭→검증→보험→거래를 하나의 Deal Workspace에서 추적.

### 8.2 K-SURE Policy Registry (혜택 하드코딩 금지)

```text
policy_name, target_company_type, benefit_count,
valid_from, valid_to, source_url, verified_at, manual_verification_required
```

2026-07-22 검증 기준 초기 레코드:

| 항목 | 값 |
|---|---|
| 현행 공표 혜택 | 신규·리턴 고객 한정 국외기업 신용조사 **3건 무료**(등록일부터 1년, K-Sight 게시) |
| 정상 수수료 | 중소중견 요약보고서 33,000원 / Full Report 49,500원 (VAT 포함, 후불제) |
| 과거 제도(표시 금지) | "연 10회 무료 + 초과 3만원"은 2019.10 시행 우대조치 — 현행 공식 페이지에 부재 |
| UI 원칙 | 수치 대신 "대상여부 조회" 링크 + `verified_at` 표시 |

---

## 9. Phase 0 확정 범위

### 9.1 최소 DB (17 테이블, §2.3 경량 노트 적용 가능)

`buyers, buyer_identifiers, buyer_signals, contacts_vault, contact_legal_basis, source_registry, suppression_entries, matches, slots, campaigns, campaign_recipients, messages, message_events, conversations, credit_ledger, approval_tasks, audit_logs`

### 9.2 어드민 화면 10종 + 고객 화면 3종

어드민: 바이어 검수 / 연락 가능성 검수 / 수동 매칭 / 캠페인 승인 / 발송 큐 / 응답 인박스 / 슬롯·크레딧 / 출처 권리 관리 / 수신거부 관리 / 감사 로그

고객(벤치마크 반영, `docs/PRODUCT.md` §Phase 0): Export Passport 입력·무료 진단 결과 / 바이어 매칭 근거 카드 / 성과 퍼널 대시보드

### 9.3 완료 조건 (10항목 전부 충족 시 Phase 0 종료)

- [ ] 일반 API에서 연락처 평문 조회 불가
- [ ] 관리자 화면에서도 원칙적으로 연락처 평문 비노출
- [ ] 모든 발송 전 수신거부·빈도상한 자동 확인
- [ ] 처리근거 없는 연락처는 발송 큐 등록 불가
- [ ] 발송 승인자·승인 시각 기록
- [ ] 하드바운스·컴플라이언스 차단 시 크레딧 자동 복원
- [ ] 바이어 회신을 플랫폼 중계함에서 확인 가능
- [ ] 고객별 발송·응답·미팅 성과 추적 가능
- [ ] 출처별 사용권리·원본 레코드 추적 가능
- [ ] 모든 관리자 행동에 감사 로그 생성

### 9.4 KPI (성과 정의)

주성과: 긍정 응답률(관심 응답 ÷ 전달 완료), 미팅·견적·계약 전환. 보조: 전달률, 오픈율.
운영: 바이어 소진율, 슬롯 가동률, 슬롯당 매출, 긍정응답 획득비용, 중복접촉 차단률.

---

## 10. 후속 설계 문서 (우선순위)

P0: ① 슬롯 상품정의서 ② 컴플라이언스 정책표(출처 권리·국가 규칙·보관/삭제·국외이전) ③ 발송 상태도 ④ 데이터 사전·ERD ⑤ 권한 매트릭스
P1: ⑥ Intent Score 산정명세 ⑦ Source Rights Registry 명세 ⑧ 보관·삭제 정책 ⑨ 장애·백업·복구 ⑩ 성과지표·대조군 실험 설계

상품 구조·가격·전환 퍼널·경쟁 포지셔닝: **`docs/PRODUCT.md`** (경쟁사 벤치마크 반영 재설계본)

---

## 근거 (주요 출처)

- K-SURE 수수료·제도: <https://www.ksure.or.kr/rh-kr/cntnts/i-115/web.do> · K-Sight 3건 무료: <https://ksight.ksure.or.kr/find-buyer> · 2019 보도자료(과거 제도): <https://ksure.or.kr/rh-kr/bbs/i-414/detail.do?ntt_sn=9667>
- Data Liberation Project CBP B/L FOIA 거부: <https://www.data-liberation-project.org/requests/cbp-bills-of-lading/> · 19 CFR 103.31: <https://www.ecfr.gov/current/title-19/chapter-I/part-103/subpart-C/section-103.31>
- KISA 정보통신망법 안내서 7차 개정(2026-03-04): <https://www.kisa.or.kr/401/form?postSeq=3608>
- PIPC 국외이전 제도: <https://www.pipc.go.kr/np/default/page.do?mCode=D060040010> · 개인정보 보호법 §28조의8: <https://casenote.kr/법령/개인정보_보호법/제28조의8>
- CASL 가이드: <https://crtc.gc.ca/eng/com500/guide.htm>
- 잡코리아 v 사람인(DB권, 크롤링): <https://www.minwho.kr/kr/business/business_case_view.php?bgu=view&idx=34175>
- GoBizKorea 약관: <https://kr.gobizkorea.com/customer/termsOfService/selTermsOfServiceInfo.do> · KOTRA 저작권정책: <https://dream.kotra.or.kr/kotranews/cms/com/index.do?MENU_ID=1010>
