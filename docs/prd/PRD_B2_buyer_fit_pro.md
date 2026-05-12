# PRD: B2 - Buyer Fit Pro (신용레포트 PDF)

## 1. 목적
D&B 신용데이터 기반 바이어 신용레포트를 PDF로 생성. 25C 차감 유료 기능.

## 2. MVP 구현 범위
- 바이어 신용정보 조회 (D&B API 또는 가정 데이터)
- PDF 레포트 자동 생성
- 25C 크레딧 차감 후 다운로드 링크 제공

## 3. 주요 기능
- 바이어 기업명·DUNS번호로 신용 조회
- 재무현황·신용등급·거래이력 포함 PDF
- 생성된 PDF 24시간 임시 다운로드 링크

## 4. 필요한 데이터
- D&B API Key (환경변수: `DNB_API_KEY`) → C3과 연동
- PDF 템플릿 (ReportLab 또는 WeasyPrint)

## 5. API/화면 요구사항
```
POST /v1/buyers/{buyer_id}/report → {user_id} → {report_url, expires_at}
GET  /v1/buyers/{buyer_id}/report/download → PDF 파일 반환
```
- 25C 차감 후 생성 (A1 deduct 연동)

## 6. 예외처리
- D&B 데이터 없음 → "신용정보 미확인 바이어" 안내 + 크레딧 미차감
- PDF 생성 실패 → 크레딧 롤백
- 다운로드 링크 만료 → 재생성 안내 (재차감)

## 7. 테스트 기준
- 정상 바이어 ID → PDF URL 반환 + 25C 차감 확인
- D&B 없는 바이어 → 크레딧 미차감 확인
- 만료 링크 접근 → 404 반환

## 8. 개발 TASK
- B2-01: D&B API 연동 (C3 완료 후 연결, MVP는 mock 데이터)
- B2-02: PDF 생성 서비스 (ReportLab)
- B2-03: POST /v1/buyers/{id}/report 엔드포인트 + 25C 차감
- B2-04: 임시 다운로드 링크 생성/만료 관리
- B2-05: 프론트 "신용레포트 받기" 버튼 + 다운로드

## 9. 우선순위
**7순위** — A1·C3 완료 후 진행

## 10. PR 제목 추천
`feat(report): B2 Buyer Fit Pro 신용레포트 PDF 생성`
