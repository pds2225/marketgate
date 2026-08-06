# 마켓게이트 (MarketGate)

> 한국 화장품 수출기업을 위한 해외 바이어 발굴·중개 플랫폼

---

## 📌 이 프로젝트는 뭔가요?

마켓게이트는 한국의 화장품 수출기업이 전 세계에서 진짜로 제품을 사고 싶어하는 바이어를 쉽게 찾고, **연락처를 직접 사고파는 대신 플랫폼이 안전하게 중개 발송**해주는 거래 인프라입니다.

| 기존 방식 | 마켓게이트 방식 |
|----------|---------------|
| KOTRA 홈페이지에 직접 들어가서 하나하나 검색 | 모든 바이어 데이터를 한 곳에서 한눈에 보기 |
| 600만 개 기업 중에서 수작업으로 찾기 | 화장품 관심 바이어만 자동으로 골라주기 |
| 한 바이어 정보는 있지만 "살 의향"은 불확실 | 인콰이어리/구매오퍼 데이터로 "살 의향" 확인 |
| 바이어 연락처를 통째로 구매 (법적 리스크) | 연락처 비노출, 플랫폼이 대신 제안 발송 |

### 누가 쓰나요?

- 화장품 제조/수출 중소기업
- 무역회사 해외영업팀
- KOTRA 해외무역관
- 화장품 유통/브랜드사 수출 담당자

---

## 🚧 현재 서비스 범위 (K-뷰티 HS 330499 파일럿)

- **품목 범위**: K-뷰티 스킨케어 **HS 330499 단일 품목** 파일럿으로 제한합니다.
- **운영 형태**: 외부 유료 서비스가 아닌 **컨설턴트 동행 파일럿**입니다. 결제·에스크로·다품목·완전 셀프서비스는 후순위입니다.
- **중개 모델**: 바이어 연락처 원문은 판매·노출하지 않고, 인콰이어리는 `draft → review_required → approved → queued → sent/failed` 순서의 **관리자 승인 큐**로 발송합니다.
- **데이터 정책**: API·CSV 원본에 없는 값(수입이력·수입액·성장률·검증일 등)은 생성하지 않으며, 화면에는 "자료 내 확인 불가"로 표시합니다.
- **설계 기준 문서**: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (v2 확정본). 상태 머신·스키마·정책은 이 문서가 기준입니다.

---

## 🗂️ 저장소 구조

```
marketgate/
├── apps/
│   ├── frontend-react/          ← 메인 웹앱 (React + Vite, Vercel 배포)
│   └── web-dig-landing/         ← 정적 랜딩 페이지 (HTML/CSS/JS)
│
├── services/
│   ├── p1-export-fit-api/       ← 메인 백엔드 API (FastAPI, Render 배포)
│   │                              바이어 추천 / 인콰이어리 / 크레딧·구독
│   └── cosmetics_mvp_preprocess/← 바이어 데이터 수집·필터링 파이프라인
│
├── db/
│   ├── migrations/              ← PostgreSQL 스키마 (Phase 0, Vault 암호화 포함)
│   └── tests/                   ← 마이그레이션 회귀 테스트
│
├── data/raw/                    ← 원본 데이터
├── scripts/                     ← data / dev / integrations / maintenance
├── tools/                       ← 파이썬 유틸 스크립트 + 테스트
├── ops/monitoring/              ← 운영·모니터링
├── archive/                     ← 구형 코드 보관 (legacy-export-intelligence)
└── docs/                        ← 설계 문서 (ARCHITECTURE.md가 최상위 기준)
```

### 문서 읽는 순서

1. `docs/ARCHITECTURE.md` — 목표 아키텍처 확정본 (상태 머신·스키마·정책)
2. `docs/PRODUCT.md` — 상품 구조·가격·전환 퍼널
3. `docs/ERD.md` — 데이터베이스 구조
4. `TASKS.md` — 현재 진행 중인 작업과 다음 순서

---

## 🚀 개발 현황 (2026-08 기준)

### ✅ MVP 개발 완료 (2026-08-02 선언)

- **MVP E2E**: HS코드 입력 → 바이어 조회 → 인콰이어리 초안 생성·발송 요청까지 전 구간 동작
- **검증**: 백엔드 전체 테스트 **214 passed / 0 failed**, 프론트엔드 프로덕션 빌드 성공 (2026-08-02 실행)
- **프론트엔드**: 랜딩 → 유망국 분석 → 바이어 검색 → 인콰이어리 모달 연결 완료
- **Phase 0 DB**: 17테이블 DDL·ERD·데이터 사전, 연락처 암호화 금고(Vault), 키 회전 — PostgreSQL 16 CI 통과

### 진행 순서 (2026-08-02 결정)

