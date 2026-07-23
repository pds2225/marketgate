-- ============================================================
-- MarketGate Phase 0 초기 스키마 (17테이블)
-- 근거: docs/ARCHITECTURE.md §9.1 (테이블 목록), §2.3 (통합 금지 5종·경량 노트),
--       §4.1 (Legal Basis), §4.2 (Source Rights), §5.1~5.2 (상태·이벤트), §7.1·§7.4
-- 원칙:
--   * vault 스키마 = Contact Vault 권한 분리 경계. 애플리케이션 롤(mg_app)은
--     vault에 접근 불가, mg_vault_broker만 접근 (완료조건 ① 일반 API 평문 조회 불가)
--   * credit_ledger / audit_logs / message_events 는 append-only (수정·삭제 금지 트리거)
--   * 통합 금지 5종: contacts_vault, contact_legal_basis, suppression_entries,
--     credit_ledger, audit_logs
--   * 잔액은 집계 뷰(credit_balances)로만 산출 — 원장에 잔액 컬럼 없음
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS vault;

-- ---------- ENUM ----------

CREATE TYPE core.source_rights_code AS ENUM (
  'OPEN_REUSE','INTERNAL_ANALYTICS','OUTREACH_ALLOWED','CUSTOMER_PROVIDED',
  'CONSENTED_INBOUND','CONTRACT_REQUIRED','PROHIBITED','UNKNOWN');

CREATE TYPE core.legal_basis_code AS ENUM (
  'OPTED_IN','CONTRACT_REQUIRED','LEGITIMATE_INTEREST_REVIEW',
  'PUBLIC_CORPORATE_CONTACT','UNKNOWN_BASIS','WITHDRAWN','SUPPRESSED');

CREATE TYPE core.buyer_verification_status AS ENUM (
  'DISCOVERED','IDENTIFIED','ACTIVE_SIGNAL','CONTACTABLE','VERIFIED',
  'ENGAGED','QUALIFIED','CONVERTED','SUPPRESSED','DORMANT');

CREATE TYPE core.campaign_status AS ENUM (
  -- 정상 경로 12단계 (§5.1)
  'DRAFT','COMPLIANCE_REVIEW','APPROVED','SLOT_RESERVED','CREDIT_AUTHORIZED',
  'QUEUED','SENDING','DELIVERED','RESPONDED','QUALIFIED','INTRODUCED',
  'CLOSED_WON','CLOSED_LOST',
  -- 예외 상태 9종 (§5.1)
  'REJECTED_COMPLIANCE','SUPPRESSED','HARD_BOUNCED','SOFT_BOUNCED',
  'RETRYING','CANCELLED','CREDIT_RESTORED','REFUNDED','COMPLAINT_RECEIVED');

CREATE TYPE core.message_event_type AS ENUM (
  'queued','sent','delivered','open','soft_bounce','hard_bounce',
  'complaint','unsubscribe','reply_positive','reply_negative','auto_reply');

CREATE TYPE core.credit_event_type AS ENUM (
  'PURCHASE','HOLD','CAPTURE','RESTORE','REFUND',
  'TRIAL_CREDITED','TRIAL_REFUNDED','ADJUSTMENT');

CREATE TYPE core.suppression_scope AS ENUM ('EMAIL','DOMAIN','COMPANY');

CREATE TYPE core.contact_channel AS ENUM ('EMAIL','PHONE','FORM','SOCIAL');

-- ---------- append-only 가드 ----------

CREATE FUNCTION core.forbid_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% is append-only: % not allowed', TG_TABLE_NAME, TG_OP;
END $$;

-- ---------- 1. source_registry (§4.2) ----------

