# TASK: 바이어 명단 v2 기준 정적 통계 JSON 재생성 (2026-10-13)

## 배경
PR #174(ac5a3d5)에서 `buyer_candidate.csv`가 36,241 → 44,571건으로 바뀌었지만
`apps/frontend-react/public/data/summary.json`, `buyers.json`은 예전 값(36,241) 그대로였다.

## 한 일
- `python scripts/data/build_buyer_data.py` 재실행 → total 44,571, 연락처 보유 2,043건
- 연락처는 스크립트 규칙대로 마스킹됨(diff에서 평문 이메일/전화/키 없음 확인)

## 확인 사항
- 첫 화면(AuthPage)·관리자 화면 숫자는 이 정적 JSON이 아니라 백엔드 `GET /v1/demo/summary`
  (buyer_candidate.csv 직접 집계)에서 온다. 따라서 화면 숫자가 바뀌려면 **Render 백엔드가
  ac5a3d5 이후 커밋으로 재배포**되어야 한다. 2026-10-13 확인 시 운영·e2e 모두 36,241(미배포).
- 관련 테스트: `services/p1-export-fit-api/tests/test_demo_buyer_limit_mg002.py` 4 passed,
  로컬 `get_demo_summary()` total = 44,571.
