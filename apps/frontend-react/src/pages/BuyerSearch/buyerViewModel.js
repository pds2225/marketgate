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

/** 이메일 형식(소유 확인 아님). */
export function isEmailFormatValid(email) {
  const text = String(email || '').trim()
  if (!text) return false
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)
}

/** 전화 형식(소유 확인 아님) — 숫자 8자리 이상. */
export function isPhoneFormatValid(phone) {
  const digits = String(phone || '').replace(/\D/g, '')
  return digits.length >= 8
}

/**
 * 연락처 상태:
 * - unavailable: 없음
 * - discovered: 보유(형식 미통과·추정 등)
 * - format_validated: 이메일/전화 형식이 통과 (소유 검증 아님)
 * - ownership_verified: 별도 소유 확인 절차 전까지 부여하지 않음
 */
export function deriveContactStatus(item) {
  if (!item?.has_contact) return 'unavailable'
  const emailOk = isEmailFormatValid(item.contact_email)
  const phoneOk = isPhoneFormatValid(item.contact_phone)
  if ((emailOk || phoneOk) && !item.contact_email_estimated) {
    return 'format_validated'
  }
  return 'discovered'
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

  const countryIso3 = String(
    item.source_target_country_iso3 || item.country_iso3 || ''
  )
    .trim()
    .toUpperCase();

  return {
    id: `MG-${hsCode}-${index + 1}`,
    rank: index + 1,
    name: item.buyer_name || '이름 미확인',
    legalName: (item.buyer_name || '').toLowerCase(),
    industry: item.source_dataset || '유통/바이어',
    country: `${countryCode} ${countryName}`,
    // CV API requires ISO3; display `country` is a label (norm/name), not the code.
    countryIso3: /^[A-Z]{3}$/.test(countryIso3) ? countryIso3 : '',
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
    hsCode: item.hs_code_norm || hsCode,
    hsLabel: categoryLabel,
    keywords: item.matched_terms?.length
      ? item.matched_terms
      : String(item.keywords_norm || '')
          .split('|')
          .map((part) => part.trim())
          .filter((part) => part && part.toLowerCase() !== 'none'),
    matchedBy: item.matched_by || '',
    decision: item.decision || '',
    buyerHsCode: item.hs_code_norm || '',
    keywordsRaw: item.keywords_norm || '',
    reasons: (() => {
      const lines = [...(item.recommendation_lines || item.explanation_reasons || [])]
        .map((text) => String(text || '').trim())
        .filter(Boolean);
      if (item.matched_by) lines.push(`매칭 방식: ${item.matched_by}`);
      if (Array.isArray(item.matched_terms) && item.matched_terms.length) {
        lines.push(`매칭 키워드: ${item.matched_terms.join(', ')}`);
      } else if (item.keywords_norm) {
        lines.push(`원본 키워드: ${item.keywords_norm}`);
      }
      if (item.hs_code_norm) lines.push(`바이어 HS: ${item.hs_code_norm}`);
      if (item.decision) lines.push(`판정: ${item.decision}`);
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

/** CV-02 registry_check_status only — never mix with contact/trade/credit. */
export const REGISTRY_CHECK_STATUSES = [
  'BASIC_CONFIRMED',
  'BASIC_PARTIAL',
  'DATA_MISMATCH',
  'INACTIVE_ENTITY',
  'CREDIT_CHECK_REQUIRED',
];

/** Official external lookup pages (no paid D&B/K-SURE API). */
export const EXTERNAL_LOOKUP_LINKS = {
  dunsLookup: {
    label: 'D-U-N-S 조회',
    href: 'https://www.dnb.com/duns-number/lookup.html',
  },
  ksureSight: {
    label: 'K-SURE 기업 조회',
    href: 'https://ksight.ksure.or.kr/find-buyer',
  },
  ksureCredit: {
    label: 'K-SURE 신용조사 신청',
    href: 'https://www.ksure.or.kr/rh-kr/cntnts/i-115/web.do',
  },
};

export function isRegistryCheckStatus(status) {
  return REGISTRY_CHECK_STATUSES.includes(status);
}

/** Resolve ISO3 for company-verification POST (CV-02/CV-03 contract). */
export function resolveBuyerCountryIso3(buyer) {
  const direct = String(buyer?.countryIso3 || '')
    .trim()
    .toUpperCase();
  if (/^[A-Z]{3}$/.test(direct)) return direct;
  return '';
}

/**
 * Map CV-02 API record → CV-03 card view model.
 * API fields: registry_check_status, country_iso3, completed_at
 * UI fields: status, country, verified_at
 * Unknown enum → status null (확인 결과 없음). Never copies contact/trade/credit.
 */
export function mapCompanyVerificationResponse(data) {
  const rawStatus = data?.registry_check_status;
  const status = isRegistryCheckStatus(rawStatus) ? rawStatus : null;
  const provider = data?.result_json?.provider || data?.provider;
  const mock = data?.result_json?.mock === true;
  let details;
  if (!status) {
    details = '확인 결과 없음';
  } else if (provider) {
    details = mock
      ? `법인 기본검증 제공자: ${provider} (mock · 자동 신용등급 조회 아님)`
      : `법인 기본검증 제공자: ${provider}`;
  }
  return {
    verification_id: data?.verification_id || '',
    status,
    company_name: data?.company_name || '',
    country: data?.country_iso3 || '',
    verified_at: data?.completed_at || data?.requested_at || '',
    details,
  };
}

function _httpDetail(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d?.msg || JSON.stringify(d)).join('; ');
  }
  return err?.message || '';
}

/** Map CV-02 HTTP errors for the BuyerSearch card. Do not treat 404 as "API not deployed". */
export function mapCompanyVerificationHttpError(err) {
  if (
    err?.name === 'AbortError' ||
    err?.name === 'CanceledError' ||
    err?.code === 'ERR_CANCELED'
  ) {
    return { kind: 'timeout', message: null };
  }
  const status = err?.response?.status;
  const detail = _httpDetail(err);
  if (status === 401 || status === 403) {
    return { kind: 'auth', message: '로그인이 필요합니다. 로그인 후 다시 시도해 주세요.' };
  }
  if (status === 400 || status === 422) {
    return { kind: 'invalid', message: detail || '요청 값이 올바르지 않습니다.' };
  }
  if (status === 404) {
    return { kind: 'not_found', message: '검증 결과를 찾을 수 없습니다.' };
  }
  if (status === 503) {
    return {
      kind: 'store',
      message: '검증 저장소를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.',
    };
  }
  if (status === 502 || status === 504) {
    return {
      kind: 'provider',
      message: '외부 조회가 지연되거나 실패했습니다. 잠시 후 다시 시도해 주세요.',
    };
  }
  if (status === 500) {
    return { kind: 'server', message: '서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.' };
  }
  return { kind: 'unknown', message: detail || '검증 요청에 실패했습니다.' };
}

export const COMPANY_VERIFICATION_INTRO =
  '현재 결과는 법적 실체와 등록정보에 대한 기본확인입니다. 재무상태, 결제이력, 신용등급 및 지급능력 확인은 별도의 신용조사가 필요합니다.';

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
