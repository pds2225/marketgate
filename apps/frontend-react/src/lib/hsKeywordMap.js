/**
 * 제품 키워드 → 카테고리/HS 매핑 (프론트 공유).
 * 보유 카테고리·키워드만 사용 — 외부 스크래핑 없음.
 */
export const CATEGORY_HS = {
  'K-뷰티': { hsCode: '330499', hsLabel: '스킨케어' },
  '건강식품': { hsCode: '210690', hsLabel: '건강기능식품' },
  'K-패션': { hsCode: '620343', hsLabel: '여성 의류' },
  '반도체': { hsCode: '854140', hsLabel: '반도체 소자' },
}

/** 키워드(정규화) → 카테고리 라벨 */
export const KEYWORD_TO_CATEGORY = {
  'k-뷰티': 'K-뷰티',
  k뷰티: 'K-뷰티',
  뷰티: 'K-뷰티',
  화장품: 'K-뷰티',
  스킨: 'K-뷰티',
  스킨케어: 'K-뷰티',
  세럼: 'K-뷰티',
  앰플: 'K-뷰티',
  토너: 'K-뷰티',
  크림: 'K-뷰티',
  로션: 'K-뷰티',
  마스크팩: 'K-뷰티',
  선크림: 'K-뷰티',
  메이크업: 'K-뷰티',
  립스틱: 'K-뷰티',
  쿠션: 'K-뷰티',
  클렌징: 'K-뷰티',
  에센스: 'K-뷰티',
  파운데이션: 'K-뷰티',
  아이크림: 'K-뷰티',
  미스트: 'K-뷰티',
  비누: 'K-뷰티',
  샴푸: 'K-뷰티',
  beauty: 'K-뷰티',
  cosme: 'K-뷰티',
  skincare: 'K-뷰티',
  cosmetic: 'K-뷰티',
  sunscreen: 'K-뷰티',
  건강: '건강식품',
  건강식품: '건강식품',
  홍삼: '건강식품',
  인삼: '건강식품',
  프로바이오틱스: '건강식품',
  건기식: '건강식품',
  영양제: '건강식품',
  비타민: '건강식품',
  콜라겐: '건강식품',
  유산균: '건강식품',
  오메가: '건강식품',
  단백질: '건강식품',
  효소: '건강식품',
  차: '건강식품',
  tea: '건강식품',
  health: '건강식품',
  supplement: '건강식품',
  probiotic: '건강식품',
  패션: 'K-패션',
  'k-패션': 'K-패션',
  k패션: 'K-패션',
  의류: 'K-패션',
  옷: 'K-패션',
  한복: 'K-패션',
  디자이너: 'K-패션',
  니트: 'K-패션',
  원피스: 'K-패션',
  재킷: 'K-패션',
  자켓: 'K-패션',
  청바지: 'K-패션',
  가방: 'K-패션',
  apparel: 'K-패션',
  fashion: 'K-패션',
  garment: 'K-패션',
  반도체: '반도체',
  칩: '반도체',
  메모리: '반도체',
  전자: '반도체',
  웨이퍼: '반도체',
  ic: '반도체',
  led: '반도체',
  semiconductor: '반도체',
  chip: '반도체',
  memory: '반도체',
}

function normalize(input) {
  return String(input || '')
    .toLowerCase()
    .replace(/[\s\-_]/g, '')
}

/**
 * @returns {{ category: string, hsCode: string, hsLabel: string, matchedKeyword?: string } | null}
 */
export function resolveProductToHs(input) {
  const raw = String(input || '').trim()
  if (!raw) return null

  const six = raw.match(/\b(\d{6})\b/)
  if (six) {
    const hs = six[1]
    if (hs.startsWith('33')) return { category: 'K-뷰티', hsCode: hs, hsLabel: '스킨케어', matchedKeyword: hs }
    if (hs.startsWith('21')) return { category: '건강식품', hsCode: hs, hsLabel: '건강기능식품', matchedKeyword: hs }
    if (hs.startsWith('62') || hs.startsWith('61')) return { category: 'K-패션', hsCode: hs, hsLabel: '여성 의류', matchedKeyword: hs }
    if (hs.startsWith('85')) return { category: '반도체', hsCode: hs, hsLabel: '반도체 소자', matchedKeyword: hs }
    return { category: hs, hsCode: hs, hsLabel: '수출품목', matchedKeyword: hs }
  }

  const lower = normalize(raw)
  for (const [keyword, category] of Object.entries(KEYWORD_TO_CATEGORY)) {
    if (lower.includes(normalize(keyword))) {
      const meta = CATEGORY_HS[category]
      return {
        category,
        hsCode: meta.hsCode,
        hsLabel: meta.hsLabel,
        matchedKeyword: keyword,
      }
    }
  }

  if (raw.startsWith('33')) return { category: 'K-뷰티', ...CATEGORY_HS['K-뷰티'], matchedKeyword: raw }
  if (raw.startsWith('21')) return { category: '건강식품', ...CATEGORY_HS['건강식품'], matchedKeyword: raw }
  if (raw.startsWith('62') || raw.startsWith('61')) return { category: 'K-패션', ...CATEGORY_HS['K-패션'], matchedKeyword: raw }
  if (raw.startsWith('85')) return { category: '반도체', ...CATEGORY_HS['반도체'], matchedKeyword: raw }

  return null
}

export function detectCategory(input) {
  const resolved = resolveProductToHs(input)
  return resolved?.category || null
}
