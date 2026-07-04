from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class Filters(BaseModel):
    exclude_countries_iso3: Optional[List[str]] = None
    min_trade_value_usd: Optional[float] = 0.0

    @field_validator("exclude_countries_iso3")
    @classmethod
    def validate_iso3_list(cls, v):
        if v is None:
            return v
        for x in v:
            if not isinstance(x, str) or len(x.strip()) != 3:
                raise ValueError("exclude_countries_iso3 must be ISO3 strings (len=3)")
        return [x.strip().upper() for x in v]

    @field_validator("min_trade_value_usd")
    @classmethod
    def validate_min_trade(cls, v):
        if v is None:
            return 0.0
        if v < 0:
            raise ValueError("min_trade_value_usd must be >= 0")
        return float(v)


class PredictRequest(BaseModel):
    hs_code: str = Field(..., description="6-digit HS code")
    exporter_country_iso3: str = Field(..., description="Exporter ISO3")
    top_n: Optional[int] = Field(10, description="1~20, default 10")
    year: Optional[int] = Field(None, description="default: 2023 (latest available data year)")
    filters: Optional[Filters] = Field(default_factory=Filters)

    @field_validator("hs_code")
    @classmethod
    def validate_hs6(cls, v):
        v = v.strip()
        if len(v) != 6 or not v.isdigit():
            raise ValueError("hs_code must be 6 digits")
        return v

    @field_validator("exporter_country_iso3")
    @classmethod
    def validate_exporter_iso3(cls, v):
        v = v.strip().upper()
        if len(v) != 3:
            raise ValueError("exporter_country_iso3 must be ISO3 (len=3)")
        return v

    @field_validator("top_n")
    @classmethod
    def validate_top_n(cls, v):
        if v is None:
            return 10
        if v < 1 or v > 20:
            raise ValueError("top_n must be between 1 and 20")
        return int(v)

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        if v is None:
            return 2023  # TODO: update to latest data year when CSVs are refreshed
        v = int(v)
        # World Bank / Trade data currently available up to 2023
        # Clamp future years to 2023 to avoid silent empty results
        if v > 2023:
            return 2023
        return v


class PredictResult(BaseModel):
    rank: int
    partner_country_iso3: str
    fit_score: float
    score_components: Dict[str, float]
    explanation: Dict[str, Any]
    # B1 추가 필드 (additive — 기존 구조 불변, SIM_SPEC §2.3/§3.3)
    compliance: Optional[Dict[str, Any]] = None
    data_coverage: Optional[Dict[str, Any]] = None
    warnings: List[Dict[str, Any]] = Field(default_factory=list)


class PredictDiagnostics(BaseModel):
    candidate_count: int
    eligible_count: int
    returned_count: int
    hard_filter_reason_counts: Dict[str, int]
    missing_indicator_counts: Dict[str, int]
    zero_result_reasons: List[str]
    quality_warnings: List[str]
    trade_signal_counts: Dict[str, int]
    sample_countries_by_reason: Dict[str, List[str]]
    # 가산 필드 (matchA): 미지원/데이터없음 vs 바이어없음 구분 (기존 구조 불변)
    coverage_status: Optional[str] = None
    coverage_message: Optional[str] = None


class BuyerShortlistItem(BaseModel):
    buyer_name: str
    source_dataset: Optional[str] = None
    country_norm: Optional[str] = None
    source_target_country_iso3: Optional[str] = None
    source_target_country_name: Optional[str] = None
    source_target_country_rank: Optional[int] = None
    hs_code_norm: Optional[str] = None
    keywords_norm: Optional[str] = None
    has_contact: bool = False
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_website: Optional[str] = None
    final_score: float
    decision: str
    score_breakdown: Dict[str, Any]
    recommendation_lines: List[str]
    explanation_reasons: List[str]
    matched_by: Optional[str] = None
    matched_terms: List[str] = Field(default_factory=list)
    # 가산 필드 (matchA): 출처 검증·추정 연락처 배지 (기존 구조 불변)
    source_verification: Optional[str] = None
    source_verified: Optional[bool] = None
    contact_email_estimated: Optional[bool] = None
    # 가산 필드 (matchC): HS 관련성 등급(strong/weak/none)·검증 연락처 보유 배지
    match_relevance: Optional[str] = None
    has_verified_contact: Optional[bool] = None


