/**
 * API 바이어 응답 → 화면 뷰모델 변환 (P0).
 *
 * 데이터 정책: API·CSV 원본에 없는 값은 생성하지 않는다.
 * - 수입이력·수입액·성장률·RFM·갱신일은 원본에 없으므로 전부 null.
 * - 화면은 null 을 '자료 내 확인 불가'로 표시한다.
 * - 검증 상태는 contact/trade/credit 3개 축으로 분리해 관리한다.
 * 순수 함수 — 동일 입력은 항상 동일 결과 (Math.random / Date 사용 금지).
 */

export const COUNTRY_NAME_MAP = {
  de: '독일', nl: '네덜란드', cn: '중국', us: '미국', jp: '일본', fr: '프랑스',
  tw: '대만', vn: '베트남', gb: '영국', au: '호주', ca: '캐나다', in: '인도',
  id: '인도네시아', my: '말레이시아', ph: '필리핀', sg: '싱가포르', th: '태국',
  kr: '한국', it: '이탈리아', es: '스페인', mx: '멕시코', br: '브라질',
  germany: '독일', netherlands: '네덜란드', china: '중국', usa: '미국',
  japan: '일본', france: '프랑스', taiwan: '대만', vietnam: '베트남',
};

export const CONTACT_STATUS_LABELS = {
  unavailable: '연락처 없음',
  discovered: '연락처 보유(미검증)',
  format_validated: '형식 검증됨',
  ownership_verified: '소유 검증됨',
};

export const TRADE_STATUS_LABELS = {
  unavailable: '수입실적 자료 내 확인 불가',
  source_confirmed: '출처 확인됨',
  recent_activity_confirmed: '최근 활동 확인됨',
};

export const CREDIT_STATUS_LABELS = {
  not_requested: '신용조사 미신청',
  pending: '신용조사 진행 중',
  report_received: '신용보고서 수신',
  expired: '신용보고서 만료',
};

/**
 * 연락처 상태: 보유 여부만 원본에서 확인 가능하다.
 * format_validated / ownership_verified 는 검증 절차 도입 전까지 부여하지 않는다.
 */
export function deriveContactStatus(item) {
  return item?.has_contact ? 'discovered' : 'unavailable';
}

/**
 * 거래(출처) 상태: 백엔드가 계산한 source_verification(verified/unverified)만 사용.
 * 수입실적 데이터 자체는 원본에 없으므로 recent_activity_confirmed 는 부여하지 않는다.
 */
export function deriveTradeStatus(item) {
  return item?.source_verification === 'verified' ? 'source_confirmed' : 'unavailable';
}

/** 신용 상태: 신용조사 연동 전 — 항상 미신청. */
export function deriveCreditStatus() {
  return 'not_requested';
}

function buildMetrics(scoreBreakdown) {
  if (!scoreBreakdown || typeof scoreBreakdown !== 'object') return null;
  const defs = [
    { key: 'trade_history_score', label: '수입 이력 매칭' },
    { key: 'growth_score', label: '시장 성장률' },
    { key: 'gdp_score', label: 'GDP 규모' },
    { key: 'distance_score', label: '거리/물류 이점' },
  ];
  const metrics = defs
    .filter(({ key }) => typeof scoreBreakdown[key] === 'number')
    .map(({ key, label }) => ({
      label,
      value: Math.round(scoreBreakdown[key] * 100),
    }));
  return metrics.length > 0 ? metrics : null;
}

