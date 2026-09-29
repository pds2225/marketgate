-- ============================================================
-- Auth persistence: users + token blacklist
-- Render 무료 플랜은 배포마다 파일시스템이 초기화되므로,
-- 인증 데이터를 PostgreSQL에 영구 저장한다.
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS auth_users (
    user_id         text PRIMARY KEY,
    email           text NOT NULL UNIQUE,
    hashed_pw       text NOT NULL,
    role            text NOT NULL DEFAULT 'user',
    plan            text NOT NULL DEFAULT 'Basic',
    login_fail_count int NOT NULL DEFAULT 0,
    locked_until    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users (email);

CREATE TABLE IF NOT EXISTS auth_token_blacklist (
    jti         text PRIMARY KEY,
    blacklisted_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
