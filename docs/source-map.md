# 원본 폴더와 새 통합 폴더 매핑

## 실제 개발 기준으로 가져온 것

| 원래 위치 | 새 위치 | 설명 |
|---|---|---|
| `D:\valueup-mvp\merged_workspace_20260416\apps\frontend-react` | `apps/frontend-react` | 현재 기준 React 화면 |
| `D:\valueup-mvp\merged_workspace_20260416\apps\web-dig-landing` | `apps/web-dig-landing` | 정적 웹 시안 |
| `D:\valueup-mvp\merged_workspace_20260416\services\p1-export-fit-api` | `services/p1-export-fit-api` | 수출 유망국 추천 P1 API |
| `D:\valueup-mvp\merged_workspace_20260416\services\ml-export-engine` | `services/ml-export-engine` | 실험용 ML 백엔드 |
| `D:\valueup-mvp\merged_workspace_20260416\archive\legacy-export-intelligence` | `archive/legacy-export-intelligence` | 레거시 참고 코드 |
| `D:\valueup-mvp\monitoring` | `ops/monitoring` | 모니터링 설정 |

## 이번 새 통합 폴더에 직접 넣지 않은 것

| 원래 위치 | 제외 이유 |
|---|---|
| `D:\valueup-mvp\개발자결과물` | 인수인계/공유용 복사본이 많아 기준본으로 쓰기 부적합 |
| `D:\valueup-mvp\download data` | 원본 데이터 창고 성격이 강하고 파일 수가 많음 |
| `D:\valueup-mvp\github 20260223` | 원본 저장소 보관용으로 유지 |
| `D:\valueup-mvp\node_modules` | 재설치 가능한 의존성 산출물 |
| `D:\valueup-mvp\backend\\logs`, `__pycache__`, `venv`, `dist` | 실행 산출물/캐시 |

## 기준 해석

- 앞으로 화면 기준은 `apps/frontend-react`
- 추천 서버 기준은 `services/p1-export-fit-api`
- 실험 엔진 기준은 `services/ml-export-engine`
- 나머지는 참고 또는 원본 보관 성격으로 해석
