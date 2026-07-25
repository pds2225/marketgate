import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeProfitability } from '../src/lib/profitability.js';

const BASE_INPUT = {
  unitPrice: 100,
  quantity: 1000,
  unitCost: 60,
  logisticsCost: 2500,
  insuranceCost: 300,
  tariffRate: 8,
  customsFee: 200,
  paymentFeeRate: 2.5,
  otherCost: 500,
};

test('정상식: 제품원가·보험·관세·통관비·결제수수료·기타비용을 모두 포함한다', () => {
  const r = computeProfitability(BASE_INPUT);
  assert.equal(r.revenue, 100_000); // 100 × 1,000
  assert.equal(r.productCost, 60_000); // 60 × 1,000
  assert.equal(r.tariff, 8_000); // 100,000 × 8%
  assert.equal(r.paymentFee, 2_500); // 100,000 × 2.5%
  // 60,000 + 2,500 + 300 + 8,000 + 200 + 2,500 + 500
  assert.equal(r.totalCost, 74_000);
  assert.equal(r.profit, 26_000);
  assert.equal(r.profitRate, 26);
});

test('기존식(제품원가·결제수수료 누락)은 이익을 과대계상한다 — 회귀 방지 비교', () => {
  // 기존 ExportFlowPage 계산: totalCost = 물류비 + 관세 + 기타비용 (원가·수수료·보험·통관비 없음)
  const legacyTotalCost =
    BASE_INPUT.logisticsCost +
    BASE_INPUT.unitPrice * BASE_INPUT.quantity * (BASE_INPUT.tariffRate / 100) +
    BASE_INPUT.otherCost;
  const legacyProfit = BASE_INPUT.unitPrice * BASE_INPUT.quantity - legacyTotalCost;

  const corrected = computeProfitability(BASE_INPUT);
  assert.equal(legacyProfit, 89_000); // 과대계상된 이익
  assert.equal(corrected.profit, 26_000); // 정상 이익
  assert.ok(
    legacyProfit - corrected.profit === 63_000,
    '기존식은 제품원가 60,000 + 결제수수료 2,500 + 보험 300 + 통관비 200 = 63,000 USD 만큼 과대계상'
  );
});

test('매출 0이면 순이익률은 0 (0 나눗셈 방지)', () => {
  const r = computeProfitability({ ...BASE_INPUT, quantity: 0 });
  assert.equal(r.revenue, 0);
  assert.equal(r.profitRate, 0);
});

test('적자 구조가 그대로 드러난다 (원가 > 단가)', () => {
  const r = computeProfitability({ ...BASE_INPUT, unitCost: 120 });
  assert.ok(r.profit < 0);
  assert.ok(r.profitRate < 0);
});

test('결정성: 동일 입력 10회 → 결과 동일', () => {
  const first = computeProfitability(BASE_INPUT);
  for (let i = 0; i < 10; i++) {
    assert.deepEqual(computeProfitability(BASE_INPUT), first);
  }
});
