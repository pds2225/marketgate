# MarketGate Buyer Matching 이어받기 메모

작성일: 2026-09-04 (Asia/Seoul)

이 문서는 다음 세션에서 Buyer Matching 작업을 바로 이어가기 위한 개발 메모다. `TASK.md`가 작업 지시의 최종 기준이며, 이 문서는 현재 코드와 미완료 작업을 빠르게 파악하기 위한 보조 기록이다.

## 작업 위치와 기준

- 레포: `pds2225/marketgate`
- 원래 작업공간: `C:\Users\ekth3\marketgate-buyer-mvp-p0`
- 메모 브랜치: `docs/continuation-note-20260904`
- 메모 브랜치는 기존 `agent/buyer-matching-mvp-p0`의 `8e159d3`에서 생성했다.
- 당시 기준: `origin/main = e2d1ed4`로부터 로컬 작업 커밋 4개가 앞서 있었다. 원격 push/PR/merge는 이 메모 작업에서 수행하지 않았다.
- `TASK.md`의 현재 미완료/막힘 작업은 MG-004(실사용 기업검증 E2E), MG-007(운영 실발송), MG-008(실제 P2 CSV 제공·연결)이다. 없는 데이터나 자격증명을 만들어 해결하지 않는다.

## 지금까지 구현된 Buyer Matching 범위

최근 커밋에서 Buyer Matching WAVE 1의 엄격 게이트와 출처 보존을 진행했다.

- `f1d5675 feat-buyer-strict-gate-provenance`: strict buyer gate/provenance 관련 핵심 구현
- `d04f63b test-buyer-shortlist-provenance`: shortlist provenance 회귀 테스트 보강
- `8e159d3 fix-task09-strict-gate-validation`: `task09_validate_top20()`에서 `strict_buyer_gate=True`를 강제하고 메타 검증 추가
- 관련 백엔드·전처리 영역:
  - `services/cosmetics_mvp_preprocess/shortlist_service.py`
  - `services/cosmetics_mvp_preprocess/task09_validate_top20.py`
  - `services/p1-export-fit-api/app/services/buyer_shortlist.py`
  - `services/p1-export-fit-api/tests/test_trade_fallback.py`

목표는 점수만 높은 바이어를 보여주는 것이 아니라, buyer gate 결과와 근거, 실제 출처를 함께 보존해 사용자가 왜 포함/제외됐는지 확인할 수 있게 하는 것이다. 연락처가 있다는 사실만으로 소유권 검증 완료로 표시하면 안 된다.

## 아직 커밋하지 않은 현재 UI 변경

현재 작업공간에는 아래 3개 파일의 사용자 변경이 남아 있다. 삭제하거나 되돌리지 말고, 내용 검토 후 의도한 변경만 별도 커밋한다.

- `apps/frontend-react/src/pages/BuyerSearch/buyerViewModel.js`
  - `PASS/UNKNOWN/FAIL` 게이트 라벨과 fail-closed 정규화
  - `source_names` 및 `source_dataset/source_name`의 출처 dedupe/정규화
  - `gate_reasons`, `match_relevance`, `has_verified_contact` 화면 모델 보존
- `apps/frontend-react/src/pages/BuyerSearch/index.tsx`
  - 목록/상세에 게이트 상태 배지, 게이트 근거, 출처 기록 표시
  - 기존 `연락처 보유 = 소유 검증`으로 오해할 수 있는 문구를 완화
- `apps/frontend-react/tests/buyerViewModel.test.mjs`
  - provenance 보존 및 알 수 없는 게이트 값의 `UNKNOWN` 처리 테스트

주의: 이 메모를 커밋할 때도 위 3개 파일은 stage하지 않았다. 다음 세션에서 실제 API 응답 계약과 맞는지 확인한 뒤 커밋한다.

## 다음 세션 실행 순서

1. 상태와 diff를 먼저 확인한다.

   ```text
   git status --short --branch
   git diff -- apps/frontend-react/src/pages/BuyerSearch/buyerViewModel.js apps/frontend-react/src/pages/BuyerSearch/index.tsx apps/frontend-react/tests/buyerViewModel.test.mjs
   ```

2. 실제 API/서비스가 UI가 기대하는 필드를 내보내는지 확인한다. 특히 `gate_status`, `gate_reasons`, `source_names`, `match_relevance`, `has_verified_contact`가 실제 응답에서 누락될 때 UI가 임의 값을 만들지 않고 `UNKNOWN`/빈 출처로 안전하게 처리되는지 확인한다.

3. 관련 테스트를 실행한다.

   ```text
   cd apps/frontend-react
   npm run test:unit
   npm run lint
   npm run build
   cd ../..
   python -m pytest services/cosmetics_mvp_preprocess/tests/test_task09_validate_top20.py -q
   python -m pytest services/p1-export-fit-api/tests/test_trade_fallback.py -q
   ```

4. 가능하면 실제 로컬 사용자 흐름에서 HS 검색 → Buyer Search 목록 → 바이어 상세를 확인한다. 테스트 통과나 localhost 화면 확인만으로 `DONE` 처리하지 말고, `TASK.md`의 `USER_E2E`와 실제 데이터 조건을 별도로 기록한다.

5. 검토가 끝나면 이번 UI 파일만 명시적으로 stage/commit한다. `git add -A`, `reset --hard`, `clean`, force push는 금지한다. 이후 fetch로 `origin/main`과 ahead/behind를 다시 확인한다.

## 보존해야 할 원칙

- 실제 buyer 데이터와 실제 출처만 사용한다. 가짜 바이어·가짜 연락처·근거 없는 검증 상태를 만들지 않는다.
- gate가 `UNKNOWN`이면 통과로 취급하지 않는다. 연락처 형식/존재와 소유권 검증을 구분한다.
- MG-006/007/008의 이미 반영된 범위를 Buyer Matching UI 변경과 임의로 섞지 않는다.
- 운영 DB, SMTP, 유료 외부 API, 실제 발송은 별도 승인·자격증명·격리 환경 없이 실행하지 않는다.
- `TASK.md`의 최신 일반 요청을 현재 작업에 임의로 합치지 않는다.

## 이 시점의 검증 상태

- 코드 변경: Buyer gate/provenance 백엔드·전처리 커밋은 존재하며, UI 3개 파일은 미커밋
- 단위/통합 테스트: 이 메모 작성 시점에 새로 실행하지 않음
- 실제 사용자 E2E: 이 메모 작성 시점에 실행하지 않음
- 원격 push/PR/merge: 하지 않음
- 주의 대상: pytest 임시 디렉터리 일부는 권한 경고가 있었으므로, 테스트 실행 시 기존 파일을 삭제하거나 덮어쓰지 말고 별도 임시 경로를 사용한다.
