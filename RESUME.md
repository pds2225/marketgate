# RESUME.md — 세션 재시작 시 이어하기 진입점

> 새 세션을 시작하면 이 파일을 가장 먼저 읽어라. (최종 갱신: 2026-08-01)

## 0. 30초 컨텍스트
MarketGate 로컬/원격을 `origin/main`에 맞추고, 이미 반영된 잔여 브랜치·워크트리를 정리한 상태. 다음 선택은 A-기술 MVP 이어서 또는 stash 정리.

## 1. 빠른 재개 (복붙용)
```powershell
cd D:\marketgate
git status -sb
git pull origin main
# 선택: stash 확인
git stash list
```

## 2. 완료된 작업 ✅
- [x] 로컬 main ← origin/main 동기화
- [x] cosmetics 파이프라인 커밋·푸시(이후 main 포함) 확인
- [x] 미반영으로 보이던 브랜치 전수 확인 → 대부분 이미 반영/대체
- [x] 잔여 로컬 브랜치·원격 23개·tmp 워크트리 삭제
- [x] 브랜치 정리 스킬·위키 메모 저장

## 3. 남은 작업 ⬜ (다음 세션에서 이어서)
- [ ] `git stash list` 3개 중 불필요분 drop 여부 결정
- [ ] A-기술 MVP(랜딩 CTA·인콰이어리 발송/큐·가짜 UI 라벨·크레딧 deduct) 착수 여부
- [ ] (선택) `.git/worktrees` 고아 메타 prune — 잠금 프로세스 종료 후

## 4. 핵심 결정·제약 (되돌리지 말 것)
- 미반영 판별은 **`origin/main` 기준** (로컬 main behind 시 착시)
- 옛 feature tip을 최신 main 위에 무작정 머지하지 말 것(프론트/결제 회귀)
- `buyer_candidate.csv` 대량 diff ≠ 소스 삭제; 커밋 시 산출 CSV 주의
- demo 연락처 언마스크 브랜치는 머지 금지
- A-MVP 시트 ≠ 구글 WBS Phase0 Vault 트랙

## 5. 핵심 파일 인덱스 (어디에 뭐가 있나)
| 알고 싶은 것 | 파일 |
|---|---|
| A-기술 MVP 스프린트 시트 | `docs/sheets/A_MVP_기술닫기.csv` |
| 이메일 백필 | `tools/backfill_buyer_emails.py` |
| 브랜치 정리 절차 스킬 | `~/.claude/skills/omc-learned/git-unmerged-branch-cleanup.md` |
| 위키: 브랜치 정리 | `.omc/wiki/marketgate-branch-cleanup-vs-origin-main.md` |
| 위키: 파이프라인 메모 | `.omc/wiki/marketgate-cosmetics-pipeline-mvp-notes.md` |

## 6. 검증된 사실 (재확인 불필요)
- 현재 브랜치: `main` only, tip = origin/main
- ahead 원격 브랜치: 0 (정리 직후 기준)
- `valid_until` 만료 → `signal_usable=False`는 정상
- wiki “3개”: OMC wiki 중복 등록 + `wiki-session-capture`는 closeout용 별도

## 7. 재개 시 첫 행동
1. `git status -sb` / `git stash list` 확인  
2. A-MVP 진행할지 사용자에게 확인  
3. 진행 시 Landing CTA·인콰이어리 경로부터
