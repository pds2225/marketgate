import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowLeft, LayoutGrid, Building2, Mail, Phone, Globe, CheckCircle2,
  Download, Share2, Info, ChevronRight, Star, FileText, BarChart3, Sparkles,
  Loader2, Database, AlertCircle, RefreshCw, Shield,
  TrendingUp, ExternalLink, Search, Zap, Cpu, Shirt, Stethoscope,
  Settings2, X, Calculator, DollarSign, Percent, TrendingDown, ArrowUpRight,
  Globe2, Users, ChevronLeft, MapPin,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Toaster, toast } from 'sonner';
import api from '@/lib/api';
import { computeProfitability } from '@/lib/profitability';
import {
  mapApiBuyersToViewModels,
  groupBuyersByCountry,
  CONTACT_STATUS_LABELS,
  TRADE_STATUS_LABELS,
  CREDIT_STATUS_LABELS,
} from './buyerViewModel';
import CreditUnlockPanel from '@/components/CreditUnlockPanel';
import { displayContact, makeBuyerKey } from '@/lib/creditWallet';

/* ── Types ── */
// 데이터 정책: API·CSV 원본에 없는 값(수입이력·수입액·성장률·RFM·갱신일)은 항상 null 이며
// 화면에는 '자료 내 확인 불가'로 표시한다. 검증 상태는 contact/trade/credit 3축으로 분리한다.
interface ExportConditions {
  productionCapacity: string; moq: string; targetAmountKrw: string;
  unitPriceUSD: number; costPriceUSD: number; logisticsRate: number;
  tariffRate: number; exchangeRate: number; certifications: string[];
}
interface Buyer {
  id: string; rank: number; name: string; legalName: string; industry: string;
  country: string; region: string; dataSource: string; dataDate: string | null; csvTrace: string | null;
  contactName: string; email: string; phone: string; website: string;
  contactStatus: 'unavailable' | 'discovered' | 'format_validated' | 'ownership_verified';
  tradeStatus: 'unavailable' | 'source_confirmed' | 'recent_activity_confirmed';
  creditStatus: 'not_requested' | 'pending' | 'report_received' | 'expired';
  emailEstimated: boolean; sourceVerification: string;
  score: number; scoreLabel: string;
  metrics: { label: string; value: number }[] | null;
  hsCode: string; hsLabel: string; keywords: string[];
  reasons: { text: string; source: string }[];
  importHistory: null; totalImportValue: null; importGrowthRate: null;
  rfm: null; lastUpdatedDays: null;
}
interface CategoryData { label: string; hsCode: string; hsLabel: string; icon: React.ReactNode; buyers: Buyer[]; countries: string[]; }
interface CountryRec { countryName: string; countryCode: string; flag: string; buyerCount: number; avgScore: number; contactableCount: number; topBuyerName: string; topBuyerScore: number; buyers: Buyer[]; }
type Step = 'countries' | 'buyers' | 'detail';
const KEYWORD_MAP: Record<string, string> = { 'k-뷰티': 'K-뷰티', 'k뷰티': 'K-뷰티', '뷰티': 'K-뷰티', '화장품': 'K-뷰티', '스킨': 'K-뷰티', '스킨케어': 'K-뷰티', '세럼': 'K-뷰티', '메이크업': 'K-뷰티', '건강': '건강식품', '건강식품': '건강식품', '홍삼': '건강식품', '인삼': '건강식품', '프로바이오틱스': '건강식품', '건기식': '건강식품', '영양제': '건강식품', '패션': 'K-패션', 'k-패션': 'K-패션', 'k패션': 'K-패션', '의류': 'K-패션', '옷': 'K-패션', '한복': 'K-패션', '디자이너': 'K-패션', '반도체': '반도체', '칩': '반도체', '메모리': '반도체', '전자': '반도체', 'semiconductor': '반도체', 'chip': '반도체', 'skincare': 'K-뷰티', 'health': '건강식품', 'fashion': 'K-패션', 'apparel': 'K-패션' };
function detectCategory(input: string): string | null { const lower = input.toLowerCase().replace(/[\s\-]/g, ''); for (const [k, v] of Object.entries(KEYWORD_MAP)) { if (lower.includes(k.replace(/[\s\-]/g, ''))) return v; } if (input.startsWith('33')) return 'K-뷰티'; if (input.startsWith('21')) return '건강식품'; if (input.startsWith('62')) return 'K-패션'; if (input.startsWith('85')) return '반도체'; return null; }
function copyToClipboard(text: string) { navigator.clipboard.writeText(text).then(() => toast.success('클립보드에 복사되었습니다', { description: text })); }
function formatDate() { const d = new Date(); return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`; }
// 보고서 내용은 화면에 이미 렌더링된 데이터로 클라이언트에서 직접 파일을 만들어 내려준다.
// (서버가 보내주는 파일 본문 contentObject 가 비어 있어 PDF 바이너리가 없으므로, 한글이 깨지지 않는
//  텍스트 파일로 저장해 실제로 다운로드되도록 한다. jsPDF 기본 폰트는 한글을 렌더링하지 못한다.)
function downloadTextFile(fileName: string, text: string) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}
function buildBuyerReportText(buyer: Buyer): string {
  const lines: string[] = [];
  lines.push('바이어 상세 보고서 (BUYER DETAIL REPORT)');
  lines.push(`리포트 ID: #${buyer.id}`);
  lines.push(`발행일: ${formatDate()}`);
  lines.push('데이터 제공: KOTRA 공공데이터 CSV 기반 분석');
  lines.push('='.repeat(50));
  lines.push('');
  lines.push('[기본 프로필]');
  lines.push(`기업명: ${buyer.name}${buyer.legalName ? ` (${buyer.legalName})` : ''}`);
  lines.push(`업종: ${buyer.industry}`);
  lines.push(`국가/지역: ${buyer.country} · ${buyer.region}`);
  lines.push(`HS 코드: ${buyer.hsCode} (${buyer.hsLabel})`);
  lines.push(`데이터 출처: ${buyer.dataSource}`);
  lines.push(`원본 추적: ${buyer.csvTrace || '자료 내 확인 불가'}`);
  lines.push(`데이터 수집일: ${buyer.dataDate || '자료 내 확인 불가'}`);
  lines.push('');
  lines.push('[연락처]');
  lines.push(`담당자: ${buyer.contactName || '정보 없음'}`);
  lines.push(`이메일: ${buyer.email || '정보 없음'}`);
  lines.push(`전화: ${buyer.phone || '정보 없음'}`);
  lines.push(`웹사이트: ${buyer.website || '정보 없음'}`);
  lines.push(`연락처 상태: ${CONTACT_STATUS_LABELS[buyer.contactStatus]}`);
  lines.push(`거래(출처) 상태: ${TRADE_STATUS_LABELS[buyer.tradeStatus]}`);
  lines.push(`신용 상태: ${CREDIT_STATUS_LABELS[buyer.creditStatus]}`);
  lines.push('');
  lines.push('[수입 동향]');
  lines.push('누적 수입액·성장률·RFM: 자료 내 확인 불가 (원본 데이터에 수입실적 미포함)');
  if (buyer.reasons.length) {
    lines.push('');
    lines.push('[매칭 근거]');
    buyer.reasons.forEach(r => lines.push(`- ${r.text}${r.source ? ` (출처: ${r.source})` : ''}`));
  }
  lines.push('');
  lines.push('[참고·엔진 점수 — 공식 순위 아님]');
  lines.push(`엔진 점수: ${buyer.score}점 (${buyer.scoreLabel})`);
  return lines.join('\n');
}
// API 응답 → 뷰모델 변환·국가 그룹핑은 buyerViewModel.js 의 순수 함수를 사용한다
// (Math.random / Date 기반 합성값 생성 금지 — 동일 입력 = 동일 결과).

