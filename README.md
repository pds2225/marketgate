# 🌐 마켓게이트 (MarketGate)

> 한국 화장품 수출기업을 위한 해외 바이어 발굴 플랫폼

---

## 📌 이 프로젝트는 뭔가요?

**마켓게이트**는 한국의 화장품 수출기업이 전 세계에서 진짜로 제품을 사고 싶어하는 바이어를 쉽게 찾을 수 있게 도와주는 데이터 플랫폼입니다.

### 왜 필요한가요?

| 기존 방식 | 마켓게이트 방식 |
|----------|---------------|
| KOTRA 홈페이지에 직접 들어가서 검색 | 모든 바이어 데이터를 한 곳에서 한눈에 |
| 600만 개 기업 중에서 수작업으로 찾기 | 화장품 관심 바이어만 자동 필터링 |
| 한 바이어 정보는 있지만 살 의향은 불확실 | 인콰이어리/구매오퍼 데이터로 "살 의향" 확인 |
| 여러 사이트 왔다갔다 | CSV 하나로 Excel에서 바로 분석 |

### 누가 쓰나요?

- 화장품 제조/수출 중소기업
- 무역회사 해외영업팀
- KOTRA 해외무역관
- 화장품 유통/브랜드사 수출 담당자

---

## 📊 현재 보유 데이터 (2025년 4월 기준)

총 **18,012건**의 화장품 관심 해외 바이어 데이터

| 데이터 출처 | 건수 | 특징 |
|------------|------|------|
| KOTRA SNS 마케팅 수집 바이어 | 12,666건 | SNS에서 직접 수집한 관심 바이어 |
| GoBizKorea 인콰이어리 (2024) | 2,429건 | 올해 바이어가 직접 "이 제품 살게요" 문의 |
| GoBizKorea 인콰이어리 (2021~2023) | 2,981건 | 과거 인콰이어리 누적 |
| GoBizKorea 구매오퍼 | 166건 | 구매 의향을 공식 신청한 바이어 |
| NIPA 글로벌ICT포털 | 1,853건 | ICT/통신 바이어 (전화번호 100% 포함) |

### 국가별 분포 Top 10

| 국가 | 건수 | 비고 |
|------|------|------|
| 🇮🇳 인도 | 2,605건 | 소비재 시장 확대 중 |
| 🇺🇸 미국 | 2,053건 | K-뷰티 인기 상승 |
| 🇵🇰 파키스탄 | 822건 | 신흥 시장 |
| 🇵🇭 필리핀 | 1,045건 | 동남아 허브 |
| 🇲🇾 말레이시아 | 501건 | 동남아 진출 거점 |
| 🇻🇳 베트남 | 449건 | 급성장 중 |
| 🇯🇵 일본 | 409건 | 프리미엄 수요 |
| 🇮🇩 인도네시아 | 348건 | 인구 대국 |

---

## 🗂️ 데이터 구성

```
services/cosmetics_mvp_preprocess/
│
├── output/                          ← 바로 사용할 수 있는 데이터
│   ├── buyer_candidate.csv           (기존: 34,088건)
│   ├── buyer_candidate_CLEANED_20250430.csv  ← 최신 화장품 데이터 (18,012건)
│   ├── NONCOS_buyer_data_20250430.csv         ← 비화장품 데이터 (2,083건)
│   └── raw/                         ← 원본 보관
│       ├── sns_buyer_2025.csv
│       ├── gobiz_inquiry_2024.csv
│       ├── gobiz_inquiry_2021_2023.csv
│       ├── gobiz_purchase_offer.csv
│       └── nipa_ict_buyer.csv
│
├── docs/                            ← 사용 설명서
│   ├── DATA_COLLECTION_GUIDE.md     (데이터 수집 가이드)
│   ├── NICE_DNB_신청가이드.txt     (NICE D&B API 신청 방법)
│   └── GITHUB_ACTIONS_GUIDE.txt    (자동화 사용법)
│
└── scripts/                         ← 자동화 스크립트
    ├── fetch_govdata_api.py       (공공데이터 API 호출)
    ├── fetch_buykorea_inquiry.py  (buyKOREA 인콰이어리 수집)
    ├── nice_dnb_poc.py            (NICE D&B 바이어 검증)
    └── enrich_emails.py           (이메일 확보 파이프라인)
```

---

## 🚀 자동화: 파일만 넣으면 알아서 필터링

### 어떻게 작동하나요?

1. **새로운 바이어 CSV를 `raw/` 폴더에 업로드**
2. **GitHub이 1~2분 안에 자동 실행**
3. **화장품 관련 바이어만 골라서 `COS_combined_YYYYMMDD.csv` 생성**

### 예시

```
[새 파일 업로드]
  RAW_importyeti_us_20250601.csv
        ↓
[GitHub Actions 자동 실행]
        ↓
[Python이 자동으로]
  ├─ CSV 읽기
  ├─ 컬럼 통일 (기업명, 국가, 품목)
  ├─ 화장품 키워드 필터링
  │   ├─ lipstick, serum, cream, perfume
  │   ├─ 화장품, 뷰티, 크림, 로션
  │   └─ HS코드 3303~3307
  ├─ 중복 제거 (같은 기업+국가는 1개만)
  └─ 결과 저장
        ↓
[자동 생성됨]
  output/COS_combined_20250601.csv
```

---

## 📥 새 데이터 넣는 방법 (3단계)

### 파일명 규칙

