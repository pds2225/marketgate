-- ============================================================
-- MarketGate W-019: Vault Access Broker
-- 근거: docs/ARCHITECTURE.md §2.1 (발송워커의 Vault 직접 접속 금지,
--       토큰·정책 검증 후 일시 복호화), §4.1 (Legal Basis), §4.2 (Source Rights),
--       §5.3 (상호동의 시에만 연락처 공개), §9.3 완료조건 ①③④⑤⑩
-- 구현 방식:
--   * Broker = broker 스키마의 SECURITY DEFINER 함수 집합.
--     mg_app은 vault 스키마 접근 자체가 불가(0001에서 강제)하고 broker 함수 EXECUTE만 가능.
--     함수 내부에서 정책 게이트를 전부 통과한 경우에만 일시 복호화 값을 반환하고,
--     모든 접근(성공·거부)을 audit_logs에 기록한다.
--   * 암호화: pgcrypto pgp_sym_encrypt + HMAC 지문.
--     Phase 0 키는 DB 설정(mg.vault_key)으로 주입 — 운영 전환 시 KMS 봉투 암호화로
--     교체(contacts_vault.key_id 필드가 그 경계). 하드코딩 금지.
-- ============================================================

BEGIN;

-- pgcrypto는 vault 스키마에 설치: 암호화 프리미티브를 public에 노출하지 않고,
-- Broker 함수의 search_path(vault, core)에서 바로 해석되게 한다
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA vault;

CREATE SCHEMA IF NOT EXISTS broker;

-- ---------- 키 조회 (설정 미주입 시 즉시 실패: 평문·기본키 운용 방지) ----------

CREATE FUNCTION vault.enc_key() RETURNS text
LANGUAGE plpgsql STABLE AS $$
DECLARE k text;
BEGIN
  k := current_setting('mg.vault_key', true);
  IF k IS NULL OR k = '' THEN
    RAISE EXCEPTION 'vault key not configured (set mg.vault_key)';
  END IF;
  RETURN k;
END $$;

CREATE FUNCTION vault.fingerprint(p_value text) RETURNS text
LANGUAGE sql STABLE SET search_path = vault, pg_temp AS $$
  SELECT encode(hmac(lower(trim(p_value)), vault.enc_key(), 'sha256'), 'hex')
$$;

-- ---------- 저장 경로: 정책 게이트 통과 시에만 수납 ----------

CREATE FUNCTION broker.store_contact(
  p_buyer_id     uuid,
  p_channel      core.contact_channel,
  p_plain_value  text,
  p_source_id    text,
  p_legal_basis  core.legal_basis_code,
  p_collection_method text,
  p_jurisdiction text,
  p_actor        text
) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = vault, core, pg_temp AS $$
DECLARE
  v_policy jsonb;
  v_contact_id uuid;
BEGIN
  -- 게이트 1: Source Rights 정책 store_contact=true 필수 (§4.2)
  SELECT policy INTO v_policy FROM core.source_registry WHERE source_id = p_source_id;
  IF v_policy IS NULL THEN
    RAISE EXCEPTION 'unknown source %', p_source_id;
  END IF;
  IF COALESCE((v_policy->>'store_contact')::boolean, false) IS NOT TRUE THEN
    RAISE EXCEPTION 'source % policy forbids contact storage (store_contact=false)', p_source_id;
  END IF;

  INSERT INTO vault.contacts_vault (buyer_id, channel, encrypted_value, key_id, value_fingerprint, source_id)
  VALUES (p_buyer_id, p_channel,
          pgp_sym_encrypt(p_plain_value, vault.enc_key()),
          'mg.vault_key/v1',
          vault.fingerprint(p_plain_value),
          p_source_id)
  ON CONFLICT (buyer_id, channel, value_fingerprint) DO UPDATE SET updated_at = now()
  RETURNING contact_id INTO v_contact_id;

  -- 처리근거 원장 동시 기록 (§4.1: 근거 없는 연락처 없음)
  INSERT INTO vault.contact_legal_basis
    (contact_id, buyer_id, source_id, collected_at, collection_method,
     legal_basis_code, jurisdiction, valid_from)
  VALUES
    (v_contact_id, p_buyer_id, p_source_id, now(), p_collection_method,
     p_legal_basis, p_jurisdiction, now());

  INSERT INTO core.audit_logs (actor, actor_role, action, object_type, object_id, after_state)
  VALUES (p_actor, 'vault_broker', 'VAULT_STORE', 'contact', v_contact_id::text,
          jsonb_build_object('buyer_id', p_buyer_id, 'source_id', p_source_id,
                             'legal_basis', p_legal_basis));
  RETURN v_contact_id;
END $$;

-- ---------- 발송용 일시 복호화: 3중 게이트 + 감사 기록 ----------

