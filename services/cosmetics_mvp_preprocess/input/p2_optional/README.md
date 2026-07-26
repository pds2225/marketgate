# P2 optional drop-in

TradeKorea / KITA / KOTRA 무역관은 **공개 일괄 CSV가 없습니다** (`ACCESS_GATED`, L002).

회원·무역관에서 **합법적으로 수령한** 목록만 아래 파일명으로 넣고 merge를 실행하세요.

| 파일 | 소스 |
|---|---|
| `tradekorea.csv` | TradeKorea 회원 수령분 |
| `kita.csv` | KITA/무역협회 수령분 |
| `kotra_trade_office.csv` | KOTRA 무역관 배포분 |

스키마는 `*.csv.example` 헤더를 따르세요.  
`country_norm` 또는 `country_raw` 필수. `normalized_name`이 절반 초과면 buyer, 아니면 opportunity.

```bash
python3 tools/merge_p1_p2_buyer_sources.py
```

금지: 로그인 UI 스크래핑, 원본에 없는 `contact_*` 채움.
