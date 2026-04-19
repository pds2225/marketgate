Write-Host "VALUE-UP 통합 작업본 실행" -ForegroundColor Cyan

$root = "D:\valueup-mvp\unified_workspace_20260418"
$frontend = Join-Path $root "apps\frontend-react"
$p1 = Join-Path $root "services\p1-export-fit-api"

Write-Host ""
Write-Host "1) P1 API 서버 창을 엽니다." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$p1'; uvicorn main:app --reload"
)

Write-Host "2) React 화면 서버 창을 엽니다." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$frontend'; npm run dev"
)

Write-Host ""
Write-Host "브라우저 주소" -ForegroundColor Green
Write-Host "- 프론트: http://localhost:5173"
Write-Host "- P1 API: http://localhost:8000"
Write-Host ""
Write-Host "필요한 패키지가 없다면 각 창에서 먼저 install을 실행해야 합니다." -ForegroundColor DarkYellow
