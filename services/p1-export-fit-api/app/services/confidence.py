"""신뢰도(confidence) — SIMULATION_SPEC §3.

필수 5필드의 결측률 기반으로 confidence(0~1)와 등급을 계산한다.
- confidence = round(1.0 - missing_rate, 2)  (§3.1, §5.2)
- 등급 경계: >=0.8 high / >=0.6 medium / >=0.4 low / else very_low  (§3.2)
"""
from typing import Any, Dict

# SPEC §3.1 필수 필드 5종
REQUIRED_FIELDS = ["export_score", "gdp", "growth_rate", "market_size", "news_risk"]

# 리스크 평가 신호 필드 — 현재 데이터 소스 미구현으로 항상 결측이다.
RISK_FIELD = "news_risk"

# 리스크 미평가 시 표시(display)용 confidence 상한 등급 (matchA — 라벨링만, 수치 불변)
_CAPPED_LEVEL_WHEN_RISK_UNASSESSED = "medium"


def confidence_level(confidence: float) -> str:
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.6:
        return "medium"
    if confidence >= 0.4:
        return "low"
    return "very_low"


def _cap_display_level(level: str, risk_assessed: bool) -> str:
    """리스크가 평가되지 않았으면 'high' 표시를 막아 medium으로 낮춘다(표시용)."""
    if not risk_assessed and level == "high":
        return _CAPPED_LEVEL_WHEN_RISK_UNASSESSED
    return level


def build_data_coverage(available_data: Dict[str, Any]) -> Dict[str, Any]:
    """필수 필드 값 딕셔너리(None=결측)로 data_coverage 블록(§3.3, §5.2)을 만든다."""
    total = len(REQUIRED_FIELDS)
    missing_fields = [f for f in REQUIRED_FIELDS if available_data.get(f) is None]
    available_count = total - len(missing_fields)
    missing_rate = len(missing_fields) / total
    confidence = round(1.0 - missing_rate, 2)
    level = confidence_level(confidence)

    # 리스크(news_risk) 평가 여부 — 미평가면 'high' 표시를 막는다(수치/기존필드 불변, 가산).
    risk_assessed = available_data.get(RISK_FIELD) is not None
    display_level = _cap_display_level(level, risk_assessed)
    return {
        "confidence": confidence,
        "confidence_level": level,
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
        # 가산 필드 (matchA): 리스크 미평가 시 가짜 high 라벨 방지 + 정직 표시
        "risk_assessed": risk_assessed,
        "display_confidence_level": display_level,
        "risk_note": None if risk_assessed else "리스크(뉴스/제재 동향) 미평가 — 신뢰도 상한 medium",
    }
