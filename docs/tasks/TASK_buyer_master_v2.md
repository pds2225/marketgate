# TASK: buyer master v2 반영 (feat/buyer-master-v2)

## 목표
앱이 쓰는 바이어 파일 `services/cosmetics_mvp_preprocess/output/buyer_candidate.csv`를 새 통합본(44,571건)으로 교체한다.

## 범위
- buyer_candidate.csv 교체 (기존 22개 열 이름 유지 + 새 열 change_note, email_guessed, hs_flag, address, buyer_name, contact_ready, contact_ready_without_hs, contact_type 추가)
- 생성 스크립트 `tools/buyer_master/merge.py` 참고용 추가
- 코드 변경 없음. Supabase(운영 DB) 쓰기 없음.

## 검증 (변경 파일 관련 테스트만)
- cosmetics_mvp_preprocess: test_task05, test_task07, test_keyword_performance, test_task09
- p1-export-fit-api: test_matchD_relevance, test_demo_buyer_limit_mg002, test_e2e_smoke
- 스모크: HS 330499 검색 시 K-SURE 화장품 바이어(연락처 있음)가 나오는지
