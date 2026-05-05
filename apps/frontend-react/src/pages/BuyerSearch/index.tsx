import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  Send, Mic, ArrowLeft, LayoutGrid, Building2, Mail, Phone, Globe, CheckCircle2,
  Download, Share2, Info, ChevronRight, Star, FileText, BarChart3, Sparkles,
  Loader2, Hash, Database, AlertCircle, RefreshCw, ShieldCheck, Shield,
  TrendingUp, Clock, ExternalLink, Search, Zap, Cpu, Shirt, Stethoscope,
  Settings2, X, Calculator, DollarSign, Percent, TrendingDown, ArrowUpRight,
  Globe2, Users, Activity, ChevronLeft, MapPin, Award, FileDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Toaster, toast } from 'sonner';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip, Legend, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';

/* ── Types ── */
interface ImportMonth { month: string; amount: number; prevYearAmount: number; }
interface RFMScore { R: number; F: number; M: number; }
interface ExportConditions {
  productionCapacity: string; moq: string; targetAmountKrw: string;
  unitPriceUSD: number; costPriceUSD: number; logisticsRate: number;
  tariffRate: number; exchangeRate: number; certifications: string[];
}
interface DNBData {
  transactionDetail: { transactionID: string; transactionTimestamp: string; status: string };
  inquiryDetail: { duns: string; productID: string; reportFormat: string; orderReason: string; tradeUp: string; customerReference: string; language: string };
  organization: {
    primaryName: string; duns: string; countryISOAlpha2Code: string; countryName: string;
    primaryAddress: { streetAddress: string; addressLocality: string; addressRegion: string; postalCode: string };
    telephone: string; fax: string;
    registerNumbers: { type: string; number: string }[];
    industryCodes: { type: string; code: string; description: string }[];
    numberOfEmployees: number; salesRevenue: number; capitalDetails: number;
    corporateLinkage: { domesticUltimate?: { name: string; address: string; duns: string }; globalUltimate?: { name: string; address: string; duns: string }; parent?: { name: string; address: string; duns: string } };
    currentPrincipals: { name: string; title: string }[];
    competitors: { name: string; salesRevenue: string; employees: number }[];
    formerPrimaryNames: string[];
  };
  contents: { contentFormat: string; contentObject: string; fileName: string };
}
interface Buyer {
  id: string; rank: number; name: string; legalName: string; industry: string;
  country: string; region: string; dataSource: string; dataDate: string; csvTrace: string;
  contactName: string; contactRole: string; email: string; phone: string; website: string;
  contactVerified: boolean; contactVerifiedDate: string;
  score: number; scoreLabel: string;
  metrics: { label: string; value: number; benchmark: number }[];
  hsCode: string; hsLabel: string; keywords: string[];
  reasons: { text: string; highlight: string; source: string }[];
  trustLevel: string; trustBadge: 'platinum' | 'gold' | 'silver';
  importHistory: ImportMonth[]; totalImportValue: string; importGrowthRate: number;
  rfm: RFMScore; lastUpdatedDays: number;
  competitors?: { name: string; score: number; importValue: string; growth: number; country: string }[];
  dnbData?: DNBData;
}
interface CategoryData { label: string; hsCode: string; hsLabel: string; icon: React.ReactNode; buyers: Buyer[]; countries: string[]; }
interface Message { role: 'user' | 'ai' | 'error'; text: string; chips?: string[]; }
interface CountryRec { countryName: string; countryCode: string; flag: string; buyerCount: number; avgScore: number; totalImportValue: string; avgGrowthRate: number; topBuyerName: string; topBuyerScore: number; buyers: Buyer[]; }
type Step = 'countries' | 'buyers' | 'detail';

