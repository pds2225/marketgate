/**
 * 수출 수익성 계산 (P0 정상식).
 *
 * 총매출   = 판매단가 × 수량
 * 제품원가 = 개당 원가 × 수량
 * 총비용   = 제품원가 + 국제물류비 + 보험료 + 관세 + 통관비 + 결제수수료 + 기타비용
 * 순이익   = 총매출 − 총비용
 * 순이익률 = 순이익 ÷ 총매출 × 100
 *
 * 관세·결제수수료는 총매출(FOB 금액) 기준 요율(%)로 계산한다.
 * 순수 함수 — 동일 입력은 항상 동일 결과를 반환한다.
 */
export function computeProfitability({
  unitPrice = 0,
  quantity = 0,
  unitCost = 0,
  logisticsCost = 0,
  insuranceCost = 0,
  tariffRate = 0,
  customsFee = 0,
  paymentFeeRate = 0,
  otherCost = 0,
} = {}) {
  const revenue = unitPrice * quantity;
  const productCost = unitCost * quantity;
  const tariff = revenue * (tariffRate / 100);
  const paymentFee = revenue * (paymentFeeRate / 100);
  const totalCost =
    productCost + logisticsCost + insuranceCost + tariff + customsFee + paymentFee + otherCost;
  const profit = revenue - totalCost;
  const profitRate = revenue > 0 ? (profit / revenue) * 100 : 0;
  return { revenue, productCost, tariff, paymentFee, totalCost, profit, profitRate };
}
