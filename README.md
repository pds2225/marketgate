# MarketGate

이 레포는 MarketGate의 현재 기준 코드입니다.
기존 `D:\valueup-mvp\unified_workspace_20260418` 작업본을 `D:\marketgate`로 병합해, 로컬 폴더명과 GitHub 레포명을 `marketgate`로 통일했습니다.

비개발자 기준으로 쉽게 말하면:

- `프론트엔드`는 사용자가 보는 화면입니다.
- `백엔드`는 화면 뒤에서 계산을 하는 서버입니다.
- `API`는 다른 프로그램이 그 서버 기능을 호출하는 통로입니다.

## 왜 새 통합 폴더를 다시 만들었나

기존 루트에는 아래가 한곳에 섞여 있었습니다.

- 현재 화면 코드
- 실험용 백엔드
- P1 추천 API
- 정적 웹 시안
- 인수인계 복사본
- 원본 데이터 창고
- ZIP, PDF, 문서, 캐시, 로그

이 상태에서는 "무엇이 기준본인지"가 계속 흐려집니다.

그래서 이번 폴더는 `실제로 개발을 계속할 코드`만 다시 모아 새 기준본으로 만들었습니다.

## 폴더 구성

```text
marketgate/
├─ apps/
│  ├─ frontend-react/          현재 기준 React 화면
│  └─ web-dig-landing/         정적 웹 시안
├─ services/
│  ├─ p1-export-fit-api/       수출 유망국 추천 P1 API
│  └─ ml-export-engine/        중력모형 + XGBoost 실험 엔진
├─ archive/
│  └─ legacy-export-intelligence/  방향이 달랐던 초기 레거시
├─ ops/
│  └─ monitoring/              Prometheus/Alertmanager 설정
├─ docs/                       구조와 출처 설명 문서
└─ scripts/                    실행 보조 스크립트
```

## 기준본으로 봐야 할 폴더

### 1. `services/p1-export-fit-api`

현재 가장 중요한 서버입니다.

- HS 코드와 수출국을 넣으면 추천 국가 점수를 계산합니다.
- 현재 프로젝트에서 확인된 핵심 기능은 `바이어 개별 매칭`보다 이 `수출 유망국 추천 P1`입니다.

### 2. `apps/frontend-react`

현재 기준 화면입니다.

- 사용자가 실제로 보는 분석 화면입니다.
- 현재는 `services/p1-export-fit-api`와 연결되는 방향으로 정리돼 있습니다.

### 3. `services/ml-export-engine`

실험용 추천 엔진입니다.

- 중력모형과 XGBoost 기반 실험 백엔드입니다.
- 운영 기준본이라기보다 연구/검증용 성격이 강합니다.

## 이번 통합에 넣은 것

- 현재 React 화면
- P1 추천 API
- 실험용 ML 백엔드
- 정적 웹 시안
- 레거시 참고 코드
- 모니터링 설정

## 이번 통합에서 뺀 것

- `개발자결과물` 전체 복사본
- `download data` 전체 원본 데이터 창고
- ZIP, PDF, HWP, DOCX 같은 문서 원본
- `node_modules`
- `venv`
- `dist`
- 로그, 캐시, `__pycache__`

뺀 이유는 단순합니다.
실행 기준본을 흐리게 하는 중복/산출물은 새 통합 폴더에 넣지 않는 편이 유지보수에 유리하기 때문입니다.

## 빠른 실행

### P1 API 실행

```powershell
cd D:\marketgate\services\p1-export-fit-api
pip install -r requirements.txt
uvicorn main:app --reload
```

### React 화면 실행

```powershell
cd D:\marketgate\apps\frontend-react
npm install
npm run dev
```

### 실험용 ML 엔진 실행

```powershell
cd D:\marketgate\services\ml-export-engine
pip install -r requirements.txt
uvicorn api:app --reload --port 8001
```

## 현재 꼭 알아둘 점

- `p1-export-fit-api`는 실행 자체는 됩니다.
- 하지만 현재 포함된 `trade_data.csv`는 국가별 거래 상대국 정보가 부족해서 추천 결과가 `0건`이 되는 문제가 남아 있습니다.
- 즉, 폴더 구조 정리는 끝났고, 다음 핵심 과제는 `데이터 품질 보강`입니다.

## 다음 권장 순서

1. 이 폴더를 앞으로의 기준 개발 폴더로 사용
2. `frontend-react`와 `p1-export-fit-api`를 함께 기준본으로 고정
3. `trade_data.csv`를 국가별 파트너 데이터가 있는 파일로 교체
4. 그다음에 남은 레거시/복사본은 보관 전용으로만 유지