export function mapApiBuyerToViewModel(item, index, hsCode, categoryLabel) {
  const countryCode = String(
    item.country_norm || item.source_target_country_iso3 || 'unknown'
  ).toLowerCase();
  const countryName =
    COUNTRY_NAME_MAP[countryCode] || item.source_target_country_name || countryCode;
  const email = item.contact_email || '';

  return {
    id: `MG-${hsCode}-${index + 1}`,
    rank: index + 1,
    name: item.buyer_name || '이름 미확인',
    legalName: (item.buyer_name || '').toLowerCase(),
    industry: item.source_dataset || '유통/바이어',
    country: `${countryCode} ${countryName}`,
    region: item.source_target_country_name || countryName,
    dataSource: item.source_dataset || '출처 미상',
    // 원본에 수집일이 없으므로 생성하지 않는다 (기존: 오늘 날짜를 수집일로 표기)
    dataDate: null,
    csvTrace: item.source_dataset ? `${item.source_dataset}.csv` : null,
    contactName: item.contact_name || '',
    email,
    phone: item.contact_phone || '',
    website: item.contact_website || '',
    // 검증 상태 3축 분리 — has_contact 만으로 '검증 완료'를 표시하지 않는다
    contactStatus: deriveContactStatus(item),
    tradeStatus: deriveTradeStatus(item),
    creditStatus: deriveCreditStatus(item),
    emailEstimated: !!item.contact_email_estimated,
    sourceVerification: item.source_verification || 'unknown',
    score: Math.round(item.final_score ?? 0),
    scoreLabel:
      (item.final_score ?? 0) >= 90 ? '매우 적합' : (item.final_score ?? 0) >= 80 ? '적합' : '보통',
    metrics: buildMetrics(item.score_breakdown),
    hsCode,
    hsLabel: categoryLabel,
    keywords: item.matched_terms || [],
    matchedBy: item.matched_by || '',
    reasons: (() => {
      const lines = [...(item.recommendation_lines || item.explanation_reasons || [])]
        .map((text) => String(text || '').trim())
        .filter(Boolean);
      if (item.matched_by) lines.push(`매칭 방식: ${item.matched_by}`);
      if (Array.isArray(item.matched_terms) && item.matched_terms.length) {
        lines.push(`매칭 키워드: ${item.matched_terms.join(', ')}`);
      }
      if (item.source_dataset) lines.push(`출처 데이터셋: ${item.source_dataset}`);
      // 중복 제거(동일 문장)
      const seen = new Set();
      return lines
        .filter((text) => {
          if (seen.has(text)) return false;
          seen.add(text);
          return true;
        })
        .map((text) => ({
          text,
          source: item.source_dataset || '출처 미상',
        }));
    })(),
    // 원본에 없는 값 — 전부 null ('자료 내 확인 불가'로 렌더링)
    importHistory: null,
    totalImportValue: null,
    importGrowthRate: null,
    rfm: null,
    lastUpdatedDays: null,
  };
}

export function mapApiBuyersToViewModels(items, hsCode, categoryLabel) {
  return (items || []).map((item, index) =>
    mapApiBuyerToViewModel(item, index, hsCode, categoryLabel)
  );
}

/** 국가별 그룹핑 — 실측 가능한 값(건수·평균점수·연락처 보유 수)만 집계한다. */
export function groupBuyersByCountry(buyers) {
  const groups = new Map();
  for (const buyer of buyers) {
    const code = buyer.country.split(' ')[0];
    const name = buyer.country.split(' ').slice(1).join(' ');
    const key = `${code}|${name}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(buyer);
  }
  const flagMap = { de: '🇩🇪', nl: '🇳🇱', cn: '🇨🇳', us: '🇺🇸', jp: '🇯🇵', fr: '🇫🇷', tw: '🇹🇼', vn: '🇻🇳' };
  const result = [];
  for (const [key, list] of groups.entries()) {
    const [code, name] = key.split('|');
    const sorted = [...list].sort((a, b) => b.score - a.score);
    result.push({
      countryName: name,
      countryCode: code,
      flag: flagMap[code] || '🌐',
      buyerCount: list.length,
      avgScore: Math.round(list.reduce((sum, b) => sum + b.score, 0) / list.length),
      contactableCount: list.filter((b) => b.contactStatus !== 'unavailable').length,
      topBuyerName: sorted[0].name,
      topBuyerScore: sorted[0].score,
      buyers: sorted,
    });
  }
  return result.sort((a, b) => b.avgScore - a.avgScore);
}
