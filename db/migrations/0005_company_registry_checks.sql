-- ============================================================
-- CV-01: 해외기업 기본검증 DB 마이그레이션
-- 법인 실체·등록상태·입력정보 일치 여부 검증 결과 저장.
-- 재실행 가능 (IF NOT EXISTS / IF NOT EXISTS 패턴).
-- 기존 인증·결제·크레딧 테이블 비변경.
-- ============================================================

BEGIN;

-- ---------- ENUM: 검증 상태 (5종) ----------

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'registry_check_status') THEN
    CREATE TYPE core.registry_check_status AS ENUM (
      'VERIFIED',          -- 법인 실체 확인, 정보 일치
      'PARTIAL_MATCH',     -- 일부 정보만 일치
      'MISMATCH',          -- 입력 정보 불일치
      'INACTIVE',          -- 비활성/해산 법인
      'CREDIT_CHECK_REQUIRED'  -- 신용조사 필요 (추가 확인)
    );
  END IF;
END $$;

-- ---------- company_registry_checks 테이블 ----------

CREATE TABLE IF NOT EXISTS core.company_registry_checks (
  check_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            text NOT NULL,
  company_name       text NOT NULL,
  country_iso3       char(3) NOT NULL,
  registration_number text,
  provider           text NOT NULL DEFAULT 'opencorporates',
  registry_check_status core.registry_check_status,
  result_json        jsonb,
  provider_ref       text,
  requested_at       timestamptz NOT NULL DEFAULT now(),
  completed_at       timestamptz,
  error_code         text,
  error_message      text
);

CREATE INDEX IF NOT EXISTS idx_company_registry_checks_user
  ON core.company_registry_checks (user_id, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_company_registry_checks_company
  ON core.company_registry_checks (company_name, country_iso3);

COMMIT;
