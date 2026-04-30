# MarketGate Git 자동 백업 스크립트 (Stash-Pull-Pop 안전 모드)
# 5분마다 변경사항을 감지하여 자동으로 add → stash → pull → pop → commit → push
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
Write-Log "=== Git Auto Backup Started (Stash-Pull-Pop Mode) ==="
Write-Log "Repository: $repoPath"
Write-Log "Interval: $($intervalSeconds / 60) minutes"
Write-Log "Log file: $logFile"
Write-Log "Stop: Task Manager > PowerShell PID 종료"
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
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

            # 1. Stash (untracked 포함)
            git stash push -m "auto-backup-stash-$timestamp" --include-untracked 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git stash failed" }
            Write-Log "[STASH] Local changes saved."

            # 2. Pull (원격 최신 가져오기, rebase 없이 merge)
            $behind = git rev-list --count HEAD..origin/main 2>$null
            if ($behind -gt 0) {
                Write-Log "[PULL] origin/main is $behind commit(s) ahead. Pulling..."
                git pull origin main --quiet 2>$null
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "[ERROR] git pull failed. Restoring stash and stopping."
                    git stash pop 2>$null
                    exit 1
                }
                Write-Log "[PULL] Synced with origin/main."
            }

            # 3. Stash Pop (로컬 변경 복원)
            git stash pop 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Log "[ERROR] git stash pop failed (conflict?). Manual fix required."
                exit 1
            }
            Write-Log "[POP] Stash restored."

            # 4. 충돌 체크
            $conflicts = git diff --name-only --diff-filter=U 2>$null
            if ($conflicts) {
                Write-Log "[CONFLICT] Conflict detected in: $($conflicts -join ', ')"
                Write-Log "[STOP] Auto-backup stopped. Resolve conflicts and restart."
                exit 1
            }

            # 5. Add + Commit + Push
            git add -A 2>$null
            git commit -m "auto-backup: $timestamp" 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git commit failed" }

            git push origin main 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git push failed" }

            Write-Log "[DONE] Backup pushed to origin/main."
        }
    } catch {
        Write-Log "[ERROR] $_"
    }

    Start-Sleep -Seconds $intervalSeconds
}
