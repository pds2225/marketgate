# -*- coding: utf-8 -*-
"""CV-02: OpenCorporates Mock company verification API."""
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth_deps import get_current_user
from app.company_verification_store import create_verification, get_verification

router = APIRouter(prefix="/v1", tags=["company-verification"])

MOCK_STATUSES = [
    "BASIC_CONFIRMED",
    "BASIC_PARTIAL",
    "DATA_MISMATCH",
    "INACTIVE_ENTITY",
    "CREDIT_CHECK_REQUIRED",
]

PROVIDER = "opencorporates"


class VerificationRequest(BaseModel):
    company_name: str = Field(..., min_length=1)
    country_iso3: str = Field(..., min_length=3, max_length=3)
    registration_number: str | None = None


def _deterministic_status(company_name: str) -> str:
    h = hashlib.sha256(company_name.encode("utf-8")).hexdigest()
    idx = int(h, 16) % 5
    return MOCK_STATUSES[idx]


@router.post("/company-verifications")
def create_company_verification(
    req: VerificationRequest,
    user: dict = Depends(get_current_user),
):
    status = _deterministic_status(req.company_name)
    result_json = {
        "provider": PROVIDER,
        "match_status": status,
        "mock": True,
    }
    record = create_verification(
        user_id=user["user_id"],
        company_name=req.company_name,
        country_iso3=req.country_iso3.upper(),
        registration_number=req.registration_number,
        provider=PROVIDER,
        registry_check_status=status,
        result_json=result_json,
    )
    return record


@router.get("/company-verifications/{verification_id}")
def get_company_verification(
    verification_id: str,
    user: dict = Depends(get_current_user),
):
    record = get_verification(verification_id, user["user_id"])
    if record is None:
        raise HTTPException(status_code=404, detail="verification_not_found")
    return record
