# MarketGate 작업 체크포인트

최종 갱신: 2026-09-12

## 목표

- 로컬 `main` 동기화 후 브랜치·워크트리를 정리하되, 미반영 작업과 stash는 보존한다.

## 완료 ✅

- repo 확인: `D:\marketgate`, origin=`https://github.com/pds2225/marketgate.git`
- GitHub 기본 브랜치 확인: `main`, 원격 HEAD=`ac756e180bb1579523d993c4467e204b4458cdbc`
- 기존 로컬 main=`bc049549091d7fb1c91ebe08cfd6943227952f6b`
- 로컬 main 고유 커밋을 `backup/local-main-before-sync-20260912` 브랜치에 보존하고 해시 일치 확인
- stash 3개와 모든 기존 워크트리는 변경하지 않음
- `origin/main` fetch 완료: 기존 로컬 main은 고유 1커밋, 원격보다 122커밋 뒤였음
- 로컬 `main`을 원격 `main`과 동일한 `ac756e180bb1579523d993c4467e204b4458cdbc`로 갱신
- `main`에서 `git pull --ff-only origin main` 실행 결과: `Already up to date.`
- 정리 현황 조사 완료: 열린 Claude 창 1개, 자동 삭제 가능한 고아 worktree 메타 후보 11개
- `origin/main` 포함 완료 확인: `cursor/critical-bug-investigation-4bd0`, `docs/remove-next-task-20260813`, `worktree-feat-export-calculators`의 커밋 기준선, `worktree-wondrous-twirling-piglet`

## 보존 중인 작업

- `D:\marketgate\.claude\worktrees\feat-export-calculators`: 수정 및 미추적 파일 있음. 다른 작업이므로 손대지 말 것.
- `D:\marketgate\.claude\worktrees\wondrous-twirling-piglet`: 원격 브랜치가 삭제된 로컬 워크트리. 보존.
- `D:\tmp\wt-marketgate-task`: `docs/task-ops-gates-20260813` 워크트리. 보존.
- stash 3개 유지. 적용하거나 삭제하지 말 것.

## 현재 상태 / 다음 액션 ⬜

1. 현재 루트 브랜치는 `main`이며 GitHub `main`과 동기화됨.
2. 사용자 승인 후에만 고아 worktree 메타 11개를 `git worktree prune`으로 정리한다.
3. 사용자 승인 후에만 이미 main에 포함된 깨끗한 잔여 로컬 브랜치/워크트리를 제거한다.
4. GitHub CLI 인증 오류로 PR 상태를 확인하지 못했으므로 원격 브랜치는 삭제하지 않는다.

## 핵심 결정과 제약

- 기존 커밋은 삭제하지 않고 복구 브랜치로 먼저 보존한다.
- 계산기 워크트리, 다른 워크트리, stash는 수정·적용·삭제하지 않는다.
- 더티 계산기 워크트리, 고유 커밋이 있는 backup 2개와 `docs/task-ops-gates-20260813`, stash 3개는 보존한다.
- push, PR 생성, merge, 원격 브랜치 삭제는 이번 정리 범위에 포함하지 않는다.
- `.env`, Secret, 런타임 데이터는 읽거나 출력하지 않는다.

## 재개 명령

```powershell
cd D:\marketgate
git status --short --branch
git branch -vv
git worktree list --porcelain
git stash list
```
