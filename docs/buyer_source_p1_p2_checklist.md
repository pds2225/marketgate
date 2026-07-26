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

## P2 — 드롭인 전 UNKNOWN (L002)

아래는 **존재·접근·이용권 확인 전** 단정 금지. CSV를 아래 폴더에 두면 스크립트가 편입한다.

- 폴더: `services/cosmetics_mvp_preprocess/input/p2_optional/`
- 기대 파일 예: `tradekorea.csv`, `kita.csv`, `kotra_trade_office.csv`
- 필수에 가깝게: `country_norm` 또는 `country_raw`, 가능하면 COMMON 19컬럼
- 회사명(`normalized_name`) 비율 >50% → `buyer_candidate`, 아니면 `opportunity_item`

| 키 | 상태 | 조건 |
|---|---|---|
| TradeKorea | UNKNOWN | 공식 export/API·ToS 확인 후 |
| KITA | UNKNOWN | 회원·이용권 확인 후 |
| KOTRA 무역관 리스트 | UNKNOWN | 배포·재배포 범위 문서화 후 |

## 금지

- 원본에 없는 `contact_*` 스크래핑 자동 확정 채움
- 미확인 무료 덤프 존재를 전제로 한 로드맵 단정 (L002)
- 인콰이어리(무명)를 연락 가능 바이어로 표기
