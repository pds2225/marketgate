from __future__ import annotations

import argparse
import csv
import io
import re
import unicodedata
from enum import Enum
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


ALLOWED_SIGNAL_TYPES = {"inquiry", "offer", "consultation"}
DATE_WINDOW_DAYS = 183


class GateReason(str, Enum):
    COUNTRY_MISMATCH = "country_mismatch"
    HS_MISMATCH = "hs_mismatch"
    BANNED_COUNTRY = "banned_country"
    CAPACITY_FAIL = "capacity_fail"
    SIGNAL_TYPE_INVALID = "signal_type_invalid"
    EXPIRED = "expired"
    AMBIGUOUS_PRODUCT = "ambiguous_product"


GATE_REASON_ORDER_BUYER = (
    GateReason.COUNTRY_MISMATCH,
    GateReason.BANNED_COUNTRY,
    GateReason.HS_MISMATCH,
    GateReason.CAPACITY_FAIL,
)
GATE_REASON_ORDER_OPPORTUNITY = (
    GateReason.SIGNAL_TYPE_INVALID,
    GateReason.EXPIRED,
    GateReason.AMBIGUOUS_PRODUCT,
)

DEFAULT_BANNED_COUNTRY_KEYS = {
    "KOR",
    "KR",
    "KOREA",
    "REPUBLICOFKOREA",
    "SOUTHKOREA",
    "대한민국",
    "한국",
}

GENERIC_TITLE_TOKENS = {
    "test",
    "sample",
    "general",
    "product",
    "products",
    "offer",
    "inquiry",
    "inquire",
    "inquiry",
    "item",
    "goods",
    "signal",
    "request",
    "demo",
    "dummy",
    "example",
    "consultation",
    "consult",
    "테스트",
    "샘플",
    "일반",
    "상품",
    "제품",
    "오퍼",
    "인콰이어리",
    "문의",
    "상담",
    "요청",
}

KEYWORD_MATCH_STOPWORDS = {
    "skin",
    "care",
    "beauty",
    "skincare",
    "beautycare",
    "general",
    "product",
    "products",
    "item",
    "items",
    "goods",
    "offer",
    "inquiry",
    "inquiries",
    "inquire",
    "consultation",
    "consult",
    "request",
    "signal",
    "sample",
    "test",
    "tests",
    "demo",
    "dummy",
    "example",
    "피부",
    "케어",
    "뷰티",
    "일반",
    "상품",
    "제품",
    "오퍼",
    "문의",
    "상담",
    "요청",
    "샘플",
    "테스트",
    "데모",
    "예시",
    "더미",
}

ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
KEYWORD_SPLIT_RE = re.compile(r"[,\|;/\n\r\t·•]+")
NON_ALNUM_RE = re.compile(r"[^0-9A-Za-z가-힣]+")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\u3000", " ")
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def normalize_country(value: Any) -> str:
    text = normalize_text(value).upper()
    text = re.sub(r"[\s\-\_\/\\\.\,\:\;\(\)\[\]\{\}·•'`\"]+", "", text)
    return text


