# P1/P2 바이어·기회 소스 편입 체크리스트

## P1 — CONFIRMED (로컬 raw 병합)

| 소스 | 경로 | 타겟 | 비고 |
|---|---|---|---|
| buyKOREA 화장품 인콰이어리 | `output/raw/buykorea_inquiry_2023_2025_cosmetics.csv` | `opportunity_item` | 회사명·이메일 없음 → 바이어 아님 |
| GoBizKorea 인콰이어리 2021–2023 | `output/raw/gobiz_inquiry_2021_2023.csv` | `opportunity_item` | 동일 |
| GoBizKorea 인콰이어리 2024 | `output/raw/gobiz_inquiry_2024.csv` | `opportunity_item` | 동일 |
| GoBizKorea 구매오퍼 | `output/raw/gobiz_purchase_offer.csv` | `opportunity_item` | 동일 |
| K-SURE 화장품 / 바이어검색 | 기존 `buyer_candidate` | `buyer_candidate` | 이미 편입, 이동 없음 |

실행:

```bash
python3 tools/merge_p1_p2_buyer_sources.py
```

리포트: `tools/reports/p1_p2_buyer_merge_report.json`  
P2 접근 조사: `tools/reports/p2_source_access_findings.json`

## P2 — 접근 검증 완료 → ACCESS_GATED (L002)

2026-07-26 공식 경로 조사: **세 소스 모두 공개 일괄 CSV/OpenAPI 없음.**  
미확인 무료 덤프를 전제로 편입하지 않는다. 회원·무역관 수령분을 COMMON 스키마로 변환해 드롭인한다.

- 폴더: `services/cosmetics_mvp_preprocess/input/p2_optional/`
- 스키마 예: 동 폴더 `*.csv.example` (헤더만)
- 필수에 가깝게: `country_norm` 또는 `country_raw`, 가능하면 COMMON 19컬럼
- 회사명(`normalized_name`) 비율 >50% → `buyer_candidate`, 아니면 `opportunity_item`

| 키 | 상태 | 접근 경로 | 제약 |
|---|---|---|---|
| TradeKorea | ACCESS_GATED | [바이어DB 거래제안](https://kr.tradekorea.com/seller/buyer/buyerDB.do) | UI 검색·C/L만. 1일1회·월5회, 1회20사. 연락처 미제공(국가·회사·품목). 일괄 export/API 없음 |
| KITA | ACCESS_GATED | [tradeKorea 서비스](https://www.kita.org/info/globalService/tradeKorea.do) | 바이어 DB 일괄 CSV/API 없음. 공개 대체 K-SURE API는 이미 P1 buyer에 편입 |
| KOTRA 무역관 리스트 | ACCESS_GATED | [무역투자24](https://www.kotra.or.kr) 수출24·트라이빅 | 일괄 다운로드 없음. 건당 발굴(유료) 또는 기업회원 맞춤. 배포분 재배포 범위 문서화 후 드롭인 |

드롭인 파일명:

- `tradekorea.csv`
- `kita.csv`
- `kotra_trade_office.csv`

## 금지

- 원본에 없는 `contact_*` 스크래핑 자동 확정 채움
- 미확인 무료 덤프 존재를 전제로 한 로드맵 단정 (L002)
- 인콰이어리(무명)를 연락 가능 바이어로 표기
- 회원 전용 UI를 스크래핑해 CSV를 “확보”한 것처럼 표기
