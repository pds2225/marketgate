"""merge_p1_p2_buyer_sources — opportunity actionable has_contact 단위 테스트."""

from __future__ import annotations

import pandas as pd

from merge_p1_p2_buyer_sources import _actionable_opportunity, _align_frame, _truthy_contact


def test_actionable_opportunity_requires_country_and_surface() -> None:
    assert _actionable_opportunity(pd.Series({"country_norm": "미국", "title": "스킨케어 수입"}))
    assert _actionable_opportunity(pd.Series({"country_norm": "일본", "normalized_name": "ABC Cosme"}))
    assert not _actionable_opportunity(pd.Series({"country_norm": "", "title": "스킨케어"}))
    assert not _actionable_opportunity(pd.Series({"country_norm": "미국", "title": "", "normalized_name": ""}))


def test_align_opportunity_sets_has_contact_without_email() -> None:
    raw = pd.DataFrame(
        [
            {
                "source_dataset": "대한무역투자진흥공사_buyKOREA인콰이어리",
                "title": "K-beauty serum inquiry",
                "country_norm": "미국",
                "contact_email": "",
                "contact_phone": "",
                "contact_website": "",
                "has_contact": "False",
            }
        ]
    )
    aligned = _align_frame(raw, "opportunity_item")
    assert aligned.loc[0, "has_contact"] == "True"
    assert _truthy_contact(aligned.loc[0])


def test_align_buyer_does_not_invent_contact() -> None:
    raw = pd.DataFrame(
        [
            {
                "source_dataset": "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보",
                "normalized_name": "Some Buyer LLC",
                "country_norm": "미국",
                "contact_email": "",
                "has_contact": "False",
            }
        ]
    )
    aligned = _align_frame(raw, "buyer_candidate")
    assert aligned.loc[0, "has_contact"] == "False"
