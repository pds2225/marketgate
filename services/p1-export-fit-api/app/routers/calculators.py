"""수출 계산기 API 라우터.

비로그인 접근 허용 — 계산기는 유입 퍼널의 첫 단계다.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from app.services.calculators import (
    DESTINATION_COUNTRIES,
    calc_export_price,
    calc_cbm,
    calc_buyer_landed_cost,
)

router = APIRouter(prefix="/v1/calculators", tags=["calculators"])


# ── 수출단가 계산 ────────────────────────────────────────────
@router.post("/export-price")
def export_price(payload: Dict[str, Any] = Body(...)):
    try:
        unit_price = float(payload.get("unit_price", 0))
        qty = int(payload.get("qty", 0))
        inland_transport = float(payload.get("inland_transport", 0))
        customs_docs = float(payload.get("customs_docs", 0))
        freight_usd = float(payload.get("freight_usd", 0))
        insurance_rate = float(payload.get("insurance_rate", 0.001))
        fx_rate = float(payload.get("fx_rate", 1372.50))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid numeric input")

    if unit_price <= 0 or qty <= 0:
        raise HTTPException(status_code=400, detail="unit_price and qty must be > 0")
    if fx_rate <= 0:
        raise HTTPException(status_code=400, detail="fx_rate must be > 0")

    return calc_export_price(
        unit_price=unit_price,
        qty=qty,
        inland_transport=inland_transport,
        customs_docs=customs_docs,
        freight_usd=freight_usd,
        insurance_rate=insurance_rate,
        fx_rate=fx_rate,
    )


# ── CBM · 컨테이너 계산 ──────────────────────────────────────
@router.post("/cbm")
def cbm(payload: Dict[str, Any] = Body(...)):
    try:
        box_w = float(payload.get("box_w_cm", 0))
        box_d = float(payload.get("box_d_cm", 0))
        box_h = float(payload.get("box_h_cm", 0))
        qty = int(payload.get("qty", 0))
        weight_per_box = float(payload.get("weight_per_box_kg", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid numeric input")

    if box_w <= 0 or box_d <= 0 or box_h <= 0:
        raise HTTPException(status_code=400, detail="box dimensions must be > 0")
    if qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")

    return calc_cbm(
        box_w_cm=box_w,
        box_d_cm=box_d,
        box_h_cm=box_h,
        qty=qty,
        weight_per_box_kg=weight_per_box,
    )


# ── 바이어 도착원가 ──────────────────────────────────────────
@router.post("/landed-cost")
def landed_cost(payload: Dict[str, Any] = Body(...)):
    hs_code = str(payload.get("hs_code", "")).strip()
    country = str(payload.get("country", "")).strip().lower()

    if not hs_code:
        raise HTTPException(status_code=400, detail="hs_code required")
    if not country:
        raise HTTPException(status_code=400, detail="country required")

    try:
        cif_usd = float(payload.get("cif_usd", 0))
        fx_rate = float(payload.get("fx_rate", 1372.50))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid numeric input")

    if cif_usd <= 0:
        raise HTTPException(status_code=400, detail="cif_usd must be > 0")

    return calc_buyer_landed_cost(
        hs_code=hs_code,
        country=country,
        cif_usd=cif_usd,
        fx_rate=fx_rate,
    )


# ── 도착국 목록 (프론트 카드용) ───────────────────────────────
@router.get("/countries")
def countries():
    return DESTINATION_COUNTRIES
