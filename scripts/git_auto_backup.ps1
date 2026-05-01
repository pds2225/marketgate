# MarketGate Git ?먮룞 諛깆뾽 ?ㅽ겕由쏀듃 (Stash-Pull-Pop ?덉쟾 紐⑤뱶)
# 5遺꾨쭏??蹂寃쎌궗??쓣 媛먯??섏뿬 ?먮룞?쇰줈 add ??stash ??pull ??pop ??commit ??push
# ?ㅽ뻾: PowerShell -File scripts/git_auto_backup.ps1

$repoPath = "D:\marketgate"
$logFile = "D:\marketgate\.git-auto-backup.log"
$intervalSeconds = 300  # 5遺?
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
Write-Log "Stop: Task Manager > PowerShell PID 醫낅즺"
Write-Log ""

while ($true) {
    try {
        Set-Location $repoPath

        # ?꾩옱 釉뚮옖移??뺤씤
        $branch = git rev-parse --abbrev-ref HEAD 2>$null
        if ($branch -ne "main") {
            Write-Log "[SKIP] Current branch is '$branch', not main."
            Start-Sleep -Seconds $intervalSeconds
            continue
        }

        # ?먭꺽 理쒖떊 ?곹깭 fetch
        git fetch origin main --quiet 2>$null

        # 蹂寃쎌궗???뺤씤 (untracked + modified + deleted)
        $status = git status --short 2>$null

        if ([string]::IsNullOrWhiteSpace($status)) {
            Write-Log "[CHECK] No local changes."
        } else {
            $changeCount = ($status -split "`n" | Where-Object { $_.Trim() -ne "" }).Count
            Write-Log "[BACKUP] $changeCount changed file(s) detected."
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

            # 1. Stash (untracked ?ы븿)
            if (Test-Path "$epoPath\.git-auto-backup.log") { Remove-Item "$epoPath\.git-auto-backup.log" -Force }
            git stash push -m "auto-backup-stash-$timestamp" --include-untracked 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git stash failed" }
            Write-Log "[STASH] Local changes saved."

            # 2. Pull (?먭꺽 理쒖떊 媛?몄삤湲? rebase ?놁씠 merge)
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

            # 3. Stash Pop (濡쒖뺄 蹂寃?蹂듭썝)
            git stash pop 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Log "[ERROR] git stash pop failed (conflict?). Manual fix required."
                exit 1
            }
            Write-Log "[POP] Stash restored."

            # 4. 異⑸룎 泥댄겕
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

