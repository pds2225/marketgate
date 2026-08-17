import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  mapApiBuyersToViewModels,
  deriveContactStatus,
  deriveTradeStatus,
  deriveCreditStatus,
  groupBuyersByCountry,
  resolveBuyerCountryIso3,
  mapCompanyVerificationResponse,
  COMPANY_VERIFICATION_INTRO,
  EXTERNAL_CREDIT_LOOKUP_LINKS,
  CONTACT_STATUS_LABELS,
} from '../src/pages/BuyerSearch/buyerViewModel.js';

const API_ITEMS = [
  {
    buyer_name: 'acme trading gmbh',
    source_dataset: 'kotra_trade_leads',
    country_norm: 'germany',
    has_contact: true,
    contact_email: 'buy@acme.de',
    contact_email_estimated: false,
    contact_phone: '+49-40-000',
    contact_website: 'acme.de',
    final_score: 91.2,
    source_verification: 'verified',
    score_breakdown: { trade_history_score: 0.8, growth_score: 0.7 },
    recommendation_lines: ['테스트 사유'],
    matched_terms: ['skincare'],
  },
  {
    buyer_name: 'no contact ltd',
    source_dataset: 'sns_scrape',
    country_norm: 'vietnam',
    has_contact: false,
    contact_email: '',
    final_score: 55,
    source_verification: 'unverified',
  },
];

test('작업1: 원본에 없는 수입이력·수입액·성장률·RFM·갱신일은 전부 null', () => {
  const [buyer] = mapApiBuyersToViewModels(API_ITEMS, '330499', 'K-뷰티');
  assert.equal(buyer.importHistory, null);
  assert.equal(buyer.totalImportValue, null);
  assert.equal(buyer.importGrowthRate, null);
  assert.equal(buyer.rfm, null);
  assert.equal(buyer.lastUpdatedDays, null);
  assert.equal(buyer.dataDate, null); // 오늘 날짜 수집일 생성 금지
});

test('작업1: final_score 기반 임의 수입액($M 파생값)을 만들지 않는다', () => {
  const buyers = mapApiBuyersToViewModels(API_ITEMS, '330499', 'K-뷰티');
  for (const buyer of buyers) {
    assert.equal(buyer.totalImportValue, null);
    const serialized = JSON.stringify(buyer);
    assert.ok(!/\$\d+(\.\d+)?M/.test(serialized), 'no fabricated $xM values');
  }
});

test('작업2: contact/trade/credit 상태 분리 — has_contact 만으로 검증완료 표시 금지', () => {
  const [withContact, noContact] = mapApiBuyersToViewModels(API_ITEMS, '330499', 'K-뷰티');
  assert.equal(withContact.contactStatus, 'format_validated'); // 형식만 통과 — 소유 검증 아님
  assert.equal(withContact.tradeStatus, 'source_confirmed');
  assert.equal(withContact.creditStatus, 'not_requested');
  assert.equal(noContact.contactStatus, 'unavailable');
  assert.equal(noContact.tradeStatus, 'unavailable');
  assert.equal(noContact.creditStatus, 'not_requested');
});

test('작업2: 검증 절차 없는 상태값(format_validated/ownership_verified)은 부여하지 않는다', () => {
  assert.equal(deriveContactStatus({ has_contact: true }), 'discovered');
  assert.equal(deriveContactStatus({ has_contact: false }), 'unavailable');
  assert.equal(deriveTradeStatus({ source_verification: 'unverified' }), 'unavailable');
  assert.equal(deriveCreditStatus({}), 'not_requested');
});

test('L010: 추정(estimated) 연락처는 형식이 맞아도 format_validated 로 승격하지 않는다', () => {
  assert.equal(
    deriveContactStatus({
      has_contact: true,
      contact_email: 'guess@acme.de',
      contact_email_estimated: true,
    }),
    'discovered'
  );
  // 추정 이메일 + 형식 통과 전화번호 조합도 승격 금지
  assert.equal(
    deriveContactStatus({
      has_contact: true,
      contact_email: 'guess@acme.de',
      contact_phone: '+49-40-1234567',
      contact_email_estimated: true,
    }),
    'discovered'
  );
});

test('L010: 형식 미통과(이메일 형식 오류 + 전화 8자리 미만)는 discovered 유지', () => {
  assert.equal(
    deriveContactStatus({
      has_contact: true,
      contact_email: 'not-an-email',
      contact_phone: '1234567',
      contact_email_estimated: false,
    }),
    'discovered'
  );
});

test('L010: 원본(CSV/API) 필드만으로는 ownership_verified 를 부여하지 않는다', () => {
  const RAW_INPUTS = [
    ...API_ITEMS,
    { has_contact: true, contact_email: 'buy@acme.de', contact_email_estimated: false },
    { has_contact: true, contact_phone: '+49-40-1234567' },
    { has_contact: true, contact_email: 'guess@acme.de', contact_email_estimated: true },
    // 원본이 검증됨을 자칭해도 무시한다 — 소유 확인 절차는 존재하지 않는다
    { has_contact: true, ownership_verified: true, contact_verified: true, verified: true },
    { has_contact: false },
    {},
  ];
  const ALLOWED = ['unavailable', 'discovered', 'format_validated'];
  for (const item of RAW_INPUTS) {
    const status = deriveContactStatus(item);
    assert.notEqual(status, 'ownership_verified', `ownership_verified 금지: ${JSON.stringify(item)}`);
    assert.ok(ALLOWED.includes(status), `허용되지 않은 상태 ${status}: ${JSON.stringify(item)}`);
  }
  for (const buyer of mapApiBuyersToViewModels(API_ITEMS, '330499', 'K-뷰티')) {
    assert.notEqual(buyer.contactStatus, 'ownership_verified');
  }
});

