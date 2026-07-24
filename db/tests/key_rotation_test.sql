\set ON_ERROR_STOP on

BEGIN;

DO $test$
DECLARE
  v_buyer_id uuid;
  v_contact_id uuid;
  v_second_buyer_id uuid;
  v_second_contact_id uuid;
  v_rotated integer;
  v_fingerprint text;
  v_plain text;
BEGIN
  PERFORM set_config('mg.vault_key', 'w020-old-key', true);
  PERFORM set_config('mg.vault_fingerprint_key', 'w020-stable-fingerprint', true);
  PERFORM set_config('mg.vault_key_v2', 'w020-new-key', true);

  INSERT INTO core.source_registry
    (source_id, source_name, rights_code, policy)
  VALUES
    ('w020-test', 'W-020 test source', 'OUTREACH_ALLOWED',
     '{"store_core":true,"store_contact":true,"send_outreach":true}'::jsonb);

  INSERT INTO core.buyers (display_name, normalized_name)
  VALUES ('W020 Buyer One', 'w020-buyer-one')
  RETURNING buyer_id INTO v_buyer_id;

  v_contact_id := broker.store_contact(
    v_buyer_id, 'EMAIL', 'first@example.com', 'w020-test',
    'OPTED_IN', 'test', 'KOR', 'w020-test'
  );

  SELECT value_fingerprint INTO v_fingerprint
  FROM vault.contacts_vault
  WHERE contact_id = v_contact_id
    AND key_id = 'mg.vault_key/v1';
  IF v_fingerprint IS NULL THEN
    RAISE EXCEPTION 'initial contact did not use v1 key metadata';
  END IF;

  v_rotated := broker.rotate_vault_key(
    'mg.vault_key/v2', 'setting:mg.vault_key_v2', 'w020-test'
  );
  IF v_rotated <> 1 THEN
    RAISE EXCEPTION 'expected 1 rotated contact, got %', v_rotated;
  END IF;

  SELECT vault.pgp_sym_decrypt(encrypted_value, vault.key_material(key_id))
  INTO v_plain
  FROM vault.contacts_vault
  WHERE contact_id = v_contact_id
    AND key_id = 'mg.vault_key/v2'
    AND value_fingerprint = v_fingerprint;
  IF v_plain IS DISTINCT FROM 'first@example.com' THEN
    RAISE EXCEPTION 'rotated contact cannot be decrypted';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM vault.key_registry
    WHERE key_id = 'mg.vault_key/v1' AND status = 'RETIRED'
  ) OR NOT EXISTS (
    SELECT 1 FROM vault.key_registry
    WHERE key_id = 'mg.vault_key/v2' AND status = 'ACTIVE'
  ) THEN
    RAISE EXCEPTION 'key registry status transition is invalid';
  END IF;

  INSERT INTO core.buyers (display_name, normalized_name)
  VALUES ('W020 Buyer Two', 'w020-buyer-two')
  RETURNING buyer_id INTO v_second_buyer_id;

  v_second_contact_id := broker.store_contact(
    v_second_buyer_id, 'EMAIL', 'second@example.com', 'w020-test',
    'OPTED_IN', 'test', 'KOR', 'w020-test'
  );
  IF NOT EXISTS (
    SELECT 1 FROM vault.contacts_vault
    WHERE contact_id = v_second_contact_id
      AND key_id = 'mg.vault_key/v2'
  ) THEN
    RAISE EXCEPTION 'new contact did not use active v2 key';
  END IF;

  BEGIN
    PERFORM broker.rotate_vault_key(
      'mg.vault_key/v3', 'setting:mg.vault_key_missing', 'w020-test'
    );
    RAISE EXCEPTION 'missing-key rotation unexpectedly succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM = 'missing-key rotation unexpectedly succeeded' THEN
      RAISE;
    END IF;
  END;

  IF vault.active_key_id() <> 'mg.vault_key/v2' THEN
    RAISE EXCEPTION 'failed rotation changed the active key';
  END IF;
  IF has_function_privilege(
    'mg_app', 'broker.rotate_vault_key(text,text,text)', 'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'mg_app must not rotate vault keys';
  END IF;
  IF has_function_privilege(
    'mg_vault_broker', 'broker.rotate_vault_key(text,text,text)', 'EXECUTE'
  ) OR NOT has_function_privilege(
    'mg_vault_key_admin', 'broker.rotate_vault_key(text,text,text)', 'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'vault key rotation privilege boundary is invalid';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM core.audit_logs
    WHERE action = 'VAULT_KEY_ROTATE'
      AND after_state->>'old_key_id' = 'mg.vault_key/v1'
      AND after_state->>'new_key_id' = 'mg.vault_key/v2'
  ) THEN
    RAISE EXCEPTION 'rotation audit event missing';
  END IF;
  IF EXISTS (
    SELECT 1 FROM vault.key_registry
    WHERE to_jsonb(vault.key_registry)::text LIKE '%w020-new-key%'
  ) OR EXISTS (
    SELECT 1 FROM core.audit_logs
    WHERE after_state::text LIKE '%w020-new-key%'
  ) THEN
    RAISE EXCEPTION 'secret material was persisted';
  END IF;
END
$test$;

ROLLBACK;

\echo 'W-020 key rotation tests passed'
