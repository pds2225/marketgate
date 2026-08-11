"""B7 — Export Action Plan 30/60/90 (순수함수, FastAPI import 금지).

readiness 결과(readiness_score + 선택적 dimensions) + top_buyer_name + buyer_signal 을 받아
정확히 3구간(0-30 / 31-60 / 61-90)의 결정론적 액션 플랜을 만든다.

같은 입력 → 같은 출력(결정론). 네트워크·파일쓰기·전역상태 변경 0 (순수함수).
"""
from __future__ import annotations

from typing import Any, Optional

WINDOWS = ["0-30", "31-60", "61-90"]

# readiness_score → 실행 트랙 (READINESS_THRESHOLDS 와 동일 경계: >=75 / >=50 / <50)
_TRACK_PASS = 75
_TRACK_WARN = 50

_FALLBACK_BUYER = "the top-matched buyer"


def _resolve_track(readiness_score: int) -> str:
    if readiness_score >= _TRACK_PASS:
        return "ready"          # 즉시 실행 (바이어 컨택 중심)
    if readiness_score >= _TRACK_WARN:
        return "improving"      # 보강 후 실행
    return "foundational"       # 기초 검증 우선


def _phase_0_30(track: str, buyer: str, buyer_signal: str) -> list[str]:
    """0-30일: 트랙별 즉시 액션. actions[0] 은 항상 top_buyer 를 참조(저준비도 포함)."""
    if track == "ready":
        actions = [
            f"{buyer}에게 맞춤 영업 레터(인콰이어리)를 발송하고 제품 카탈로그·가격표를 공유한다",
            "상위 바이어 3곳에 우선순위를 매겨 1차 컨택을 시작한다",
            "수출 단가·랜디드코스트(관세·물류 포함)를 확정해 견적 초안을 작성한다",
        ]
    elif track == "improving":
        actions = [
            f"{buyer}의 적합성·연락처를 재검증한 뒤 1차 컨택을 진행한다",
            "약한 준비 항목(시장·바이어·마진·규제 중 미흡 차원)을 우선 보강한다",
            "대상 시장의 인증·규제 요건을 점검해 진입 장벽을 정리한다",
        ]
    else:  # foundational
        actions = [
            f"{buyer}의 연락처와 바이어 적합성을 먼저 검증한다(컨택 전 사실 확인)",
            "대상 시장의 수요·경쟁을 재조사해 진입 타당성을 확인한다",
            "수익성(마진) 구조와 최소 수량(MOQ) 가정을 재점검한다",
        ]
    if buyer_signal == "none":
        actions.append("shortlist 바이어가 부족하므로 바이어 발굴·검증 범위를 넓힌다")
    return actions


def _phase_31_60(track: str, buyer: str) -> list[str]:
    """31-60일: 협상·샘플·규제 준비."""
    if track == "ready":
        return [
            f"{buyer}와 샘플·견적 조건을 협의하고 NDA/거래 조건을 조율한다",
            "선적 샘플을 준비하고 결제·인코텀즈 조건 초안을 작성한다",
            "필요 인증·통관 서류를 사전 점검한다",
        ]
    if track == "improving":
        return [
            "1차 컨택에 응답한 바이어와 샘플·조건 협의를 시작한다",
            "가격 경쟁력을 높이기 위해 원가·물류 옵션을 비교한다",
            "필요 인증·라벨링 요건을 구체화한다",
        ]
    return [
        "검증된 바이어 후보군을 대상으로 소량 컨택을 시작한다",
        "시장 진입에 필요한 핵심 인증·규제 요건을 확보 계획에 반영한다",
        "가격·마진 시나리오를 재설계해 손익분기 조건을 맞춘다",
    ]


def _phase_61_90(track: str, buyer: str) -> list[str]:
    """61-90일: 계약·물류·반복주문·스케일업."""
    if track == "ready":
        return [
            f"{buyer}와 1차 계약(또는 PO)을 체결하고 선적·물류를 실행한다",
            "초도 물량 출하 후 재주문·정기 공급 조건을 협의한다",
            "성과를 바탕으로 인접 시장·바이어로 파이프라인을 확장한다",
        ]
    if track == "improving":
        return [
            "조건 협의가 마무리된 바이어와 1차 거래를 성사시킨다",
            "초도 거래 피드백으로 제품·가격을 보정한다",
            "준비도 점수를 재측정해 다음 분기 목표를 설정한다",
        ]
    return [
        "보강된 준비도를 바탕으로 우선 바이어와 소규모 시범 거래를 추진한다",
        "시범 거래 결과로 시장 적합성·수익성을 재검증한다",
        "준비도 점수를 재측정해 본격 진입 시점을 판단한다",
    ]


def build_action_plan(
    *,
    readiness_score: int,
    top_buyer_name: Optional[str] = None,
    buyer_signal: Optional[str] = "none",
    dimensions: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """30/60/90 액션 플랜 생성. 정확히 3구간, 각 actions 비어있지 않음, phase[0] 액션이 buyer 참조."""
    score = int(readiness_score)
    buyer = str(top_buyer_name or "").strip() or _FALLBACK_BUYER
    signal = str(buyer_signal or "none").strip().lower()
    track = _resolve_track(score)

    phases = [
        {"window": WINDOWS[0], "title": "0-30일: 즉시 실행", "actions": _phase_0_30(track, buyer, signal)},
        {"window": WINDOWS[1], "title": "31-60일: 협상·준비", "actions": _phase_31_60(track, buyer)},
        {"window": WINDOWS[2], "title": "61-90일: 계약·확장", "actions": _phase_61_90(track, buyer)},
    ]

    # dimensions 가 있으면 미흡 차원에 대한 결정론적 보강 메모를 추가(액션 구조는 불변)
    focus: list[str] = []
    if dimensions:
        label = {"market": "시장 적합성", "buyer": "바이어 신호", "margin": "수익성", "compliance": "규제·제재"}
        for dim in ("market", "buyer", "margin", "compliance"):
            verdict = dimensions.get(dim)
            if verdict in ("warn", "fail"):
                focus.append(label[dim])

    return {
        "readiness_score": score,
        "track": track,
        "top_buyer_name": top_buyer_name,
        "phases": phases,
        "focus_areas": focus,
    }