test('L010: has_contact 만으로는 소유검증(검증 완료) 라벨이 노출되지 않는다', () => {
  const status = deriveContactStatus({ has_contact: true });
  assert.equal(status, 'discovered');
  assert.equal(CONTACT_STATUS_LABELS[status], '연락처 보유(미검증)');
  assert.notEqual(CONTACT_STATUS_LABELS[status], CONTACT_STATUS_LABELS.ownership_verified);
  // format_validated 라벨도 '소유 검증'을 주장하지 않는다
  assert.equal(CONTACT_STATUS_LABELS.format_validated, '형식 검증됨');
});

test('결정성: 동일 입력 10회 조회 → 결과 동일 (Math.random 제거 검증)', () => {
  const first = JSON.stringify(mapApiBuyersToViewModels(API_ITEMS, '330499', 'K-뷰티'));
  for (let i = 0; i < 10; i++) {
    const run = JSON.stringify(mapApiBuyersToViewModels(API_ITEMS, '330499', 'K-뷰티'));
    assert.equal(run, first, `run ${i + 1} differs`);
  }
});

test('국가 그룹핑은 실측값(건수·평균점수·연락처 보유 수)만 집계한다', () => {
  const buyers = mapApiBuyersToViewModels(API_ITEMS, '330499', 'K-뷰티');
  const groups = groupBuyersByCountry(buyers);
  assert.equal(groups.length, 2);
  const de = groups.find((g) => g.countryName === '독일');
  assert.equal(de.buyerCount, 1);
  assert.equal(de.contactableCount, 1);
  assert.equal(de.avgScore, 91);
  assert.ok(!('totalImportValue' in de), 'no fabricated country import totals');
  assert.ok(!('avgGrowthRate' in de), 'no fabricated growth rates');
});

test('L029: countryIso3 comes from API ISO3 fields, not display country label', () => {
  const withIso = mapApiBuyersToViewModels(
    [{ ...API_ITEMS[0], source_target_country_iso3: 'DEU' }],
    '330499',
    'K-뷰티',
  )[0];
  assert.equal(withIso.countryIso3, 'DEU');
  assert.equal(resolveBuyerCountryIso3(withIso), 'DEU');

  const fromCountryIso3 = mapApiBuyersToViewModels(
    [{ ...API_ITEMS[1], country_iso3: 'vnm' }],
    '330499',
    'K-뷰티',
  )[0];
  assert.equal(fromCountryIso3.countryIso3, 'VNM');

  const [noIso] = mapApiBuyersToViewModels(API_ITEMS, '330499', 'K-뷰티');
  assert.equal(noIso.countryIso3, '');
  assert.equal(resolveBuyerCountryIso3(noIso), '');
  // Display label must not be treated as ISO3 (would 422 against CV-02)
  assert.notEqual(resolveBuyerCountryIso3({ country: noIso.country }), 'GERMANY');
});

test('L029: mapCompanyVerificationResponse aligns CV-02 API → CV-03 UI fields', () => {
  const view = mapCompanyVerificationResponse({
    verification_id: 'x',
    company_name: 'Acme',
    country_iso3: 'USA',
    registry_check_status: 'BASIC_CONFIRMED',
    result_json: { provider: 'opencorporates', match_status: 'BASIC_CONFIRMED', mock: true },
    provider: 'opencorporates',
    requested_at: '2026-01-01T00:00:00+00:00',
    completed_at: '2026-01-01T01:00:00+00:00',
  });
  assert.equal(view.status, 'BASIC_CONFIRMED');
  assert.equal(view.country, 'USA');
  assert.equal(view.verified_at, '2026-01-01T01:00:00+00:00');
  assert.equal(view.company_name, 'Acme');
  assert.match(view.details, /opencorporates/);
  assert.match(view.details, /자동 신용등급 조회 아님/);
  assert.equal(view.status && view.country && view.verified_at ? 'ok' : 'broken', 'ok');
});

test('MG-003: unknown registry status maps to 확인 결과 없음 (no fake grade)', () => {
  const view = mapCompanyVerificationResponse({
    company_name: 'Ghost',
    country_iso3: 'USA',
    registry_check_status: 'VERIFIED', // legacy enum — must not pass through
    result_json: { provider: 'opencorporates', mock: true },
  });
  assert.equal(view.status, null);
  assert.equal(view.details, '확인 결과 없음');
  assert.ok(!('contactStatus' in view));
  assert.ok(!('creditStatus' in view));
});

test('MG-003: D&B/K-SURE are external lookup links only — no auto credit claim in intro', () => {
  assert.match(COMPANY_VERIFICATION_INTRO, /자동 조회하지 않/);
  assert.doesNotMatch(COMPANY_VERIFICATION_INTRO, /데이터 소스를 참조/);
  assert.deepEqual(
    EXTERNAL_CREDIT_LOOKUP_LINKS.map((l) => l.label),
    ['D&B', 'K-SURE'],
  );
  for (const link of EXTERNAL_CREDIT_LOOKUP_LINKS) {
    assert.match(link.href, /^https:\/\//);
  }
});