class BuyerShortlistSourceCountry(BaseModel):
    rank: int
    partner_country_iso3: str
    target_country_name: Optional[str] = None
    fit_score: float


class BuyerShortlistData(BaseModel):
    status: str
    target_country_iso3: Optional[str] = None
    target_country_name: Optional[str] = None
    source_countries: List[BuyerShortlistSourceCountry] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    items: List[BuyerShortlistItem] = Field(default_factory=list)
    error: Optional[str] = None


class PredictData(BaseModel):
    input: Dict[str, Any]
    results: List[PredictResult]
    diagnostics: PredictDiagnostics
    buyers: Optional[BuyerShortlistData] = None


class PredictResponse(BaseModel):
    request_id: str
    status: str
    timestamp: str
    data: PredictData


class LegacyPredictResult(BaseModel):
    country: str
    score: float
    expected_export_usd: Optional[float] = None
    explanation: Dict[str, Any]


class LegacyPredictResponse(BaseModel):
    request_id: str
    status: str
    timestamp: str
    data_source: str
    input: Dict[str, Any]
    top_countries: List[LegacyPredictResult]
    diagnostics: PredictDiagnostics


# --- B6: AI Sales Letter 개인화 (additive — 기존 키/의미 불변) ---
class InquiryRequest(BaseModel):
    buyer_name: str = Field(..., description="Buyer company name")
    contact_email: str = Field(..., description="Buyer contact email")
    hs_code: str = Field(..., description="HS code for the product")
    sender_company: str = Field(..., description="Sender company name")
    sender_name: str = Field(..., description="Sender person name")
    message: Optional[str] = Field(default="", description="Optional additional message")
    # 바이어 페이로드 (Optional+default — 미전달 시 기존 draft와 동일)
    country: Optional[str] = Field(default=None, description="Buyer country (personalization)")
    match_relevance: Optional[str] = Field(default=None, description="strong/weak/none (personalization)")
    recommendation_lines: Optional[List[str]] = Field(
        default=None, description="Buyer recommendation reasons (personalization)"
    )


class InquiryResponse(BaseModel):
    inquiry_id: str
    buyer_name: str
    contact_email: str
    hs_code: str
    sender_company: str
    sender_name: str
    message: str
    draft_ko: str
    draft_en: str
    created_at: str
    status: str = "draft_ready"
    # B6 가산 필드 (Optional+default — 기존 응답 스키마 불변)
    personalized: bool = False
    country: Optional[str] = None
    match_relevance: Optional[str] = None


# --- B5: Export Readiness Check (additive — predict 응답 재호출/재계산 없이 DTO 소비) ---
class ReadinessRequest(BaseModel):
    country_fit_score: Optional[float] = Field(
        default=None, description="predict data.results[k].fit_score (post-penalty). None=빈 시장(no_market)"
    )
    compliance: Optional[str] = Field(
        default=None, description="None=비제재 / 'restricted'=수출 제한 (categorical, 재감점 없음)"
    )
    buyer_signal: Optional[str] = Field(
        default=None, description="strong/weak/none (직접 지정 시). buyers_items 가 있으면 그쪽이 우선"
    )
    buyers_items: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="raw predict data.buyers.items (서버가 shortlist 중 max match_relevance 집계)"
    )
    margin_grade: Optional[str] = Field(
        default=None, description="simulation profit_grade (보통/손익분기/적자/우수)"
    )
    top_buyer_name: Optional[str] = Field(
        default=None, description="predict data.buyers.items[0].buyer_name"
    )


class ReadinessResponse(BaseModel):
    readiness_score: int
    verdict: str
    dimensions: Dict[str, str]
    reason: str
    top_buyer_name: Optional[str] = None
    weights: Dict[str, float] = Field(default_factory=dict)