/* ── Data ── */
// 카테고리 정의 (검색 진입용). 바이어 목록은 항상 API 실데이터로만 채운다 —
// 가상의 예시 바이어(하드코딩 목업)는 데이터 정책 위반이라 제거했다.
const CATEGORIES: CategoryData[] = [
  { label: 'K-뷰티', hsCode: '330499', hsLabel: '스킨케어', icon: <Sparkles className="h-4 w-4" />, countries: [], buyers: [] },
  { label: '건강식품', hsCode: '210690', hsLabel: '건강기능식품', icon: <Stethoscope className="h-4 w-4" />, countries: [], buyers: [] },
  { label: 'K-패션', hsCode: '6203', hsLabel: '여성 의류', icon: <Shirt className="h-4 w-4" />, countries: [], buyers: [] },
  { label: '반도체', hsCode: '8541', hsLabel: '반도체 소자', icon: <Cpu className="h-4 w-4" />, countries: [], buyers: [] },
];

/* ── Reusable small components ── */
// 실측 데이터만 표시한다: /v1/demo/summary 의 실제 바이어 후보 집계.
// 조회 실패 시 숫자를 지어내지 않고 '자료 내 확인 불가'로 표시한다.
const DataStatsBanner: React.FC = () => {
  const [summary, setSummary] = useState<{ total: number; countryCount: number } | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api.get('/v1/demo/summary')
      .then((res) => setSummary({ total: res.data?.total ?? 0, countryCount: res.data?.countryCount ?? 0 }))
      .catch(() => setFailed(true));
  }, []);
  const fmt = (v: number | undefined) => (v == null ? '—' : v.toLocaleString());
  return (
    <div className="bg-white border-b border-slate-200 px-4 py-3">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center gap-1.5 text-xs text-slate-500"><Globe2 className="h-4 w-4 text-blue-600" /><span className="font-bold text-slate-800">{failed ? '자료 내 확인 불가' : fmt(summary?.countryCount)}</span><span>개국 데이터</span></div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-1.5 text-xs text-slate-500"><Users className="h-4 w-4 text-emerald-600" /><span className="font-bold text-slate-800">{failed ? '자료 내 확인 불가' : fmt(summary?.total)}</span><span>개 바이어 후보 (등록 데이터 기준)</span></div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-1 text-[10px] text-slate-400">KOTRA 공공데이터 CSV 기반 · K-뷰티 HS 330499 파일럿</div>
      </div>
    </div>
  );
};

// 검증 상태 3축 뱃지 — has_contact 하나로 '신뢰도 높음/검증 완료'를 표시하던 것을 대체
const StatusBadges: React.FC<{ buyer: Buyer; compact?: boolean }> = ({ buyer, compact }) => {
  const contactTone = buyer.contactStatus === 'unavailable' ? 'bg-slate-100 text-slate-500 border border-slate-200' : 'bg-amber-50 text-amber-700 border border-amber-200';
  const tradeTone = buyer.tradeStatus === 'source_confirmed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-500 border border-slate-200';
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${contactTone}`}>
        <Shield className="h-3 w-3" />
        {CONTACT_STATUS_LABELS[buyer.contactStatus]}{buyer.emailEstimated ? ' · 추정' : ''}
      </span>
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${tradeTone}`}>
        {TRADE_STATUS_LABELS[buyer.tradeStatus]}
      </span>
      {!compact && (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-500 border border-slate-200">
          {CREDIT_STATUS_LABELS[buyer.creditStatus]}
        </span>
      )}
    </span>
  );
};

// '자료 내 확인 불가' 공통 표시 — 원본 데이터에 없는 항목을 빈 화면 대신 명시적으로 알린다
const DataUnavailable: React.FC<{ title: string; description: string }> = ({ title, description }) => (
  <div className="flex flex-col items-center justify-center py-10 text-center bg-slate-50 border border-dashed border-slate-200 rounded-xl">
    <Database className="h-8 w-8 text-slate-300 mb-2" />
    <p className="text-sm font-semibold text-slate-600">{title} — 자료 내 확인 불가</p>
    <p className="text-xs text-slate-400 mt-1 max-w-sm">{description}</p>
  </div>
);

const ScoreBar: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="mb-3 last:mb-0">
    <div className="flex justify-between items-center mb-1.5"><span className="text-xs text-slate-600">{label}</span><span className="text-xs font-semibold text-slate-800">{value}점</span></div>
    <div className="relative h-2.5 bg-slate-100 rounded-full overflow-hidden"><div className="absolute top-0 left-0 h-full bg-emerald-500 rounded-full transition-all duration-700" style={{ width: `${value}%` }} /></div>
  </div>
);

