/**
 * 토스 PG checkout 헬퍼 — 실결제 키는 서버 env.
 * paymentConfig.mode === 'toss' 일 때 CreditTopUp / Pricing 에서 사용.
 */
import api from './api.js'

/**
 * @returns {Promise<{ ok: true, checkout_url: string, data: object } | { ok: false, reason: string, data?: object }>}
 */
export async function startTossCheckout({ product_type, package: pkg, plan }) {
  const payload =
    product_type === 'credit'
      ? { product_type, package: pkg }
      : { product_type, plan }

  const { data } = await api.post('/v1/payment/checkout', payload)

  if (!data?.ready) {
    return {
      ok: false,
      reason: data?.message || 'toss_not_ready',
      data,
    }
  }

  const url = data.checkout_url
  if (!url || typeof url !== 'string') {
    return { ok: false, reason: 'missing_checkout_url', data }
  }

  return { ok: true, checkout_url: url, data }
}

/** 서버에 토스 키가 준비됐는지 조회 (선택). */
export async function fetchPaymentProvider() {
  try {
    const { data } = await api.get('/v1/payment/provider')
    return data
  } catch {
    return { provider: 'toss', ready: false }
  }
}
