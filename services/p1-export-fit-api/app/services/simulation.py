import csv
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
TARIFF_PATH = os.path.join(DATA_DIR, "tariff_rates.csv")
LOGISTICS_PATH = os.path.join(DATA_DIR, "logistics_rates.json")

_tariff_cache: dict = {}
_logistics_cache: dict = {}


def _load_tariff() -> dict:
    global _tariff_cache
    if _tariff_cache:
        return _tariff_cache
    result: dict = {}
    try:
        with open(TARIFF_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                result[f"{row['hs_code']}:{row['country']}"] = float(row["tariff_rate"])
    except FileNotFoundError:
        pass
    _tariff_cache = result
    return result


def _load_logistics() -> dict:
    global _logistics_cache
    if _logistics_cache:
        return _logistics_cache
    try:
        with open(LOGISTICS_PATH, "r", encoding="utf-8") as f:
            _logistics_cache = json.load(f)
    except FileNotFoundError:
        _logistics_cache = {}
    return _logistics_cache


def _get_tariff_rate(hs_code: str, country: str) -> tuple[float, bool]:
    key = f"{hs_code}:{country.lower()}"
    tariff = _load_tariff()
    if key in tariff:
        return tariff[key], False
    return 0.05, True


def _get_logistics_rate(mode: str, country: str) -> float:
    rates = _load_logistics()
    mode_rates = rates.get(mode, {})
    return mode_rates.get(country.lower(), mode_rates.get("default", 3.0))


def calc_landed_cost(
    hs_code: str,
    country: str,
    unit_price: float,
    qty: int,
    logistics: str,
) -> dict:
    tariff_rate, is_fallback = _get_tariff_rate(hs_code, country)
    logistics_rate = _get_logistics_rate(logistics, country)

    product_total = unit_price * qty
    tariff_cost = product_total * tariff_rate
    logistics_cost = qty * logistics_rate
    insurance_cost = product_total * 0.005
    landed = product_total + tariff_cost + logistics_cost + insurance_cost
    margin_rate = (product_total / landed) - 1

    if margin_rate < 0:
        grade = "적자"
    elif margin_rate < 0.05:
        grade = "손익분기"
    elif margin_rate < 0.15:
        grade = "보통"
    else:
        grade = "우수"

    result: dict = {
        "product_total": round(product_total, 2),
        "tariff_cost": round(tariff_cost, 2),
        "logistics_cost": round(logistics_cost, 2),
        "insurance_cost": round(insurance_cost, 2),
        "landed_cost": round(landed, 2),
        "margin_rate": round(margin_rate, 4),
        "tariff_rate_applied": tariff_rate,
        "profit_grade": grade,
    }
    if is_fallback:
        result["warning"] = "관세율 가정값 적용 (5%)"
    return result


def calc_bep(price: float, fixed_cost: float, variable_cost: float) -> dict:
    if price <= variable_cost:
        raise ValueError("price must be greater than variable_cost")
    bep_qty = fixed_cost / (price - variable_cost)
    return {
        "bep_qty": round(bep_qty, 2),
        "bep_revenue": round(bep_qty * price, 2),
    }
