/**
 * 크레딧 단가·충전 패키지 단일 설정.
 * unlockCost / packages 숫자만 바꾸면 UI·차감·표시가 따라간다.
 */
export const creditConfig = {
  unlockCost: 5,
  currency: 'KRW',
  startingBalance: 100,
  packages: [
    { id: 'small', name: '소형', credits: 10, price: 20000, active: true },
    { id: 'medium', name: '중형', credits: 30, price: 54000, active: true },
    { id: 'large', name: '대형', credits: 100, price: 160000, active: true },
  ],
}

export function activePackages() {
  return (creditConfig.packages || []).filter((p) => p.active !== false)
}

/** 패키지 크레딧으로 대략 몇 건 언락 가능한지 (표시용) */
export function approxUnlockCount(credits) {
  const cost = Math.max(1, Number(creditConfig.unlockCost) || 1)
  return Math.floor(Number(credits || 0) / cost)
}

export function formatPrice(price) {
  return `${Number(price || 0).toLocaleString('ko-KR')}원`
}