CREATE FUNCTION broker.resolve_contact_for_send(
  p_contact_id  uuid,
  p_campaign_id uuid,
  p_actor       text
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = vault, core, pg_temp AS $$
DECLARE
  v_row vault.contacts_vault%ROWTYPE;
  v_basis core.legal_basis_code;
  v_policy jsonb;
  v_campaign_status core.campaign_status;
  v_reason text;
BEGIN
  SELECT * INTO v_row FROM vault.contacts_vault WHERE contact_id = p_contact_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'contact % not found', p_contact_id;
  END IF;

  -- 게이트 1: Legal Basis (§4.1 — 발송 불가 코드 차단, 최신 근거 기준)
  SELECT legal_basis_code INTO v_basis
  FROM vault.contact_legal_basis
  WHERE contact_id = p_contact_id
  ORDER BY COALESCE(valid_from, collected_at) DESC NULLS LAST LIMIT 1;
  IF v_basis IS NULL OR v_basis IN ('UNKNOWN_BASIS','WITHDRAWN','SUPPRESSED') THEN
    v_reason := format('legal basis %s not sendable', COALESCE(v_basis::text, 'NONE'));
  END IF;

  -- 게이트 2: Suppression 무매치 (이메일 지문 + 기업 단위, §2.1)
  IF v_reason IS NULL AND EXISTS (
    SELECT 1 FROM core.suppression_entries
    WHERE (scope = 'EMAIL'   AND value_fingerprint = v_row.value_fingerprint)
       OR (scope = 'COMPANY' AND value_fingerprint = v_row.buyer_id::text)
  ) THEN
    v_reason := 'suppressed';
  END IF;

  -- 게이트 3: Source Rights 정책 send_outreach=true (§4.2)
  IF v_reason IS NULL THEN
    SELECT policy INTO v_policy FROM core.source_registry WHERE source_id = v_row.source_id;
    IF COALESCE((v_policy->>'send_outreach')::boolean, false) IS NOT TRUE THEN
      v_reason := format('source %s policy forbids outreach', v_row.source_id);
    END IF;
  END IF;

  -- 게이트 4: 승인된 발송 문맥에서만 (캠페인 상태 검증, §5.1)
  IF v_reason IS NULL THEN
    SELECT status INTO v_campaign_status FROM core.campaigns WHERE campaign_id = p_campaign_id;
    IF v_campaign_status IS NULL
       OR v_campaign_status NOT IN ('CREDIT_AUTHORIZED','QUEUED','SENDING','RETRYING') THEN
      v_reason := format('campaign %s not in sendable state (%s)',
                         p_campaign_id, COALESCE(v_campaign_status::text, 'NONE'));
    END IF;
  END IF;

  -- 거부·성공 모두 감사 기록 (완료조건 ⑩)
  -- 주의: 거부를 RAISE EXCEPTION으로 처리하면 이 감사 INSERT까지 롤백되어
  -- 거부 이력이 사라진다. 따라서 거부는 NULL 반환 + WARNING으로 처리하고
  -- 호출자(발송워커)는 NULL을 발송 불가로 취급한다.
  INSERT INTO core.audit_logs (actor, actor_role, action, object_type, object_id, after_state)
  VALUES (p_actor, 'vault_broker',
          CASE WHEN v_reason IS NULL THEN 'VAULT_RESOLVE_OK' ELSE 'VAULT_RESOLVE_DENIED' END,
          'contact', p_contact_id::text,
          jsonb_build_object('campaign_id', p_campaign_id, 'deny_reason', v_reason));

  IF v_reason IS NOT NULL THEN
    RAISE WARNING 'vault access denied: %', v_reason;
    RETURN NULL;
  END IF;

  RETURN pgp_sym_decrypt(v_row.encrypted_value, vault.enc_key());
END $$;

-- ---------- 수신거부 등록 (지문 기반 — 평문 불필요) ----------

CREATE FUNCTION broker.suppress_contact(
  p_contact_id uuid,
  p_reason     text,
  p_actor      text
) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = vault, core, pg_temp AS $$
DECLARE v_fp text;
BEGIN
  SELECT value_fingerprint INTO v_fp FROM vault.contacts_vault WHERE contact_id = p_contact_id;
  IF v_fp IS NULL THEN
    RAISE EXCEPTION 'contact % not found', p_contact_id;
  END IF;
  INSERT INTO core.suppression_entries (scope, value_fingerprint, reason, source_event_ref)
  VALUES ('EMAIL', v_fp, p_reason, p_contact_id::text)
  ON CONFLICT (scope, value_fingerprint) DO NOTHING;
  UPDATE vault.contact_legal_basis
     SET legal_basis_code = 'SUPPRESSED', suppression_reason = p_reason
   WHERE contact_id = p_contact_id;
  INSERT INTO core.audit_logs (actor, actor_role, action, object_type, object_id, after_state)
  VALUES (p_actor, 'vault_broker', 'VAULT_SUPPRESS', 'contact', p_contact_id::text,
          jsonb_build_object('reason', p_reason));
END $$;

-- ---------- 권한: mg_app은 테이블이 아닌 Broker 함수만 ----------

REVOKE ALL ON FUNCTION broker.store_contact(uuid, core.contact_channel, text, text, core.legal_basis_code, text, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION broker.resolve_contact_for_send(uuid, uuid, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION broker.suppress_contact(uuid, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION vault.enc_key() FROM PUBLIC;
REVOKE ALL ON FUNCTION vault.fingerprint(text) FROM PUBLIC;

GRANT USAGE ON SCHEMA broker TO mg_app;  -- Broker 함수 호출 경로만 — vault 스키마 접근은 계속 차단
GRANT EXECUTE ON FUNCTION broker.store_contact(uuid, core.contact_channel, text, text, core.legal_basis_code, text, text, text) TO mg_app, mg_vault_broker;
GRANT EXECUTE ON FUNCTION broker.resolve_contact_for_send(uuid, uuid, text) TO mg_app, mg_vault_broker;
GRANT EXECUTE ON FUNCTION broker.suppress_contact(uuid, text, text) TO mg_app, mg_vault_broker;

COMMIT;
