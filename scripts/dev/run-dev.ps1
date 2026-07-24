Write-Host "MarketGate 개발 환경 실행" -ForegroundColor Cyan

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$frontend = Join-Path $root "apps\frontend-react"
$p1 = Join-Path $root "services\p1-export-fit-api"

foreach ($path in @($frontend, $p1)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "필수 폴더를 찾을 수 없습니다: $path"
    }
}

Write-Host ""
Write-Host "1) P1 API 서버 창을 엽니다." -ForegroundColor Yellow
Start-Process powershell -WorkingDirectory $p1 -ArgumentList @(
    "-NoExit",
    "-Command",
    "uvicorn main:app --reload --port 8000"
)

Write-Host "2) React 화면 서버 창을 엽니다." -ForegroundColor Yellow
Start-Process powershell -WorkingDirectory $frontend -ArgumentList @(
    "-NoExit",
    "-Command",
    "npm run dev"
)

Write-Host ""
Write-Host "브라우저 주소" -ForegroundColor Green
Write-Host "- 프론트: http://localhost:5173"
Write-Host "- P1 API: http://localhost:8000"
Write-Host ""
Write-Host "필요한 패키지가 없다면 각 창에서 먼저 설치해야 합니다." -ForegroundColor DarkYellow
