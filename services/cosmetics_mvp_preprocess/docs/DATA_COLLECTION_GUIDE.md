# MarketGate 데이터 수집 가이드
# 작성일: 2026-04-30

## 1. 현재까지 수집된 파일 목록

### 화장품 필터링 데이터 (바로 사용 가능)

| 파일 | 건수 | 크기 | 데이터 성격 |
|------|------|------|------------|
| `sns_buyer_cosmetics_transformed.csv` | 12,666건 | 2.8MB | KOTRA SNS 마케팅 바이어 (화장품) |
| `gobiz_inquiry_2024_cosmetics_transformed.csv` | 2,429건 | 616KB | GoBizKorea 인콰이어리 2024 (화장품) |
| `gobiz_inquiry_2021_2023_cosmetics_transformed.csv` | 2,981건 | 629KB | GoBizKorea 인콰이어리 2021-2023 (화장품) |
| `gobiz_purchase_offer_cosmetics_transformed.csv` | 166건 | 95KB | GoBizKorea 구매오퍼 (화장품) |
| `nipa_ict_buyer_transformed.csv` | 1,853건 | 529KB | NIPA 글로벌ICT포털 바이어 (ICT) |

**화장품 데이터 합계: 18,242건**

---

## 2. 이중 저장 구조 (향후 수집 시 적용)

### 원칙: 모든 데이터는 "원본 전체 + 화장품 필터링" 동시 저장

```
[API 호출] → [전체 원본 저장] → [화장품 필터링] → [화장품만 별도 저장]
     ↓
RAW_*.csv (전체 원본 DB) → 나중에 다른 품목 확장 시 사용
COS_*.csv (화장품만) → 지금 당장 사용
```

### 파일명 규칙

| 접두사 | 의미 | 예시 |
|--------|------|------|
| `RAW_` | 원본 전체 데이터 | `RAW_sns_buyer_2024.csv` |
| `COS_` | 화장품 필터링 데이터 | `COS_sns_buyer_2024.csv` |
| `TR_` | 통합 스키마 변환 데이터 | `TR_buyer_candidate_merged.csv` |

---

## 3. GoBizKorea API 연동 템플릿

### 필요 정보
- Base URL: `https://kr.gobizkorea.com` (또는 개발서버 URL)
- API Key: GoBizKorea 개발자 센터에서 발급

### 제공 API 목록

| API | URL | Method | 용도 |
|-----|-----|--------|------|
| 상품정보 제공 | `/api/goodsInfos.do` | POST | 키워드/카테고리로 상품 검색 |
| 카테고리 제공 | `/api/ctgryCodes.do` | GET/POST | 3Depth 카테고리 조회 |
| 주문정보 수신 | `/api/orderInfoSet.do` | GET/POST | 주문 정보 전송 |
| 판매정보 수신 | `/api/salesInfoSet.do` | GET/POST | 판매 정보 전송 |
| 상품정보 변경조회 | `/api/goodsInfosUptd.do` | GET/POST | 변경된 상품만 조회 |

### API 키 발급처
- https://kr.gobizkorea.com/customer/api/openApiInfo.do

---

## 4. 화장품 키워드 필터 목록

```python
COSMETICS_KEYWORDS = [
    # 영문
    'cosmetic', 'cosmetics', 'beauty', 'makeup', 'skincare', 'skin care',
    'lipstick', 'cream', 'lotion', 'serum', 'perfume', 'fragrance',
    'lip', 'nail', 'hair', 'body', 'facial', 'mask', 'sunscreen',
    'essence', 'toner', 'cleansing', 'moisturizer', 'foundation',
    'filler', 'botox', 'peeling', 'peel',
    'essential oil', 'aroma',
    # 한글
    '화장품', '미용', '향수', '크림', '로션', '세럼', '립스틱',
    '보톡스', '필러', '에센셜 오일', '아로마',
]
```

---

## 5. 미반영 API 현황 (추후 수집 대상)

| 데이터명 | data.go.kr ID | 상태 | 전체 행수 |
|---------|---------------|------|----------|
| KOTRA 인콰이어리 (buyKOREA) | 15155499 | 활용신청 필요 | 40,305 |
| KOTRA 국가정보 | 15034830 | 활용신청 필요 | - |
| KOTRA 해외시장뉴스 | 15034831 | 활용신청 필요 | - |
| KOTRA 상품DB | 15034958 | 활용신청 필요 | - |
| KOTRA 무역사기사례 | 15034754 | 활용신청 필요 | - |
| KOTRA 기업성공사례 | 15034755 | 활용신청 필요 | - |

---

## 6. 다음 단계

1. **B 완료**: 기존 buyer_candidate.csv와 병합
2. **활용신청**: data.go.kr에서 buyKOREA 인콰이어리(15155499) 활용신청
3. **GoBizKorea API**: API 키 발급 후 상품/카테고리 데이터 연동
4. **이중 저장**: 앞으로 모든 수집은 RAW + COS 동시 저장
