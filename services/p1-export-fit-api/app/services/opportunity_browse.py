"""보유 opportunity_item.csv 탐색 — 합성/스크래핑 없이 원본 필드만 반환."""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
COSMETICS_DIR = ROOT / "services" / "cosmetics_mvp_preprocess"
if str(COSMETICS_DIR) not in sys.path:
    sys.path.insert(0, str(COSMETICS_DIR))

from shortlist_service import load_opportunity_frame  # noqa: E402
from task05_shortlist import normalize_opportunity_record, normalize_text  # noqa: E402


@lru_cache(maxsize=1)
def _rows_cached() -> tuple[dict[str, Any], ...]:
    frame = load_opportunity_frame()
    rows: list[dict[str, Any]] = []
    for raw in frame.to_dict(orient="records"):
        rec = normalize_opportunity_record(raw)
        title = normalize_text(rec.get("title"))
        if not title:
            continue
        has_contact = bool(
            normalize_text(rec.get("contact_email"))
            or normalize_text(rec.get("contact_phone"))
            or normalize_text(rec.get("contact_website"))
            or normalize_text(rec.get("contact_name"))
        )
        rows.append(
            {
                "title": title,
                "product_name": normalize_text(rec.get("product_name_norm")),
                "country_norm": normalize_text(rec.get("country_norm")),
                "country_iso3": normalize_text(rec.get("country_iso3")),
                "signal_type": normalize_text(rec.get("signal_type")),
                "hs_code_norm": normalize_text(rec.get("hs_code_norm")),
                "keywords_norm": normalize_text(rec.get("keywords_norm")),
                "valid_until": normalize_text(rec.get("valid_until")),
                "source_dataset": normalize_text(rec.get("source_dataset")),
                "source_snapshot_date": normalize_text(rec.get("source_snapshot_date")),
                "signal_usable": bool(rec.get("signal_usable", False)),
                "has_contact": has_contact,
                "contact_name": normalize_text(rec.get("contact_name")),
                "contact_email": normalize_text(rec.get("contact_email")),
                "contact_phone": normalize_text(rec.get("contact_phone")),
                "contact_website": normalize_text(rec.get("contact_website")),
            }
        )
    return tuple(rows)


def clear_opportunity_browse_cache() -> None:
    _rows_cached.cache_clear()


def list_opportunities(
    *,
    q: str = "",
    country: str = "",
    hs: str = "",
    signal_type: str = "",
    source: str = "",
    usable_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    q_n = normalize_text(q).casefold()
    country_n = normalize_text(country)
    hs_n = normalize_text(hs)
    type_n = normalize_text(signal_type).casefold()
    source_n = normalize_text(source).casefold()

    filtered: list[dict[str, Any]] = []
    countries: set[str] = set()
    sources: set[str] = set()
    types: set[str] = set()

    for row in _rows_cached():
        if row["country_norm"]:
            countries.add(row["country_norm"])
        if row["source_dataset"]:
            sources.add(row["source_dataset"])
        if row["signal_type"]:
            types.add(row["signal_type"])

        if usable_only and not row["signal_usable"]:
            continue
        if country_n and row["country_norm"] != country_n:
            continue
        if hs_n:
            row_hs = row["hs_code_norm"] or ""
            if not row_hs or hs_n not in row_hs:
                continue
        if type_n and type_n not in (row["signal_type"] or "").casefold():
            continue
        if source_n and source_n not in (row["source_dataset"] or "").casefold():
            continue
        if q_n:
            blob = " ".join(
                [
                    row["title"],
                    row["product_name"],
                    row["keywords_norm"],
                    row["country_norm"],
                    row["hs_code_norm"],
                ]
            ).casefold()
            if q_n not in blob:
                continue
        filtered.append(row)

    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    page = filtered[offset : offset + limit]
    return {
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
        "items": page,
        "facets": {
            "countries": sorted(countries),
            "sources": sorted(sources),
            "signal_types": sorted(types),
        },
    }