/* ── Helpers ── */
function generateImportHistory(baseAmount: number, growth: number): ImportMonth[] {
  const months: ImportMonth[] = [];
  const labels = ['2024.05','2024.06','2024.07','2024.08','2024.09','2024.10','2024.11','2024.12','2025.01','2025.02','2025.03','2025.04','2025.05','2025.06','2025.07','2025.08','2025.09','2025.10','2025.11','2025.12','2026.01','2026.02','2026.03','2026.04'];
  for (let i = 0; i < 24; i++) {
    const amount = Math.round(baseAmount * (1 + Math.sin(i/3)*0.15) * (1 + (growth/100)*(i/24)) * (0.9 + Math.random()*0.2));
    months.push({ month: labels[i], amount, prevYearAmount: Math.round(amount * (0.7 + Math.random()*0.4)) });
  }
  return months;
}
function createDNBData(ov: { duns?: string; primaryName?: string; countryCode?: string; countryName?: string; employees?: number; revenue?: number; capital?: number; tel?: string } = {}): DNBData {
  const duns = ov.duns || '804735132';
  const cc = ov.countryCode || 'US';
  return {
    transactionDetail: { transactionID: `TXN-${Math.random().toString(36).slice(2,10).toUpperCase()}`, transactionTimestamp: new Date().toISOString(), status: 'OK' },
    inquiryDetail: { duns, productID: 'birstd', reportFormat: 'PDF', orderReason: '6332', tradeUp: 'hq', customerReference: 'MarketGate buyer verification', language: 'ko' },
    organization: {
      primaryName: ov.primaryName || 'GORMAN MFG CO INC', duns, countryISOAlpha2Code: cc, countryName: ov.countryName || '미국',
      primaryAddress: { streetAddress: '492 Koller St', addressLocality: 'San Francisco', addressRegion: 'CA', postalCode: '94110' },
      telephone: ov.tel || '+1-415-555-0123', fax: '+1-415-555-0124',
      registerNumbers: [{ type: '사업자등록번호', number: '12-3456789' }, { type: '법인등록번호', number: '123456-7890123' }],
      industryCodes: [{ type: 'SIC', code: '3541', description: 'Machine Tools, Metal Cutting Types' }, { type: 'NAICS', code: '333517', description: 'Machine Tool Manufacturing' }],
      numberOfEmployees: ov.employees || 150,
      salesRevenue: ov.revenue || 50000000,
      capitalDetails: ov.capital || 1000000,
      corporateLinkage: { domesticUltimate: { name: 'Gorman Manufacturing Holdings', address: '492 Koller St, San Francisco, CA 94110', duns: '804735133' }, globalUltimate: { name: 'Gorman Manufacturing Holdings', address: '492 Koller St, San Francisco, CA 94110', duns: '804735133' } },
      currentPrincipals: [{ name: 'John Gorman', title: 'CEO / President' }, { name: 'Sarah Chen', title: 'CFO' }, { name: 'Michael Park', title: 'VP Operations' }],
      competitors: [{ name: 'Precision Tools Inc', salesRevenue: '$42M', employees: 120 }, { name: 'MetalWorks Corp', salesRevenue: '$38M', employees: 95 }],
      formerPrimaryNames: ['Gorman Tool & Die Co.'],
    },
    contents: { contentFormat: 'application/pdf', contentObject: '', fileName: 'dnb_report.pdf' },
  };
}
const KEYWORD_MAP: Record<string, string> = { 'k-뷰티': 'K-뷰티', 'k뷰티': 'K-뷰티', '뷰티': 'K-뷰티', '화장품': 'K-뷰티', '스킨': 'K-뷰티', '스킨케어': 'K-뷰티', '세럼': 'K-뷰티', '메이크업': 'K-뷰티', '건강': '건강식품', '건강식품': '건강식품', '홍삼': '건강식품', '인삼': '건강식품', '프로바이오틱스': '건강식품', '건기식': '건강식품', '영양제': '건강식품', '패션': 'K-패션', 'k-패션': 'K-패션', 'k패션': 'K-패션', '의류': 'K-패션', '옷': 'K-패션', '한복': 'K-패션', '디자이너': 'K-패션', '반도체': '반도체', '칩': '반도체', '메모리': '반도체', '전자': '반도체', 'semiconductor': '반도체', 'chip': '반도체', 'skincare': 'K-뷰티', 'health': '건강식품', 'fashion': 'K-패션', 'apparel': 'K-패션' };
function detectCategory(input: string): string | null { const lower = input.toLowerCase().replace(/[\s\-]/g, ''); for (const [k, v] of Object.entries(KEYWORD_MAP)) { if (lower.includes(k.replace(/[\s\-]/g, ''))) return v; } if (input.startsWith('33')) return 'K-뷰티'; if (input.startsWith('21')) return '건강식품'; if (input.startsWith('62')) return 'K-패션'; if (input.startsWith('85')) return '반도체'; return null; }
function copyToClipboard(text: string) { navigator.clipboard.writeText(text).then(() => toast.success('클립보드에 복사되었습니다', { description: text })); }
function formatDate() { const d = new Date(); return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`; }
function parseImportValue(val: string) { const n = parseFloat(val.replace(/[^0-9.]/g, '')); return val.includes('M') ? n*1000000 : n*1000; }
function groupByCountry(buyers: Buyer[]): CountryRec[] { const m = new Map<string, Buyer[]>(); for (const b of buyers) { const code = b.country.split(' ')[0]; const name = b.country.split(' ').slice(1).join(' '); const key = `${code}|${name}`; if (!m.has(key)) m.set(key, []); m.get(key)!.push(b); } const res: CountryRec[] = []; for (const [key, list] of m.entries()) { const [code, name] = key.split('|'); const fm: Record<string,string> = { de: '🇩🇪', nl: '🇳🇱', cn: '🇨🇳', us: '🇺🇸', jp: '🇯🇵', fr: '🇫🇷', tw: '🇹🇼', vn: '🇻🇳' }; const tv = list.reduce((s, b) => s + parseImportValue(b.totalImportValue), 0); const tg = list.reduce((s, b) => s + b.importGrowthRate, 0); res.push({ countryName: name, countryCode: code, flag: fm[code] || '🌐', buyerCount: list.length, avgScore: Math.round(list.reduce((s, b) => s + b.score, 0) / list.length), totalImportValue: `$${(tv/1000000).toFixed(1)}M`, avgGrowthRate: Math.round(tg / list.length), topBuyerName: list[0].name, topBuyerScore: list[0].score, buyers: list.sort((a, b) => b.score - a.score) }); } return res.sort((a, b) => b.avgScore - a.avgScore); }
function useCountUp(target: number, duration = 2000) { const [value, setValue] = useState(0); useEffect(() => { let start = 0; const step = (ts: number) => { if (!start) start = ts; const p = Math.min((ts - start) / duration, 1); setValue(Math.floor(p * target)); if (p < 1) requestAnimationFrame(step); }; const raf = requestAnimationFrame(step); return () => cancelAnimationFrame(raf); }, [target, duration]); return value; }

/* ── Data ── */
const CATEGORIES: CategoryData[] = [
  {
    label: 'K-뷰티', hsCode: '330499', hsLabel: '스킨케어', icon: <Sparkles className="h-4 w-4" />, countries: ['독일', '네덜란드'],
    buyers: [
      { id: 'MG-001', rank: 1, name: 'Beauty Wholesale GmbH', legalName: 'beauty wholesale gmbh', industry: '뷰티 유통사', country: 'de 독일', region: '함부르크', dataSource: 'KOTRA 글로벌 바이어 정보', dataDate: '2026.04.10', csvTrace: 'kotra_buyers_202604.csv / row 1,847', contactName: 'Ms. Anna Schmidt', contactRole: '담당자 Procurement Team', email: 'contact@beauty-wholesale.de', phone: '+49-40-1234-5678', website: 'www.beauty-wholesale.de', contactVerified: true, contactVerifiedDate: '2026.04.10', score: 92, scoreLabel: '매우 적합', metrics: [{ label: '수입 이력 매칭', value: 95, benchmark: 72 }, { label: '시장 성장률', value: 88, benchmark: 65 }, { label: 'GDP 규모', value: 78, benchmark: 80 }, { label: '거리/물류 이점', value: 85, benchmark: 60 }], hsCode: '330499', hsLabel: '스킨케어', keywords: ['skincare', 'serum', 'k-beauty', 'moisturizing'], reasons: [{ text: '최근 2년간 스킨케어 품목 수입 실적 보유 (누적 $2.4M)', highlight: '수입 실적', source: 'KOTRA 수출입 DB' }, { text: '한국 화장품 유통 채널 확장 중 (2025년 신규 매장 12개)', highlight: '유통 채널 확장', source: 'Company Annual Report' }, { text: '온라인/오프라인 복합 유통망 보유 (전국 45개 매장)', highlight: '복합 유통망', source: 'Trade Map Germany' }], trustLevel: '높음', trustBadge: 'platinum', importHistory: generateImportHistory(120000, 18), totalImportValue: '$2.4M', importGrowthRate: 18, rfm: { R: 92, F: 85, M: 88 }, lastUpdatedDays: 2, competitors: [{ name: 'CosmoDirect GmbH', score: 84, importValue: '$1.8M', growth: 12, country: '독일' }, { name: 'BeautyNet Europe', score: 79, importValue: '$1.3M', growth: 8, country: '네덜란드' }, { name: 'SkinTrend Hamburg', score: 76, importValue: '$0.9M', growth: -3, country: '독일' }], dnbData: createDNBData({ duns: '804735132', primaryName: 'Beauty Wholesale GmbH', countryCode: 'DE', countryName: '독일', employees: 320, revenue: 78000000, capital: 5000000, tel: '+49-40-1234-5678' }) },
      { id: 'MG-002', rank: 2, name: 'EuroBeauty Distribution AG', legalName: 'eurobeauty distribution ag', industry: '화장품 수입·유통', country: 'de 독일', region: '뮌헨', dataSource: 'KOTRA 글로벌 바이어 정보', dataDate: '2026.04.08', csvTrace: 'kotra_buyers_202604.csv / row 2,103', contactName: 'Mr. Klaus Weber', contactRole: '담당자 Import Manager', email: 'klaus.weber@eurobeauty.de', phone: '+49-89-8765-4321', website: 'www.eurobeauty.de', contactVerified: true, contactVerifiedDate: '2026.04.08', score: 87, scoreLabel: '적합', metrics: [{ label: '수입 이력 매칭', value: 82, benchmark: 72 }, { label: '시장 성장률', value: 90, benchmark: 65 }, { label: 'GDP 규모', value: 85, benchmark: 80 }, { label: '거리/물류 이점', value: 80, benchmark: 60 }], hsCode: '330499', hsLabel: '스킨케어', keywords: ['skincare', 'anti-aging', 'k-beauty', 'wholesale'], reasons: [{ text: '유럽 남부 지역 K-뷰티 독점 유망 (이탈리아·스페인 총판)', highlight: '독점 유망', source: 'KOTRA 지사 보고서' }, { text: '면세점 채널 입점 경험 다수 (프랑크푸르트·뮌헨 공항)', highlight: '면세점 채널', source: 'Duty Free Korea' }, { text: '올해 매출 목표 대비 수입 의지 높음 (2026년 목표 $5M)', highlight: '수입 의지', source: 'Company Q1 Report' }], trustLevel: '높음', trustBadge: 'gold', importHistory: generateImportHistory(95000, 22), totalImportValue: '$1.9M', importGrowthRate: 22, rfm: { R: 85, F: 78, M: 82 }, lastUpdatedDays: 4, competitors: [{ name: 'CosmoDirect GmbH', score: 84, importValue: '$1.8M', growth: 12, country: '독일' }, { name: 'BeautyNet Europe', score: 79, importValue: '$1.3M', growth: 8, country: '네덜란드' }], dnbData: createDNBData({ duns: '333444555', primaryName: 'EuroBeauty Distribution AG', countryCode: 'DE', countryName: '독일' }) },
      { id: 'MG-003', rank: 3, name: 'SkinCare Direct BV', legalName: 'skincare direct b.v.', industry: '온라인 뷰티 리테일', country: 'nl 네덜란드', region: '암스테르담', dataSource: '관세청 수출입 통계', dataDate: '2026.04.05', csvTrace: 'customs_2026q1.csv / row 4,221', contactName: 'Ms. Sophie van Dijk', contactRole: '담당자 Buying Team', email: 'sophie@skincaredirect.nl', phone: '+31-20-555-0199', website: 'www.skincaredirect.nl', contactVerified: true, contactVerifiedDate: '2026.04.05', score: 83, scoreLabel: '적합', metrics: [{ label: '수입 이력 매칭', value: 75, benchmark: 72 }, { label: '시장 성장률', value: 92, benchmark: 65 }, { label: 'GDP 규모', value: 70, benchmark: 80 }, { label: '거리/물류 이점', value: 88, benchmark: 60 }], hsCode: '330499', hsLabel: '스킨케어', keywords: ['skincare', 'serum', 'e-commerce', 'moisturizing'], reasons: [{ text: '네덜란드 온라인 뷰티 시장 점유율 상위 5%', highlight: '시장 점유율 상위 5%', source: 'EcommerceNL 2026' }, { text: '한국 브랜드 직구 플랫폼 운영 중 (월 방문 120만)', highlight: '직구 플랫폼', source: 'SimilarWeb Analytics' }, { text: '유럽 물류 허브 활용한 재수출 가능 (독일·벨기에 2일 배송)', highlight: '재수출 가능', source: 'Logistics Report' }], trustLevel: '보통', trustBadge: 'silver', importHistory: generateImportHistory(70000, 25), totalImportValue: '$1.5M', importGrowthRate: 25, rfm: { R: 78, F: 88, M: 75 }, lastUpdatedDays: 7, dnbData: createDNBData({ duns: '999888777', primaryName: 'SkinCare Direct B.V.', countryCode: 'NL', countryName: '네덜란드', employees: 85, revenue: 42000000, capital: 2000000, tel: '+31-20-555-0199' }) },
    ],
  },
  {
    label: '건강식품', hsCode: '210690', hsLabel: '건강기능식품', icon: <Stethoscope className="h-4 w-4" />, countries: ['중국', '미국'],
    buyers: [
      { id: 'MG-011', rank: 1, name: 'Shanghai Wellness Import Co.', legalName: 'shanghai wellness import co., ltd.', industry: '건강식품 수입·유통', country: 'cn 중국', region: '상하이', dataSource: 'KOTRA 상해 무역관', dataDate: '2026.04.12', csvTrace: 'kotra_shanghai_202604.csv / row 892', contactName: 'Mr. Li Wei', contactRole: '담당자 Import Director', email: 'liwei@swimport.cn', phone: '+86-21-5555-0123', website: 'www.swimport.cn', contactVerified: true, contactVerifiedDate: '2026.04.12', score: 89, scoreLabel: '매우 적합', metrics: [{ label: '수입 이력 매칭', value: 90, benchmark: 68 }, { label: '시장 성장률', value: 95, benchmark: 70 }, { label: 'GDP 규모', value: 85, benchmark: 85 }, { label: '거리/물류 이점', value: 72, benchmark: 55 }], hsCode: '210690', hsLabel: '건강기능식품', keywords: ['health food', 'ginseng', 'probiotics', 'red ginseng'], reasons: [{ text: '한국산 홍삼 제품 연간 수입액 $4.2M (상위 3위)', highlight: '홍삼 제품 수입', source: 'China Customs 2025' }, { text: '티몰·징둥 직영 플래그십 스토어 운영 중', highlight: '직영 플래그십', source: 'Tmall Partner Report' }, { text: '2026년 Q1 한국 건강식품 수입액 전년 대비 34% 증가', highlight: '34% 증가', source: 'KOTRA 상해 무역관' }], trustLevel: '높음', trustBadge: 'platinum', importHistory: generateImportHistory(220000, 34), totalImportValue: '$4.2M', importGrowthRate: 34, rfm: { R: 90, F: 88, M: 92 }, lastUpdatedDays: 1, competitors: [{ name: 'Beijing Health Link', score: 81, importValue: '$2.9M', growth: 15, country: '중국' }, { name: 'Guangzhou NutriCorp', score: 75, importValue: '$1.8M', growth: 9, country: '중국' }], dnbData: createDNBData({ duns: '112233445', primaryName: 'Shanghai Wellness Import Co., Ltd.', countryCode: 'CN', countryName: '중국', employees: 450, revenue: 120000000, capital: 15000000, tel: '+86-21-5555-0123' }) },
      { id: 'MG-012', rank: 2, name: 'VitaCare USA Inc.', legalName: 'vitacare usa inc.', industry: '건강보조식품 유통', country: 'us 미국', region: '캘리포니아', dataSource: 'KITA USA 사무소', dataDate: '2026.04.09', csvTrace: 'kita_usa_202604.csv / row 341', contactName: 'Ms. Sarah Johnson', contactRole: '담당자 Sourcing Manager', email: 'sarah@vitacareusa.com', phone: '+1-213-444-7890', website: 'www.vitacareusa.com', contactVerified: true, contactVerifiedDate: '2026.04.09', score: 85, scoreLabel: '적합', metrics: [{ label: '수입 이력 매칭', value: 82, benchmark: 68 }, { label: '시장 성장률', value: 80, benchmark: 70 }, { label: 'GDP 규모', value: 92, benchmark: 85 }, { label: '거리/물류 이점', value: 65, benchmark: 55 }], hsCode: '210690', hsLabel: '건강기능식품', keywords: ['probiotics', 'collagen', 'vitamin', 'korean ginseng'], reasons: [{ text: '미국 서부 지역 한국 건강식품 1위 유통사', highlight: '1위 유통사', source: 'Nielsen Health US' }, { text: 'Whole Foods·CVS 입점 완료 (2025년 확장)', highlight: 'Whole Foods·CVS', source: 'Retailer Data' }, { text: '자체 온라인몰 월 주문 85,000건', highlight: '월 주문 85,000건', source: 'Internal Report' }], trustLevel: '높음', trustBadge: 'gold', importHistory: generateImportHistory(180000, 15), totalImportValue: '$3.1M', importGrowthRate: 15, rfm: { R: 82, F: 75, M: 88 }, lastUpdatedDays: 5, dnbData: createDNBData({ duns: '556677889', primaryName: 'VitaCare USA Inc.', countryCode: 'US', countryName: '미국' }) },
    ],
  },
  {
    label: 'K-패션', hsCode: '6203', hsLabel: '여성 의류', icon: <Shirt className="h-4 w-4" />, countries: ['일본', '프랑스'],
    buyers: [
      { id: 'MG-021', rank: 1, name: 'Tokyo Style Lab Co.', legalName: 'tokyo style lab co., ltd.', industry: '패션 리테일·기획', country: 'jp 일본', region: '도쿄', dataSource: 'KOTRA 오사카 무역관', dataDate: '2026.04.11', csvTrace: 'kotra_osaka_202604.csv / row 567', contactName: 'Ms. Yuki Tanaka', contactRole: '담당자 Buyer Lead', email: 'yuki@tokyostylelab.jp', phone: '+81-3-3333-4444', website: 'www.tokyostylelab.jp', contactVerified: true, contactVerifiedDate: '2026.04.11', score: 91, scoreLabel: '매우 적합', metrics: [{ label: '수입 이력 매칭', value: 93, benchmark: 70 }, { label: '시장 성장률', value: 82, benchmark: 60 }, { label: 'GDP 규모', value: 88, benchmark: 82 }, { label: '거리/물류 이점', value: 90, benchmark: 65 }], hsCode: '6203', hsLabel: '여성 의류', keywords: ['fashion', 'womenswear', 'k-fashion', 'seoul style'], reasons: [{ text: '도쿄·오사카·후쿠오카 3개 직영 매장 운영', highlight: '3개 직영 매장', source: 'Company IR' }, { text: '한국 디자이너 브랜드 단독 계약 8건 체결', highlight: '단독 계약 8건', source: 'Fashion Biz Japan' }, { text: '2026 S/S 한국 브랜드 수주액 전년 대비 28% 증가', highlight: '28% 증가', source: 'Textile News' }], trustLevel: '높음', trustBadge: 'platinum', importHistory: generateImportHistory(150000, 28), totalImportValue: '$2.8M', importGrowthRate: 28, rfm: { R: 94, F: 80, M: 90 }, lastUpdatedDays: 3, dnbData: createDNBData({ duns: '998877665', primaryName: 'Tokyo Style Lab Co., Ltd.', countryCode: 'JP', countryName: '일본', employees: 220, revenue: 95000000, capital: 8000000, tel: '+81-3-3333-4444' }) },
      { id: 'MG-022', rank: 2, name: 'Paris Mode Select', legalName: 'paris mode select sarl', industry: '프랑스 패션 셀렉트숍', country: 'fr 프랑스', region: '파리', dataSource: 'KOTRA 파리 무역관', dataDate: '2026.04.06', csvTrace: 'kotra_paris_202604.csv / row 231', contactName: 'Mme. Camille Dubois', contactRole: '담당자 Founder', email: 'camille@parismodeselect.fr', phone: '+33-1-4444-5555', website: 'www.parismodeselect.fr', contactVerified: true, contactVerifiedDate: '2026.04.06', score: 78, scoreLabel: '적합', metrics: [{ label: '수입 이력 매칭', value: 72, benchmark: 70 }, { label: '시장 성장률', value: 75, benchmark: 60 }, { label: 'GDP 규모', value: 80, benchmark: 82 }, { label: '거리/물류 이점', value: 68, benchmark: 65 }], hsCode: '6203', hsLabel: '여성 의류', keywords: ['fashion', 'paris', 'korean designer', 'boutique'], reasons: [{ text: '마레·생제르맹 2개 셀렉트숍 운영 (고객층 20대~30대)', highlight: '마레·생제르맹', source: 'Paris Retail Guide' }, { text: '한국 패션 브랜드 팝업스토어 진행 경험', highlight: '팝업스토어 경험', source: 'Event History' }, { text: '온라인 채널 확장 중 (인스타그램 팔로워 18만)', highlight: '팔로워 18만', source: 'Social Media Metrics' }], trustLevel: '보통', trustBadge: 'silver', importHistory: generateImportHistory(55000, 12), totalImportValue: '$0.9M', importGrowthRate: 12, rfm: { R: 70, F: 65, M: 72 }, lastUpdatedDays: 12, dnbData: createDNBData({ duns: '554433221', primaryName: 'Paris Mode Select SARL', countryCode: 'FR', countryName: '프랑스' }) },
    ],
  },
  {
    label: '반도체', hsCode: '8541', hsLabel: '반도체 소자', icon: <Cpu className="h-4 w-4" />, countries: ['대만', '베트남'],
    buyers: [
      { id: 'MG-031', rank: 1, name: 'Taiwan ChipSource Corp.', legalName: 'taiwan chipsource corp.', industry: '반도체 부품 유통', country: 'tw 대만', region: '신주', dataSource: 'KOTRA 타이페이 무역관', dataDate: '2026.04.13', csvTrace: 'kotra_taipei_202604.csv / row 104', contactName: 'Mr. Chen Ming-Hao', contactRole: '담당자 VP Procurement', email: 'chen.mh@chipsource.tw', phone: '+886-3-555-6789', website: 'www.chipsource.tw', contactVerified: true, contactVerifiedDate: '2026.04.13', score: 95, scoreLabel: '매우 적합', metrics: [{ label: '수입 이력 매칭', value: 98, benchmark: 75 }, { label: '시장 성장률', value: 92, benchmark: 68 }, { label: 'GDP 규모', value: 80, benchmark: 78 }, { label: '거리/물류 이점', value: 88, benchmark: 58 }], hsCode: '8541', hsLabel: '반도체 소자', keywords: ['semiconductor', 'chip', 'memory', 'foundry'], reasons: [{ text: 'TSMC 2차 협력사 등록, 한국 부품 수입액 연간 $12M', highlight: 'TSMC 2차 협력사', source: 'TSMC Supplier Registry' }, { text: '메모리 반도체 한국산 의존도 45% (삼성·SK)', highlight: '의존도 45%', source: 'Taiwan Semiconductor Yearbook' }, { text: '2026년 Q2 수입 물량 전년 동기 대비 52% 증가', highlight: '52% 증가', source: 'MOEA Taiwan' }], trustLevel: '높음', trustBadge: 'platinum', importHistory: generateImportHistory(650000, 52), totalImportValue: '$12.1M', importGrowthRate: 52, rfm: { R: 96, F: 90, M: 95 }, lastUpdatedDays: 1, competitors: [{ name: 'Vietnam SemiTech', score: 82, importValue: '$4.5M', growth: 35, country: '베트남' }, { name: 'SG Electronics', score: 74, importValue: '$2.1M', growth: 18, country: '싱가포르' }], dnbData: createDNBData({ duns: '776655443', primaryName: 'Taiwan ChipSource Corp.', countryCode: 'TW', countryName: '대만', employees: 680, revenue: 280000000, capital: 50000000, tel: '+886-3-555-6789' }) },
      { id: 'MG-032', rank: 2, name: 'Hanoi Tech Components', legalName: 'hanoi tech components jsc', industry: '전자부품 수입·조립', country: 'vn 베트남', region: '하노이', dataSource: 'KOTRA 하노이 무역관', dataDate: '2026.04.07', csvTrace: 'kotra_hanoi_202604.csv / row 778', contactName: 'Ms. Nguyen Thi Lan', contactRole: '담당자 Supply Chain Director', email: 'lan.nt@hanoitech.vn', phone: '+84-24-3333-4444', website: 'www.hanoitech.vn', contactVerified: true, contactVerifiedDate: '2026.04.07', score: 81, scoreLabel: '적합', metrics: [{ label: '수입 이력 매칭', value: 78, benchmark: 75 }, { label: '시장 성장률', value: 88, benchmark: 68 }, { label: 'GDP 규모', value: 65, benchmark: 78 }, { label: '거리/물류 이점', value: 92, benchmark: 58 }], hsCode: '8541', hsLabel: '반도체 소자', keywords: ['semiconductor', 'assembly', 'samsung partner', ' Vietnam'], reasons: [{ text: '삼성전자 베트남 공장 1차 협력사 (부품 공급)', highlight: '삼성 1차 협력사', source: 'Samsung Vietnam Supplier List' }, { text: '하노이·호치민 물류 허브 활용 (한국 3일 배송)', highlight: '3일 배송', source: 'Vietnam Logistics Report' }, { text: '2026년 반도체 조립 물량 2배 증가 계획', highlight: '2배 증가 계획', source: 'Company Press Release' }], trustLevel: '보통', trustBadge: 'gold', importHistory: generateImportHistory(220000, 38), totalImportValue: '$3.8M', importGrowthRate: 38, rfm: { R: 80, F: 85, M: 76 }, lastUpdatedDays: 8, dnbData: createDNBData({ duns: '334455667', primaryName: 'Hanoi Tech Components JSC', countryCode: 'VN', countryName: '베트남' }) },
    ],
  },
];

/* ── Reusable small components ── */
const DataStatsBanner: React.FC = () => {
  const countries = useCountUp(47, 1500);
  const buyers = useCountUp(12847, 2000);
  return (
    <div className="bg-white border-b border-slate-200 px-4 py-3">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center gap-1.5 text-xs text-slate-500"><Globe2 className="h-4 w-4 text-blue-600" /><span className="font-bold text-slate-800">{countries}</span><span>개국 수출 대상국</span></div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-1.5 text-xs text-slate-500"><Users className="h-4 w-4 text-emerald-600" /><span className="font-bold text-slate-800">{buyers.toLocaleString()}</span><span>개 글로벌 바이어</span></div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-1.5 text-xs text-slate-500"><Activity className="h-4 w-4 text-amber-600" /><span className="font-bold text-slate-800">240만</span><span>건 수입실적 데이터</span></div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-1 text-[10px] text-slate-400"><span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />KOTRA·관세청·World Bank 실시간 연동</div>
      </div>
    </div>
  );
};

const TrustBadge: React.FC<{ level: 'platinum' | 'gold' | 'silver'; days: number }> = ({ level, days }) => {
  const c = { platinum: { label: 'Platinum', color: 'bg-slate-800 text-white', icon: <ShieldCheck className="h-3 w-3" /> }, gold: { label: 'Gold', color: 'bg-amber-50 text-amber-700 border border-amber-200', icon: <Shield className="h-3 w-3" /> }, silver: { label: 'Silver', color: 'bg-slate-100 text-slate-600 border border-slate-200', icon: <Shield className="h-3 w-3" /> } }[level];
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${c.color}`}>{c.icon} {c.label}</span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <p className="font-semibold">{level === 'platinum' ? '최고 신뢰도' : level === 'gold' ? '높은 신뢰도' : '일반 신뢰도'}</p>
          <p className="text-xs mt-1">{level === 'platinum' ? '연락처 + 수입실적 모두 검증됨' : level === 'gold' ? '수입실적 확인됨 (연락처는 2차 검증 중)' : '추정/파생 데이터 기반'}</p>
          <p className="text-[10px] text-slate-400 mt-1">{days}일 전 최종 확인</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

