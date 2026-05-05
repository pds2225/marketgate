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
    year: Optional[int] = Field(2023, description="default 2023")
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
            return 2023
        # 안정적으로 일단 2023년을 임시로 넣어둠. 문서엔 없어서 추후 전체 코드 검토 시 공유 필요 
        return int(v)


class PredictResult(BaseModel):
    rank: int
    partner_country_iso3: str
    fit_score: float
    score_components: Dict[str, float]
    explanation: Dict[str, Any]


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


class InquiryRequest(BaseModel):
    buyer_name: str = Field(..., description="Buyer company name")
    contact_email: str = Field(..., description="Buyer contact email")
    hs_code: str = Field(..., description="HS code for the product")
    sender_company: str = Field(..., description="Sender company name")
    sender_name: str = Field(..., description="Sender person name")
    message: Optional[str] = Field(default="", description="Optional additional message")


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
