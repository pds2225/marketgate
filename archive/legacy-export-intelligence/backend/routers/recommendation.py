"""Recommendation API endpoints.

Exposes a POST endpoint that accepts a recommendation request containing
an HS code, the list of current export countries, and a target objective
(either discovering new markets or expanding existing ones). The endpoint
returns a list of recommended countries with scores and rationales.
"""

from fastapi import APIRouter, HTTPException
from ..models.schemas import RecommendationRequest, RecommendationResponse
from ..services.recommendation_service import get_recommendations

router = APIRouter()


@router.post("/", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest) -> RecommendationResponse:
    """Generate a list of recommended export countries.

    Parameters
    ----------
    request : RecommendationRequest
        The input payload describing the product HS code, current export
        destinations, and the business objective.

    Returns
    -------
    RecommendationResponse
        A response containing a list of recommended countries with associated
        scores and rationales.
    """
    try:
        return get_recommendations(request)
    except Exception as exc:  # pragma: no cover - catch all unexpected errors
        raise HTTPException(status_code=500, detail=str(exc)) from exc