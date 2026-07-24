# MarketGate 개발 모니터링 — 항목별 시트 분리

## 원본
- Google Sheet: https://docs.google.com/spreadsheets/d/1lmzSGu0fPYwVaoP82n-9tbMGtUmzE_G1j2wcblZldQg
- 원본 상태: **단일 Untitled 시트**에 `■■■ [섹션] ■■■` 마커로 11개 섹션이 세로 연결됨

## 산출물
| 탭 | 파일 | 용도 |
|---|---|---|
| 개요 | `01_개요.csv` | rows≈30, cols=2 |
| 개발과제 | `02_개발과제.csv` | rows≈23, cols=12 |
| 작업분해 | `03_작업분해.csv` | rows≈86, cols=9 |
| 아키텍처 | `04_아키텍처.csv` | rows≈57, cols=6 |
| 수집소스 | `05_수집소스.csv` | rows≈28, cols=10 |
| 상품가격 | `06_상품가격.csv` | rows≈28, cols=6 |
| 법률규제 | `07_법률규제.csv` | rows≈31, cols=6 |
| 검증기록 | `08_검증기록.csv` | rows≈13, cols=6 |
| KPI기준 | `09_KPI기준.csv` | rows≈21, cols=6 |
| 오답노트 | `10_오답노트.csv` | rows≈8, cols=7 |
| 원문목록 | `11_원문목록.csv` | rows≈19, cols=3 |

- 통합 파일: `MarketGate_개발모니터링_항목별시트.xlsx` (위 11탭)
- 적용 스크립트: `apply_to_google_sheets.py` (기존 스프레드시트에 11탭 write + 재읽기 검증)

## 구글 쓰기 경로 열기 (이 Cloud Agent에서 불가한 것)
이 런타임에는 **Google/Zapier MCP가 연결되어 있지 않고**, OAuth·서비스계정 키도 없음.
에이전트가 대신 Google 로그인을 “열어” 줄 수는 없다. 아래 중 **하나**를 사람이 열어 주면 즉시 적용 가능.

### 경로 A — 서비스 계정 (권장, 기존 파일 유지·L008 준수)
1. GCP에서 서비스 계정 생성 → JSON 키 발급
2. 해당 이메일로 위 스프레드시트를 **편집자** 공유
3. Cloud Agent / 로컬 환경에 시크릿 설정:
   - `GOOGLE_SERVICE_ACCOUNT_JSON` = JSON 전체 문자열  
     또는 `GOOGLE_SERVICE_ACCOUNT_FILE` = 키 파일 경로
4. 실행:

```bash
cd tools/dev-monitor-sheets
python3 apply_to_google_sheets.py
```

### 경로 B — Zapier
- 이 Agent MCP 목록에 Zapier 서버가 **없음**
- Cursor Desktop에서 Zapier MCP를 연결하거나, Zapier Webhook URL을 시크릿으로 제공해야 함
- 대량 11탭 재작성에는 경로 A가 더 적합 (Zapier는 행 단위에 가깝다)

### 경로 C — 수동 가져오기
- xlsx를 드라이브 `파일 → 가져오기`로 올린 뒤, 기존 v3에 탭 복사

## 탭 구성 (개요 섹션 안내 기준)
1. 개요
2. 개발과제 (문제 단위 22건, 상태만 갱신)
3. 작업분해 (WBS 77건 — 실제 개발 진행 추적)
4. 아키텍처
5. 수집소스
6. 상품가격
7. 법률규제
8. 검증기록
9. KPI기준
10. 오답노트
11. 원문목록

## 주의 (L003)
숫자 나열(예: `1·2·10`)은 RAW 텍스트로 기록. 적용 스크립트가 쓰기 후 `개발과제!A1:C2`를 재읽어 대조한다.
