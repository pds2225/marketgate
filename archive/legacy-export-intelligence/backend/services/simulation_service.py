"""Business logic for performance simulation.

This service provides a simplistic implementation of the export performance
prediction. It combines basic market and company parameters to estimate a
potential revenue range and a probability of success. The formulas are
deliberately simple and should be replaced with data‑driven models once
historical data and machine learning infrastructure are available.
"""

from __future__ import annotations

from ..models.schemas import SimulationRequest, SimulationResponse


def simulate_performance(request: SimulationRequest) -> SimulationResponse:
    """Estimate expected revenue and success probability for an export plan.

    Parameters
    ----------
    request : SimulationRequest
        The simulation parameters including market size, growth rate,
        company pricing and capacity, competitor count and tariff rate.

    Returns
    -------
    SimulationResponse
        Estimated revenue range, probability of success and explanatory text.
    """
    # Basic revenue model: combine market size and company capacity
    base_revenue = (request.market_size * 0.5) + (
        request.company_average_price * request.company_average_moq * 0.3
    )
    # Apply penalty for competition (up to 30% reduction)
    competition_penalty = 1.0 - min(request.competitor_count * 0.02, 0.30)
    estimated_revenue = base_revenue * competition_penalty

    revenue_min = estimated_revenue * 0.8
    revenue_max = estimated_revenue * 1.2

    # Success probability model
    probability = 0.0
    # Factor 1: market growth rate
    probability += 0.3 if request.market_growth_rate > 0.05 else 0.15
    # Factor 2: competition intensity
    probability += 0.3 if request.competitor_count < 10 else 0.1
    # Factor 3: tariff rate
    probability += 0.2 if request.tariff_rate < 0.05 else 0.1
    # Factor 4: baseline success assumption
    probability += 0.2
    # Clamp to [0, 1]
    probability = max(0.0, min(probability, 1.0))

    # Build rationale
    reasons = []
    if request.market_growth_rate > 0.05:
        reasons.append(
            f"해당 시장의 성장률이 {request.market_growth_rate:.1%}로 높아 수요 증가가 예상됩니다."
        )
    else:
        reasons.append(
            f"해당 시장의 성장률이 {request.market_growth_rate:.1%}로 낮아 성장성이 제한적일 수 있습니다."
        )
    if request.competitor_count < 10:
        reasons.append(
            f"경쟁업체 수가 {request.competitor_count}개로 적어 진입 장벽이 낮습니다."
        )
    else:
        reasons.append(
            f"경쟁업체 수가 {request.competitor_count}개로 많아 시장 경쟁이 치열합니다."
        )
    if request.tariff_rate < 0.05:
        reasons.append(
            f"관세율이 {request.tariff_rate:.1%}로 낮아 가격 경쟁력이 있습니다."
        )
    else:
        reasons.append(
            f"관세율이 {request.tariff_rate:.1%}로 높아 가격 경쟁력이 낮을 수 있습니다."
        )
    rationale = " ".join(reasons)

    return SimulationResponse(
        revenue_min=round(revenue_min, 2),
        revenue_max=round(revenue_max, 2),
        success_probability=round(probability, 2),
        rationale=rationale,
    )