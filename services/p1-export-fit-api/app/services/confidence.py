"""신뢰도(confidence) — SIMULATION_SPEC §3.

필수 5필드의 결측률 기반으로 confidence(0~1)와 등급을 계산한다.
- confidence = round(1.0 - missing_rate, 2)  (§3.1, §5.2)
- 등급 경계: >=0.8 high / >=0.6 medium / >=0.4 low / else very_low  (§3.2)
"""
from typing import Any, Dict

# SPEC §3.1 필수 필드 5종
REQUIRED_FIELDS = ["export_score", "gdp", "growth_rate", "market_size", "news_risk"]


def confidence_level(confidence: float) -> str:
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.6:
        return "medium"
    if confidence >= 0.4:
        return "low"
    return "very_low"


def build_data_coverage(available_data: Dict[str, Any]) -> Dict[str, Any]:
    """필수 필드 값 딕셔너리(None=결측)로 data_coverage 블록(§3.3, §5.2)을 만든다."""
    total = len(REQUIRED_FIELDS)
    missing_fields = [f for f in REQUIRED_FIELDS if available_data.get(f) is None]
    available_count = total - len(missing_fields)
    missing_rate = len(missing_fields) / total
    confidence = round(1.0 - missing_rate, 2)
    return {
        "confidence": confidence,
        "confidence_level": confidence_level(confidence),
        "missing_rate": round(missing_rate, 2),
        "total_fields": total,
        "available_fields": available_count,
        "missing_fields": missing_fields,
        "available_data": {
            k: v for k, v in available_data.items()
            if k in REQUIRED_FIELDS and v is not None
        },
        "data_source_status": {
            f: ("success" if available_data.get(f) is not None else "failed")
            for f in REQUIRED_FIELDS
        },
    }