def normalize_hs_code(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    return digits[:6] if digits else ""


def _split_keywords(value: Any) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    parts: list[str] = []
    for piece in KEYWORD_SPLIT_RE.split(text):
        piece = normalize_text(piece)
        if piece:
            parts.append(piece)
    return parts


def normalize_keywords(value: Any) -> str:
    seen: set[str] = set()
    normalized: list[str] = []
    for token in _split_keywords(value):
        norm = WHITESPACE_RE.sub(" ", token).casefold()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        normalized.append(norm)
    return " | ".join(normalized)


def _keyword_variants(value: Any) -> set[str]:
    variants: set[str] = set()
    for token in _split_keywords(value):
        lowered = WHITESPACE_RE.sub(" ", token).casefold()
        if not lowered:
            continue
        variants.add(lowered)
        variants.add(WHITESPACE_RE.sub("", lowered))
        variants.add(re.sub(r"[^0-9a-z가-힣]+", "", lowered))
    return {variant for variant in variants if variant}


def _first_non_empty(record: Mapping[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = normalize_text(record.get(key))
        if value:
            return value
    return ""


def _normalize_date_candidate(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    text = text.replace("년", "-").replace("월", "-").replace("일", "")
    text = text.replace(".", "-").replace("/", "-")
    text = WHITESPACE_RE.sub("", text)
    return text


def parse_date(value: Any) -> date | None:
    text = _normalize_date_candidate(value)
    if not text:
        return None

    for fmt in (
        "%Y%m%d",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%m.%d.%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def normalize_signal_type(value: Any) -> str:
    text = normalize_text(value).casefold()
    if not text:
        return ""

    compact = re.sub(r"[\s\-\_\/\\\.\,\:\;\(\)\[\]\{\}·•'`\"]+", "", text)

    if "구매오퍼" in compact or "offer" in compact:
        return "offer"
    if "consultation" in compact or "상담" in compact or "신청" in compact:
        return "consultation"
    if "inquiry" in compact or "인콰이어리" in compact or "문의" in compact:
        return "inquiry"
    if text in ALLOWED_SIGNAL_TYPES:
        return text
    return compact


def derive_signal_type(record: Mapping[str, Any]) -> str:
    candidates = [
        record.get("signal_type"),
        record.get("signal_type_norm"),
        record.get("signal_category"),
        record.get("signal"),
        record.get("source_dataset"),
        record.get("source_file"),
    ]
    for candidate in candidates:
        signal_type = normalize_signal_type(candidate)
        if signal_type in ALLOWED_SIGNAL_TYPES:
            return signal_type
    return normalize_signal_type(candidates[0]) if candidates else ""


def is_ambiguous_product(value: Any) -> bool:
    text = normalize_text(value)
    if not text:
        return True

    compact = NON_ALNUM_RE.sub("", text)
    if len(compact) <= 3:
        return True
    if compact.isdigit():
        return True

    tokens = [token for token in re.split(r"[\s,\|;/·•_-]+", text) if token]
    meaningful = []
    for token in tokens:
        normalized = NON_ALNUM_RE.sub("", token).casefold()
        if normalized and normalized not in GENERIC_TITLE_TOKENS:
            meaningful.append(normalized)

    return not meaningful


is_title_unclear = is_ambiguous_product
is_product_unclear = is_ambiguous_product


def is_title_or_product_unclear(title: Any, product_name: Any = "") -> bool:
    title_text = normalize_text(title)
    product_text = normalize_text(product_name)
    if title_text and not is_ambiguous_product(title_text):
        return False
    if product_text and not is_ambiguous_product(product_text):
        return False
    return True


def _pick_signal_date(valid_until: Any, created_at: Any) -> tuple[str, date | None]:
    valid_date = parse_date(valid_until)
    if valid_date is not None:
        return "valid_until", valid_date
    created_date = parse_date(created_at)
    if created_date is not None:
        return "created_at", created_date
    return "", None


def is_signal_usable(
    signal_type: Any,
    valid_until: Any,
    created_at: Any,
    title: Any = "",
    product_name: Any = "",
    reference_date: date | None = None,
) -> bool:
    ref = reference_date or date.today()
    normalized_signal_type = normalize_signal_type(signal_type)
    if normalized_signal_type not in ALLOWED_SIGNAL_TYPES:
        return False

    if is_title_or_product_unclear(title, product_name):
        return False

    if is_expired(valid_until, created_at, reference_date=reference_date):
        return False

    date_source, signal_date = _pick_signal_date(valid_until, created_at)
    if signal_date is None:
        return False

    if date_source == "valid_until":
        delta_days = (signal_date - ref).days
    else:
        delta_days = (ref - signal_date).days
    return 0 <= delta_days <= DATE_WINDOW_DAYS


def is_expired(
    valid_until: Any,
    created_at: Any,
    reference_date: date | None = None,
) -> bool:
    ref = reference_date or date.today()
    date_source, signal_date = _pick_signal_date(valid_until, created_at)
    if signal_date is None:
        return True

    if date_source == "valid_until":
        return ref > signal_date

    return (ref - signal_date).days > DATE_WINDOW_DAYS


def _extract_match_terms(record: Mapping[str, Any], keys: Iterable[str]) -> set[str]:
    variants: set[str] = set()
    for key in keys:
        variants.update(_keyword_match_variants(record.get(key)))
    return variants


def _is_broad_keyword_token(token: str) -> bool:
    compact = normalize_text(token).casefold()
    compact = re.sub(r"[^0-9a-z가-힣]+", "", compact)
    return compact in KEYWORD_MATCH_STOPWORDS


def _keyword_match_variants(value: Any) -> set[str]:
    variants: set[str] = set()
    for token in _split_keywords(value):
        lowered = WHITESPACE_RE.sub(" ", token).casefold()
        if not lowered:
            continue
        compact = re.sub(r"[^0-9a-z가-힣]+", "", lowered)
        if not compact or _is_broad_keyword_token(compact):
            continue
        variants.add(compact)
    return variants


def match_hs_or_keywords(
    buyer: Mapping[str, Any],
    opportunity: Mapping[str, Any],
) -> dict[str, Any]:
    buyer_hs = normalize_hs_code(
        _first_non_empty(buyer, ("hs_code_norm", "hs_code", "hs_code_raw"))
    )
    opportunity_hs = normalize_hs_code(
        _first_non_empty(opportunity, ("hs_code_norm", "hs_code", "hs_code_raw"))
    )

    if buyer_hs and opportunity_hs:
        if buyer_hs == opportunity_hs:
            return {
                "matched": True,
                "match_mode": "hs_exact",
                "reason": "hs_exact",
                "buyer_hs_code_norm": buyer_hs,
                "opportunity_hs_code_norm": opportunity_hs,
                "matched_terms": [],
            }

        if buyer_hs[:4] == opportunity_hs[:4] and len(buyer_hs) >= 4 and len(opportunity_hs) >= 4:
            return {
                "matched": True,
                "match_mode": "hs_prefix_4",
                "reason": "hs_prefix_4",
                "buyer_hs_code_norm": buyer_hs,
                "opportunity_hs_code_norm": opportunity_hs,
                "matched_terms": [],
            }

        if buyer_hs[:2] == opportunity_hs[:2] and len(buyer_hs) >= 2 and len(opportunity_hs) >= 2:
            return {
                "matched": True,
                "match_mode": "hs_prefix_2",
                "reason": "hs_prefix_2",
                "buyer_hs_code_norm": buyer_hs,
                "opportunity_hs_code_norm": opportunity_hs,
                "matched_terms": [],
            }

        return {
            "matched": False,
            "match_mode": "hs",
            "reason": "hs_mismatch",
            "buyer_hs_code_norm": buyer_hs,
            "opportunity_hs_code_norm": opportunity_hs,
            "matched_terms": [],
        }

    buyer_terms = _extract_match_terms(buyer, ("keywords_norm", "normalized_name", "title"))
    opportunity_terms = _extract_match_terms(
        opportunity,
        ("product_name_norm", "keywords_norm", "title"),
    )
    intersection = sorted(buyer_terms & opportunity_terms)
    if intersection:
        return {
            "matched": True,
            "match_mode": "keyword",
            "reason": "keyword_match",
            "buyer_hs_code_norm": buyer_hs,
            "opportunity_hs_code_norm": opportunity_hs,
            "matched_terms": intersection,
        }

    return {
        "matched": False,
        "match_mode": "keyword",
        "reason": "keyword_mismatch",
        "buyer_hs_code_norm": buyer_hs,
        "opportunity_hs_code_norm": opportunity_hs,
        "matched_terms": [],
    }


def _capacity_value(record: Mapping[str, Any]) -> float | None:
    for key in ("capacity", "monthly_capacity", "annual_capacity", "production_capacity", "supply_capacity", "max_capacity"):
        value = normalize_text(record.get(key))
        if not value:
            continue
        cleaned = re.sub(r"[^0-9.]+", "", value)
        if not cleaned:
            continue
        try:
            return float(cleaned)
        except ValueError:
            continue
    return None


def _country_is_banned(country_value: Any, banned_countries: Iterable[str]) -> bool:
    country_key = normalize_country(country_value)
    banned_keys = {normalize_country(value) for value in banned_countries}
    return bool(country_key and country_key in banned_keys)


def _format_gate_reasons(reasons: Iterable[GateReason], order: Iterable[GateReason]) -> list[str]:
    reason_set = {reason.value for reason in reasons}
    ordered: list[str] = []
    for reason in order:
        if reason.value in reason_set and reason.value not in ordered:
            ordered.append(reason.value)
    for reason in sorted(reason_set - set(ordered)):
        if reason not in ordered:
            ordered.append(reason)
    return ordered


def _merge_target_fields(
    opportunity: Mapping[str, Any] | None,
    target_country_norm: str | None,
    target_hs_code_norm: str | None,
    target_keywords_norm: str | None,
    target_product_name_norm: str | None,
    target_title: str | None,
) -> dict[str, str]:
    merged = {
        "country_norm": normalize_text(target_country_norm),
        "hs_code_norm": normalize_hs_code(target_hs_code_norm),
        "keywords_norm": normalize_keywords(target_keywords_norm),
        "product_name_norm": normalize_text(target_product_name_norm),
        "title": normalize_text(target_title),
    }

    if opportunity is not None:
        if not merged["country_norm"]:
            merged["country_norm"] = normalize_text(
                _first_non_empty(opportunity, ("country_norm", "country", "country_raw"))
            )
        if not merged["hs_code_norm"]:
            merged["hs_code_norm"] = normalize_hs_code(
                _first_non_empty(opportunity, ("hs_code_norm", "hs_code", "hs_code_raw"))
            )
        if not merged["keywords_norm"]:
            merged["keywords_norm"] = normalize_keywords(opportunity.get("keywords_norm"))
        if not merged["product_name_norm"]:
            merged["product_name_norm"] = normalize_text(
                _first_non_empty(opportunity, ("product_name_norm", "normalized_name"))
            )
        if not merged["title"]:
            merged["title"] = normalize_text(_first_non_empty(opportunity, ("title",)))

    return merged


def buyer_hard_gate(
    buyer: Mapping[str, Any],
    opportunity: Mapping[str, Any] | None = None,
    *,
    target_country_norm: str | None = None,
    target_hs_code_norm: str | None = None,
    target_keywords_norm: str | None = None,
    target_product_name_norm: str | None = None,
    target_title: str | None = None,
    banned_countries: Iterable[str] | None = None,
    required_capacity: float | int | None = None,
) -> dict[str, Any]:
    merged_target = _merge_target_fields(
        opportunity=opportunity,
        target_country_norm=target_country_norm,
        target_hs_code_norm=target_hs_code_norm,
        target_keywords_norm=target_keywords_norm,
        target_product_name_norm=target_product_name_norm,
        target_title=target_title,
    )

    reasons: list[GateReason] = []

    buyer_country = normalize_country(
        _first_non_empty(buyer, ("country_norm", "country", "country_raw"))
    )
    if merged_target["country_norm"] and (
        not buyer_country or buyer_country != normalize_country(merged_target["country_norm"])
    ):
        reasons.append(GateReason.COUNTRY_MISMATCH)

    if banned_countries is None:
        banned_countries = DEFAULT_BANNED_COUNTRY_KEYS
    if _country_is_banned(buyer_country, banned_countries):
        reasons.append(GateReason.BANNED_COUNTRY)

    match_result = {"matched": True, "reason": "match_not_checked"}
    if merged_target["hs_code_norm"] or merged_target["keywords_norm"] or merged_target["product_name_norm"] or merged_target["title"]:
        target_record = {
            "hs_code_norm": merged_target["hs_code_norm"],
            "keywords_norm": merged_target["keywords_norm"],
            "product_name_norm": merged_target["product_name_norm"],
            "title": merged_target["title"],
        }
        match_result = match_hs_or_keywords(buyer, target_record)
        if not match_result["matched"]:
            reasons.append(GateReason.HS_MISMATCH)

    if required_capacity is not None:
        capacity = _capacity_value(buyer)
        required_capacity_value = float(required_capacity)
        if capacity is None or capacity < required_capacity_value:
            reasons.append(GateReason.CAPACITY_FAIL)

    reasons = list(dict.fromkeys(reasons))
    return {
        "passed": not reasons,
        "gate_reason": _format_gate_reasons(reasons, GATE_REASON_ORDER_BUYER),
        "matched_by": match_result.get("match_mode", ""),
        "matched_terms": match_result.get("matched_terms", []),
    }


def opportunity_hard_gate(
    opportunity: Mapping[str, Any],
    reference_date: date | None = None,
) -> dict[str, Any]:
    reasons: list[GateReason] = []
    signal_type = derive_signal_type(opportunity)
    valid_until = opportunity.get("valid_until")
    created_at = opportunity.get("created_at")
    title = _first_non_empty(opportunity, ("title",))
    product_name = _first_non_empty(opportunity, ("product_name_norm", "keywords_norm"))

    if signal_type not in ALLOWED_SIGNAL_TYPES:
        reasons.append(GateReason.SIGNAL_TYPE_INVALID)

    if is_expired(valid_until, created_at, reference_date=reference_date):
        reasons.append(GateReason.EXPIRED)

    if is_title_or_product_unclear(title, product_name):
        reasons.append(GateReason.AMBIGUOUS_PRODUCT)

    reasons = list(dict.fromkeys(reasons))
    return {
        "passed": not reasons,
        "gate_reason": _format_gate_reasons(reasons, GATE_REASON_ORDER_OPPORTUNITY),
        "signal_type": signal_type,
        "signal_usable": is_signal_usable(
            signal_type,
            valid_until,
            created_at,
            title=title,
            product_name=product_name,
            reference_date=reference_date,
        ),
        "expired": is_expired(valid_until, created_at, reference_date=reference_date),
    }


def normalize_opportunity_record(
    opportunity: Mapping[str, Any],
    reference_date: date | None = None,
) -> dict[str, Any]:
    record = dict(opportunity)
    signal_type = derive_signal_type(record)
    title_text = normalize_text(record.get("title"))
    product_name_text = normalize_text(record.get("product_name_norm"))
    keywords_text = normalize_text(record.get("keywords_norm"))
    if not product_name_text:
        if title_text and not is_ambiguous_product(title_text):
            product_name_text = title_text
        elif keywords_text and not is_ambiguous_product(keywords_text):
            product_name_text = keywords_text
        else:
            product_name_text = title_text or keywords_text
    signal_usable = is_signal_usable(
        signal_type,
        record.get("valid_until"),
        record.get("created_at"),
        title=title_text,
        product_name=product_name_text,
        reference_date=reference_date,
    )
    record.pop("has_contact", None)
    record["signal_type"] = signal_type
    record["signal_usable"] = signal_usable
    record["product_name_norm"] = product_name_text
    return record


def normalize_opportunity_records(
    opportunities: Iterable[Mapping[str, Any]],
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    return [normalize_opportunity_record(record, reference_date=reference_date) for record in opportunities]


normalize_opportunity_item = normalize_opportunity_record
rename_opportunity_has_contact_to_signal_usable = normalize_opportunity_record
evaluate_buyer_hard_gate = buyer_hard_gate
evaluate_opportunity_hard_gate = opportunity_hard_gate


def read_csv_records(path: Path) -> list[dict[str, str]]:
    last_error: Exception | None = None
    raw = path.read_bytes()
    for encoding in ENCODINGS:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        reader = csv.DictReader(io.StringIO(text))
        return [
            {key: value for key, value in row.items()}
            for row in reader
        ]
    raise RuntimeError(f"CSV 파일을 읽지 못했습니다: {path} / 마지막 오류: {last_error}")


def write_csv_records(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def transform_opportunity_csv(
    input_path: Path,
    output_path: Path | None = None,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    records = read_csv_records(input_path)
    normalized = normalize_opportunity_records(records, reference_date=reference_date)
    if output_path is not None:
        write_csv_records(output_path, normalized)
    return normalized


def _demo() -> None:
    ref_date = date(2026, 4, 22)
    buyer = {
        "country_norm": "베트남",
        "hs_code_norm": "330499",
        "keywords_norm": "skincare | beauty",
        "capacity": "50",
    }
    opportunity = {
        "source_dataset": "대한무역투자진흥공사_인콰이어리 정보",
        "title": "Skincare inquiry",
        "keywords_norm": "skincare | beauty",
        "valid_until": "2026-06-30",
        "created_at": "",
        "has_contact": True,
    }

    print("[demo] normalized_opportunity =", normalize_opportunity_record(opportunity, reference_date=ref_date))
    print(
        "[demo] buyer_gate =",
        buyer_hard_gate(
            buyer,
            opportunity,
            target_country_norm="미국",
            target_hs_code_norm="300490",
            banned_countries={"베트남"},
            required_capacity=100,
        ),
    )
    print("[demo] opportunity_gate =", opportunity_hard_gate(opportunity, reference_date=ref_date))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TASK-05 shortlist용 Hard Gate 규칙")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="샘플 레코드로 데모 로그를 출력한다.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.demo or not any(vars(args).values()):
        _demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