```
RAW_데이터소스_YYYYMMDD.csv
```

| ✅ 맞는 예시 | ❌ 틀린 예시 |
|------------|------------|
| `RAW_buykorea_20250601.csv` | ~~`buykorea.csv`~~ (RAW 없음) |
| `RAW_importyeti_us_20250601.csv` | ~~`RAW_data.xlsx`~~ (엑셀 안 됨) |
| `RAW_kotra_rfq_20250601.csv` | ~~`인콰이어리.csv`~~ (한글명 비권장) |

### 방법 1: GitHub 웹사이트에서 (가장 쉬움)

1. [github.com/pds2225/marketgate](https://github.com/pds2225/marketgate) 접속
2. `services/cosmetics_mvp_preprocess/output/raw/` 폴더로 이동
3. **"Add file" → "Upload files"** 클릭
4. CSV 파일을 드래그해서 놓기
5. **"Commit changes"** 클릭
6. **1~2분 후** `output/` 폴더에 `COS_combined_YYYYMMDD.csv` 자동 생성됨

### 방법 2: Git 명령어로

```bash
git clone https://github.com/pds2225/marketgate.git
cd marketgate
cp ~/Downloads/RAW_xxx.csv services/cosmetics_mvp_preprocess/output/raw/
git add .
git commit -m "Add: RAW_xxx"
git push origin main
```

---

## 🔍 데이터 활용 예시

### Excel로 열어서 바로 쓰기

1. `buyer_candidate_CLEANED_20250430.csv` 다운로드
2. Excel에서 열기 (한글이 깨지면 "데이터 → 텍스트/CSV 가져오기 → UTF-8 선택")
3. 필터로 국가별, 품목별 정렬
4. 영업팀에 배포

### Python으로 분석하기

```python
import pandas as pd

# 데이터 로드
df = pd.read_csv("buyer_candidate_CLEANED_20250430.csv", encoding='utf-8-sig')

# 국가별 통계
print(df['country_raw'].value_counts())

# 품목별 검색
serum_buyers = df[df['keywords_raw'].str.contains('serum', case=False)]
print(f"세럼 관심 바이어: {len(serum_buyers)}건")
```

---

## 📋 데이터 컬럼 설명

| 컬럼명 | 뜻 | 예시 |
|--------|-----|------|
| `title` | 관심 품목 | `lipsticks and cosmetics` |
| `normalized_name` | 기업명 | `Lazada Group` |
| `country_raw` | 국가 | `US` |
| `country_iso3` | ISO 국가코드 | `USA` |
| `hs_code_raw` | HS 품목분류코드 | `330499` |
| `keywords_raw` | 원본 키워드 | `beauty products, skincare` |
| `has_contact` | 연락처 유무 | `True` / `False` |
| `contact_phone` | 전화번호 | `(+7) 727 388 80 00` |
| `contact_website` | 웹사이트 | `https://...` |
| `source_dataset` | 데이터 출처 | `KOTRA SNS 마케팅 수집 바이어` |
| `valid_until` | 데이터 기준일 | `2025-11-27` |

---

## 🎯 향후 계획

### 단기 (2025년 2분기)

| 작업 | 목표 | 상태 |
|------|------|------|
| KOTRA buyKOREA 인콰이어리 수집 | 40,305건 활용신청 완료 후 추가 | ⏳ 대기 중 |
| NICE D&B 바이어 검증 | 100개 샘플로 PoC 검증 | 🔜 즉시 가능 |
| 이메일 확보 파이프라인 | 기업 홈페이지 → 이메일 스크래핑 | ⏳ 대기 중 |

### 중기 (2025년 3분기)

- ImportYeti 미국 수입 이력 데이터 추가
- 정부지원 (수출바우처/데이터바우처) 신청으로 NICE D&B 정식 도입
- 바이어 등급 자동 분류 (A/B/C) → 영업 우선순위 자동 산정

---

## ⚠️ 알아두면 좋은 점

1. **이메일은 공공데이터에서 제공되지 않습니다**
   - 개인정보보호법 때문입니다
   - 대안: KOTRA 해외무역관 소개, 기업 홈페이지 공개 이메일 수집

2. **화장품이 아닌 데이터도 일부 포함될 수 있습니다**
   - `NONCOS_buyer_data_*.csv`로 분리 보관됩니다
   - 키워드나 HS코드로 한 번 더 필터링하면 완벽해집니다

3. **데이터는 수시로 업데이트됩니다**
   - 최신 데이터는 `COS_combined_YYYYMMDD.csv` (날짜가 붙은 파일)입니다

---

## 🤝 기여 방법

새로운 바이어 데이터가 있으면 `raw/` 폴더에 CSV만 넣어주세요.
GitHub Actions가 알아서 화장품 필터링 + 통합해 드립니다.

**파일명 규칙만 지키면 됩니다:**
```
RAW_데이터소스_YYYYMMDD.csv
```

---

## 📞 문의 및 지원

| 항목 | 내용 |
|------|------|
| 저장소 주인 | pds2225 (밸류업파트너스) |
| 데이터 출처 | KOTRA, GoBizKorea, NIPA, data.go.kr |
| 정부지원 | 수출바우처 / 데이터바우처 (75% 할인) |
| API 문의 | NICE D&B Open API (openapi.nicednb.com) |

---

> **마켓게이트**는 한국의 우수한 화장품이 세계로 뻗어나가는 디지털 교두보가 되는 것을 목표로 합니다.
