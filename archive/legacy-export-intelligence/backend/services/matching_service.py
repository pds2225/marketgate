"""Business logic for buyer–seller matching.

The matching service compares a given profile (either buyer or seller) against
a set of opposite profiles loaded from the in-memory database. It computes a
simple fit score based on HS code alignment, price range overlap, minimum
order quantity (MOQ) compatibility, certification requirements and country
considerations. The output includes the top matches with their scores and
human‑readable rationales.
"""

from __future__ import annotations

from typing import List

from ..database.database import load_seller_profiles, load_buyer_profiles
from ..models.schemas import MatchRequest, MatchResponse, MatchItem, Profile


def _price_overlap(a_range: List[float] | None, b_range: List[float] | None) -> bool:
    """Return True if two price ranges overlap.

    If either range is missing, assume overlap.
    """
    if not a_range or not b_range:
        return True
    return not (a_range[1] < b_range[0] or b_range[1] < a_range[0])


def _moq_compatible(required: int | None, offered: int | None) -> bool:
    """Check whether the offered MOQ meets or is below the required MOQ.

    If either side is None, assume compatibility.
    """
    if required is None or offered is None:
        return True
    return offered <= required


def _certification_match(req_certs: List[str] | None, offered_certs: List[str] | None) -> bool:
    """Check whether offered certifications cover all required certifications.

    If no requirements, return True.
    """
    req_set = set(req_certs or [])
    offered_set = set(offered_certs or [])
    return req_set.issubset(offered_set)


def find_matches(request: MatchRequest) -> MatchResponse:
    """Compute a list of potential matches for the given profile.

    Parameters
    ----------
    request : MatchRequest
        The profile seeking matches.

    Returns
    -------
    MatchResponse
        A response containing partner identifiers, fit scores and rationales.
    """
    profile: Profile = request.profile
    role = profile.role.lower()
    matches: List[MatchItem] = []

    # Load opposite party profiles
    if role == "seller":
        candidates = load_buyer_profiles()
    elif role == "buyer":
        candidates = load_seller_profiles()
    else:
        raise ValueError(f"Unknown role: {profile.role}")

    for candidate in candidates:
        fit_score = 0.0
        reasons = []
        # HS code match
        if candidate["hs_code"] == profile.hs_code:
            fit_score += 25
            reasons.append("HS 코드가 정확히 일치합니다.")
        else:
            # Partial match could be implemented by comparing first 4 digits
            if candidate["hs_code"][:4] == profile.hs_code[:4]:
                fit_score += 15
                reasons.append("HS 코드 앞 4자리가 일치합니다.")
        # Price range overlap
        if _price_overlap(candidate.get("price_range"), profile.price_range):
            fit_score += 20
            reasons.append("희망 단가 범위가 겹칩니다.")
        else:
            reasons.append("단가 범위가 서로 다릅니다.")
        # MOQ compatibility
        # For buyer role, buyer.moq must be >= seller.moq (seller's minimum) else false; for seller role, seller.moq must be <= buyer.moq
        if role == "seller":
            # seller looking at buyer: buyer MOQ requirement must be >= seller's capability
            compatible = _moq_compatible(candidate.get("moq"), profile.moq)
        else:
            # buyer looking at seller: seller MOQ must be <= buyer's acceptable MOQ
            compatible = _moq_compatible(profile.moq, candidate.get("moq"))
        if compatible:
            fit_score += 20
            reasons.append("MOQ 조건이 적합합니다.")
        else:
            reasons.append("MOQ 조건이 맞지 않습니다.")
        # Certification match: seller must have the certifications buyer requires or vice versa
        if role == "seller":
            cert_match = _certification_match(candidate.get("certifications"), profile.certifications)
        else:
            cert_match = _certification_match(profile.certifications, candidate.get("certifications"))
        if cert_match:
            fit_score += 15
            reasons.append("인증 조건이 충족됩니다.")
        else:
            reasons.append("인증 요구 사항을 충족하지 않습니다.")
        # Country consideration: encourage cross‑border transactions
        if candidate.get("country") != profile.country:
            fit_score += 10
            reasons.append("다른 국가 간 거래로 시장 다변화가 가능합니다.")
        else:
            reasons.append("동일 국가 거래입니다.")

        # Construct match object if score above threshold
        if fit_score > 30:
            matches.append(
                MatchItem(
                    partner_id=candidate["id"],
                    fit_score=round(fit_score, 1),
                    rationale=" ".join(reasons),
                )
            )

    # Sort matches by score descending and return top five
    sorted_matches = sorted(matches, key=lambda m: m.fit_score, reverse=True)[:5]
    return MatchResponse(matches=sorted_matches)