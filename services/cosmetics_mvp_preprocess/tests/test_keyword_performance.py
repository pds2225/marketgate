from datetime import date
from pathlib import Path
import re
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import task06_fit_score as scoring
import shortlist_service as shortlist
from task05_shortlist import KEYWORD_MATCH_STOPWORDS, normalize_keywords, normalize_text


def _original_keyword_terms(record, keys):
    """Unmodified 09ae2f7 algorithm as an independent equality oracle."""
    tokens = set()
    for key in keys:
        normalized = normalize_keywords(record.get(key))
        if not normalized:
            normalized = normalize_keywords(normalize_text(record.get(key)).replace(" ", " | "))
        for token in normalized.split(" | "):
            candidates = [token.casefold(), *re.split(r"[\s_\-\/,&\(\)\[\]]+", token.casefold())]
            for candidate in candidates:
                compact = re.sub(r"[^0-9a-z가-힣]+", "", candidate)
                if (len(compact) <= 2 or compact in KEYWORD_MATCH_STOPWORDS
                    or any(blocked and blocked in compact for blocked in scoring.BLOCKED_KEYWORD_COMPACTS)
                    or any(weak and weak in compact for weak in scoring.WEAK_KEYWORD_COMPACTS)):
                    continue
                tokens.add(compact)
    return tokens


@pytest.mark.parametrize("value", [None, "", float("nan"), "Serum/마스크,alpha-beta_[toner] (cream)",
    "Straße | café | İSTANBUL | abc123", "aa | 123 | hello_world", ["serum", "cream"],
    *[f"prefix{x}suffix | {x}" for x in sorted(scoring.BLOCKED_KEYWORD_COMPACTS | scoring.WEAK_KEYWORD_COMPACTS)],
])
def test_compiled_keywords_are_exactly_equivalent(value):
    row = {"keywords_norm": value, "normalized_name": "Alpha Serum_Company", "title": "한국 ABC Buyer"}
    keys = ("keywords_norm", "normalized_name", "title")
    assert scoring._keyword_terms(row, keys) == _original_keyword_terms(row, keys)


def test_supplier_terms_once_per_scoring_batch_and_buyer_cache_content_keys(monkeypatch):
    buyer = {"normalized_name": "Alpha", "country_norm": "미국", "hs_code_norm": "330499", "keywords_norm": "serum"}
    profile = {"target_country_norm": "미국", "target_hs_code_norm": "330499", "target_keywords_norm": "serum"}
    expected = [scoring.fit_score_v0(buyer, profile, reference_date=date(2026, 4, 22)) for _ in range(3)]
    calls = []
    original = scoring._keyword_terms

    def counted(record, keys):
        calls.append(tuple(keys))
        return original(record, keys)

    monkeypatch.setattr(scoring, "_keyword_terms", counted)
    actual = scoring.score_buyers([buyer] * 3, profile, reference_date=date(2026, 4, 22))
    assert [{k: v for k, v in row.items() if k != "buyer"} for row in actual] == expected
    assert calls.count(("keywords_norm", "product_name_norm", "title")) == 1
    scoring._keyword_terms_cached.cache_clear()
    first = original(buyer, ("keywords_norm",))
    assert isinstance(first, frozenset)
    assert original(buyer, ("keywords_norm",)) is first
    buyer["keywords_norm"] = "beta"
    assert original(buyer, ("keywords_norm",)) != first


def test_internal_shortlisting_preserves_frames_and_public_loader_isolation(tmp_path):
    buyers = pd.DataFrame([
        {"normalized_name": "Alpha", "country_norm": "미국", "hs_code_norm": "330499", "keywords_norm": "serum"},
        {"normalized_name": "Beta", "country_norm": "일본", "hs_code_norm": "330499", "keywords_norm": "cream"},
    ])
    buyers.to_csv(tmp_path / "buyer_candidate.csv", index=False)
    pd.DataFrame(columns=["title", "country_norm"]).to_csv(tmp_path / "opportunity_item.csv", index=False)
    shortlist.clear_shortlist_cache()
    shared = shortlist._load_frame_cached(str(tmp_path), "buyer_candidate.csv")
    snapshot = shared.copy(deep=True)
    profile = {"target_country_norm": "미국", "target_hs_code_norm": "330499", "target_keywords_norm": "serum"}
    first = shortlist.shortlist_buyers(output_dir=tmp_path, supplier_profile=profile, reference_date=date(2026, 4, 22))
    public = shortlist.load_buyer_frame(tmp_path)
    public.loc[0, "normalized_name"] = "poison"
    second = shortlist.shortlist_buyers(output_dir=tmp_path, supplier_profile=profile, reference_date=date(2026, 4, 22))
    assert first == second
    assert first["items"][0]["buyer_name"] == "Alpha"
    pd.testing.assert_frame_equal(shared, snapshot)
    shortlist.clear_shortlist_cache()
