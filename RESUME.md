# RESUME.md — MarketGate 작업 체크포인트

최종 갱신: 2026-10-04

## 0. 현재 목표
- Render DB 이전 준비: Supabase 싱가포르 프로젝트를 만들고 Session pooler URI(5432, 비밀번호 포함)를 기존 보안 입력란에 저장한다.
- 현재 실행 막힘: 브라우저 연결 목록이 비어 있고 Chrome/IAB 열기 모두 불가. Supabase 및 보안 입력 화면에 접근하지 못했다.

## 1. 확인된 상태
- repo: D:\marketgate, origin=https://github.com/pds2225/marketgate.git
- 로컬 main=ac756e180bb1579523d993c4467e204b4458cdbc. 로컬 origin/main 기준 11커밋 뒤; 원격 fetch는 실행하지 않았다.
- stash 3개와 기존 worktree 유지. 미추적 파일 및 데이터 출력 폴더 보존.
- 사용자 제공 정보(직접 검증 안 됨): Render DB 백업 20KB; auth_users 83, credit_accounts 9, auth_token_blacklist 14, company_registry_checks 10, payment_ledger 0, subscriptions 0.
- 프로젝트 생성, URI 저장, DB 복원, 운영 연결 주소 교체 모두 미실행.

## 2. 다음 액션
- Supabase에 로그인한 브라우저 및 사용자가 말한 보안 URI 입력 화면을 연결한 뒤 중복 프로젝트/지역/요금부터 확인.
- 싱가포르 프로젝트 준비 후 Connect → Session pooler → 5432 URI를 해당 보안 입력란에만 저장. 비밀번호 직접 입력/확정이 필요한 단계는 사용자에게 인계.
- 복원/운영 주소 교체는 이번 실행에서 착수하지 않음. 기존 흐름대로 주소 교체 직전 최신 백업을 다시 확보한 뒤 진행해야 한다.

## 3. 결정과 제약
- 비밀번호, URI, API Key, Token, .env 값을 채팅/로그/체크포인트에 기록하지 않는다.
- 백엔드/프론트엔드 코드, .env, TASKS.md, auto_prompt_*.md, workflow 및 런타임 데이터 수정 금지.
- commit/push/PR/merge/원격 브랜치 삭제 없음.
- 유료 생성/결제, 복구 불가 작업, 운영 DB 연결 교체는 별도 확인 없이 진행하지 않는다.

## 4. 이전 Git 정리 작업 보존
- 2026-09-12 로컬 main 고유 커밋 bc049549091d7fb1c91ebe08cfd6943227952f6b를 backup/local-main-before-sync-20260912에 보존한 뒤 main을 ac756e180bb1579523d993c4467e204b4458cdbc로 동기화했다(이전 체크포인트 기록).
- 고아 worktree 메타 11개 및 main 포함 잔여 브랜치 정리는 보류. 사용자가 승인하기 전 prune/삭제 금지.
- feat-export-calculators(수정/미추적 있음), wondrous-twirling-piglet, D:\tmp\wt-marketgate-task, backup 2개, docs/task-ops-gates-20260813 및 stash 3개 보존.
- 현재 추가 등록된 D:\mg-perf 및 v_up dashboard worktree도 변경하지 않는다. 과거 GitHub CLI 인증 오류 상태는 이번에 재검증하지 않았다.

## 5. 빠른 재개
```powershell
cd D:\marketgate
git status --short --branch
git worktree list --porcelain
git stash list
```
- 관련 규칙: D:\marketgate\AGENTS.md
- 첫 행동: 브라우저 연결을 재확인하고 Supabase와 기존 보안 입력 화면에서 준비 작업 재개.