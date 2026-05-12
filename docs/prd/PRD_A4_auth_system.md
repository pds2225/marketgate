# PRD: A4 - 회원 인증 시스템

## 1. 목적
회원가입/로그인/세션 관리 및 플랜별 접근 제어 구현.

## 2. MVP 구현 범위
- 이메일+비밀번호 인증 (JWT)
- 회원가입 / 로그인 / 로그아웃
- user_id를 "default"에서 실제 ID로 교체

## 3. 주요 기능
- 회원가입 (이메일 인증 선택)
- JWT 발급 및 갱신 (Access + Refresh Token)
- 플랜별 API 접근 제어
- 비밀번호 재설정

## 4. 필요한 데이터
- `data/users.json` 또는 SQLite: `{user_id, email, hashed_pw, plan, created_at}`
- JWT Secret Key (환경변수: `JWT_SECRET`)

## 5. API/화면 요구사항
```
POST /v1/auth/register            → {email, password} → {user_id, token}
POST /v1/auth/login               → {email, password} → {access_token, refresh_token}
POST /v1/auth/refresh             → {refresh_token} → {access_token}
POST /v1/auth/logout              → 토큰 무효화
GET  /v1/auth/me                  → {user_id, email, plan}
```

## 6. 예외처리
- 중복 이메일 → 409 Conflict
- 토큰 만료 → 401 Unauthorized
- 비밀번호 틀림 5회 → 계정 잠금 (15분)
- JWT 위변조 → 401 반환
- 비밀번호 bcrypt 해싱 필수 (평문 저장 금지)

## 7. 테스트 기준
- 회원가입 → 로그인 → 토큰으로 /v1/credits/balance 조회 성공
- 만료 토큰으로 요청 → 401 반환
- Basic 플랜으로 Pro 전용 API 호출 → 403 반환

## 8. 개발 TASK
- A4-01: 사용자 저장소 + 비밀번호 해싱
- A4-02: JWT 발급/검증 유틸
- A4-03: 회원가입/로그인/로그아웃 API
- A4-04: 기존 API에 인증 미들웨어 적용 (user_id 교체)
- A4-05: 프론트 로그인 화면 + 토큰 관리

## 9. 우선순위
**4순위** — A1~A3 완료 후 진행. 보안 필수 항목

## 10. PR 제목 추천
`feat(auth): A4 JWT 기반 회원 인증 시스템 구현`