const ContactRow: React.FC<{ icon: React.ReactNode; label: string; value: string; action?: 'copy' | 'link' | 'phone'; href?: string }> = ({ icon, label, value, action, href }) => {
  // 연락처 값이 비어 있으면(공공데이터에 미수록) 클릭 가능한 링크 대신 "정보 없음"을 보여준다.
  // 빈 값에 링크를 걸면 tel: / https:// 로만 이동해 전화가 걸리지 않거나 빈 탭이 열려 고객이 막힌다.
  const hasValue = !!(value && value.trim());
  const handleClick = () => { if (!hasValue) return; if (action === 'copy') copyToClipboard(value); else if (action === 'link' && href) window.open(href, '_blank', 'noopener,noreferrer'); else if (action === 'phone' && href) window.location.href = href; };
  return (
    <div className="flex items-start gap-3 py-2 group">
      <div className="mt-0.5 text-slate-400">{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-slate-500 mb-0.5">{label}</div>
        {hasValue ? (
          <button onClick={handleClick} className={`text-sm text-slate-800 break-all text-left ${action ? 'hover:text-blue-600 hover:underline cursor-pointer' : ''}`}>{value}</button>
        ) : (
          <span className="text-sm text-slate-400">정보 없음</span>
        )}
      </div>
      {action === 'copy' && hasValue && (
        <TooltipProvider><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity" onClick={handleClick}><FileText className="h-3.5 w-3.5" /></Button></TooltipTrigger><TooltipContent side="left"><p>복사하기</p></TooltipContent></Tooltip></TooltipProvider>
      )}
    </div>
  );
};

/* ── Export Condition Panel (condensed) ── */
const MOQ_OPTIONS = ['100개','500개','1,000개','2,000개','5,000개','10,000개 이상'];
const PROD_OPTIONS = ['500개 이하','500~2,000개','2,000~5,000개','5,000개 이상'];
const TARGET_OPTIONS = ['1천만원','5천만원','1억원','5억원','10억원 이상'];
const CERT_OPTIONS = ['ISO','GMP','FDA','CE','HACCP','FSSC','Organic'];

// 공용 수익성 모듈(computeProfitability)로 계산 — 제품원가·관세·통관비 포함 정상식
function simulateExport(c: ExportConditions) {
  const moqNum = parseInt(c.moq.replace(/[^0-9]/g,''))||1000;
  const revenueUSD = c.unitPriceUSD * moqNum;
  const logisticsUSD = revenueUSD * (c.logisticsRate/100);
  const customsFeeUSD = 200;
  const sim = computeProfitability({
    unitPrice: c.unitPriceUSD,
    quantity: moqNum,
    unitCost: c.costPriceUSD,
    logisticsCost: logisticsUSD,
    tariffRate: c.tariffRate,
    customsFee: customsFeeUSD,
  });
  const targetNum = parseInt(c.targetAmountKrw.replace(/[^0-9]/g,''))||5000;
  const targetUSD = targetNum * 10000 / c.exchangeRate;
  const dealsNeeded = revenueUSD > 0 ? Math.ceil(targetUSD/revenueUSD) : 0;
  const bepDeals = (c.unitPriceUSD - c.costPriceUSD) > 0 ? Math.ceil((logisticsUSD+customsFeeUSD)/(c.unitPriceUSD-c.costPriceUSD)) : 0;
  return { revenueUSD, profitUSD: sim.profit, marginRate: sim.profitRate, dealsNeeded, bepDeals, tariffUSD: sim.tariff, logisticsUSD, customsFeeUSD, totalCostUSD: sim.totalCost };
}

const ExportConditionPanel: React.FC<{ open: boolean; onClose: () => void; conditions: ExportConditions; onChange: (c: ExportConditions) => void; onApply: () => void; onReset: () => void; }> = ({ open, onClose, conditions, onChange, onApply, onReset }) => {
  const sim = simulateExport(conditions);
  const isProfitable = sim.marginRate > 0;
  const update = (patch: Partial<ExportConditions>) => onChange({ ...conditions, ...patch });
  return (
    <div className={`fixed inset-0 z-50 transition-opacity ${open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}>
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className={`absolute right-0 top-0 h-full w-[520px] bg-white shadow-2xl transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200"><div className="flex items-center gap-2"><Settings2 className="h-5 w-5 text-blue-600" /><h2 className="text-lg font-bold text-slate-800">수출 조건 등록</h2></div><Button variant="ghost" size="icon" onClick={onClose}><X className="h-5 w-5" /></Button></div>
          <ScrollArea className="flex-1 px-5 py-4">
            <p className="text-sm text-slate-500 mb-5">내 수출 조건을 입력하면 MOQ·인증·수익성이 맞는 바이어만 추천됩니다.</p>
            <div className="mb-5"><label className="text-sm font-semibold text-slate-800 mb-2 block">Q1. 월간 생산 가능 수량</label><div className="flex flex-wrap gap-2">{PROD_OPTIONS.map(opt => <button key={opt} onClick={() => update({ productionCapacity: opt })} className={`rounded-lg px-3 py-2 text-xs font-medium border transition-colors ${conditions.productionCapacity === opt ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>{opt}</button>)}</div></div>
            <div className="mb-5"><label className="text-sm font-semibold text-slate-800 mb-2 block">Q2. 최소 주문 단위 (MOQ)</label><div className="flex flex-wrap gap-2">{MOQ_OPTIONS.map(opt => <button key={opt} onClick={() => update({ moq: opt })} className={`rounded-lg px-3 py-2 text-xs font-medium border transition-colors ${conditions.moq === opt ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>{opt}</button>)}</div></div>
            <div className="mb-5"><label className="text-sm font-semibold text-slate-800 mb-2 block">Q3. 연간 수출 희망 금액</label><div className="flex flex-wrap gap-2">{TARGET_OPTIONS.map(opt => <button key={opt} onClick={() => update({ targetAmountKrw: opt })} className={`rounded-lg px-3 py-2 text-xs font-medium border transition-colors ${conditions.targetAmountKrw === opt ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>{opt}</button>)}</div></div>
            <div className="mb-5 bg-slate-50 rounded-xl p-4 border border-slate-100">
              <label className="text-sm font-semibold text-slate-800 mb-3 block flex items-center gap-1.5"><Calculator className="h-4 w-4 text-blue-600" /> 단가 및 원가 정보 (수익성 계산용)</label>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div><label className="text-xs text-slate-500 mb-1 block">제품 단가 (FOB, USD)</label><div className="flex items-center bg-white border border-slate-200 rounded-lg px-3 py-2"><DollarSign className="h-4 w-4 text-slate-400 mr-2" /><input type="number" value={conditions.unitPriceUSD} onChange={e => update({ unitPriceUSD: parseFloat(e.target.value)||0 })} className="w-full text-sm outline-none bg-transparent" /></div></div>
                <div><label className="text-xs text-slate-500 mb-1 block">생산원가 (USD)</label><div className="flex items-center bg-white border border-slate-200 rounded-lg px-3 py-2"><DollarSign className="h-4 w-4 text-slate-400 mr-2" /><input type="number" value={conditions.costPriceUSD} onChange={e => update({ costPriceUSD: parseFloat(e.target.value)||0 })} className="w-full text-sm outline-none bg-transparent" /></div></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs text-slate-500 mb-1 block">물류비 (%)</label><div className="flex items-center bg-white border border-slate-200 rounded-lg px-3 py-2"><Percent className="h-4 w-4 text-slate-400 mr-2" /><input type="number" value={conditions.logisticsRate} onChange={e => update({ logisticsRate: parseFloat(e.target.value)||0 })} className="w-full text-sm outline-none bg-transparent" /></div></div>
                <div><label className="text-xs text-slate-500 mb-1 block">관세율 (%)</label><div className="flex items-center bg-white border border-slate-200 rounded-lg px-3 py-2"><Percent className="h-4 w-4 text-slate-400 mr-2" /><input type="number" value={conditions.tariffRate} onChange={e => update({ tariffRate: parseFloat(e.target.value)||0 })} className="w-full text-sm outline-none bg-transparent" /></div></div>
              </div>
              <div className="mt-3"><label className="text-xs text-slate-500 mb-1 block">환율 (KRW/USD)</label><div className="flex items-center bg-white border border-slate-200 rounded-lg px-3 py-2"><span className="text-sm text-slate-400 mr-2">₩</span><input type="number" value={conditions.exchangeRate} onChange={e => update({ exchangeRate: parseFloat(e.target.value)||1300 })} className="w-full text-sm outline-none bg-transparent" /></div></div>
            </div>
            <div className="mb-5">
              <label className="text-sm font-semibold text-slate-800 mb-2 block">Q4. 보유 인증 (복수 선택)</label>
              <div className="flex flex-wrap gap-2">{CERT_OPTIONS.map(cert => <button key={cert} onClick={() => { const next = conditions.certifications.includes(cert) ? conditions.certifications.filter(c=>c!==cert) : [...conditions.certifications, cert]; update({ certifications: next }); }} className={`rounded-lg px-3 py-2 text-xs font-medium border transition-colors ${conditions.certifications.includes(cert) ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>{cert}</button>)}</div>
            </div>
            <div className={`mb-5 rounded-xl p-4 border ${isProfitable ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
              <h3 className="text-sm font-bold mb-3 flex items-center gap-1.5"><TrendingUp className={`h-4 w-4 ${isProfitable ? 'text-emerald-600' : 'text-red-600'}`} /> 실시간 수익성 시뮬레이션 (Landed Cost)</h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-slate-600">1회 거래 매출 (FOB)</span><span className="font-semibold">${sim.revenueUSD.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-slate-600">- 생산원가</span><span className="text-red-600">-${(conditions.costPriceUSD * (parseInt(conditions.moq.replace(/[^0-9]/g,''))||1000)).toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-slate-600">- 관세 ({conditions.tariffRate}%)</span><span className="text-red-600">-${sim.tariffUSD.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-slate-600">- 물류비 ({conditions.logisticsRate}%)</span><span className="text-red-600">-${sim.logisticsUSD.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-slate-600">- 통관비 (고정)</span><span className="text-red-600">-${sim.customsFeeUSD}</span></div>
                <Separator className="my-1" />
                <div className="flex justify-between"><span className="text-slate-800 font-semibold">= 1회 순이익</span><span className={`font-bold ${isProfitable ? 'text-emerald-700' : 'text-red-600'}`}>${sim.profitUSD.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-slate-800 font-semibold">예상 마진율</span><span className={`font-bold ${isProfitable ? 'text-emerald-700' : 'text-red-600'}`}>{sim.marginRate.toFixed(1)}%</span></div>
              </div>
              <div className="mt-3 bg-white rounded-lg p-3 border border-slate-100">
                <div className="flex items-center justify-between text-xs mb-1"><span className="text-slate-600">연간 목표 달성 필요 거래 횟수</span><span className="font-bold text-slate-800">{sim.dealsNeeded}건</span></div>
                <div className="flex items-center justify-between text-xs"><span className="text-slate-600">Break-even (손익분기) 거래 횟수</span><span className="font-bold text-blue-700">{sim.bepDeals}건</span></div>
              </div>
              {!isProfitable && <p className="text-[11px] text-red-600 mt-2 flex items-center gap-1"><TrendingDown className="h-3 w-3" /> 현재 조건에서는 적자 수출 구조입니다. 단가 상승 또는 원가 절감이 필요합니다.</p>}
            </div>
          </ScrollArea>
          <div className="px-5 py-4 border-t border-slate-200 bg-slate-50">
            {/* 원본 데이터에 바이어별 수입실적이 없어 조건 기반 바이어 필터링은 제공하지 않는다 (시뮬레이션 전용) */}
            <div className="flex items-center justify-between mb-3"><span className="text-xs text-slate-500">입력 조건 기반 수익성 시뮬레이션 (바이어 필터링 아님)</span><Badge variant="outline" className="text-xs">{conditions.moq} · {conditions.targetAmountKrw}</Badge></div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1 text-sm" onClick={() => { update({ productionCapacity: '', moq: '1,000개', targetAmountKrw: '5천만원', unitPriceUSD: 12.5, costPriceUSD: 8, logisticsRate: 8, tariffRate: 8, exchangeRate: 1300, certifications: [] }); onReset(); }}>초기화</Button>
              <Button className="flex-1 bg-blue-600 hover:bg-blue-700 text-sm" onClick={() => { onApply(); onClose(); }}><ArrowUpRight className="h-4 w-4 mr-1" /> 시뮬레이션 확인 완료</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ── SearchBar ── */
const SUGGESTED_KEYWORDS = ['스킨케어', '홍삼', '여성의류', '메모리 반도체'];
const SearchBar: React.FC<{ onSearch: (text: string) => void; activeCategory: string; loading: boolean; initialQuery?: string; }> = ({ onSearch, activeCategory, loading, initialQuery = '' }) => {
  const [input, setInput] = useState(initialQuery);
  useEffect(() => {
    if (initialQuery) setInput(initialQuery);
  }, [initialQuery]);
  const submit = () => { if (!input.trim() || loading) return; onSearch(input.trim()); };
  return (
    <div className="bg-white border-b border-slate-200">
      <div className="max-w-3xl mx-auto px-5 py-4">
        <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-2.5 focus-within:border-blue-300 transition-colors">
          <Search className="h-4 w-4 text-slate-400 flex-shrink-0" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder="제품 키워드 또는 HS코드 입력 (예: K-뷰티, 스킨케어, 330499)"
            className="flex-1 bg-transparent text-sm text-slate-800 placeholder:text-slate-400 outline-none"
          />
          <Button size="sm" className="h-8 rounded-full bg-blue-600 hover:bg-blue-700 text-white gap-1.5 px-4" onClick={submit} disabled={!input.trim() || loading}>
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
            검색
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <span className="text-[11px] text-slate-400 mr-1">카테고리</span>
          {CATEGORIES.map((cat) => (
            <button key={cat.label} onClick={() => !loading && onSearch(cat.label)} disabled={loading} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50 ${activeCategory === cat.label ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'}`}>{cat.icon} {cat.label}</button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <span className="text-[11px] text-slate-400 mr-1">추천 검색어</span>
          {SUGGESTED_KEYWORDS.map((kw) => (
            <button key={kw} onClick={() => !loading && onSearch(kw)} disabled={loading} className="text-xs bg-white border border-slate-200 rounded-full px-3 py-1.5 text-slate-600 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-colors disabled:opacity-50"><Search className="h-3 w-3 inline mr-1" />{kw}</button>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ── CountryListPanel ── */
const CountryListPanel: React.FC<{ countries: CountryRec[]; categoryLabel: string; categoryHs: string; onSelectCountry: (c: CountryRec) => void; onOpenConditions: () => void; hasConditions: boolean; }> = ({ countries, categoryLabel, categoryHs, onSelectCountry, onOpenConditions, hasConditions }) => {
  // 파일럿: 점수 순위가 아니라 연락처·후보 수 실측으로 정렬해 사용자가 판단하게 한다.
  const sorted = useMemo(
    () => [...countries].sort((a, b) => b.contactableCount - a.contactableCount || b.buyerCount - a.buyerCount),
    [countries],
  );
  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
        <div className="flex items-center gap-2"><Globe className="h-4 w-4 text-slate-500" /><h1 className="text-sm font-semibold text-slate-800">국가 후보 리스트</h1></div>
        <Button variant="ghost" size="sm" className={`h-7 text-xs gap-1 ${hasConditions ? 'text-blue-600 bg-blue-50' : 'text-slate-500'}`} onClick={onOpenConditions}><Settings2 className="h-3.5 w-3.5" />수익성 시뮬레이션</Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="px-5 py-5 max-w-3xl mx-auto">
          <div className="bg-slate-900 text-white rounded-xl px-5 py-4 mb-6">
            <div className="flex items-center justify-between mb-2"><span className="text-xs font-bold tracking-wider text-blue-200">COUNTRY FACTS</span><span className="text-xs text-slate-400">{categoryLabel} · HS {categoryHs}</span></div>
            <p className="text-xs text-slate-300 mt-2">{sorted.length}개국 · 정렬: 연락처 보유 수 → 바이어 후보 수 (공공데이터 CSV). 적합도 점수로 순위를 매기지 않습니다.</p>
          </div>
          <div className="space-y-3">
            {sorted.map((c) => (
              <button key={c.countryCode} onClick={() => onSelectCountry(c)} className="w-full text-left bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition-all group">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0"><div className="w-14 h-14 rounded-xl bg-slate-100 flex items-center justify-center text-3xl">{c.flag}</div></div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1"><h3 className="text-lg font-bold text-slate-900">{c.countryName}</h3></div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mb-3">
                      <span className="flex items-center gap-1"><Users className="h-3.5 w-3.5" />바이어 후보 {c.buyerCount}개</span>
                      <span className="flex items-center gap-1"><Mail className="h-3.5 w-3.5" />연락처 보유 {c.contactableCount}개</span>
                    </div>
                    <p className="text-xs text-slate-400">대표 후보: <span className="font-medium text-slate-600">{c.topBuyerName || '자료 내 확인 불가'}</span></p>
                  </div>
                  <div className="flex-shrink-0 self-center"><ChevronRight className="h-5 w-5 text-slate-300 group-hover:text-blue-500 transition-colors" /></div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
};

/* ── BuyerListPanel ── */
const BuyerListPanel: React.FC<{ country: CountryRec; onSelectBuyer: (b: Buyer) => void; onBack: () => void; onOpenConditions: () => void; hasConditions: boolean; }> = ({ country, onSelectBuyer, onBack, onOpenConditions, hasConditions }) => {
  const sortedBuyers = useMemo(
    () => [...country.buyers].sort((a, b) => {
      const ac = a.contactStatus === 'unavailable' ? 0 : 1;
      const bc = b.contactStatus === 'unavailable' ? 0 : 1;
      if (bc !== ac) return bc - ac;
      const at = a.tradeStatus === 'source_confirmed' ? 1 : 0;
      const bt = b.tradeStatus === 'source_confirmed' ? 1 : 0;
      return bt - at;
    }),
    [country.buyers],
  );
  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-200">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onBack}><ChevronLeft className="h-4 w-4 text-slate-600" /></Button>
        <div className="flex items-center gap-2"><span className="text-2xl">{country.flag}</span><div><h1 className="text-sm font-semibold text-slate-800">{country.countryName} 바이어 리스트</h1><p className="text-xs text-slate-500">총 {country.buyers.length}개 · 정렬: 연락처 → 출처 확인 (점수 순위 없음)</p></div></div>
        <div className="ml-auto"><Button variant="ghost" size="sm" className={`h-7 text-xs gap-1 ${hasConditions ? 'text-blue-600 bg-blue-50' : 'text-slate-500'}`} onClick={onOpenConditions}><Settings2 className="h-3.5 w-3.5" />수익성 시뮬레이션</Button></div>
      </div>
      <ScrollArea className="flex-1">
        <div className="px-5 py-5 max-w-3xl mx-auto space-y-3">
          {sortedBuyers.map((buyer) => (
            <button key={buyer.id} onClick={() => onSelectBuyer(buyer)} className="w-full text-left bg-white border border-slate-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-md transition-all group">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0"><div className="w-12 h-12 rounded-lg bg-slate-100 flex items-center justify-center"><Building2 className="h-6 w-6 text-slate-400" /></div></div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5"><h3 className="text-base font-bold text-slate-900">{buyer.name}</h3></div>
                  <p className="text-xs text-slate-500">({buyer.legalName})</p>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-slate-500"><span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{buyer.region}</span><span>{buyer.industry}</span><span className="text-slate-400">HS {buyer.hsCode}</span><span className="flex items-center gap-1"><Mail className="h-3 w-3" />{buyer.email ? displayContact(buyer.email, { unlocked: false, kind: 'email' }) : '연락처 없음'}</span></div>
                  <div className="flex flex-wrap items-center gap-2 mt-3">
                    <StatusBadges buyer={buyer} compact />
                    <span className="text-[10px] text-slate-400">{buyer.dataSource || '출처 미상'}</span>
                  </div>
                </div>
                <div className="flex-shrink-0 self-center"><ChevronRight className="h-5 w-5 text-slate-300 group-hover:text-blue-500 transition-colors" /></div>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
};

/* ── BuyerDetailPanel ── */
const BuyerDetailPanel: React.FC<{ buyer: Buyer; onBack: () => void; inputHsCode: string; category: string; }> = ({ buyer, onBack, inputHsCode, category }) => {
  const [showMeta, setShowMeta] = useState(false);
  const [favorited, setFavorited] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');

  const handleFavorite = () => { setFavorited(!favorited); toast.success(favorited ? '관심 바이어에서 제거했습니다' : '관심 바이어로 등록했습니다'); };
  const handleShare = () => { copyToClipboard(`${window.location.origin}?buyer=${buyer.id}`); };
  const handleDownloadPDF = () => { const fileName = `buyer_report_${buyer.id}.txt`; downloadTextFile(fileName, buildBuyerReportText(buyer)); toast.success('바이어 보고서를 저장했습니다', { description: `파일: ${fileName}` }); };
  const isMismatch = inputHsCode !== buyer.hsCode && inputHsCode !== category;

  const tabs = [
    { key: 'profile', label: '기본 프로필', icon: <Building2 className="h-3.5 w-3.5" /> },
    { key: 'match', label: '매칭 근거', icon: <Sparkles className="h-3.5 w-3.5" /> },
    { key: 'import', label: '수입 이력', icon: <TrendingUp className="h-3.5 w-3.5" /> },
    { key: 'fit', label: '참고 점수', icon: <BarChart3 className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 bg-white">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onBack}><ChevronLeft className="h-4 w-4 text-slate-600" /></Button>
          <div><h1 className="text-sm font-semibold text-slate-800">{buyer.name}</h1><p className="text-xs text-slate-500">{buyer.country} · {buyer.industry}</p></div>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500 hover:text-blue-600" onClick={handleShare}><Share2 className="h-4 w-4" /></Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500 hover:text-blue-600" onClick={handleDownloadPDF}><Download className="h-4 w-4" /></Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-5 py-5 max-w-3xl mx-auto">
          <div className="bg-slate-900 text-white rounded-xl px-5 py-4 mb-5">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2"><FileText className="h-4 w-4 text-blue-300" /><span className="text-xs font-bold tracking-wider text-blue-200">BUYER DETAIL REPORT</span></div>
              <span className="text-xs text-slate-400">리포트 ID: #{buyer.id}</span>
            </div>
            <div className="grid grid-cols-2 gap-y-1 gap-x-4 text-xs text-slate-300 mt-2">
              <div><span className="text-slate-500">발행일:</span> {formatDate()}</div>
              <div><span className="text-slate-500">데이터 기준일:</span> {buyer.dataDate || '자료 내 확인 불가'}</div>
              <div className="col-span-2"><span className="text-slate-500">분석 대상:</span> {buyer.country} · HS {buyer.hsCode} ({buyer.hsLabel})</div>
            </div>
          </div>

          <div className="flex items-start gap-2 bg-blue-50 border border-blue-100 rounded-lg px-4 py-3 mb-5"><Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" /><p className="text-xs text-blue-800 leading-relaxed">KOTRA 공공데이터 CSV 기반 바이어 후보 분석 결과입니다. 원본에 없는 수입실적·신용정보는 표시하지 않습니다.</p></div>

          {isMismatch && <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-5"><AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" /><div className="text-xs text-amber-800 leading-relaxed"><span className="font-semibold">입력하신 {inputHsCode}과(와) 유사한 HS 코드 {buyer.hsCode}({buyer.hsLabel})의 결과입니다.</span><br />해당 코드는 동일 카테고리({buyer.hsLabel}) 내 유사 품목으로 매칭되었습니다.</div></div>}

          <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
            {tabs.map((t) => <button key={t.key} onClick={() => setActiveTab(t.key)} className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${activeTab === t.key ? 'bg-slate-800 text-white' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'}`}>{t.icon} {t.label}</button>)}
          </div>

          {activeTab === 'profile' && (
            <div className="mb-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap"><h2 className="text-xl font-bold text-slate-900">{buyer.name}</h2><StatusBadges buyer={buyer} /></div>
                    <p className="text-xs text-slate-500">({buyer.legalName})</p>
                  </div>
                  <Button variant="ghost" size="icon" className={`h-8 w-8 ${favorited ? 'text-amber-500' : 'text-slate-300 hover:text-amber-500'}`} onClick={handleFavorite}><Star className={`h-5 w-5 ${favorited ? 'fill-current' : ''}`} /></Button>
                </div>
                <div className="grid grid-cols-2 gap-y-3 gap-x-6 text-sm mb-4">
                  <div><span className="text-xs text-slate-500 block mb-0.5">업종</span><span className="text-slate-800 font-medium">{buyer.industry}</span></div>
                  <div><span className="text-xs text-slate-500 block mb-0.5">국가/지역</span><span className="text-slate-800 font-medium">{buyer.country} · {buyer.region}</span></div>
                  <div><span className="text-xs text-slate-500 block mb-0.5">데이터 출처</span><span className="text-slate-800">{buyer.dataSource}</span></div>
                  <div><span className="text-xs text-slate-500 block mb-0.5">원본 추적</span><span className="text-slate-800 text-xs font-mono">{buyer.csvTrace || '자료 내 확인 불가'}</span></div>
                  <div className="col-span-2"><span className="text-xs text-slate-500 block mb-0.5">데이터 수집일</span><span className="text-slate-800">{buyer.dataDate || '자료 내 확인 불가'}</span></div>
                </div>
                <Separator className="my-3" />
                <div className="space-y-1">
                  <ContactRow icon={<Building2 className="h-4 w-4" />} label="담당자" value={buyer.contactName} />
                </div>
                <CreditUnlockPanel
                  buyerKey={makeBuyerKey({ id: buyer.id, name: buyer.name, country: buyer.country, dataSource: buyer.dataSource })}
                  email={buyer.email}
                  phone={buyer.phone}
                  website={buyer.website}
                  variant="light"
                />
                {buyer.contactStatus !== 'unavailable' ? (
                  <div className="flex items-center gap-2 mt-4 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 w-fit"><AlertCircle className="h-4 w-4 text-amber-600" /><span className="text-xs font-medium text-amber-700">{CONTACT_STATUS_LABELS[buyer.contactStatus]}</span><span className="text-[10px] text-amber-500">형식·소유 검증 절차 전 상태입니다</span></div>
                ) : (
                  <div className="flex items-center gap-2 mt-4 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 w-fit"><AlertCircle className="h-4 w-4 text-slate-500" /><span className="text-xs font-medium text-slate-600">연락처 없음</span><span className="text-[10px] text-slate-400">자료 내 확인 불가 — 발송 불가</span></div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'import' && (
            <div className="mb-6">
              {/* 원본 CSV(buyer_candidate)에 수입실적이 없다 — 지어내지 않고 명시한다 */}
              <DataUnavailable
                title="수입 이력·수입액·성장률"
                description="KOTRA 바이어 후보 데이터에는 기업별 수입실적이 포함되어 있지 않습니다. 수입실적 데이터 연동 전까지는 표시하지 않습니다."
              />
            </div>
          )}

          {activeTab === 'fit' && (
            <div className="mb-6">
              <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-4 text-xs text-amber-900 leading-relaxed">
                이 탭의 숫자는 <strong>엔진 참고용</strong>이며 공식 순위·추천이 아닙니다. 파일럿에서는 연락처·출처·HS 등 실데이터로 판단하세요.
              </div>
              <details className="bg-white border border-slate-200 rounded-xl p-5">
                <summary className="cursor-pointer text-sm font-semibold text-slate-700">엔진 참고 점수 펼치기 ({buyer.score}점 · {buyer.scoreLabel})</summary>
                <div className="flex items-center gap-4 mt-5 mb-5">
                  <div className="text-center"><div className="text-3xl font-bold text-slate-500">{buyer.score}<span className="text-base">점</span></div><div className="flex items-center justify-center gap-1 mt-1"><span className="text-xs text-slate-400">{buyer.scoreLabel}</span></div></div>
                  <Separator orientation="vertical" className="h-12" />
                  <div className="flex-1"><p className="text-xs text-slate-500 mb-2">P1이 공공데이터 지표를 합산한 참고값입니다 (100점 만점). 의사결정 기준으로 쓰지 마세요.</p></div>
                </div>
                {buyer.metrics ? (
                  <div className="bg-slate-50 rounded-lg p-4">{buyer.metrics.map((m) => <ScoreBar key={m.label} label={m.label} value={m.value} />)}</div>
                ) : (
                  <DataUnavailable title="세부 점수" description="이 바이어의 점수 세부 내역이 응답에 포함되어 있지 않습니다." />
                )}
              </details>
              <div className="mt-5">
                <DataUnavailable
                  title="RFM 모델"
                  description="RFM(최근성·빈도·금액)은 기업별 수입실적이 필요합니다. 원본 데이터에 수입실적이 없어 계산하지 않습니다."
                />
              </div>
            </div>
          )}

          {activeTab === 'match' && (
            <div className="mb-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div><span className="text-xs text-slate-500 block mb-1">매칭 HS 코드</span><span className="text-sm font-semibold text-slate-800">{buyer.hsCode} ({buyer.hsLabel})</span></div>
                  <div><span className="text-xs text-slate-500 block mb-1">매칭 키워드</span><div className="flex flex-wrap gap-1.5">{buyer.keywords.map((kw) => <Badge key={kw} className="bg-pink-50 text-pink-700 border-pink-200 hover:bg-pink-100 text-[10px] font-medium px-2 py-0.5">{kw}</Badge>)}</div></div>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block mb-2">추천 이유</span>
                  <ol className="space-y-3">{buyer.reasons.map((r, idx) => <li key={idx} className="flex items-start gap-2.5 text-sm text-slate-700"><span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-50 text-blue-600 text-xs font-bold flex items-center justify-center mt-0.5">{idx + 1}</span><div className="flex-1"><p className="leading-relaxed">{r.text}</p><button onClick={() => toast.info(r.source, { description: '원본 데이터 출처' })} className="inline-flex items-center gap-1 mt-1 text-[10px] text-blue-600 hover:text-blue-800 hover:underline"><ExternalLink className="h-3 w-3" /> 출처: {r.source}</button></div></li>)}</ol>
                </div>
              </div>
            </div>
          )}

          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3"><Database className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">검증 상태</h3></div>
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              {/* has_contact 하나로 '신뢰도 높음'을 매기던 표시를 상태 3축으로 대체 */}
              <div className="space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-slate-500">연락처 상태 (contact_status)</span><span className="font-semibold text-slate-800">{CONTACT_STATUS_LABELS[buyer.contactStatus]}{buyer.emailEstimated ? ' · 추정 이메일' : ''}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">거래·출처 상태 (trade_status)</span><span className="font-semibold text-slate-800">{TRADE_STATUS_LABELS[buyer.tradeStatus]}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">신용 상태 (credit_status)</span><span className="font-semibold text-slate-800">{CREDIT_STATUS_LABELS[buyer.creditStatus]}</span></div>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed mt-3">출처: {buyer.dataSource} · 검증일: 자료 내 확인 불가. 연락처 보유는 검증 완료를 의미하지 않습니다.</p>
            </div>
          </div>

          <div className="mb-8">
            <button onClick={() => setShowMeta(!showMeta)} className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-700 transition-colors"><ChevronRight className={`h-3.5 w-3.5 transition-transform ${showMeta ? 'rotate-90' : ''}`} />원본 데이터 상세 보기</button>
            {showMeta && <div className="mt-2 bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-600 space-y-1 font-mono"><div>원본 파일: {buyer.csvTrace || '자료 내 확인 불가'}</div><div>수집 기관: {buyer.dataSource}</div><div>수집 일시: {buyer.dataDate || '자료 내 확인 불가'}</div><div>출처 검증: {buyer.sourceVerification}</div></div>}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
};

/* ================================================================== */
/*  App                                                               */
/* ================================================================== */
interface BuyerSearchPageProps {
  onClose?: () => void;
}

export default function BuyerSearchPage({ onClose }: BuyerSearchPageProps) {
  const [currentCategory, setCurrentCategory] = useState<string>('');
  const [step, setStep] = useState<Step>('countries');
  const [selectedCountry, setSelectedCountry] = useState<CountryRec | null>(null);
  const [selectedBuyer, setSelectedBuyer] = useState<Buyer | null>(null);
  const [inputHsCode, setInputHsCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchErrorKind, setSearchErrorKind] = useState<'network' | 'empty' | 'input' | null>(null);
  const [lastQuery, setLastQuery] = useState<string>('');
  const [showConditionPanel, setShowConditionPanel] = useState(false);
  const [conditions, setConditions] = useState<ExportConditions>({ productionCapacity: '2,000~5,000개', moq: '1,000개', targetAmountKrw: '5천만원', unitPriceUSD: 12.5, costPriceUSD: 8, logisticsRate: 8, tariffRate: 8, exchangeRate: 1300, certifications: ['ISO', 'GMP'] });
  const [dynamicCategory, setDynamicCategory] = useState<CategoryData | null>(null);
  // 랜딩에서 sessionStorage(mg_search_query)로 넘긴 검색어 — 마운트 시 1회 소비·자동 검색
  const [seedQuery, setSeedQuery] = useState('');

  const categoryData = useMemo(() => dynamicCategory || CATEGORIES.find((c) => c.label === currentCategory), [dynamicCategory, currentCategory]);
  // 바이어별 수입실적 데이터가 원본에 없어 MOQ 기반 바이어 필터링은 제공하지 않는다.
  // 조건 패널은 수익성 시뮬레이션 용도로만 사용하고, 목록은 항상 전체 실데이터를 보여준다.
  const countryRecs = useMemo(() => (categoryData?.buyers.length ? groupBuyersByCountry(categoryData.buyers) : []), [categoryData]);
  const hasConditions = false;

  const handleSearch = async (text: string) => {
    setInputHsCode(text);
    setLastQuery(text);
    setLoading(true);
    setSearchError(null);
    setSearchErrorKind(null);

    try {
      let hsCode = text.trim();
      const detected = detectCategory(text);
      const sixDigit = text.match(/\b(\d{6})\b/);

      if (detected) {
        const cat = CATEGORIES.find((c) => c.label === detected);
        if (cat) hsCode = cat.hsCode;
      } else if (sixDigit) {
        hsCode = sixDigit[1];
      } else if (!/^\d{6}$/.test(hsCode)) {
        const inputErr: any = new Error('HS 코드는 6자리 숫자이거나, K-뷰티/건강식품/K-패션/반도체 중 하나를 입력해 주세요.');
        inputErr.errorKind = 'input';
        throw inputErr;
      }

      const res = await api.post('/v1/predict', {
        hs_code: hsCode,
        exporter_country_iso3: 'KOR',
        top_n: 5,
        year: 2023,
        filters: { min_trade_value_usd: 0 },
      });

      const buyersData = res.data?.data?.buyers;
      if (!buyersData || buyersData.status !== 'ok' || !buyersData.items?.length) {
        const emptyErr: any = new Error('현재 조건에 맞는 바이어를 찾지 못했습니다.');
        emptyErr.errorKind = 'empty';
        throw emptyErr;
      }

      const mappedBuyers = mapApiBuyersToViewModels(buyersData.items, hsCode, detected || hsCode);
      const grouped = groupBuyersByCountry(mappedBuyers);

      const newCategory: CategoryData = {
        label: detected || hsCode,
        hsCode,
        hsLabel: detected || '수출품목',
        icon: <Sparkles className="h-4 w-4" />,
        buyers: mappedBuyers,
        countries: grouped.map((c) => c.countryName),
      };

      setDynamicCategory(newCategory);
      setCurrentCategory(detected || hsCode);
      setStep('countries');
      setSelectedCountry(null);
      setSelectedBuyer(null);
      setSearchError(null);
      setSearchErrorKind(null);
      toast.success(`${detected || hsCode} 기준 ${grouped.length}개국, ${mappedBuyers.length}개 바이어 후보를 찾았습니다`);
    } catch (err: any) {
      // Classify the failure so the user sees an actionable message instead of stale results.
      let kind: 'network' | 'empty' | 'input' = err.errorKind || 'network';
      let msg: string;
      const status = err.response?.status;
      if (kind === 'input') {
        msg = err.message;
      } else if (kind === 'empty') {
        msg = '현재 조건에 맞는 바이어를 찾지 못했습니다.';
      } else if (status && status >= 500) {
        msg = '바이어 분석 서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.';
      } else if (status) {
        msg = err.response?.data?.detail || '요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
      } else {
        // No response at all → backend down / network error.
        msg = '서버에 연결하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.';
      }
      // Clear stale results so the error panel is shown instead of the previous search's data.
      setDynamicCategory(null);
      setCurrentCategory('');
      setStep('countries');
      setSelectedCountry(null);
      setSelectedBuyer(null);
      setSearchError(msg);
      setSearchErrorKind(kind);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // 랜딩 히어로/칩에서 넘긴 mg_search_query 를 1회 읽어 자동 검색한다.
  useEffect(() => {
    let q = '';
    try {
      q = (sessionStorage.getItem('mg_search_query') || '').trim();
      if (q) sessionStorage.removeItem('mg_search_query');
    } catch {
      /* noop */
    }
    if (!q) return;
    setSeedQuery(q);
    void handleSearch(q);
    // mount 시 1회만 — handleSearch 의존성 의도적으로 제외
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectCountry = (c: CountryRec) => { setSelectedCountry(c); setStep('buyers'); };
  const handleSelectBuyer = (b: Buyer) => { setSelectedBuyer(b); setStep('detail'); };
  const handleBackToCountries = () => { setStep('countries'); setSelectedCountry(null); setSelectedBuyer(null); };
  const handleBackToBuyers = () => { setStep('buyers'); setSelectedBuyer(null); };
  const handleApplyConditions = () => {
    // 수입실적 데이터가 없어 바이어 필터링은 하지 않는다 — 시뮬레이션 확인용 패널로만 동작.
    toast.info('수익성 시뮬레이션을 확인했습니다', { description: '바이어 목록은 필터링 없이 전체 실데이터를 표시합니다.' });
  };
  const handleResetConditions = () => {};

  const renderRightPanel = () => {
    if (!categoryData) return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 px-6 text-center">
        {searchError ? (
          searchErrorKind === 'network' ? (
            <>
              <AlertCircle className="h-12 w-12 mb-4 text-rose-300" />
              <p className="text-sm font-medium text-rose-600">{searchError}</p>
              <p className="text-xs mt-1 text-slate-500">서버 연결이 일시적으로 끊겼을 수 있어요.</p>
              {lastQuery && (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4 gap-1.5"
                  disabled={loading}
                  onClick={() => handleSearch(lastQuery)}
                >
                  {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  다시 시도
                </Button>
              )}
            </>
          ) : searchErrorKind === 'empty' ? (
            <>
              <Database className="h-12 w-12 mb-4 text-slate-200" />
              <p className="text-sm text-slate-600">{searchError}</p>
              <p className="text-xs mt-1">다른 키워드나 HS코드로 다시 검색해 보세요 (예: 스킨케어, 홍삼, 여성의류, 반도체)</p>
            </>
          ) : (
            <>
              <AlertCircle className="h-12 w-12 mb-4 text-amber-300" />
              <p className="text-sm text-amber-600">{searchError}</p>
              <p className="text-xs mt-1">검색어를 바꿔 다시 시도해 보세요 (예: 스킨케어, 홍삼, 여성의류, 반도체)</p>
            </>
          )
        ) : (
          <>
            <Search className="h-12 w-12 mb-4 text-slate-200" />
            <p className="text-sm">위 검색바에 제품 키워드나 HS코드를 입력해 바이어를 찾아보세요</p>
            <p className="text-xs mt-1">예: 스킨케어, 홍삼, 여성의류, 반도체</p>
          </>
        )}
      </div>
    );
    if (step === 'countries') return <CountryListPanel countries={countryRecs} categoryLabel={currentCategory} categoryHs={categoryData.hsCode} onSelectCountry={handleSelectCountry} onOpenConditions={() => setShowConditionPanel(true)} hasConditions={hasConditions} />;
    if (step === 'buyers' && selectedCountry) return <BuyerListPanel country={selectedCountry} onSelectBuyer={handleSelectBuyer} onBack={handleBackToCountries} onOpenConditions={() => setShowConditionPanel(true)} hasConditions={hasConditions} />;
    if (step === 'detail' && selectedBuyer) return <BuyerDetailPanel buyer={selectedBuyer} onBack={handleBackToBuyers} inputHsCode={inputHsCode || '330303'} category={currentCategory} />;
    return null;
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-slate-50">
      <Toaster position="top-center" richColors />
      <header className="bg-white border-b border-slate-200 flex-shrink-0">
        <div className="h-12 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            {onClose && (
              <button onClick={onClose} className="flex items-center gap-1.5 text-sm font-medium text-slate-700 hover:text-blue-600 transition-colors mr-2">
                <ArrowLeft className="h-4 w-4" />
                <span className="font-bold">MarketGate</span>
              </button>
            )}
            <span className="text-xs font-bold text-slate-400 tracking-wider">HS {selectedBuyer?.hsCode || categoryData?.hsCode || inputHsCode || '—'}</span>
            <span className="text-xs text-slate-500">({selectedBuyer?.hsLabel || categoryData?.hsLabel || '스킨케어'})</span>
          </div>
          <div className="flex items-center gap-2"><Button variant="outline" size="sm" className="h-7 text-xs gap-1.5"><LayoutGrid className="h-3.5 w-3.5" />품 모드</Button></div>
        </div>
        <DataStatsBanner />
        <SearchBar onSearch={handleSearch} activeCategory={currentCategory} loading={loading} initialQuery={seedQuery} />
      </header>
      <div className="flex-1 overflow-hidden relative">
        {loading && <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center"><Loader2 className="h-8 w-8 text-blue-600 animate-spin mb-3" /><p className="text-sm text-slate-600">바이어 데이터를 분석 중입니다...</p><p className="text-xs text-slate-400 mt-1">KOTRA 공공데이터 CSV 기반 분석 중</p></div>}
        {renderRightPanel()}
      </div>
      <ExportConditionPanel open={showConditionPanel} onClose={() => setShowConditionPanel(false)} conditions={conditions} onChange={setConditions} onApply={handleApplyConditions} onReset={handleResetConditions} />
    </div>
  );
}
