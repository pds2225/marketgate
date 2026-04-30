# MarketGate Git 자동 백업 스크립트
# 5분마다 변경사항을 감지하여 자동으로 add → commit → push
# 실행: PowerShell -File scripts/git_auto_backup.ps1

$repoPath = "D:\marketgate"
$logFile = "D:\marketgate\.git-auto-backup.log"
$intervalSeconds = 300  # 5분

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    Write-Host $line
    $line | Add-Content $logFile -Encoding UTF8
}

Set-Location $repoPath
Write-Log "=== Git Auto Backup Started ==="
Write-Log "Repository: $repoPath"
Write-Log "Interval: $($intervalSeconds / 60) minutes"
Write-Log "Log file: $logFile"
Write-Log "Stop: Task Manager > PowerShell 프로세스 종료"
Write-Log ""

while ($true) {
    try {
        Set-Location $repoPath

        # 현재 브랜치 확인
        $branch = git rev-parse --abbrev-ref HEAD 2>$null
        if ($branch -ne "main") {
            Write-Log "[SKIP] Current branch is '$branch', not main."
            Start-Sleep -Seconds $intervalSeconds
            continue
        }

        # 원격 최신 상태 fetch
        git fetch origin main --quiet 2>$null

        # 변경사항 확인 (untracked + modified + deleted)
        $status = git status --short 2>$null

        if ([string]::IsNullOrWhiteSpace($status)) {
            Write-Log "[CHECK] No local changes."
        } else {
            $changeCount = ($status -split "`n" | Where-Object { $_.Trim() -ne "" }).Count
            Write-Log "[BACKUP] $changeCount changed file(s) detected."

            # add
            git add -A 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git add failed" }

            # commit
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            git commit -m "auto-backup: $timestamp" 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git commit failed" }

            # 원격과 동기화 (rebase로 충돌 최소화)
            $behind = git rev-list --count main..origin/main 2>$null
            if ($behind -gt 0) {
                Write-Log "[SYNC] origin/main is $behind commit(s) ahead. Pulling..."
                git pull origin main --rebase --quiet 2>$null
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "[ERROR] Pull rebase failed. Stopping auto-backup to prevent data loss."
                    Write-Log "[HINT] Manually resolve conflicts and restart this script."
                    exit 1
                }
            }

            # push
            git push origin main 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git push failed" }

            Write-Log "[DONE] Backup pushed to origin/main."
        }
    } catch {
        Write-Log "[ERROR] $_"
    }

    Start-Sleep -Seconds $intervalSeconds
}
