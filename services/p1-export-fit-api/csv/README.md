# CSV 데이터 파일 안내

이 폴더는 통합 작업본 기준으로 실행에 필요한 CSV를 한곳에 모아 둔 상태입니다.

## 현재 들어 있는 파일

- `외교부_국가표준코드_20251222.csv` — 국가명 ↔ ISO3 매핑
- `외교부_국가표준코드_20251222_original.csv` — 원본 보관본
- `country_distance.csv` — 국가 간 거리 데이터
- `WB_WDI_NY_GDP_MKTP_CD_define column.csv` — World Bank GDP
- `WB_WDI_NY_GDP_MKTP_KD_ZG_define column.csv` — World Bank GDP 성장률
- `kotra_export_recommend_all.csv` — KOTRA 수출 추천 데이터
- `trade_data.csv` — UN Comtrade 무역 실적 데이터

## 주의사항

- 파일 유무 기준으로는 이 폴더만으로 P1 API 실행이 가능하도록 정리했습니다.
- 다만 `trade_data.csv`는 현재 확인상 `partnerISO` 값이 `W00` 중심이라, 나라별 추천 결과 품질이 낮거나 결과가 비는 문제가 남아 있습니다.
- 즉, 파일은 모였지만 데이터 품질까지 완전히 해결된 상태는 아닙니다.
