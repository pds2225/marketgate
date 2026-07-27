"""backfill_buyer_emails 단위 테스트 (네트워크 없음)."""

from __future__ import annotations

import pandas as pd

from backfill_buyer_emails import _email_map_from_frame, _norm_key, backfill


def test_norm_key_strips_noise() -> None:
    assert _norm_key("ABC Cosmetics, Ltd.", "미국") == _norm_key("abc cosmetics ltd", "미국")


def test_backfill_fills_empty_email_only() -> None:
    buyer = pd.DataFrame(
        [
            {
                "normalized_name": "Alpha Beauty",
                "country_norm": "미국",
                "contact_email": "",
                "has_contact": "False",
            },
            {
                "normalized_name": "Beta Co",
                "country_norm": "일본",
                "contact_email": "keep@beta.jp",
                "has_contact": "True",
            },
        ]
    )
    snap = pd.DataFrame(
        [
            {
                "normalized_name": "Alpha Beauty",
                "country_norm": "미국",
                "contact_email": "sales@alpha.com",
                "contact_phone": "1-555",
            },
            {
                "normalized_name": "Beta Co",
                "country_norm": "일본",
                "contact_email": "other@beta.jp",
            },
        ]
    )
    mp = _email_map_from_frame(snap)
    out, stats = backfill(buyer, [("git_snapshot", mp)])
    assert out.loc[0, "contact_email"] == "sales@alpha.com"
    assert out.loc[0, "has_contact"] == "True"
    assert out.loc[1, "contact_email"] == "keep@beta.jp"
    assert stats["filled"] == 1
    assert stats["with_email_after"] == 2
