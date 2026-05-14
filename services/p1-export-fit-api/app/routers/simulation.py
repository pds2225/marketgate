from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException

from app.auth_deps import get_current_user
from app.services.simulation import calc_landed_cost, calc_bep

router = APIRouter(prefix="/v1/simulation", tags=["simulation"])


@router.post("/landed-cost")
def landed_cost(
    payload: Dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
):
    hs_code = str(payload.get("hs_code", "")).strip()
    country = str(payload.get("country", "")).strip()
    logistics = str(payload.get("logistics", "sea")).strip().lower()

    if not hs_code:
        raise HTTPException(status_code=400, detail="hs_code required")
    if not country:
        raise HTTPException(status_code=400, detail="country required")
    if logistics not in ("air", "sea"):
        raise HTTPException(status_code=400, detail="logistics must be 'air' or 'sea'")

    try:
        unit_price = float(payload.get("unit_price", 0))
        qty = int(payload.get("qty", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid unit_price or qty")

    if unit_price <= 0 or qty <= 0:
        raise HTTPException(status_code=400, detail="unit_price and qty must be > 0")

    return calc_landed_cost(hs_code, country, unit_price, qty, logistics)


@router.post("/bep")
def bep(
    payload: Dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
):
    try:
        price = float(payload.get("price", 0))
        fixed_cost = float(payload.get("fixed_cost", 0))
        variable_cost = float(payload.get("variable_cost", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid input values")

    if price <= 0 or fixed_cost <= 0:
        raise HTTPException(status_code=400, detail="price and fixed_cost must be > 0")

    try:
        return calc_bep(price, fixed_cost, variable_cost)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
