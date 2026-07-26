/**
 * 결제 제공자 전환 설정.
 * - sim: 파일럿 충전(서버 charge / 로컬) — 기본값
 * - toss: /v1/payment/checkout → 토스 PG (키·웹훅은 서버 env)
 *
 * 실결제 붙일 때: mode 를 'toss' 로 바꾸고
 * 서버에 TOSS_CLIENT_KEY, TOSS_SECRET_KEY(확인용), TOSS_WEBHOOK_SECRET, BASE_URL 설정.
 */
export const paymentConfig = {
  mode: 'sim', // 'sim' | 'toss'
  provider: 'toss',
  currency: 'KRW',
  /** 토스 결제위젯/SDK 붙일 때 프론트에서 참조 (실키는 서버 checkout 응답의 client_key 사용) */
  toss: {
    // 공개 클라이언트 키는 서버 checkout 이 내려줌. 여기엔 플레이스홀더만.
    clientKeyEnvHint: 'TOSS_CLIENT_KEY',
    successPath: '/payment/callback',
    failPath: '/payment/callback?status=fail',
  },
}

export function isTossPaymentEnabled() {
  return paymentConfig.mode === 'toss'
}
