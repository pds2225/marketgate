"""
matchD 회귀 테스트 — 바이어 매칭 관련성 정확도 강화.

버그(고정 대상): 정렬 1순위가 decision이라, HS/키워드 매칭이 전혀 없는
무관(match_relevance="none") 바이어가 decision="shortlist"이기만 하면
강한 HS 매칭(strong) 후보를 제치고 상위로 올라오던 결함. 관련 없는 바이어가
관련 있는 바이어보다 위에 노출됨.

이 테스트는 "무관 바이어는 decision이 좋아도 관련 바이어를 추월하지 못한다"와
"관련성이 같으면 기존 우선순위(decision 등)는 그대로 유지된다(과교정 금지)"를
_buyer_sort_key 단위로 결정론적으로 고정한다. 기존 응답 필드는 불변(정렬 순서만).
"""
from __future__ import annotations

from app.services.buyer_shortlist import _buyer_sort_key


def _item(**over):
    base = {
        "decision": "candidate",
        "match_relevance": "weak",
        "has_verified_contact": False,
        "source_verified": False,
        "final_score": 0.0,
        "has_contact": False,
        "_source_fit_score": 0.0,
        "source_target_country_rank": 999,
    }
    base.update(over)
    return base


def _order(items):
    """reverse=True 정렬과 동일한 순서로 정렬해 반환."""
    return sorted(items, key=_buyer_sort_key, reverse=True)


def test_unrelated_shortlist_does_not_outrank_related_candidate():
    """핵심 fix: 무관(none) shortlist가 강한 매칭(strong) candidate를 추월하면 안 된다."""
    none_shortlist = _item(decision="shortlist", match_relevance="none", final_score=95.0)
    strong_candidate = _item(decision="candidate", match_relevance="strong", final_score=40.0)

    assert _buyer_sort_key(strong_candidate) > _buyer_sort_key(none_shortlist)
    assert _order([none_shortlist, strong_candidate]) == [strong_candidate, none_shortlist]


def test_unrelated_shortlist_does_not_outrank_weak_candidate():
    """무관(none)은 약한 매칭(weak) candidate보다도 위로 올라오지 못한다."""
    none_shortlist = _item(decision="shortlist", match_relevance="none", final_score=99.0)
    weak_candidate = _item(decision="candidate", match_relevance="weak", final_score=10.0)

    assert _buyer_sort_key(weak_candidate) > _buyer_sort_key(none_shortlist)


def test_strong_shortlist_still_ranks_first():
    """과교정 금지: 강한 매칭 shortlist는 여전히 최상위를 유지한다."""
    strong_shortlist = _item(decision="shortlist", match_relevance="strong", final_score=50.0)
    strong_candidate = _item(decision="candidate", match_relevance="strong", final_score=90.0)
    none_shortlist = _item(decision="shortlist", match_relevance="none", final_score=90.0)

    ordered = _order([strong_candidate, none_shortlist, strong_shortlist])
    assert ordered[0] is strong_shortlist


def test_same_relevance_keeps_decision_priority():
    """관련성이 같으면 기존 우선순위(decision > ...)는 그대로 유지(과교정 금지)."""
    strong_shortlist = _item(decision="shortlist", match_relevance="strong", final_score=10.0)
    strong_candidate = _item(decision="candidate", match_relevance="strong", final_score=99.0)

    assert _buyer_sort_key(strong_shortlist) > _buyer_sort_key(strong_candidate)


def test_sort_key_is_deterministic():
    """같은 입력 2회 → 동일 키(결정론)."""
    item = _item(decision="shortlist", match_relevance="weak", final_score=12.34)
    assert _buyer_sort_key(item) == _buyer_sort_key(item)
