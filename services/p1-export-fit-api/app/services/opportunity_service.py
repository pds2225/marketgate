"""Opportunity (구매 신호) browse service from opportunity_item.csv.

Enables the product to use inquiry/offer demand signals already merged
(buyKOREA / GoBizKorea) — not contactable buyers, but usable market signals.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_COSMETICS_DIR = _ROOT / "services" / "cosmetics_mvp_preprocess"
if str(_COSMETICS_DIR) not in sys.path:
    sys.path.insert(0, str(_COSMETICS_DIR))

from shortlist_service import load_opportunity_frame  # noqa: E402


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "nan", "none", "null"} else text


@lru_cache(maxsize=1)
def _frame_cached():
    return load_opportunity_frame()


def invalidate_cache() -> None:
    _frame_cached.cache_clear()


def get_opportunity_summary() -> dict[str, Any]:
    df = _frame_cached()
    if df is None or len(df) == 0:
        return {"total": 0, "by_source": [], "by_country": []}
    source = df["source_dataset"].fillna("(null)").astype(str).str.strip()
    country = df["country_norm"].fillna("").astype(str).str.strip()
    country = country[country != ""]
    return {
        "total": int(len(df)),
        "by_source": [
            {"name": str(name), "count": int(count)}
            for name, count in source.value_counts().items()
        ],
        "by_country": [
            {"name": str(name), "count": int(count)}
            for name, count in country.value_counts().head(40).items()
        ],
    }


def list_opportunities(
    *,
    country: str = "",
    q: str = "",
    source: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    df = _frame_cached()
    if df is None or len(df) == 0:
        return {"total": 0, "items": [], "limit": limit, "offset": offset}

    work = df.copy()
    country_f = _clean(country)
    q_f = _clean(q).casefold()
    source_f = _clean(source).casefold()

    if country_f:
        work = work[
            work["country_norm"].fillna("").astype(str).str.contains(country_f, case=False, na=False)
            | work["country_raw"].fillna("").astype(str).str.contains(country_f, case=False, na=False)
        ]
    if source_f:
        work = work[
            work["source_dataset"].fillna("").astype(str).str.casefold().str.contains(source_f, na=False)
        ]
    if q_f:
        title = work["title"].fillna("").astype(str).str.casefold()
        kw = work["keywords_norm"].fillna("").astype(str).str.casefold() if "keywords_norm" in work.columns else title
        name = work["normalized_name"].fillna("").astype(str).str.casefold()
        work = work[title.str.contains(q_f, na=False) | kw.str.contains(q_f, na=False) | name.str.contains(q_f, na=False)]

    total = int(len(work))
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    page = work.iloc[offset : offset + limit]

    items: list[dict[str, Any]] = []
    for idx, row in page.iterrows():
        email = _clean(row.get("contact_email"))
        phone = _clean(row.get("contact_phone"))
        website = _clean(row.get("contact_website"))
        items.append(
            {
                "id": f"opp-{offset + len(items) + 1}",
                "title": _clean(row.get("title")) or "(제목 없음)",
                "normalized_name": _clean(row.get("normalized_name")),
                "country_norm": _clean(row.get("country_norm")),
                "country_raw": _clean(row.get("country_raw")),
                "hs_code_norm": _clean(row.get("hs_code_norm")),
                "keywords_norm": _clean(row.get("keywords_norm")),
                "source_dataset": _clean(row.get("source_dataset")),
                "source_file": _clean(row.get("source_file")),
                "valid_until": _clean(row.get("valid_until")),
                "has_contact": bool(email or phone or website),
                "contact_email": email,
                "contact_phone": phone,
                "contact_website": website,
                "record_type": "opportunity_item",
                "signal_note": "구매·문의 수요 신호 (회사 연락처 없을 수 있음)",
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