const ImportTrendChart: React.FC<{ data: ImportMonth[] }> = ({ data }) => (
  <div className="h-72 w-full">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorAmt" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/><stop offset="95%" stopColor="#10b981" stopOpacity={0}/></linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={3} stroke="#94a3b8" />
        <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" tickFormatter={(v) => `$${(v/1000).toFixed(0)}K`} />
        <ReTooltip formatter={(value: number, name: string) => [`$${value.toLocaleString()}`, name === 'amount' ? '수입액' : '전년 동기']} labelFormatter={(label) => label} contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="amount" name="수입액" stroke="#10b981" fillOpacity={1} fill="url(#colorAmt)" strokeWidth={2} dot={false} />
        <Area type="monotone" dataKey="prevYearAmount" name="전년 동기" stroke="#94a3b8" fill="none" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  </div>
);

const RFMChart: React.FC<{ rfm: RFMScore; name: string }> = ({ rfm, name }) => (
  <div className="h-56 w-full">
    <ResponsiveContainer width="100%" height="100%">
      <RadarChart cx="50%" cy="50%" outerRadius="70%" data={[{ subject: 'Recency\n(최근성)', A: rfm.R, fullMark: 100 }, { subject: 'Frequency\n(빈도)', A: rfm.F, fullMark: 100 }, { subject: 'Monetary\n(금액)', A: rfm.M, fullMark: 100 }]}>
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: '#64748b' }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
        <Radar name={name} dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} strokeWidth={2} />
        <ReTooltip formatter={(value: number) => [`${value}점`, '적합도']} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
      </RadarChart>
    </ResponsiveContainer>
  </div>
);