> **법적·컴플라이언스 관련 개발은 모든 서비스 기능이 완성된 후로 보류합니다.**
> MVP 이후 다음 단계는 매칭·슬롯·캠페인 등 서비스 기능 확장이 우선입니다.

자세한 작업 목록은 [`TASKS.md`](TASKS.md)를 참고하세요.

---

## 📊 보유 바이어 데이터

총 **18,012건**의 화장품 관심 해외 바이어 데이터

| 데이터 출처 | 건수 | 특징 |
|------------|------|------|
| KOTRA SNS 마케팅 수집 바이어 | 12,666건 | SNS에서 직접 수집한 관심 바이어 |
| GoBizKorea 인콰이어리 (2021~2023) | 2,981건 | 과거 인콰이어리 누적 |
| GoBizKorea 인콰이어리 (2024) | 2,429건 | 바이어가 직접 "이 제품 살게요" 문의 |
| NIPA 글로벌ICT포털 | 1,853건 | ICT/통신 바이어 (전화번호 100% 포함) |
| GoBizKorea 구매오퍼 | 166건 | 구매 의향을 공식 신청한 바이어 |

국가별 상위: 인도(2,605) · 미국(2,053) · 필리핀(1,045) · 파키스탄(822) · 말레이시아(501) · 베트남(449) · 일본(409) · 인도네시아(348) · UAE(285) · 카자흐스탄(280)

### 데이터 파일 위치

```
services/cosmetics_mvp_preprocess/output/
├── buyer_candidate_CLEANED_20250430.csv   ← 최신 화장품 데이터 (18,012건)
├── NONCOS_buyer_data_20250430.csv         ← 비화장품 데이터 (2,083건)
└── raw/                                   ← 원본 보관
```

### 주요 컬럼

| 컬럼명 | 뜻 | 예시 |
|--------|-----|------|
| `title` | 관심 품목 | `lipsticks and cosmetics` |
| `normalized_name` | 기업명 | `Lazada Group` |
| `country_raw` / `country_iso3` | 국가 / ISO 코드 | `US` / `USA` |
| `hs_code_raw` | HS 품목분류코드 | `330499` |
| `keywords_raw` | 원본 키워드 | `beauty products, skincare` |
| `has_contact` | 연락처 유무 | `True` / `False` |
| `contact_phone` / `contact_website` | 전화번호 / 웹사이트 | — |
| `source_dataset` | 데이터 출처 | `KOTRA SNS 마케팅 수집 바이어` |
| `valid_until` | 데이터 기준일 | `2025-11-27` |

---

## 📥 새 바이어 데이터 넣는 방법

### 파일명 규칙

```
RAW_데이터소스_YYYYMMDD.csv
```

| ✅ 맞는 예시 | ❌ 틀린 예시 |
|------------|------------|
| `RAW_buykorea_20250601.csv` | ~~`buykorea.csv`~~ (RAW 없음) |
| `RAW_importyeti_us_20250601.csv` | ~~`RAW_data.xlsx`~~ (엑셀 안 됨) |

### 절차

1. `services/cosmetics_mvp_preprocess/output/raw/` 폴더에 CSV 업로드 (GitHub 웹에서 "Add file → Upload files" 가능)
2. 커밋하면 GitHub Actions가 1~2분 안에 자동 실행
3. 화장품 키워드 필터링(lipstick, serum, cream, HS코드 3303~3307 등) + 중복 제거 후 `output/COS_combined_YYYYMMDD.csv` 자동 생성

---

## 🛠️ 개발·테스트 명령

```bash
# 백엔드 테스트 (현재 개발 중심)
cd services/p1-export-fit-api && python -m pytest --tb=short -q

# 프론트엔드 개발 서버
cd apps/frontend-react && npm run dev
```

---

## ⚠️ 알아두면 좋은 점

1. **이메일은 공공데이터에서 제공되지 않습니다** (개인정보보호법). 대안: KOTRA 해외무역관 소개, 기업 홈페이지 공개 이메일 수집.
2. **화장품이 아닌 데이터도 일부 섞일 수 있습니다.** `NONCOS_buyer_data_*.csv`로 분리 보관되며, 키워드·HS코드로 한 번 더 필터링하면 됩니다.
3. **각 출처별로 재사용 권한이 다릅니다.** 어떤 데이터를 어디까지 쓸 수 있는지는 `docs/ARCHITECTURE.md` §4.2(Source Rights Registry)가 기준입니다.

---

## 📞 문의

| 항목 | 내용 |
|------|------|
| 저장소 주인 | 밸류업파트너스 |
| 데이터 출처 | KOTRA, GoBizKorea, NIPA, 공공데이터포털 |
| 저장소 | https://github.com/pds2225/marketgate |

---

> **마켓게이트**는 한국의 우수한 화장품이 세계로 뻗어나가는 디지털 교두보가 되는 것을 목표로 합니다.
