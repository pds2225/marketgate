"""Simulation API endpoints.

This module defines a POST endpoint that accepts input parameters for
simulating export performance in a given country and product context. It
utilises a simple linear model to estimate potential revenue ranges and
probabilities of success, returning these metrics along with explanatory
text.
"""

from fastapi import APIRouter, HTTPException
from ..models.schemas import SimulationRequest, SimulationResponse
from ..services.simulation_service import simulate_performance

router = APIRouter()


@router.post("/", response_model=SimulationResponse)
async def simulate(request: SimulationRequest) -> SimulationResponse:
    """Run an export performance simulation for a product in a specific country.

    Parameters
    ----------
    request : SimulationRequest
        Input data describing the product, target country and relevant
        business metrics such as market size, growth rate and company
        specific parameters.

    Returns
    -------
    SimulationResponse
        Predicted revenue range, success probability and explanatory
        rationale.
    """
    try:
        return simulate_performance(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc