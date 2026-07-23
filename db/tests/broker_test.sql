-- W-019 Vault Access Broker 검증 스위트
\set ON_ERROR_STOP off

-- 기본 픽스처 (프레시 DB용)
INSERT INTO core.source_registry (source_id, source_name) VALUES ('test_src', '기본 거부 정책 소스') ON CONFLICT DO NOTHING;
INSERT INTO core.buyers (buyer_id, display_name, normalized_name, country_iso3)
VALUES ('11111111-1111-1111-1111-111111111111', 'Test Buyer', 'test buyer', 'USA') ON CONFLICT DO NOTHING;

-- 픽스처: 발송 허용 소스 + 발송 가능 캠페인 + 초안 캠페인
INSERT INTO core.source_registry (source_id, source_name, rights_code, policy)
VALUES ('rfq_inbound_test', 'RFQ 인바운드(테스트)', 'CONSENTED_INBOUND',
        '{"store_core":true,"store_contact":true,"use_for_scoring":true,"show_company_to_customer":true,"send_outreach":true,"commercialize_derived_output":"allowed"}')
ON CONFLICT (source_id) DO NOTHING;

INSERT INTO core.campaigns (campaign_id, seller_tenant_id, name, status)
VALUES ('aaaaaaaa-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222', '테스트 캠페인(QUEUED)', 'QUEUED'),
       ('aaaaaaaa-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', '테스트 캠페인(DRAFT)', 'DRAFT')
ON CONFLICT DO NOTHING;

\echo '=== T1: store_contact — 정책상 저장 금지 소스(test_src, default-deny) → 예외 기대 ==='
SELECT broker.store_contact('11111111-1111-1111-1111-111111111111', 'EMAIL',
  'buyer@example.com', 'test_src', 'OPTED_IN', 'inbound_form', 'US', 'tester');

\echo '=== T2: store_contact — 허용 소스(rfq_inbound_test) → 성공 기대 ==='
SELECT broker.store_contact('11111111-1111-1111-1111-111111111111', 'EMAIL',
  'buyer@example.com', 'rfq_inbound_test', 'OPTED_IN', 'inbound_form', 'US', 'tester') AS contact_id \gset
\echo contact_id: :'contact_id'

\echo '=== T3: resolve — QUEUED 캠페인 + OPTED_IN → 평문 반환 기대 ==='
SELECT broker.resolve_contact_for_send(:'contact_id', 'aaaaaaaa-0000-0000-0000-000000000001', 'send_worker') AS resolved;

\echo '=== T4: resolve — DRAFT 캠페인 → NULL 반환(거부) 기대 ==='
SELECT broker.resolve_contact_for_send(:'contact_id', 'aaaaaaaa-0000-0000-0000-000000000002', 'send_worker') IS NULL AS denied_as_null;

\echo '=== T5: suppress 후 resolve → NULL 반환(거부) 기대 ==='
SELECT broker.suppress_contact(:'contact_id', 'unsubscribe', 'webhook');
SELECT broker.resolve_contact_for_send(:'contact_id', 'aaaaaaaa-0000-0000-0000-000000000001', 'send_worker') IS NULL AS denied_as_null;

\echo '=== T6: mg_app 롤 — vault 테이블 직접 조회 → 거부 / Broker 함수 경유 → 정상 동작 기대 ==='
SET ROLE mg_app;
SELECT count(*) FROM vault.contacts_vault;
SELECT broker.store_contact('11111111-1111-1111-1111-111111111111', 'EMAIL',
  'buyer2@example.com', 'rfq_inbound_test', 'OPTED_IN', 'inbound_form', 'US', 'mg_app_user') AS app_contact \gset
SELECT left(broker.resolve_contact_for_send(:'app_contact', 'aaaaaaaa-0000-0000-0000-000000000001', 'mg_app_user'), 6) AS resolved_prefix;
RESET ROLE;

\echo '=== T7: 감사 로그 — Broker 접근 전수 기록 확인 ==='
SELECT action, count(*) FROM core.audit_logs WHERE actor_role = 'vault_broker' GROUP BY action ORDER BY action;
