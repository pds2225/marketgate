"""Matching API endpoints.

This module defines an endpoint for computing buyer–seller matches based on
profile similarity and basic business rules. The endpoint accepts a seller or
buyer profile and returns a list of potential partners with fit scores and
explanatory rationales.
"""

from fastapi import APIRouter, HTTPException
from ..models.schemas import MatchRequest, MatchResponse
from ..services.matching_service import find_matches

router = APIRouter()


@router.post("/", response_model=MatchResponse)
async def match(request: MatchRequest) -> MatchResponse:
    """Find potential trading partners for a given profile.

    Parameters
    ----------
    request : MatchRequest
        The profile information describing a buyer or seller looking for
        partners.

    Returns
    -------
    MatchResponse
        A set of matching profiles with fit scores and rationales.
    """
    try:
        return find_matches(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc