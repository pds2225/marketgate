<#
.SYNOPSIS
  MarketGate 작업 트리의 변경 상태를 읽기 전용으로 감시합니다.

.DESCRIPTION
  이 스크립트는 stash, pull, add, commit, push를 실행하지 않습니다.
  변경 파일 수와 현재 브랜치만 화면에 표시합니다.
#>
param(
    [string]$RepositoryPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [ValidateRange(5, 86400)]
    [int]$IntervalSeconds = 300,
    [switch]$Once
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath $RepositoryPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ".git"))) {
    throw "Git 저장소가 아닙니다: $repoRoot"
}

Push-Location $repoRoot
try {
    do {
        $branch = (git branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw "현재 브랜치를 확인하지 못했습니다."
        }

        $changes = @(git status --short)
        if ($LASTEXITCODE -ne 0) {
            throw "작업 트리 상태를 확인하지 못했습니다."
        }

        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        if ($changes.Count -eq 0) {
            Write-Host "[$timestamp] branch=$branch, 변경 없음" -ForegroundColor Green
        }
        else {
            Write-Host "[$timestamp] branch=$branch, 변경 $($changes.Count)개" -ForegroundColor Yellow
            $changes | ForEach-Object { Write-Host "  $_" }
        }

        if ($Once) {
            break
        }
        Start-Sleep -Seconds $IntervalSeconds
    } while ($true)
}
finally {
    Pop-Location
}
