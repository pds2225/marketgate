"""Public (no-auth) showcase snapshot built from the real buyer database.

MarketGateDemo (apps/frontend-react/src/MarketGateDemo.jsx) renders a public
showcase of the aggregated buyer DB. This module aggregates the already-loaded
buyer dataset (services/cosmetics_mvp_preprocess/output/buyer_candidate.csv,
~36k rows) into the exact shape the demo consumes, reusing the cached pandas
frame from shortlist_service (no new loader, no new dependency).

Sensitive contact details (email / phone) are only ever returned in a MASKED
form. Plaintext email / phone are never emitted.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

# Reuse the existing cached buyer-frame loader (same module buyer_shortlist uses).
_ROOT = Path(__file__).resolve().parents[4]
_COSMETICS_DIR = _ROOT / "services" / "cosmetics_mvp_preprocess"
if str(_COSMETICS_DIR) not in sys.path:
    sys.path.insert(0, str(_COSMETICS_DIR))

from shortlist_service import load_buyer_frame  # noqa: E402


# source_dataset (raw) -> short display name + official(public-institution) flag.
# Anything not listed falls back to a trimmed raw name and official=False.
_SOURCE_META: dict[str, dict[str, Any]] = {
    "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보": {"name": "KOTRA SNS", "official": True},
    "정보통신산업진흥원_글로벌ICT포털해외바이어": {"name": "NIPA ICT", "official": True},
    "한국무역보험공사_화장품 바이어 정보": {"name": "K-SURE 화장품", "official": True},
    "한국무역보험공사_바이어 검색": {"name": "K-SURE 바이어검색", "official": True},
    "중소벤처기업진흥공단_GoBizKorea인콰이어리": {"name": "GoBizKorea", "official": True},
    "EC21_GlobalB2B_BuyingLeads": {"name": "EC21", "official": False},
    "대한무역투자진흥공사_buyKOREA인콰이어리": {"name": "buyKOREA", "official": True},
    "ITC_TradeMap_ImportingCompanies": {"name": "ITC TradeMap", "official": True},
}

# How many buyer samples the demo grid renders / scores at most.
_DEFAULT_BUYER_LIMIT = 60
_MAX_BUYER_LIMIT = 200


def _is_truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none"} else text


def _to_float(value: Any) -> float | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _trust_level(has_contact: bool, official: bool, estimated: bool) -> str:
    """platinum: official source + verified contact, gold: official source,
    silver: private/estimated."""
    if official and has_contact and not estimated:
        return "platinum"
    if official:
        return "gold"
    return "silver"


def _mask_email(value: Any) -> str:
    email = _clean(value)
    if not email or "@" not in email:
        return ""
    local, _, domain = email.partition("@")
    masked_local = (local[0] + "***") if local else "***"
    if "." in domain:
        host, _, tld = domain.rpartition(".")
        masked_domain = ((host[0] if host else "*") + "***." + tld)
    else:
        masked_domain = "***"
    return f"{masked_local}@{masked_domain}"


def _mask_phone(value: Any) -> str:
    phone = _clean(value)
    digits = [c for c in phone if c.isdigit()]
    if not digits:
        return ""
    tail = "".join(digits[-4:])
    return f"***-****-{tail}"


def _industry_from_keywords(keywords: str, hs_norm: str) -> str:
    text = (keywords or "").lower()
    if "skincare" in text or "스킨" in keywords or "serum" in text or "cream" in text:
        return "스킨케어"
    if "makeup" in text or "메이크업" in keywords or "color" in text:
        return "메이크업"
    if "화장품" in keywords or "cosmetic" in text or "beauty" in text:
        return "화장품"
    if hs_norm.startswith("3304") or hs_norm.startswith("46443"):
        return "화장품 도소매"
    return "뷰티/화장품"


def _hs_display(hs_norm: str) -> str:
    """Trim the trailing '.0' that the CSV carries (e.g. '46443.0')."""
    text = _clean(hs_norm)
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _build_iso3_map(df) -> dict[str, str]:
    """country_norm -> iso3, filling rows that have a blank iso3."""
    mapping: dict[str, str] = {}
    for country, iso3 in zip(df["country_norm"].astype(str), df["country_iso3"].astype(str)):
        country = country.strip()
        iso3 = iso3.strip()
        if country and iso3 and country not in mapping:
            mapping[country] = iso3
    return mapping


def _aggregate(df) -> dict[str, Any]:
    total = int(len(df))
    iso3_map = _build_iso3_map(df)

    # ── byCountry: count + iso3, sorted desc ──
    country_counts = df["country_norm"].astype(str).str.strip()
    country_counts = country_counts[country_counts != ""]
    by_country = [
        {"name": name, "iso3": iso3_map.get(name, ""), "count": int(count)}
        for name, count in country_counts.value_counts().items()
    ]
    country_count = len(by_country)

    # ── bySource: count + official flag, sorted desc ──
    source_counts = df["source_dataset"].astype(str).str.strip()
    by_source = []
    for raw_name, count in source_counts.value_counts().items():
        meta = _SOURCE_META.get(raw_name, {})
        display = meta.get("name") or (raw_name.split("_")[-1] if raw_name else "기타")
        by_source.append(
            {"name": display, "count": int(count), "official": bool(meta.get("official", False))}
        )

    return {
        "total": total,
        "countryCount": country_count,
        "byCountry": by_country,
        "bySource": by_source,
    }


def _build_buyers(df, limit: int) -> list[dict[str, Any]]:
    iso3_map = _build_iso3_map(df)
    rank = {row["name"]: idx for idx, row in enumerate(_aggregate(df)["byCountry"])}

    # Prefer rows that carry a verified contact so the showcase has rich samples,
    # then fall back to the rest — keeps the grid representative, never empty.
    df = df.copy()
    df["_has_contact"] = df["has_contact"].map(_is_truthy)
    df = df.sort_values(by="_has_contact", ascending=False, kind="stable")

    buyers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pos, (_, row) in enumerate(df.iterrows()):
        if len(buyers) >= limit:
            break
        name = _clean(row.get("normalized_name")) or _clean(row.get("title"))
        country = _clean(row.get("country_norm"))
        if not name or not country:
            continue
        dedupe_key = f"{name.lower()}|{country}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        raw_source = _clean(row.get("source_dataset"))
        source_meta = _SOURCE_META.get(raw_source, {})
        official = bool(source_meta.get("official", False))
        has_contact = _is_truthy(row.get("has_contact"))
        estimated = _is_truthy(row.get("contact_email_estimated"))
        hs_norm = _hs_display(row.get("hs_code_norm"))
        keywords = _clean(row.get("keywords_norm"))

        buyers.append(
            {
                "id": f"b{pos}",
                "name": name[:80],
                "country": country,
                "iso3": _clean(row.get("country_iso3")) or iso3_map.get(country, ""),
                "industry": _industry_from_keywords(keywords, hs_norm),
                "hs": hs_norm,
                "source": source_meta.get("name") or (raw_source.split("_")[-1] if raw_source else "기타"),
                "trust": _trust_level(has_contact, official, estimated),
                "distanceKm": _to_float(row.get("distance_from_kr_km")),
                "hasContact": has_contact,
                "emailEstimated": estimated,
                "emailMasked": _mask_email(row.get("contact_email")),
                "phoneMasked": _mask_phone(row.get("contact_phone")),
                "website": _clean(row.get("contact_website")),
                "countryRank": rank.get(country),
            }
        )
    return buyers


@lru_cache(maxsize=1)
def _summary_cached() -> dict[str, Any]:
    return _aggregate(load_buyer_frame())


@lru_cache(maxsize=4)
def _buyers_cached(limit: int) -> tuple[dict[str, Any], ...]:
    return tuple(_build_buyers(load_buyer_frame(), limit))


def get_demo_summary() -> dict[str, Any]:
    return _summary_cached()


def get_demo_buyers(limit: int = _DEFAULT_BUYER_LIMIT) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit or _DEFAULT_BUYER_LIMIT), _MAX_BUYER_LIMIT))
    return [dict(item) for item in _buyers_cached(limit)]


def get_demo_snapshot(limit: int = _DEFAULT_BUYER_LIMIT) -> dict[str, Any]:
    return {"summary": get_demo_summary(), "buyers": get_demo_buyers(limit)}
