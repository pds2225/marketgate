-- MarketGate W-020: Vault encryption key metadata + rotation
-- Secret material is never stored in PostgreSQL. provider_ref points to
-- a session/role setting populated by the deployment KMS/Secrets adapter.
BEGIN;

DO $$ BEGIN
  CREATE ROLE mg_vault_key_admin NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
CREATE TABLE vault.key_registry (
  key_id        text PRIMARY KEY,
  provider_ref  text NOT NULL CHECK (provider_ref ~ '^setting:[A-Za-z0-9_.]+$'),
  status        text NOT NULL CHECK (status IN ('ACTIVE','DECRYPT_ONLY','RETIRED')),
  activated_at  timestamptz NOT NULL DEFAULT now(),
  retired_at    timestamptz,
  rotated_by    text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_vault_one_active_key
  ON vault.key_registry ((status))
  WHERE status = 'ACTIVE';

INSERT INTO vault.key_registry
  (key_id, provider_ref, status, rotated_by)
VALUES
  ('mg.vault_key/v1', 'setting:mg.vault_key', 'ACTIVE', '0003-bootstrap');

CREATE FUNCTION vault.active_key_id() RETURNS text
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = vault, pg_temp AS $$
DECLARE v_key_id text;
BEGIN
  SELECT key_id INTO v_key_id
  FROM vault.key_registry
  WHERE status = 'ACTIVE';
  IF v_key_id IS NULL THEN
    RAISE EXCEPTION 'no active vault encryption key';
  END IF;
  RETURN v_key_id;
END
$$;

CREATE FUNCTION vault.key_material(p_key_id text) RETURNS text
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = vault, pg_temp AS $$
DECLARE
  v_provider_ref text;
  v_status text;
  v_setting_name text;
  v_material text;
BEGIN
  SELECT provider_ref, status
  INTO v_provider_ref, v_status
  FROM vault.key_registry
  WHERE key_id = p_key_id;
  IF v_provider_ref IS NULL OR v_status NOT IN ('ACTIVE','DECRYPT_ONLY') THEN
    RAISE EXCEPTION 'vault key % is unavailable', p_key_id;
  END IF;

  v_setting_name := substring(v_provider_ref FROM 9);
  v_material := current_setting(v_setting_name, true);
  IF v_material IS NULL OR v_material = '' THEN
    RAISE EXCEPTION 'vault key material is not configured for %', p_key_id;
  END IF;
  RETURN v_material;
END
$$;

CREATE OR REPLACE FUNCTION vault.enc_key() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = vault, pg_temp AS $$
  SELECT vault.key_material(vault.active_key_id())
$$;

CREATE OR REPLACE FUNCTION vault.fingerprint(p_value text) RETURNS text
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = vault, pg_temp AS $$
DECLARE v_key text;
BEGIN
  v_key := current_setting('mg.vault_fingerprint_key', true);
  IF v_key IS NULL OR v_key = '' THEN
    v_key := current_setting('mg.vault_key', true);
  END IF;
  IF v_key IS NULL OR v_key = '' THEN
    RAISE EXCEPTION 'vault fingerprint key not configured';
  END IF;
  RETURN encode(hmac(lower(trim(p_value)), v_key, 'sha256'), 'hex');
END
$$;

CREATE FUNCTION vault.assign_active_key_id() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = vault, pg_temp AS $$
BEGIN
  NEW.key_id := vault.active_key_id();
  RETURN NEW;
END
$$;

CREATE TRIGGER trg_contacts_vault_active_key
BEFORE INSERT ON vault.contacts_vault
FOR EACH ROW EXECUTE FUNCTION vault.assign_active_key_id();

CREATE FUNCTION broker.rotate_vault_key(
  p_new_key_id text,
  p_provider_ref text,
  p_actor text
) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = vault, core, pg_temp AS $$
DECLARE
  v_old_key_id text;
  v_old_material text;
  v_new_material text;
  v_setting_name text;
  v_rotated integer;
BEGIN
  IF p_new_key_id IS NULL OR trim(p_new_key_id) = '' THEN
    RAISE EXCEPTION 'new key id is required';
  END IF;
  IF p_provider_ref !~ '^setting:[A-Za-z0-9_.]+$' THEN
    RAISE EXCEPTION 'unsupported key provider reference';
  END IF;

  v_setting_name := substring(p_provider_ref FROM 9);
  v_new_material := current_setting(v_setting_name, true);
  IF v_new_material IS NULL OR v_new_material = '' THEN
    RAISE EXCEPTION 'new vault key material is not configured';
  END IF;

  LOCK TABLE vault.key_registry IN EXCLUSIVE MODE;
  LOCK TABLE vault.contacts_vault IN EXCLUSIVE MODE;
  v_old_key_id := vault.active_key_id();
  IF v_old_key_id = p_new_key_id THEN
    RAISE EXCEPTION 'new key id is already active';
  END IF;
  v_old_material := vault.key_material(v_old_key_id);

  UPDATE vault.key_registry
  SET status = 'DECRYPT_ONLY'
  WHERE key_id = v_old_key_id;

  INSERT INTO vault.key_registry
    (key_id, provider_ref, status, rotated_by)
  VALUES
    (p_new_key_id, p_provider_ref, 'ACTIVE', p_actor);

  UPDATE vault.contacts_vault
  SET encrypted_value = pgp_sym_encrypt(
        pgp_sym_decrypt(encrypted_value, v_old_material),
        v_new_material
      ),
      key_id = p_new_key_id,
      updated_at = now()
  WHERE key_id = v_old_key_id;
  GET DIAGNOSTICS v_rotated = ROW_COUNT;

  IF EXISTS (
    SELECT 1 FROM vault.contacts_vault WHERE key_id = v_old_key_id
  ) THEN
    RAISE EXCEPTION 'vault rotation left rows on old key %', v_old_key_id;
  END IF;

  UPDATE vault.key_registry
  SET status = 'RETIRED', retired_at = now(), rotated_by = p_actor
  WHERE key_id = v_old_key_id;

  INSERT INTO core.audit_logs
    (actor, actor_role, action, object_type, object_id, after_state)
  VALUES
    (p_actor, 'vault_key_admin', 'VAULT_KEY_ROTATE', 'vault_key',
     p_new_key_id,
     jsonb_build_object(
       'old_key_id', v_old_key_id,
       'new_key_id', p_new_key_id,
       'provider_ref', p_provider_ref,
       'rotated_contacts', v_rotated
     ));
  RETURN v_rotated;
END
$$;

REVOKE ALL ON TABLE vault.key_registry
  FROM PUBLIC, mg_app, mg_vault_broker;
REVOKE ALL ON FUNCTION vault.active_key_id()
  FROM PUBLIC, mg_app, mg_vault_broker;
REVOKE ALL ON FUNCTION vault.key_material(text)
  FROM PUBLIC, mg_app, mg_vault_broker;
REVOKE ALL ON FUNCTION vault.assign_active_key_id()
  FROM PUBLIC, mg_app, mg_vault_broker;
REVOKE ALL ON FUNCTION broker.rotate_vault_key(text, text, text)
  FROM PUBLIC, mg_app, mg_vault_broker;
GRANT USAGE ON SCHEMA broker TO mg_vault_key_admin;
GRANT EXECUTE ON FUNCTION broker.rotate_vault_key(text, text, text)
  TO mg_vault_key_admin;

COMMIT;