const ScoreBar: React.FC<{ label: string; value: number; benchmark: number }> = ({ label, value, benchmark }) => (
  <div className="mb-3 last:mb-0">
    <div className="flex justify-between items-center mb-1.5"><span className="text-xs text-slate-600">{label}</span><span className="text-xs font-semibold text-slate-800">{value}점</span></div>
    <div className="relative h-2.5 bg-slate-100 rounded-full overflow-hidden"><div className="absolute top-0 left-0 h-full bg-emerald-500 rounded-full transition-all duration-700" style={{ width: `${value}%` }} /><div className="absolute top-0 h-full w-0.5 bg-slate-400 transition-all duration-700" style={{ left: `${benchmark}%` }} /></div>
    <div className="flex justify-end mt-0.5"><span className="text-[10px] text-slate-400">동종 평균 {benchmark}점</span></div>
  </div>
);

const ContactRow: React.FC<{ icon: React.ReactNode; label: string; value: string; action?: 'copy' | 'link' | 'phone'; href?: string }> = ({ icon, label, value, action, href }) => {
  const handleClick = () => { if (action === 'copy') copyToClipboard(value); else if (action === 'link' && href) window.open(href, '_blank', 'noopener,noreferrer'); else if (action === 'phone' && href) window.location.href = href; };
  return (
    <div className="flex items-start gap-3 py-2 group">
      <div className="mt-0.5 text-slate-400">{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-slate-500 mb-0.5">{label}</div>
        <button onClick={handleClick} className={`text-sm text-slate-800 break-all text-left ${action ? 'hover:text-blue-600 hover:underline cursor-pointer' : ''}`}>{value}</button>
      </div>
      {action === 'copy' && (
        <TooltipProvider><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity" onClick={handleClick}><FileText className="h-3.5 w-3.5" /></Button></TooltipTrigger><TooltipContent side="left"><p>복사하기</p></TooltipContent></Tooltip></TooltipProvider>
      )}
    </div>
  );
};

/* ── D&B Report Panel ── */
const DNBReportPanel: React.FC<{ data: DNBData }> = ({ data }) => {
  const org = data.organization;
  const handleDownload = () => {
    toast.success('D&B 기업보고서 다운로드를 시작합니다', { description: `파일: ${data.contents.fileName} · 형식: ${data.contents.contentFormat}` });
  };
  const fmtCur = (v: number) => v >= 1000000 ? `$${(v/1000000).toFixed(1)}M` : v >= 1000 ? `$${(v/1000).toFixed(0)}K` : `$${v}`;

  return (
    <div className="space-y-5">
      {/* Transaction */}
      <div className="bg-white border border-slate-200 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-2"><FileText className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">조회 거래 정보</h3></div>
        <div className="grid grid-cols-3 gap-3 text-xs">
          <div className="bg-slate-50 rounded-lg px-3 py-2"><span className="text-slate-500 block mb-0.5">거래번호</span><span className="font-mono font-medium text-slate-800">{data.transactionDetail.transactionID}</span></div>
          <div className="bg-slate-50 rounded-lg px-3 py-2"><span className="text-slate-500 block mb-0.5">조회시각</span><span className="font-medium text-slate-800">{new Date(data.transactionDetail.transactionTimestamp).toLocaleString('ko-KR')}</span></div>
          <div className="bg-slate-50 rounded-lg px-3 py-2"><span className="text-slate-500 block mb-0.5">상태</span><span className="font-medium text-emerald-700">{data.transactionDetail.status}</span></div>
        </div>
      </div>

      {/* Inquiry */}
      <div className="bg-white border border-slate-200 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-2"><Search className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">검색 조건 요약</h3></div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="text-xs">DUNS: {data.inquiryDetail.duns}</Badge>
          <Badge variant="outline" className="text-xs">보고서: {data.inquiryDetail.productID}</Badge>
          <Badge variant="outline" className="text-xs">형식: {data.inquiryDetail.reportFormat}</Badge>
          <Badge variant="outline" className="text-xs">언어: {data.inquiryDetail.language}</Badge>
          <Badge variant="outline" className="text-xs">사유: {data.inquiryDetail.orderReason}</Badge>
          <Badge variant="outline" className="text-xs">TradeUp: {data.inquiryDetail.tradeUp}</Badge>
        </div>
        {data.inquiryDetail.customerReference && <p className="text-xs text-slate-500 mt-2">메모: {data.inquiryDetail.customerReference}</p>}
      </div>

      {/* Organization */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4"><Building2 className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">기업 개요 (D&B)</h3><Badge className="text-[10px] ml-2 bg-emerald-100 text-emerald-700">상용</Badge></div>
        <div className="flex items-start gap-4 mb-4">
          <div className="w-14 h-14 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0"><Building2 className="h-7 w-7 text-blue-600" /></div>
          <div className="flex-1">
            <h2 className="text-lg font-bold text-slate-900">{org.primaryName}</h2>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs text-slate-600">DUNS: {org.duns}</Badge>
              <Badge variant="outline" className="text-xs text-slate-600">{org.countryISOAlpha2Code}</Badge>
              <span className="text-xs text-slate-500">{org.countryName}</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm mb-4">
          <div><span className="text-xs text-slate-500 block mb-0.5">주소</span><span className="text-slate-800">{org.primaryAddress.streetAddress !== '—' ? <>{org.primaryAddress.streetAddress}, {org.primaryAddress.addressLocality}, {org.primaryAddress.addressRegion} {org.primaryAddress.postalCode}</> : <span className="text-slate-400 italic">주소 정보 없음</span>}</span></div>
          <div><span className="text-xs text-slate-500 block mb-0.5">연락처</span><span className="text-slate-800">{org.telephone !== '—' ? org.telephone : <span className="text-slate-400 italic">연락처 정보 없음</span>}</span></div>
          {org.fax && org.fax !== '—' && <div><span className="text-xs text-slate-500 block mb-0.5">팩스</span><span className="text-slate-800">{org.fax}</span></div>}
        </div>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-100"><div className="text-[10px] text-emerald-600 font-medium mb-1">직원 수</div><div className="text-lg font-bold text-emerald-800">{org.numberOfEmployees > 0 ? `${org.numberOfEmployees.toLocaleString()}명` : <span className="text-sm text-emerald-400">—</span>}</div></div>
          <div className="bg-blue-50 rounded-lg p-3 border border-blue-100"><div className="text-[10px] text-blue-600 font-medium mb-1">매출액</div><div className="text-lg font-bold text-blue-800">{org.salesRevenue > 0 ? fmtCur(org.salesRevenue) : <span className="text-sm text-blue-400">—</span>}</div></div>
          <div className="bg-purple-50 rounded-lg p-3 border border-purple-100"><div className="text-[10px] text-purple-600 font-medium mb-1">자본금</div><div className="text-lg font-bold text-purple-800">{org.capitalDetails > 0 ? fmtCur(org.capitalDetails) : <span className="text-sm text-purple-400">—</span>}</div></div>
        </div>
        {org.registerNumbers.length > 0 && <div className="mb-4"><span className="text-xs text-slate-500 block mb-2">등록 정보</span><div className="flex flex-wrap gap-2">{org.registerNumbers.map((r, i) => <Badge key={i} variant="outline" className="text-xs text-slate-600">{r.type}: {r.number}</Badge>)}</div></div>}
        {org.industryCodes.length > 0 && <div className="mb-2"><span className="text-xs text-slate-500 block mb-2">업종 코드</span><div className="flex flex-wrap gap-2">{org.industryCodes.map((ic, i) => <Badge key={i} className="bg-slate-100 text-slate-700 text-xs border-slate-200">{ic.type}: {ic.code} · {ic.description}</Badge>)}</div></div>}
      </div>

      {/* Linkage */}
      {(org.corporateLinkage.domesticUltimate || org.corporateLinkage.globalUltimate || org.corporateLinkage.parent) && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3"><Globe className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">계열사 / 모회사</h3></div>
          <div className="space-y-3">
            {org.corporateLinkage.globalUltimate && <div className="flex items-start gap-3 bg-slate-50 rounded-lg p-3"><Badge className="bg-blue-100 text-blue-700 text-[10px] shrink-0">글로벌 모회사</Badge><div><p className="text-sm font-medium text-slate-800">{org.corporateLinkage.globalUltimate.name}</p><p className="text-xs text-slate-500">{org.corporateLinkage.globalUltimate.address}</p><p className="text-xs text-slate-400 font-mono">DUNS: {org.corporateLinkage.globalUltimate.duns}</p></div></div>}
            {org.corporateLinkage.domesticUltimate && <div className="flex items-start gap-3 bg-slate-50 rounded-lg p-3"><Badge className="bg-emerald-100 text-emerald-700 text-[10px] shrink-0">국내 최종 모회사</Badge><div><p className="text-sm font-medium text-slate-800">{org.corporateLinkage.domesticUltimate.name}</p><p className="text-xs text-slate-500">{org.corporateLinkage.domesticUltimate.address}</p><p className="text-xs text-slate-400 font-mono">DUNS: {org.corporateLinkage.domesticUltimate.duns}</p></div></div>}
            {org.corporateLinkage.parent && <div className="flex items-start gap-3 bg-slate-50 rounded-lg p-3"><Badge className="bg-amber-100 text-amber-700 text-[10px] shrink-0">직속 모회사</Badge><div><p className="text-sm font-medium text-slate-800">{org.corporateLinkage.parent.name}</p><p className="text-xs text-slate-500">{org.corporateLinkage.parent.address}</p><p className="text-xs text-slate-400 font-mono">DUNS: {org.corporateLinkage.parent.duns}</p></div></div>}
          </div>
        </div>
      )}

      {/* Principals */}
      {org.currentPrincipals.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3"><Users className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">임원 / 대표</h3></div>
          <div className="space-y-2">{org.currentPrincipals.map((p, i) => <div key={i} className="flex items-center gap-3 bg-slate-50 rounded-lg px-3 py-2"><div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0"><span className="text-xs font-bold text-blue-600">{p.name.charAt(0)}</span></div><div><p className="text-sm font-medium text-slate-800">{p.name}</p><p className="text-xs text-slate-500">{p.title}</p></div></div>)}</div>
        </div>
      )}

      {/* Competitors */}
      {org.competitors.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3"><BarChart3 className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">주요 경쟁사</h3></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 text-xs text-slate-500"><th className="text-left py-2 px-2 font-medium">회사명</th><th className="text-right py-2 px-2 font-medium">매출</th><th className="text-right py-2 px-2 font-medium">직원수</th></tr></thead>
              <tbody>{org.competitors.map((c, i) => <tr key={i} className="border-b border-slate-100"><td className="py-2.5 px-2 font-medium text-slate-700">{c.name}</td><td className="text-right py-2.5 px-2 text-slate-600">{c.salesRevenue}</td><td className="text-right py-2.5 px-2 text-slate-600">{c.employees.toLocaleString()}명</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      )}

      {/* Former Names */}
      {org.formerPrimaryNames.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2"><Clock className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">이전 상호</h3></div>
          <div className="flex flex-wrap gap-2">{org.formerPrimaryNames.map((n, i) => <Badge key={i} variant="outline" className="text-xs text-slate-600">{n}</Badge>)}</div>
        </div>
      )}

      {/* Download */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3"><FileDown className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">D&B 보고서 파일</h3></div>
        <div className="flex items-center gap-3 mb-3">
          <Badge className="text-[10px] bg-emerald-100 text-emerald-700">{data.contents.contentFormat}</Badge>
          <span className="text-xs text-slate-500">파일명: {data.contents.fileName}</span>
        </div>
        <div className="flex gap-2">
          <Button className="flex-1 text-sm bg-blue-600 hover:bg-blue-700" onClick={handleDownload}><FileDown className="h-4 w-4 mr-1.5" />PDF 보고서 다운로드</Button>
          <Button variant="outline" className="flex-1 text-sm" onClick={() => toast.info('텍스트 보고서 미리보기', { description: 'D&B 보고서 텍스트 추출 내용이 표시됩니다.' })}><FileText className="h-4 w-4 mr-1.5" />텍스트 보기</Button>
        </div>
      </div>

      <div className="text-center py-2"><p className="text-[10px] text-slate-400">데이터 제공: Dun & Bradstreet, Inc. · 리셀러: NICEDNB · © {new Date().getFullYear()} D&B. All rights reserved.</p></div>
    </div>
  );
};

/* ── Export Condition Panel (condensed) ── */
const MOQ_OPTIONS = ['100개','500개','1,000개','2,000개','5,000개','10,000개 이상'];
const PROD_OPTIONS = ['500개 이하','500~2,000개','2,000~5,000개','5,000개 이상'];
const TARGET_OPTIONS = ['1천만원','5천만원','1억원','5억원','10억원 이상'];
const CERT_OPTIONS = ['ISO','GMP','FDA','CE','HACCP','FSSC','Organic'];

function simulateExport(c: ExportConditions) {
  const moqNum = parseInt(c.moq.replace(/[^0-9]/g,''))||1000;
  const revenueUSD = c.unitPriceUSD * moqNum;
  const costUSD = c.costPriceUSD * moqNum;
  const tariffUSD = revenueUSD * (c.tariffRate/100);
  const logisticsUSD = revenueUSD * (c.logisticsRate/100);
  const customsFeeUSD = 200;
  const totalCostUSD = costUSD + tariffUSD + logisticsUSD + customsFeeUSD;
  const profitUSD = revenueUSD - totalCostUSD;
  const marginRate = revenueUSD > 0 ? (profitUSD/revenueUSD)*100 : 0;
  const targetNum = parseInt(c.targetAmountKrw.replace(/[^0-9]/g,''))||5000;
  const targetUSD = targetNum * 10000 / c.exchangeRate;
  const dealsNeeded = revenueUSD > 0 ? Math.ceil(targetUSD/revenueUSD) : 0;
  const bepDeals = (c.unitPriceUSD - c.costPriceUSD) > 0 ? Math.ceil((logisticsUSD+customsFeeUSD)/(c.unitPriceUSD-c.costPriceUSD)) : 0;
  return { revenueUSD, profitUSD, marginRate, dealsNeeded, bepDeals, tariffUSD, logisticsUSD, customsFeeUSD, totalCostUSD };
}

const ExportConditionPanel: React.FC<{ open: boolean; onClose: () => void; conditions: ExportConditions; onChange: (c: ExportConditions) => void; onApply: () => void; }> = ({ open, onClose, conditions, onChange, onApply }) => {
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
            <div className="flex items-center justify-between mb-3"><span className="text-xs text-slate-500">입력한 조건으로 바이어 필터링</span><Badge variant="outline" className="text-xs">{conditions.moq} · {conditions.targetAmountKrw}</Badge></div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1 text-sm" onClick={() => update({ productionCapacity: '', moq: '1,000개', targetAmountKrw: '5천만원', unitPriceUSD: 12.5, costPriceUSD: 8, logisticsRate: 8, tariffRate: 8, exchangeRate: 1300, certifications: [] })}>초기화</Button>
              <Button className="flex-1 bg-blue-600 hover:bg-blue-700 text-sm" onClick={() => { onApply(); onClose(); }}><ArrowUpRight className="h-4 w-4 mr-1" /> 이 조건으로 적합 바이어 찾기</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ── ChatPanel ── */
const ChatPanel: React.FC<{ messages: Message[]; onSend: (text: string) => void; activeCategory: string; }> = ({ messages, onSend, activeCategory }) => {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);
  const handleSend = () => { if (!input.trim()) return; onSend(input.trim()); setInput(''); };
  return (
    <div className="flex flex-col h-full bg-white border-r border-slate-200">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100"><Button variant="ghost" size="icon" className="h-8 w-8"><ArrowLeft className="h-4 w-4 text-slate-600" /></Button><span className="text-sm font-medium text-slate-700">위로</span></div>
      <ScrollArea className="flex-1 px-4 py-4" ref={scrollRef}>
        <div className="space-y-5">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'ai' && <div className="mr-2 mt-1 flex-shrink-0"><div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center"><Sparkles className="h-3.5 w-3.5 text-blue-600" /></div></div>}
              {msg.role === 'error' && <div className="mr-2 mt-1 flex-shrink-0"><div className="w-7 h-7 rounded-full bg-red-100 flex items-center justify-center"><AlertCircle className="h-3.5 w-3.5 text-red-600" /></div></div>}
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-br-md' : msg.role === 'error' ? 'bg-red-50 text-red-700 border border-red-100 rounded-bl-md' : 'bg-slate-50 text-slate-700 border border-slate-100 rounded-bl-md'}`}>
                {msg.text}
                {msg.chips && <div className="flex flex-wrap gap-2 mt-3">{msg.chips.map((chip) => <Badge key={chip} variant="outline" className="cursor-pointer bg-white hover:bg-slate-50 text-slate-600 border-slate-200 text-xs font-normal py-1 px-2.5"><Hash className="h-3 w-3 mr-1 text-slate-400" />{chip}</Badge>)}</div>}
              </div>
            </div>
          ))}
          {messages.length === 1 && <div className="mt-2"><p className="text-xs text-slate-400 mb-2 ml-10">추천 검색어</p><div className="flex flex-wrap gap-2 ml-10">{['스킨케어','홍삼','여성의류','메모리 반도체'].map((kw) => <button key={kw} onClick={() => onSend(kw)} className="text-xs bg-white border border-slate-200 rounded-full px-3 py-1.5 text-slate-600 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-colors"><Search className="h-3 w-3 inline mr-1" />{kw}</button>)}</div></div>}
        </div>
      </ScrollArea>
      <div className="px-4 py-3 border-t border-slate-100"><div className="flex gap-2 overflow-x-auto pb-2">{CATEGORIES.map((cat) => <button key={cat.label} onClick={() => onSend(cat.label)} className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors flex items-center gap-1.5 ${activeCategory === cat.label ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'}`}>{cat.icon} {cat.label}</button>)}</div></div>
      <div className="px-4 py-3 border-t border-slate-100">
        <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-2xl px-3 py-2">
          <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-600"><Mic className="h-4 w-4" /></Button>
          <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSend()} placeholder="제품명, HS 코드, 키워드를 입력하세요 (예: 스킨케어, 330499, 홍삼)" className="flex-1 bg-transparent text-sm text-slate-800 placeholder:text-slate-400 outline-none" />
          <Button size="icon" className="h-8 w-8 rounded-full bg-blue-600 hover:bg-blue-700 text-white" onClick={handleSend} disabled={!input.trim()}><Send className="h-3.5 w-3.5" /></Button>
        </div>
      </div>
    </div>
  );
};

/* ── CountryListPanel ── */
const CountryListPanel: React.FC<{ countries: CountryRec[]; categoryLabel: string; categoryHs: string; onSelectCountry: (c: CountryRec) => void; onOpenConditions: () => void; hasConditions: boolean; }> = ({ countries, categoryLabel, categoryHs, onSelectCountry, onOpenConditions, hasConditions }) => {
  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
        <div className="flex items-center gap-2"><Globe className="h-4 w-4 text-slate-500" /><h1 className="text-sm font-semibold text-slate-800">국가 추천 리스트</h1></div>
        <Button variant="ghost" size="sm" className={`h-7 text-xs gap-1 ${hasConditions ? 'text-blue-600 bg-blue-50' : 'text-slate-500'}`} onClick={onOpenConditions}><Settings2 className="h-3.5 w-3.5" />{hasConditions ? '조건 적용 중' : '조건 입력'}</Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="px-5 py-5 max-w-3xl mx-auto">
          <div className="bg-slate-900 text-white rounded-xl px-5 py-4 mb-6">
            <div className="flex items-center justify-between mb-2"><span className="text-xs font-bold tracking-wider text-blue-200">RECOMMENDED COUNTRIES</span><span className="text-xs text-slate-400">{categoryLabel} · HS {categoryHs}</span></div>
            <p className="text-xs text-slate-300 mt-2">AI가 {countries.length}개국을 적합도·성장률·수입규모 기준으로 분석한 결과입니다.</p>
          </div>
          {hasConditions && <div className="mb-4 flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5 text-xs text-blue-700"><Settings2 className="h-4 w-4" /><span>수출 조건이 등록되어 필터링이 적용 중입니다.</span></div>}
          <div className="space-y-3">
            {countries.map((c, idx) => (
              <button key={c.countryCode} onClick={() => onSelectCountry(c)} className="w-full text-left bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition-all group">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0"><div className="w-14 h-14 rounded-xl bg-slate-100 flex items-center justify-center text-3xl">{c.flag}</div></div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1"><h3 className="text-lg font-bold text-slate-900">{c.countryName}</h3>{idx === 0 && <Badge className="bg-amber-100 text-amber-700 text-[10px] border-amber-200"><Award className="h-3 w-3 mr-0.5" />1위 추천</Badge>}</div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mb-3">
                      <span className="flex items-center gap-1"><Users className="h-3.5 w-3.5" />바이어 {c.buyerCount}개</span>
                      <span className="flex items-center gap-1"><TrendingUp className="h-3.5 w-3.5" />평균 성장 +{c.avgGrowthRate}%</span>
                      <span className="flex items-center gap-1"><DollarSign className="h-3.5 w-3.5" />총 수입 {c.totalImportValue}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5 bg-emerald-50 rounded-lg px-2.5 py-1"><span className="text-sm font-bold text-emerald-700">{c.avgScore}</span><span className="text-[10px] text-emerald-600">점</span></div>
                      <span className="text-xs text-slate-400">대표 바이어: <span className="font-medium text-slate-600">{c.topBuyerName}</span> ({c.topBuyerScore}점)</span>
                    </div>
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
  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-200">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onBack}><ChevronLeft className="h-4 w-4 text-slate-600" /></Button>
        <div className="flex items-center gap-2"><span className="text-2xl">{country.flag}</span><div><h1 className="text-sm font-semibold text-slate-800">{country.countryName} 바이어 리스트</h1><p className="text-xs text-slate-500">총 {country.buyers.length}개 · 평균 적합도 {country.avgScore}점</p></div></div>
        <div className="ml-auto"><Button variant="ghost" size="sm" className={`h-7 text-xs gap-1 ${hasConditions ? 'text-blue-600 bg-blue-50' : 'text-slate-500'}`} onClick={onOpenConditions}><Settings2 className="h-3.5 w-3.5" />{hasConditions ? '조건 적용 중' : '조건 입력'}</Button></div>
      </div>
      <ScrollArea className="flex-1">
        <div className="px-5 py-5 max-w-3xl mx-auto space-y-3">
          {country.buyers.map((buyer) => (
            <button key={buyer.id} onClick={() => onSelectBuyer(buyer)} className="w-full text-left bg-white border border-slate-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-md transition-all group">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0"><div className="w-12 h-12 rounded-lg bg-slate-100 flex items-center justify-center"><Building2 className="h-6 w-6 text-slate-400" /></div></div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5"><h3 className="text-base font-bold text-slate-900">{buyer.name}</h3><TrustBadge level={buyer.trustBadge} days={buyer.lastUpdatedDays} /></div>
                  <p className="text-xs text-slate-500">({buyer.legalName})</p>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-slate-500"><span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{buyer.region}</span><span>{buyer.industry}</span><span className="flex items-center gap-1"><Mail className="h-3 w-3" />{buyer.email}</span></div>
                  <div className="flex items-center gap-2 mt-3">
                    <Badge className={`text-[10px] ${buyer.score >= 90 ? 'bg-emerald-100 text-emerald-700' : buyer.score >= 80 ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'}`}>적합도 {buyer.score}점</Badge>
                    <Badge variant="outline" className="text-[10px] text-slate-500">{buyer.totalImportValue} 수입</Badge>
                    <Badge variant="outline" className={`text-[10px] ${buyer.importGrowthRate >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>{buyer.importGrowthRate > 0 ? '+' : ''}{buyer.importGrowthRate}% YoY</Badge>
                    {buyer.dnbData && <Badge className="text-[10px] bg-indigo-100 text-indigo-700 border-indigo-200">D&B</Badge>}
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
const BuyerDetailPanel: React.FC<{ buyer: Buyer; onBack: () => void; inputHsCode: string; category: string; onRefreshBuyer: (id: string) => void; }> = ({ buyer, onBack, inputHsCode, category, onRefreshBuyer }) => {
  const [showMeta, setShowMeta] = useState(false);
  const [favorited, setFavorited] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');

  const handleFavorite = () => { setFavorited(!favorited); toast.success(favorited ? '관심 바이어에서 제거했습니다' : '관심 바이어로 등록했습니다'); };
  const handleShare = () => { copyToClipboard(`${window.location.origin}?buyer=${buyer.id}`); };
  const handleDownloadPDF = () => { toast.success('PDF 다운로드를 시작합니다', { description: `${buyer.name} 리포트` }); };
  const handleRefresh = () => { toast.promise(new Promise((resolve) => { setTimeout(() => resolve(true), 1500); }), { loading: 'KOTRA 데이터를 갱신 중입니다...', success: () => { onRefreshBuyer(buyer.id); return '데이터가 갱신되었습니다'; }, error: '갱신에 실패했습니다' }); };
  const isMismatch = inputHsCode !== buyer.hsCode && inputHsCode !== category;

  const tabs = [
    { key: 'profile', label: '기본 프로필', icon: <Building2 className="h-3.5 w-3.5" /> },
    { key: 'import', label: '수입 이력', icon: <TrendingUp className="h-3.5 w-3.5" /> },
    { key: 'fit', label: '적합도 분석', icon: <BarChart3 className="h-3.5 w-3.5" /> },
    { key: 'match', label: '매칭 상세', icon: <Sparkles className="h-3.5 w-3.5" /> },
    ...(buyer.dnbData ? [{ key: 'dnb', label: 'D&B 보고서', icon: <FileText className="h-3.5 w-3.5" /> }] : []),
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
              <div><span className="text-slate-500">데이터 기준일:</span> 2026년 4월</div>
              <div className="col-span-2"><span className="text-slate-500">분석 대상:</span> {buyer.country} · HS {buyer.hsCode} ({buyer.hsLabel})</div>
            </div>
          </div>

          <div className="flex items-start gap-2 bg-blue-50 border border-blue-100 rounded-lg px-4 py-3 mb-5"><Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" /><p className="text-xs text-blue-800 leading-relaxed">이 보고서는 AI가 생성한 것이 아닙니다. KOTRA, 관세청, World Bank 실제 데이터를 결합 분석하여 산출한 결과입니다.</p></div>

          {buyer.lastUpdatedDays > 5 && <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-5"><Clock className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" /><div className="flex-1"><p className="text-xs text-amber-800 leading-relaxed">이 바이어 정보가 <span className="font-bold">{buyer.lastUpdatedDays}일 이전 데이터</span>입니다.</p><button onClick={handleRefresh} className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-amber-700 hover:text-amber-900 underline underline-offset-2"><RefreshCw className="h-3 w-3" /> KOTRA에서 최신 데이터 확인하기</button></div></div>}

          {isMismatch && <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-5"><AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" /><div className="text-xs text-amber-800 leading-relaxed"><span className="font-semibold">입력하신 {inputHsCode}과(와) 유사한 HS 코드 {buyer.hsCode}({buyer.hsLabel})의 결과입니다.</span><br />해당 코드는 동일 카테고리({buyer.hsLabel}) 내 유사 품목으로 매칭되었습니다.</div></div>}

          <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
            {tabs.map((t) => <button key={t.key} onClick={() => setActiveTab(t.key)} className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${activeTab === t.key ? 'bg-slate-800 text-white' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'}`}>{t.icon} {t.label}</button>)}
          </div>

          {activeTab === 'profile' && (
            <div className="mb-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1"><h2 className="text-xl font-bold text-slate-900">{buyer.name}</h2><TrustBadge level={buyer.trustBadge} days={buyer.lastUpdatedDays} /></div>
                    <p className="text-xs text-slate-500">({buyer.legalName})</p>
                  </div>
                  <Button variant="ghost" size="icon" className={`h-8 w-8 ${favorited ? 'text-amber-500' : 'text-slate-300 hover:text-amber-500'}`} onClick={handleFavorite}><Star className={`h-5 w-5 ${favorited ? 'fill-current' : ''}`} /></Button>
                </div>
                <div className="grid grid-cols-2 gap-y-3 gap-x-6 text-sm mb-4">
                  <div><span className="text-xs text-slate-500 block mb-0.5">업종</span><span className="text-slate-800 font-medium">{buyer.industry}</span></div>
                  <div><span className="text-xs text-slate-500 block mb-0.5">국가/지역</span><span className="text-slate-800 font-medium">{buyer.country} · {buyer.region}</span></div>
                  <div><span className="text-xs text-slate-500 block mb-0.5">데이터 출처</span><span className="text-slate-800">{buyer.dataSource}</span></div>
                  <div><span className="text-xs text-slate-500 block mb-0.5">원본 추적</span><span className="text-slate-800 text-xs font-mono">{buyer.csvTrace}</span></div>
                  <div className="col-span-2"><span className="text-xs text-slate-500 block mb-0.5">데이터 수집일</span><span className="text-slate-800">{buyer.dataDate}</span></div>
                </div>
                <Separator className="my-3" />
                <div className="space-y-1">
                  <ContactRow icon={<Building2 className="h-4 w-4" />} label={buyer.contactRole} value={buyer.contactName} />
                  <Separator className="my-1" />
                  <ContactRow icon={<Mail className="h-4 w-4" />} label="이메일" value={buyer.email} action="copy" />
                  <Separator className="my-1" />
                  <ContactRow icon={<Phone className="h-4 w-4" />} label="전화" value={buyer.phone} action="phone" href={`tel:${buyer.phone}`} />
                  <Separator className="my-1" />
                  <ContactRow icon={<Globe className="h-4 w-4" />} label="웹사이트" value={buyer.website} action="link" href={`https://${buyer.website}`} />
                </div>
                <div className="flex items-center gap-2 mt-4 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2 w-fit"><CheckCircle2 className="h-4 w-4 text-emerald-600" /><span className="text-xs font-medium text-emerald-700">연락처 확인됨</span><span className="text-[10px] text-emerald-500">{buyer.contactVerifiedDate} 확인</span></div>
              </div>
            </div>
          )}

          {activeTab === 'import' && (
            <div className="mb-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="flex items-center gap-4 mb-4">
                  <div className="bg-emerald-50 rounded-lg px-4 py-2.5"><div className="text-[10px] text-emerald-600 font-medium">누적 수입액 (24개월)</div><div className="text-lg font-bold text-emerald-700">{buyer.totalImportValue}</div></div>
                  <div className="bg-blue-50 rounded-lg px-4 py-2.5"><div className="text-[10px] text-blue-600 font-medium">성장률 (YoY)</div><div className={`text-lg font-bold ${buyer.importGrowthRate >= 0 ? 'text-blue-700' : 'text-red-600'}`}>{buyer.importGrowthRate > 0 ? '+' : ''}{buyer.importGrowthRate}%</div></div>
                  <div className="bg-slate-50 rounded-lg px-4 py-2.5"><div className="text-[10px] text-slate-500 font-medium">최근 수입</div><div className="text-lg font-bold text-slate-700">{buyer.importHistory[buyer.importHistory.length - 1]?.month}</div></div>
                </div>
                <ImportTrendChart data={buyer.importHistory} />
              </div>
              {buyer.competitors && <div className="mt-5 bg-white border border-slate-200 rounded-xl p-5"><div className="flex items-center gap-2 mb-3"><BarChart3 className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">동종 수입 바이어 비교</h3></div><table className="w-full text-sm"><thead><tr className="border-b border-slate-200 text-xs text-slate-500"><th className="text-left py-2 px-2 font-medium">바이어</th><th className="text-center py-2 px-2 font-medium">국가</th><th className="text-center py-2 px-2 font-medium">적합도</th><th className="text-right py-2 px-2 font-medium">연간 수입</th><th className="text-right py-2 px-2 font-medium">성장률</th></tr></thead><tbody>{buyer.competitors.map((c) => <tr key={c.name} className={`border-b border-slate-100 ${c.name === buyer.name ? 'bg-emerald-50' : ''}`}><td className="py-2.5 px-2"><div className="flex items-center gap-2"><span className={`w-2 h-2 rounded-full ${c.growth >= 0 ? 'bg-emerald-400' : 'bg-red-400'}`} /><span className={`font-medium ${c.name === buyer.name ? 'text-emerald-800' : 'text-slate-700'}`}>{c.name}</span>{c.name === buyer.name && <Badge className="bg-emerald-100 text-emerald-700 text-[10px] px-1.5 py-0">현재</Badge>}</div></td><td className="text-center py-2.5 px-2 text-slate-600">{c.country}</td><td className="text-center py-2.5 px-2"><span className="font-bold text-slate-800">{c.score}</span><span className="text-xs text-slate-400">/100</span></td><td className="text-right py-2.5 px-2 text-slate-700">{c.importValue}</td><td className={`text-right py-2.5 px-2 font-medium ${c.growth >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>{c.growth > 0 ? '+' : ''}{c.growth}%</td></tr>)}</tbody></table></div>}
            </div>
          )}

          {activeTab === 'fit' && (
            <div className="mb-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="flex items-center gap-4 mb-5">
                  <div className="text-center"><div className="text-4xl font-extrabold text-emerald-600">{buyer.score}<span className="text-lg">점</span></div><div className="flex items-center justify-center gap-1 mt-1"><div className="w-2 h-2 rounded-full bg-emerald-500" /><span className="text-xs text-slate-500">{buyer.scoreLabel}</span></div></div>
                  <Separator orientation="vertical" className="h-12" />
                  <div className="flex-1"><p className="text-xs text-slate-500 mb-2">AI가 4가지 기준으로 평가한 결과입니다 (100점 만점 기준)</p><div className="flex gap-1.5">{['수입 이력', '시장 성장', 'GDP 규모', '물류'].map((t) => <span key={t} className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">{t}</span>)}</div></div>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">{buyer.metrics.map((m) => <ScoreBar key={m.label} label={m.label} value={m.value} benchmark={m.benchmark} />)}</div>
              </div>
              <div className="mt-5 bg-white border border-slate-200 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3"><Zap className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">RFM 적합도 모델</h3></div>
                <div className="flex items-center gap-4">
                  <div className="flex-1"><RFMChart rfm={buyer.rfm} name={buyer.name} /></div>
                  <div className="w-40 space-y-3">
                    <div><div className="flex justify-between text-xs mb-1"><span className="text-slate-500">Recency</span><span className="font-bold text-blue-600">{buyer.rfm.R}점</span></div><Progress value={buyer.rfm.R} className="h-1.5" /><p className="text-[10px] text-slate-400 mt-0.5">최근 수입일 가까울수록 높음</p></div>
                    <div><div className="flex justify-between text-xs mb-1"><span className="text-slate-500">Frequency</span><span className="font-bold text-blue-600">{buyer.rfm.F}점</span></div><Progress value={buyer.rfm.F} className="h-1.5" /><p className="text-[10px] text-slate-400 mt-0.5">수입 빈도 높을수록 높음</p></div>
                    <div><div className="flex justify-between text-xs mb-1"><span className="text-slate-500">Monetary</span><span className="font-bold text-blue-600">{buyer.rfm.M}점</span></div><Progress value={buyer.rfm.M} className="h-1.5" /><p className="text-[10px] text-slate-400 mt-0.5">누적 수입액 클수록 높음</p></div>
                  </div>
                </div>
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
                  <ol className="space-y-3">{buyer.reasons.map((r, idx) => <li key={idx} className="flex items-start gap-2.5 text-sm text-slate-700"><span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-50 text-blue-600 text-xs font-bold flex items-center justify-center mt-0.5">{idx + 1}</span><div className="flex-1"><p className="leading-relaxed">{r.text.split(r.highlight).map((part, i, arr) => <span key={i}>{part}{i < arr.length - 1 && <span className="bg-yellow-100 text-yellow-900 font-semibold px-0.5 rounded">{r.highlight}</span>}</span>)}</p><button onClick={() => toast.info(r.source, { description: '원본 데이터 출처' })} className="inline-flex items-center gap-1 mt-1 text-[10px] text-blue-600 hover:text-blue-800 hover:underline"><ExternalLink className="h-3 w-3" /> 출처: {r.source}</button></div></li>)}</ol>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'dnb' && buyer.dnbData && (
            <div className="mb-6">
              <DNBReportPanel data={buyer.dnbData} />
            </div>
          )}

          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3"><Database className="h-4 w-4 text-slate-500" /><h3 className="text-sm font-semibold text-slate-800">데이터 신뢰도</h3></div>
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="flex-1">
                  <div className="flex justify-between text-xs mb-1"><span className="text-slate-600">신뢰도 수준</span><span className="font-semibold text-slate-800">{buyer.trustLevel}</span></div>
                  <Progress value={buyer.trustLevel === '높음' ? 90 : buyer.trustLevel === '보통' ? 65 : 40} className="h-2" />
                </div>
              </div>
              <div className="flex items-center gap-2 mb-2"><TrustBadge level={buyer.trustBadge} days={buyer.lastUpdatedDays} /><span className="text-xs text-slate-400">{buyer.lastUpdatedDays}일 전 최종 확인</span></div>
              <p className="text-xs text-slate-500 leading-relaxed">KOTRA 및 관세청 공개 데이터 기반. 수집일 기준 연락처 확인 완료.</p>
            </div>
          </div>

          <div className="mb-8">
            <button onClick={() => setShowMeta(!showMeta)} className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-700 transition-colors"><ChevronRight className={`h-3.5 w-3.5 transition-transform ${showMeta ? 'rotate-90' : ''}`} />원본 데이터 상세 보기</button>
            {showMeta && <div className="mt-2 bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-600 space-y-1 font-mono"><div>원본 파일: {buyer.csvTrace}</div><div>수집 기관: {buyer.dataSource}</div><div>수집 일시: {buyer.dataDate}</div><div>검증 방식: 이메일/전화 크로스 체크</div><div>Trust Badge: {buyer.trustBadge.toUpperCase()}</div></div>}
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
  const [messages, setMessages] = useState<Message[]>([{ role: 'ai', text: '안녕하세요! 어떤 제품의 해외 바이어를 찾아드릴까요?\n\n현재 KOTRA·관세청·World Bank 연계 데이터 기준으로,\n→ 47개국, 12,800+ 개 바이어를 검색할 수 있습니다.\n\n아래에서 바로 시작하거나, 직접 입력해 주세요.', chips: ['K-뷰티', '건강식품', 'K-패션', '반도체'] }]);
  const [currentCategory, setCurrentCategory] = useState<string>('K-뷰티');
  const [step, setStep] = useState<Step>('countries');
  const [selectedCountry, setSelectedCountry] = useState<CountryRec | null>(null);
  const [selectedBuyer, setSelectedBuyer] = useState<Buyer | null>(null);
  const [inputHsCode, setInputHsCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [showConditionPanel, setShowConditionPanel] = useState(false);
  const [conditions, setConditions] = useState<ExportConditions>({ productionCapacity: '2,000~5,000개', moq: '1,000개', targetAmountKrw: '5천만원', unitPriceUSD: 12.5, costPriceUSD: 8, logisticsRate: 8, tariffRate: 8, exchangeRate: 1300, certifications: ['ISO', 'GMP'] });

  const categoryData = useMemo(() => CATEGORIES.find((c) => c.label === currentCategory), [currentCategory]);
  const countryRecs = useMemo(() => categoryData ? groupByCountry(categoryData.buyers) : [], [categoryData]);
  const hasConditions = !!conditions.productionCapacity && !!conditions.moq;

  const handleSend = (text: string) => {
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInputHsCode(text);
    setLoading(true);
    const detected = detectCategory(text);
    if (!detected) {
      setTimeout(() => { setMessages((prev) => [...prev, { role: 'error', text: `"${text}"에 해당하는 카테고리를 찾을 수 없습니다.\nK-뷰티, 건강식품, K-패션, 반도체 중 하나를 입력해 주세요.` }]); setLoading(false); }, 800);
      return;
    }
    const cat = CATEGORIES.find((c) => c.label === detected);
    if (!cat || cat.buyers.length === 0) {
      setTimeout(() => { setMessages((prev) => [...prev, { role: 'error', text: `${detected} 카테고리의 현재 해외 바이어 데이터가 부족합니다.` }]); setLoading(false); }, 800);
      return;
    }
    setTimeout(() => {
      setCurrentCategory(detected);
      setStep('countries');
      setSelectedCountry(null);
      setSelectedBuyer(null);
      setMessages((prev) => [...prev, { role: 'ai', text: `${cat.countries.join('/')} 지역 ${detected} 바이어를 검색했습니다.\n적합도 기준으로 ${cat.buyers.length}개국, ${cat.buyers.length}개 바이어를 발굴했습니다. 우측에서 국가를 선택해 보세요.` }]);
      setLoading(false);
    }, 1200);
  };

  const handleSelectCountry = (c: CountryRec) => { setSelectedCountry(c); setStep('buyers'); };
  const handleSelectBuyer = (b: Buyer) => { setSelectedBuyer(b); setStep('detail'); };
  const handleBackToCountries = () => { setStep('countries'); setSelectedCountry(null); setSelectedBuyer(null); };
  const handleBackToBuyers = () => { setStep('buyers'); setSelectedBuyer(null); };
  const handleRefreshBuyer = (id: string) => { toast.success(`${id} 데이터 갱신 완료`); };
  const handleApplyConditions = () => { toast.success('수출 조건이 적용되었습니다', { description: `MOQ ${conditions.moq} · 희망금액 ${conditions.targetAmountKrw}` }); };

  const renderRightPanel = () => {
    if (!categoryData) return <div className="h-full flex flex-col items-center justify-center text-slate-400"><Search className="h-12 w-12 mb-4 text-slate-200" /><p className="text-sm">검색어를 입력하면 국가 추천 리스트가 표시됩니다</p><p className="text-xs mt-1">예: 스킨케어, 홍삼, 여성의류, 반도체</p></div>;
    if (step === 'countries') return <CountryListPanel countries={countryRecs} categoryLabel={currentCategory} categoryHs={categoryData.hsCode} onSelectCountry={handleSelectCountry} onOpenConditions={() => setShowConditionPanel(true)} hasConditions={hasConditions} />;
    if (step === 'buyers' && selectedCountry) return <BuyerListPanel country={selectedCountry} onSelectBuyer={handleSelectBuyer} onBack={handleBackToCountries} onOpenConditions={() => setShowConditionPanel(true)} hasConditions={hasConditions} />;
    if (step === 'detail' && selectedBuyer) return <BuyerDetailPanel buyer={selectedBuyer} onBack={handleBackToBuyers} inputHsCode={inputHsCode || '330303'} category={currentCategory} onRefreshBuyer={handleRefreshBuyer} />;
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
      </header>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-[420px] flex-shrink-0 h-full"><ChatPanel messages={messages} onSend={handleSend} activeCategory={currentCategory} /></div>
        <div className="flex-1 h-full relative">
          {loading && <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center"><Loader2 className="h-8 w-8 text-blue-600 animate-spin mb-3" /><p className="text-sm text-slate-600">바이어 데이터를 분석 중입니다...</p><p className="text-xs text-slate-400 mt-1">KOTRA, 관세청, World Bank 데이터 연동 중</p></div>}
          {renderRightPanel()}
        </div>
      </div>
      <ExportConditionPanel open={showConditionPanel} onClose={() => setShowConditionPanel(false)} conditions={conditions} onChange={setConditions} onApply={handleApplyConditions} />
    </div>
  );
}
