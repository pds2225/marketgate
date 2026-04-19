"""Pydantic models used for request and response payloads.

These schema classes define the structure of data exchanged via API
endpoints. They are used for validation and OpenAPI documentation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Input model for generating export country recommendations."""

    hs_code: str = Field(..., description="HS 6‑digit code identifying the product.")
    current_countries: List[str] = Field(
        default_factory=list,
        description="List of ISO country codes where the product is currently exported."
    )
    target: str = Field(
        ...,
        description="Objective for the recommendation: 'new_market' or 'expansion'."
    )


class RecommendedCountry(BaseModel):
    """Representation of a single recommended country."""

    country: str = Field(..., description="ISO code of the recommended country.")
    score: float = Field(..., ge=0, le=1, description="Final recommendation score (0–1).")
    rationale: str = Field(..., description="Explanation of why this country is recommended.")


class RecommendationResponse(BaseModel):
    """Response model containing a list of recommendations."""

    recommendations: List[RecommendedCountry] = Field(
        ..., description="List of recommended countries sorted by score."
    )


class SimulationRequest(BaseModel):
    """Input model for performance simulation."""

    hs_code: str = Field(..., description="HS code of the product to simulate.")
    country: str = Field(..., description="Target export country (ISO code).")
    market_size: float = Field(..., ge=0, description="Estimated market size for this product in USD.")
    market_growth_rate: float = Field(..., description="Annual growth rate of the market (0–1).")
    company_average_price: float = Field(..., ge=0, description="Company's average unit export price in USD.")
    company_average_moq: int = Field(..., ge=1, description="Minimum order quantity the company can supply.")
    competitor_count: int = Field(..., ge=0, description="Number of major competitors in the target market.")
    tariff_rate: float = Field(..., ge=0, description="Applicable import tariff rate for the product (0–1).")


class SimulationResponse(BaseModel):
    """Response model for performance simulation."""

    revenue_min: float = Field(..., description="Lower bound estimate of expected revenue in USD.")
    revenue_max: float = Field(..., description="Upper bound estimate of expected revenue in USD.")
    success_probability: float = Field(..., ge=0, le=1, description="Estimated probability of export success (0–1).")
    rationale: str = Field(..., description="Textual explanation for the simulation result.")


class Profile(BaseModel):
    """Base profile model for buyers and sellers."""

    id: str = Field(..., description="Unique identifier for the profile.")
    role: str = Field(..., description="Role of the entity: 'seller' or 'buyer'.")
    hs_code: str = Field(..., description="HS code of the product.")
    country: str = Field(..., description="ISO code of the country.")
    price_range: Optional[List[float]] = Field(
        None,
        description="Acceptable price range (min, max) for the product in USD."
    )
    moq: Optional[int] = Field(
        None,
        description="Minimum order quantity for the product."
    )
    certifications: Optional[List[str]] = Field(
        default_factory=list,
        description="List of certifications held (e.g. FDA, CE)."
    )


class MatchRequest(BaseModel):
    """Request model for computing matches."""

    profile: Profile = Field(..., description="Profile of the party seeking matches.")


class MatchItem(BaseModel):
    """A single match result with score and rationale."""

    partner_id: str = Field(..., description="Identifier of the potential partner.")
    fit_score: float = Field(..., ge=0, le=100, description="Fit score (0–100).")
    rationale: str = Field(..., description="Explanation of how the match was scored.")


class MatchResponse(BaseModel):
    """Response model for match results."""

    matches: List[MatchItem] = Field(
        ..., description="List of partner profiles sorted by fit score."
    )