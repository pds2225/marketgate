from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shortlist_service import clear_shortlist_cache, shortlist_buyers, validate_shortlist_quality  # noqa: E402
from task05_shortlist import parse_date  # noqa: E402


DEFAULT_REFERENCE_DATE = "2025-06-01"
DEFAULT_SCENARIO = {
    "supplier_name": "MarketGate Cosmetics Supplier",
    "target_country_norm": "미국",
    "target_hs_code_norm": "3304",
    "target_keywords_norm": "cosmetics | serum | cream | mask | ampoule | makeup | lotion",
    "target_product_name_norm": "cosmetics",
    "banned_countries": "한국, 대한민국, KOREA",
}
DEFAULT_OPPORTUNITY_TITLE_CONTAINS = "ampoule"
DEFAULT_LIMIT = 20


def _reference_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError(f"reference_date 형식이 잘못되었습니다: {value}")
    return parsed


def validate_top20(
    *,
    output_dir: Path | None = None,
    reference_date: str | date = DEFAULT_REFERENCE_DATE,
    limit: int = DEFAULT_LIMIT,
    opportunity_title_contains: str = DEFAULT_OPPORTUNITY_TITLE_CONTAINS,
    supplier_profile_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    clear_shortlist_cache()
    ref = _reference_date(reference_date)
    scenario = dict(DEFAULT_SCENARIO)
    if supplier_profile_overrides:
        scenario.update(dict(supplier_profile_overrides))

    shortlist = shortlist_buyers(
        output_dir=output_dir or (ROOT / "output"),
        supplier_profile=scenario,
        reference_date=ref,
        limit=limit,
        opportunity_title_contains=opportunity_title_contains,
        opportunity_country_norm=str(scenario.get("target_country_norm", "")),
        include_rejected=False,
    )
    quality = validate_shortlist_quality(shortlist)
    top20 = shortlist.get("items", [])[:20]
    shortlist_rate = (
        round(shortlist["meta"]["shortlist_count"] / shortlist["meta"]["scored_rows"], 3)
        if shortlist["meta"]["scored_rows"]
        else 0.0
    )
    result = {
        "reference_date": ref.isoformat(),
        "scenario": scenario,
        "meta": shortlist["meta"],
        "quality": quality,
        "shortlist_rate": shortlist_rate,
        "top20": top20,
    }
    return result


def _print_result(result: Mapping[str, Any]) -> None:
    quality = result["quality"]
    print("[task09] reference_date =", result["reference_date"])
    print("[task09] meta =", result["meta"])
    print("[task09] quality =", quality)
    print("[task09] shortlist_rate =", result["shortlist_rate"])
    for index, item in enumerate(result["top20"], start=1):
        print(
            f"[task09] top{index:02d} "
            f"name={item['buyer_name']} "
            f"score={item['final_score']} "
            f"decision={item['decision']} "
            f"country={item['country_norm']} "
            f"matched_by={item['matched_by']} "
            f"contact={bool(item['contact_email'] or item['contact_phone'] or item['contact_website'])}"
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TASK-09 화장품 바이어 Top 20 결과 검증")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output", help="output CSV 폴더")
    parser.add_argument("--reference-date", type=str, default=DEFAULT_REFERENCE_DATE, help="검증 기준일")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="shortlist 반환 수")
    parser.add_argument(
        "--opportunity-title-contains",
        type=str,
        default=DEFAULT_OPPORTUNITY_TITLE_CONTAINS,
        help="선택할 opportunity title 부분 일치 조건",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = validate_top20(
        output_dir=args.output_dir,
        reference_date=args.reference_date,
        limit=args.limit,
        opportunity_title_contains=args.opportunity_title_contains,
    )
    _print_result(result)
    print("[task09] PASS" if result["quality"]["passed"] else "[task09] FAIL")
    return 0 if result["quality"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
