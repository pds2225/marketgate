-- ============================================================
-- Payment / credits / subscriptions persistence
-- Render ephemeral disk wipes payments.json + credits.json, so
-- confirm/webhook retries can double-fulfill and balances reset.
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS payment_ledger (
    order_id      text PRIMARY KEY,
    user_id       text NOT NULL,
    product_type  text,
    package       text,
    plan          text,
    amount        integer,
    status        text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payment_ledger_user
    ON payment_ledger (user_id);

CREATE TABLE IF NOT EXISTS credit_accounts (
    user_id    text PRIMARY KEY,
    balance    integer NOT NULL DEFAULT 0,
    history    jsonb NOT NULL DEFAULT '[]'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subscriptions (
    user_id    text PRIMARY KEY,
    plan       text NOT NULL DEFAULT 'Basic',
    started_at timestamptz,
    expires_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
