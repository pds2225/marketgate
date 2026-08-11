"""수출 계산기 순수 함수 모듈.

모든 함수는 dict를 반환하며, 외부 I/O가 없다.
프론트에서 중복 구현하지 않도록 서버에서만 계산한다.
"""
from __future__ import annotations

import csv
import json
import os

# ── 데이터 로드 ──────────────────────────────────────────────
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_TARIFF_PATH = os.path.join(_DATA_DIR, "tariff_rates.csv")
_VAT_PATH = os.path.join(_DATA_DIR, "vat_rates.json")

_tariff_cache: dict[str, tuple[float, bool]] = {}
_vat_cache: dict[str, float] | None = None


def _load_tariff() -> dict[str, tuple[float, bool]]:
    global _tariff_cache
    if _tariff_cache:
        return _tariff_cache
    try:
        with open(_TARIFF_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = f"{row['hs_code']}:{row['country'].lower()}"
                _tariff_cache[key] = (float(row["tariff_rate"]), False)
    except FileNotFoundError:
        pass
    return _tariff_cache


def _load_vat() -> dict[str, float]:
    global _vat_cache
    if _vat_cache is not None:
        return _vat_cache
    _vat_cache = {}
    try:
        with open(_VAT_PATH, "r", encoding="utf-8") as f:
            _vat_cache = json.load(f)
    except FileNotFoundError:
        pass
    return _vat_cache


# ── 도착국 정보 ──────────────────────────────────────────────
DESTINATION_COUNTRIES = [
    {"code": "us", "name": "미국", "flag": "🇺🇸"},
    {"code": "jp", "name": "일본", "flag": "🇯🇵"},
    {"code": "cn", "name": "중국", "flag": "🇨🇳"},
    {"code": "de", "name": "독일", "flag": "🇩🇪"},
    {"code": "vn", "name": "베트남", "flag": "🇻🇳"},
    {"code": "in", "name": "인도", "flag": "🇮🇳"},
    {"code": "au", "name": "호주", "flag": "🇦🇺"},
    {"code": "ca", "name": "캐나다", "flag": "🇨🇦"},
    {"code": "gb", "name": "영국", "flag": "🇬🇧"},
    {"code": "fr", "name": "프랑스", "flag": "🇫🇷"},
]

CONTAINER_SPECS = {
    "20ft": {"label": "20ft Dry", "effective_cbm": 28},
    "40ft": {"label": "40ft Dry", "effective_cbm": 58},
    "40hq": {"label": "40ft HQ", "effective_cbm": 68},
}


# ── 수출단가 계산 (EXW → FOB → CFR → CIF) ──────────────────
def calc_export_price(
    unit_price: float,
    qty: int,
    inland_transport: float,
    customs_docs: float,
    freight_usd: float,
    insurance_rate: float,
    fx_rate: float,
) -> dict:
    """인코텀즈 단계별 수출단가를 계산한다.

    모든 금액은 KRW 단위 (freight_usd는 USD → KRW 환산).
    보험가액 = CFR × 110% (Incoterms 2020 CIF 최소부보 관례).
    """
    exw = unit_price * qty
    fob = exw + inland_transport + customs_docs
    freight_krw = freight_usd * fx_rate
    cfr = fob + freight_krw
    insurance = cfr * 1.10 * insurance_rate
    cif = cfr + insurance

    # 원화 → USD
    exw_usd = exw / fx_rate
    fob_usd = fob / fx_rate
    cfr_usd = cfr / fx_rate
    cif_usd = cif / fx_rate

    # 단가
    fob_unit = fob_usd / qty if qty else 0
    cif_unit = cif_usd / qty if qty else 0

    # 비중 (항목별 %)
    total = cif
    breakdown = []
    items = [
        ("제품원가 (EXW)", exw),
        ("국내 내륙운송", inland_transport),
        ("수출통관 · 서류", customs_docs),
        ("국제운임", freight_krw),
        ("적하보험", insurance),
    ]
    for label, amount in items:
        pct = (amount / total * 100) if total else 0
        breakdown.append({
            "label": label,
            "amount_krw": round(amount, 2),
            "percent": round(pct, 1),
        })

    # 단계별 누적
    stages = [
        {"label": "제품원가 (EXW)", "formula": f"{unit_price:,.0f} × {qty:,}", "amount_krw": round(exw, 2)},
        {"label": "+ 국내 내륙운송", "amount_krw": round(inland_transport, 2), "cumulative_krw": round(fob - customs_docs, 2)},
        {"label": "+ 수출통관 · 서류", "amount_krw": round(customs_docs, 2), "cumulative_krw": round(fob, 2)},
        {"label": "= FOB 부산", "amount_krw": round(fob, 2), "is_stage": True},
        {"label": f"+ 국제운임 (${freight_usd:,.0f})", "amount_krw": round(freight_krw, 2), "cumulative_krw": round(cfr, 2)},
        {"label": "= CFR", "amount_krw": round(cfr, 2), "is_stage": True},
        {"label": f"+ 적하보험 (CFR × 110% × {insurance_rate*100:.2f}%)", "amount_krw": round(insurance, 2)},
        {"label": "= CIF 총액", "amount_krw": round(cif, 2), "is_stage": True},
    ]

    return {
        "exw_krw": round(exw, 2),
        "exw_usd": round(exw_usd, 2),
        "fob_krw": round(fob, 2),
        "fob_usd": round(fob_usd, 2),
        "fob_unit_usd": round(fob_unit, 2),
        "cfr_krw": round(cfr, 2),
        "cfr_usd": round(cfr_usd, 2),
        "cif_krw": round(cif, 2),
        "cif_usd": round(cif_usd, 2),
        "cif_unit_usd": round(cif_unit, 2),
        "insurance_krw": round(insurance, 2),
        "fx_rate": fx_rate,
        "breakdown": breakdown,
        "stages": stages,
    }


# ── CBM · 컨테이너 계산 ──────────────────────────────────────
def calc_cbm(
    box_w_cm: float,
    box_d_cm: float,
    box_h_cm: float,
    qty: int,
    weight_per_box_kg: float,
) -> dict:
    """박스 CBM, 컨테이너 적재율, 권고를 계산한다."""
    box_cbm = (box_w_cm * box_d_cm * box_h_cm) / 1_000_000
    total_cbm = box_cbm * qty
    total_weight = weight_per_box_kg * qty

    containers = []
    for key, spec in CONTAINER_SPECS.items():
        eff = spec["effective_cbm"]
        ratio = (total_cbm / eff * 100) if eff else 0
        if ratio <= 100:
            status = "여유" if ratio <= 85 else "거의 참"
        else:
            status = "초과"
        containers.append({
            "type": key,
            "label": spec["label"],
            "effective_cbm": eff,
            "usage_percent": round(ratio, 1),
            "status": status,
        })

    # 권고
    if total_cbm >= 15:
        recommendation = "FCL (Full Container Load)을 권장합니다. LCL 대비 비용 효율이 높습니다."
        recommended_mode = "FCL"
    elif total_cbm >= 5:
        recommendation = "LCL과 FCL을 비교해 보세요. 15 m³ 이상이면 FCL이 보통 저렴합니다."
        recommended_mode = "비교"
    else:
        recommendation = "LCL (Less than Container Load)이 적합합니다."
        recommended_mode = "LCL"

    return {
        "box_cbm": round(box_cbm, 3),
        "total_cbm": round(total_cbm, 3),
        "total_weight_kg": round(total_weight, 1),
        "rt_cbm": round(total_cbm, 3),  # Revenue Ton
        "containers": containers,
        "recommended_mode": recommended_mode,
        "recommendation": recommendation,
    }


# ── 바이어 도착원가 (기존 calc_landed_cost 확장) ──────────────
def calc_buyer_landed_cost(
    hs_code: str,
    country: str,
    cif_usd: float,
    fx_rate: float = 1372.50,
) -> dict:
    """바이어 관점의 도착원가를 계산한다.

    기존 simulation.py의 calc_landed_cost와 달리,
    CIF 금액을 직접 입력받아 관세·VAT·FTA 절감액을 계산한다.
    """
    tariff_key = f"{hs_code}:{country.lower()}"
    tariff_data = _load_tariff()

    if tariff_key in tariff_data:
        tariff_rate, is_fallback = tariff_data[tariff_key]
    else:
        tariff_rate, is_fallback = 0.05, True  # 기본 추정값

    # FTA 추정: 주요국 FTA 협정세율 (관세 없거나 낮은 국가)
    fta_countries = {"us": 0.0, "jp": 0.0, "cn": 0.04, "de": 0.065, "vn": 0.0,
                     "in": 0.05, "au": 0.0, "ca": 0.0, "gb": 0.0, "fr": 0.065}
    fta_rate = fta_countries.get(country.lower(), tariff_rate)
    has_fta = fta_rate < tariff_rate

    cif_krw = cif_usd * fx_rate
    tariff_cost_usd = cif_usd * tariff_rate
    tariff_cost_krw = cif_krw * tariff_rate

    vat_rates = _load_vat()
    vat_rate = vat_rates.get(country.lower(), 0.10)  # 기본 10%
    vat_cost_usd = (cif_usd + tariff_cost_usd) * vat_rate
    vat_cost_krw = (cif_krw + tariff_cost_krw) * vat_rate

    local_customs_usd = 150  # 현지 통관비 추정
    local_customs_krw = local_customs_usd * fx_rate

    landed_usd = cif_usd + tariff_cost_usd + vat_cost_usd + local_customs_usd
    landed_krw = cif_krw + tariff_cost_krw + vat_cost_krw + local_customs_krw

    # FTA 절감액
    fta_saving_usd = 0.0
    if has_fta:
        fta_saving_usd = cif_usd * (tariff_rate - fta_rate)
    fta_saving_krw = fta_saving_usd * fx_rate

    return {
        "cif_usd": round(cif_usd, 2),
        "cif_krw": round(cif_krw, 2),
        "tariff_rate": tariff_rate,
        "tariff_cost_usd": round(tariff_cost_usd, 2),
        "tariff_cost_krw": round(tariff_cost_krw, 2),
        "vat_rate": vat_rate,
        "vat_cost_usd": round(vat_cost_usd, 2),
        "vat_cost_krw": round(vat_cost_krw, 2),
        "local_customs_usd": round(local_customs_usd, 2),
        "local_customs_krw": round(local_customs_krw, 2),
        "landed_usd": round(landed_usd, 2),
        "landed_krw": round(landed_krw, 2),
        "is_fallback": is_fallback,
        "has_fta": has_fta,
        "fta_rate": fta_rate if has_fta else None,
        "fta_saving_usd": round(fta_saving_usd, 2),
        "fta_saving_krw": round(fta_saving_krw, 2),
        "fx_rate": fx_rate,
    }
