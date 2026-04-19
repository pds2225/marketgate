"""Business logic for generating export country recommendations.

This service layer encapsulates the logic to assemble recommendations for
export markets based on a simple rule set and a placeholder data source
representing KOTRA's export potential scores. The scoring logic is kept
deliberately straightforward in this MVP implementation: it uses a base
score from the KOTRA data and ignores more advanced factors such as
adjacency, market fit or buyer availability. Such enhancements can be
added later.
"""

from __future__ import annotations

import random
from typing import List

from ..models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendedCountry,
)

# A placeholder mapping of HS codes to sample KOTRA recommendation scores.
# In a real implementation this would be fetched via the KOTRA API using
# authentication keys and proper error handling. Each entry maps an HS code
# to a list of candidate countries along with a base score (0–1) and a
# reason from KOTRA (here we simply use dummy text).
SAMPLE_KOTRA_DATA = {
    "330499": [
        {"country": "US", "score": 0.85, "rationale": "High cosmetics demand and stable regulations."},
        {"country": "VN", "score": 0.78, "rationale": "Growing middle class and interest in K-beauty."},
        {"country": "JP", "score": 0.75, "rationale": "High purchasing power and proximity to Korea."},
        {"country": "AE", "score": 0.70, "rationale": "Expanding luxury market in the Middle East."},
        {"country": "SG", "score": 0.68, "rationale": "Regional hub with affluent consumers."},
        {"country": "CN", "score": 0.65, "rationale": "Large market but intense competition."},
    ],
    "300490": [
        {"country": "BR", "score": 0.80, "rationale": "Growing pharmaceutical imports."},
        {"country": "IN", "score": 0.77, "rationale": "Large population and rising healthcare demand."},
        {"country": "ID", "score": 0.72, "rationale": "Rapidly expanding healthcare sector."},
        {"country": "MX", "score": 0.70, "rationale": "Trade agreements facilitating imports."},
        {"country": "ZA", "score": 0.65, "rationale": "Developing pharmaceutical market."},
    ],
    "210690": [
        {"country": "US", "score": 0.82, "rationale": "High demand for food supplements."},
        {"country": "CN", "score": 0.78, "rationale": "Large health food market with growth potential."},
        {"country": "TH", "score": 0.72, "rationale": "Growing health consciousness."},
        {"country": "MY", "score": 0.70, "rationale": "Rising disposable income and interest in supplements."},
        {"country": "AU", "score": 0.68, "rationale": "Stable regulations and demand for quality imports."},
    ],
}


def get_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    """Compute export market recommendations for a given request.

    The current implementation selects up to five countries associated with the
    provided HS code from a predefined dataset. Each country's score is
    returned as the final score and the KOTRA rationale is used as the
    explanation. If the HS code is not present in the sample data, a
    fallback list of random countries and scores is generated.

    Parameters
    ----------
    request : RecommendationRequest
        The input request containing the HS code, current export countries and
        objective.

    Returns
    -------
    RecommendationResponse
        Response containing a list of recommended countries sorted by score.
    """
    hs_code = request.hs_code.strip()
    current = {c.upper() for c in request.current_countries}

    # Retrieve sample data or generate random fallback
    candidates = SAMPLE_KOTRA_DATA.get(hs_code)
    if not candidates:
        # Fallback: choose 5 random ISO country codes and random scores
        iso_codes = ["US", "CN", "JP", "DE", "FR", "GB", "CA", "VN", "IN", "AU"]
        random.shuffle(iso_codes)
        candidates = [
            {
                "country": code,
                "score": round(random.uniform(0.5, 0.8), 2),
                "rationale": "No KOTRA data available; generated recommendation."
            }
            for code in iso_codes[:5]
        ]

    # Filter out countries already present in current export list if target is new market
    if request.target.lower() == "new_market":
        filtered = [c for c in candidates if c["country"] not in current]
    else:
        filtered = candidates

    # Limit to top 5 by score
    top_candidates = sorted(filtered, key=lambda x: x["score"], reverse=True)[:5]

    recommendations: List[RecommendedCountry] = []
    for entry in top_candidates:
        recommendations.append(
            RecommendedCountry(
                country=entry["country"],
                score=entry["score"],
                rationale=entry["rationale"],
            )
        )

    return RecommendationResponse(recommendations=recommendations)