CREATE TABLE core.source_registry (
  source_id        text PRIMARY KEY,
  source_name      text NOT NULL,
  rights_code      core.source_rights_code NOT NULL DEFAULT 'UNKNOWN',
  -- 정책 객체: 기본값은 전부 거부(default-deny)
  policy           jsonb NOT NULL DEFAULT '{"store_core":false,"store_contact":false,"use_for_scoring":false,"show_company_to_customer":false,"send_outreach":false,"commercialize_derived_output":"review_required"}'::jsonb,
  contract_ref     text,
  acquired_at      date,
  valid_until      date,
  verified_at      timestamptz,
  notes            text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- ---------- 2~4. buyers / buyer_identifiers / buyer_signals ----------
-- §2.3 경량 노트: identifiers·signals는 초기 JSONB 컬럼으로 시작 가능하나
-- 스키마는 전부 수용(별도 테이블). 단일 인스턴스 전제.

CREATE TABLE core.buyers (
  buyer_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name        text NOT NULL,
  normalized_name     text NOT NULL,
  country_iso3        char(3),
  website_domain      text,
  company_size        text,
  verification_status core.buyer_verification_status NOT NULL DEFAULT 'DISCOVERED',
  intent_score        smallint CHECK (intent_score BETWEEN 0 AND 100),
  score_breakdown     jsonb,               -- §7.1 배점 근거
  primary_source_id   text REFERENCES core.source_registry(source_id),
  first_seen_at       timestamptz,
  last_signal_at      timestamptz,         -- 신선도 감점 판단(§7.1)
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_buyers_country ON core.buyers (country_iso3);
CREATE INDEX idx_buyers_norm_name ON core.buyers (normalized_name);

CREATE TABLE core.buyer_identifiers (
  identifier_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  buyer_id       uuid NOT NULL REFERENCES core.buyers(buyer_id) ON DELETE CASCADE,
  id_type        text NOT NULL,            -- domain | duns | registration_no | alias ...
  id_value       text NOT NULL,
  source_id      text REFERENCES core.source_registry(source_id),
  confidence     numeric(4,3),
  observed_at    timestamptz,
  UNIQUE (id_type, id_value, buyer_id)
);

CREATE TABLE core.buyer_signals (
  signal_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  buyer_id       uuid NOT NULL REFERENCES core.buyers(buyer_id) ON DELETE CASCADE,
  signal_type    text NOT NULL,            -- bl_import | regulatory_registration | inquiry | exhibition ...
  signal_value   jsonb NOT NULL,
  source_id      text NOT NULL REFERENCES core.source_registry(source_id),
  source_record_id text,                   -- §4.3 lineage
  observed_at    timestamptz NOT NULL,
  ingested_at    timestamptz NOT NULL DEFAULT now(),
  confidence     numeric(4,3),
  expires_at     timestamptz
);
CREATE INDEX idx_signals_buyer ON core.buyer_signals (buyer_id, observed_at DESC);

-- ---------- 5~6. Contact Vault (통합 금지 ★, vault 스키마 격리) ----------

CREATE TABLE vault.contacts_vault (
  contact_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  buyer_id          uuid NOT NULL,          -- core.buyers 참조(권한 분리를 위해 FK 미설정)
  channel           core.contact_channel NOT NULL DEFAULT 'EMAIL',
  encrypted_value   bytea NOT NULL,         -- KMS 봉투 암호화, 평문 저장 금지
  key_id            text  NOT NULL,         -- 암호화 키 식별자(회전 대비)
  value_fingerprint text  NOT NULL,         -- HMAC 지문: 중복·수신거부 대조용(복원 불가)
  source_id         text  NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (buyer_id, channel, value_fingerprint)
);

CREATE TABLE vault.contact_legal_basis (      -- §4.1 필수 필드 16개
  basis_id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id           uuid NOT NULL REFERENCES vault.contacts_vault(contact_id) ON DELETE CASCADE,
  buyer_id             uuid NOT NULL,
  source_id            text NOT NULL,
  collected_at         timestamptz,
  collection_method    text,
  legal_basis_code     core.legal_basis_code NOT NULL DEFAULT 'UNKNOWN_BASIS',
  purpose_code         text,
  consent_status       text,
  consent_scope        text,
  consent_timestamp    timestamptz,
  consent_evidence_uri text,                  -- CASL 등 증빙(수집 URL·일시)
  jurisdiction         text,                  -- Country Rule Matrix 관할 판단
  valid_from           timestamptz,
  valid_until          timestamptz,
  withdrawn_at         timestamptz,
  suppression_reason   text
);
CREATE INDEX idx_legal_basis_contact ON vault.contact_legal_basis (contact_id);

-- ---------- 7. suppression_entries (통합 금지 ★) ----------

CREATE TABLE core.suppression_entries (
  suppression_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scope             core.suppression_scope NOT NULL,
  value_fingerprint text NOT NULL,           -- EMAIL=HMAC 지문 / DOMAIN=도메인 / COMPANY=buyer_id
  reason            text NOT NULL,           -- unsubscribe | complaint | hard_bounce | manual | legal
  source_event_ref  text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (scope, value_fingerprint)
);

-- ---------- 8~9. matches / slots (§7.4) ----------

CREATE TABLE core.matches (
  match_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  seller_tenant_id uuid NOT NULL,            -- 테넌트 마스터는 Phase 0 범위 외(어드민 단일 운영)
  buyer_id        uuid NOT NULL REFERENCES core.buyers(buyer_id),
  passport_ref    text,                      -- Export Product Passport 식별자(§7.5)
  intent_score    smallint,
  eligibility_ok  boolean NOT NULL DEFAULT false,  -- Intent Score와 분리(§7.1)
  match_basis     jsonb,                     -- 매칭 근거 카드 원자료
  status          text NOT NULL DEFAULT 'PROPOSED',
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.slots (
  slot_id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  buyer_id            uuid NOT NULL REFERENCES core.buyers(buyer_id),
  product_category_id text NOT NULL,
  period_start        date NOT NULL,
  period_end          date NOT NULL,         -- 초기 파라미터: 30일(§7.4)
  seller_tenant_id    uuid,                  -- 예약 시 배정
  status              text NOT NULL DEFAULT 'AVAILABLE',  -- AVAILABLE|RESERVED|CONSUMED|RELEASED
  reserved_at         timestamptz,
  consumed_at         timestamptz,           -- delivered 시각(확정 소진, §5.2)
  CHECK (period_end > period_start),
  -- 배타성: 동일 바이어·품목군·기간에 1개사(§7.4)
  UNIQUE (buyer_id, product_category_id, period_start)
);
CREATE INDEX idx_slots_tenant ON core.slots (seller_tenant_id);

-- ---------- 10~11. campaigns / campaign_recipients (§5.1) ----------

CREATE TABLE core.campaigns (
  campaign_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  seller_tenant_id uuid NOT NULL,
  name            text NOT NULL,
  status          core.campaign_status NOT NULL DEFAULT 'DRAFT',
  template_ref    text,                      -- 승인 템플릿(광고 표시·물리 주소·수신거부 링크, §6.2)
  compliance_checklist jsonb,                -- §6.2 6항목 점검 결과
  approved_by     text,                      -- 완료조건 ⑤ 발송 승인자
  approved_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.campaign_recipients (
  recipient_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id     uuid NOT NULL REFERENCES core.campaigns(campaign_id) ON DELETE CASCADE,
  buyer_id        uuid NOT NULL REFERENCES core.buyers(buyer_id),
  slot_id         uuid REFERENCES core.slots(slot_id),
  contact_ref     uuid NOT NULL,             -- vault.contacts_vault.contact_id (FK 미설정: 권한 분리)
  status          core.campaign_status NOT NULL DEFAULT 'QUEUED',
  UNIQUE (campaign_id, buyer_id)
);

-- ---------- 12~13. messages / message_events (§5.2, 불변) ----------

CREATE TABLE core.messages (
  message_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recipient_id    uuid NOT NULL REFERENCES core.campaign_recipients(recipient_id) ON DELETE CASCADE,
  direction       text NOT NULL DEFAULT 'OUTBOUND',  -- OUTBOUND|INBOUND
  subject         text,
  body_uri        text,                      -- 본문은 오브젝트 저장소 참조
  template_version text,
  provider_message_id text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.message_events (
  event_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  message_id   uuid NOT NULL REFERENCES core.messages(message_id) ON DELETE CASCADE,
  event_type   core.message_event_type NOT NULL,
  occurred_at  timestamptz NOT NULL,
  provider_ref text,
  payload      jsonb,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_msg_events_message ON core.message_events (message_id, occurred_at);
CREATE TRIGGER trg_message_events_append_only
  BEFORE UPDATE OR DELETE ON core.message_events
  FOR EACH ROW EXECUTE FUNCTION core.forbid_mutation();

-- ---------- 14. conversations (§5.3 Response Relay) ----------

CREATE TABLE core.conversations (
  conversation_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recipient_id     uuid NOT NULL REFERENCES core.campaign_recipients(recipient_id) ON DELETE CASCADE,
  direction        text NOT NULL,            -- BUYER_TO_SELLER | SELLER_TO_BUYER
  relayed_body_uri text,
  classification   text,                     -- spam | auto_reply | interest_positive | interest_negative
  -- 연락처 공개는 양 당사자 동의 시에만(§5.3): 두 시각이 모두 기록되어야 공개
  buyer_disclosure_agreed_at  timestamptz,
  seller_disclosure_agreed_at timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- ---------- 15. credit_ledger (통합 금지 ★, append-only) ----------

CREATE TABLE core.credit_ledger (
  entry_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id      uuid NOT NULL,
  event_type     core.credit_event_type NOT NULL,
  amount_credits numeric(12,2) NOT NULL,     -- 부호 포함(+적립/-차감), 잔액 컬럼 없음
  ref_type       text,                       -- campaign | slot | order | trial ...
  ref_id         text,
  reason         text,
  created_by     text NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_credit_ledger_tenant ON core.credit_ledger (tenant_id, created_at);
CREATE TRIGGER trg_credit_ledger_append_only
  BEFORE UPDATE OR DELETE ON core.credit_ledger
  FOR EACH ROW EXECUTE FUNCTION core.forbid_mutation();

-- 잔액은 집계 뷰로만 산출
CREATE VIEW core.credit_balances AS
  SELECT tenant_id, sum(amount_credits) AS balance
  FROM core.credit_ledger GROUP BY tenant_id;

-- ---------- 16. approval_tasks (§2.3: campaigns 상태 컬럼으로 흡수 가능) ----------

CREATE TABLE core.approval_tasks (
  task_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_type   text NOT NULL,                 -- campaign_approval | manual_review | refund_approval ...
  ref_type    text NOT NULL,
  ref_id      text NOT NULL,
  status      text NOT NULL DEFAULT 'PENDING',   -- PENDING|APPROVED|REJECTED
  assigned_to text,
  decided_by  text,
  decided_at  timestamptz,
  notes       text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------- 17. audit_logs (통합 금지 ★, append-only) ----------

CREATE TABLE core.audit_logs (
  log_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor       text NOT NULL,
  actor_role  text,
  action      text NOT NULL,
  object_type text NOT NULL,
  object_id   text,
  before_state jsonb,
  after_state  jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_audit_logs_append_only
  BEFORE UPDATE OR DELETE ON core.audit_logs
  FOR EACH ROW EXECUTE FUNCTION core.forbid_mutation();

-- ---------- 권한 분리 (완료조건 ①②: 평문 비노출) ----------

DO $$ BEGIN CREATE ROLE mg_app NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE mg_vault_broker NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;

REVOKE ALL ON SCHEMA vault FROM PUBLIC;
GRANT USAGE ON SCHEMA core TO mg_app, mg_vault_broker;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA core TO mg_app;
-- append-only 테이블은 롤 차원에서도 수정·삭제 불가
REVOKE UPDATE, DELETE ON core.credit_ledger, core.audit_logs, core.message_events FROM mg_app;
-- 애플리케이션 롤은 Vault 접근 자체가 불가 — Broker 경유만
GRANT USAGE ON SCHEMA vault TO mg_vault_broker;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA vault TO mg_vault_broker;

COMMIT;
