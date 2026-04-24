from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

from shortlist_service import (
    _select_opportunity,
    build_supplier_profile,
    load_buyer_frame,
    load_opportunity_frame,
    shortlist_buyers,
)
from task05_shortlist import buyer_hard_gate, normalize_text
from task06_fit_score import score_buyers


def _non_empty_rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    filled = sum(1 for row in rows if normalize_text(row.get(key)))
    return filled / len(rows)


def _true_rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    truthy = sum(1 for row in rows if str(row.get(key, "")).strip().lower() == "true")
    return truthy / len(rows)


def _group_counts(rows: Iterable[Mapping[str, Any]], key: str) -> list[tuple[str, int]]:
    counts = Counter(normalize_text(row.get(key)) or "(빈값)" for row in rows)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _format_rate(value: float) -> str:
    return f"{value * 100:.1f}%"


def _buyer_hs_match(row: Mapping[str, Any], target_hs_code_norm: str) -> bool:
    if not target_hs_code_norm:
        return True
    buyer_hs = normalize_text(row.get("hs_code_norm"))
    if not buyer_hs:
        return False
    if len(target_hs_code_norm) >= 6:
        return buyer_hs == target_hs_code_norm or buyer_hs[:4] == target_hs_code_norm[:4]
    if len(target_hs_code_norm) >= 4:
        return buyer_hs[:4] == target_hs_code_norm[:4]
    return buyer_hs.startswith(target_hs_code_norm)


def build_diagnostic_report(
    *,
    output_dir: Path,
    target_country_norm: str,
    target_hs_code_norm: str,
    target_keywords_norm: str,
    reference_date: date,
    limit: int,
) -> str:
    buyer_rows = load_buyer_frame(output_dir=output_dir).to_dict(orient="records")
    opportunity_rows = load_opportunity_frame(output_dir=output_dir).to_dict(orient="records")

    supplier_profile = build_supplier_profile(
        supplier_name="Shortlist Diagnostic",
        target_country_norm=target_country_norm,
        target_hs_code_norm=target_hs_code_norm,
        target_keywords_norm=target_keywords_norm,
    )

    selected_opportunity = _select_opportunity(
        load_opportunity_frame(output_dir=output_dir),
        opportunity_country_norm=target_country_norm,
        reference_date=reference_date,
    )

    country_filtered_buyers = [
        row for row in buyer_rows
        if not target_country_norm or normalize_text(row.get("country_norm")) == normalize_text(target_country_norm)
    ]
    hs_filtered_buyers = [
        row for row in country_filtered_buyers
        if _buyer_hs_match(row, target_hs_code_norm)
    ]

    hard_gate_passed: list[dict[str, Any]] = []
    hard_gate_failed_reasons: Counter[str] = Counter()
    for row in hs_filtered_buyers:
        gate = buyer_hard_gate(
            row,
            selected_opportunity,
            target_country_norm=target_country_norm,
            target_hs_code_norm=target_hs_code_norm,
            target_keywords_norm=target_keywords_norm,
            target_product_name_norm=normalize_text((selected_opportunity or {}).get("product_name_norm")),
            target_title=normalize_text((selected_opportunity or {}).get("title")),
        )
        if gate.get("passed"):
            hard_gate_passed.append(row)
        else:
            hard_gate_failed_reasons[normalize_text(gate.get("gate_reason")) or "(사유없음)"] += 1

    scored_rows = score_buyers(
        buyers=country_filtered_buyers,
        supplier_profile=supplier_profile,
        opportunity=selected_opportunity,
        reference_date=reference_date,
    )
    decision_counts = Counter(str(row.get("decision") or "(unknown)") for row in scored_rows)

    shortlist_result = shortlist_buyers(
        output_dir=output_dir,
        supplier_profile=supplier_profile,
        reference_date=reference_date,
        limit=limit,
        opportunity_country_norm=target_country_norm,
        include_rejected=False,
    )
    shortlist_meta = shortlist_result.get("meta") or {}

    lines: list[str] = []
    lines.append("=== Shortlist Diagnostic Report ===")
    lines.append(f"output_dir: {output_dir}")
    lines.append(f"reference_date: {reference_date.isoformat()}")
    lines.append(f"target_country_norm: {target_country_norm or '(없음)'}")
    lines.append(f"target_hs_code_norm: {target_hs_code_norm or '(없음)'}")
    lines.append(f"target_keywords_norm: {target_keywords_norm or '(없음)'}")
    lines.append("")

    lines.append("[Source Counts] buyer_candidate.csv")
    for name, count in _group_counts(buyer_rows, "source_dataset"):
        lines.append(f"- {name}: {count}")
    lines.append("")

    lines.append("[Source Counts] opportunity_item.csv")
    for name, count in _group_counts(opportunity_rows, "source_dataset"):
        lines.append(f"- {name}: {count}")
    lines.append("")

    lines.append("[Coverage]")
    lines.append(
        "buyer_candidate.csv: "
        f"country_norm={_format_rate(_non_empty_rate(buyer_rows, 'country_norm'))}, "
        f"hs_code_norm={_format_rate(_non_empty_rate(buyer_rows, 'hs_code_norm'))}, "
        f"has_contact={_format_rate(_true_rate(buyer_rows, 'has_contact'))}"
    )
    lines.append(
        "opportunity_item.csv: "
        f"country_norm={_format_rate(_non_empty_rate(opportunity_rows, 'country_norm'))}, "
        f"hs_code_norm={_format_rate(_non_empty_rate(opportunity_rows, 'hs_code_norm'))}, "
        f"has_contact={_format_rate(_true_rate(opportunity_rows, 'has_contact'))}"
    )
    lines.append("")

    lines.append("[Selected Opportunity]")
    if selected_opportunity:
        lines.append(f"- title: {normalize_text(selected_opportunity.get('title')) or '(없음)'}")
        lines.append(f"- country_norm: {normalize_text(selected_opportunity.get('country_norm')) or '(없음)'}")
        lines.append(f"- hs_code_norm: {normalize_text(selected_opportunity.get('hs_code_norm')) or '(없음)'}")
        lines.append(f"- valid_until: {normalize_text(selected_opportunity.get('valid_until')) or '(없음)'}")
        lines.append(f"- signal_type: {normalize_text(selected_opportunity.get('signal_type')) or '(없음)'}")
    else:
        lines.append("- selected opportunity 없음")
    lines.append("")

    lines.append("[Pipeline Counts]")
    lines.append(f"- buyer 원본 건수: {len(buyer_rows)}")
    lines.append(f"- 국가 필터 후 건수: {len(country_filtered_buyers)}")
    lines.append(f"- HS 필터 후 건수: {len(hs_filtered_buyers)}")
    lines.append(f"- hard gate 통과 건수: {len(hard_gate_passed)}")
    lines.append(f"- 최종 shortlist 건수: {int(shortlist_meta.get('shortlist_count', 0))}")
    lines.append(f"- 최종 returned 건수(candidate 포함): {int(shortlist_meta.get('returned_count', 0))}")
    lines.append("")

    lines.append("[Decision Counts]")
    for name, count in sorted(decision_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {name}: {count}")
    lines.append("")

    lines.append("[Hard Gate Failure Reasons]")
    if hard_gate_failed_reasons:
        for name, count in sorted(hard_gate_failed_reasons.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {name}: {count}")
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append("[Shortlist Meta]")
    lines.append(f"- filtered_buyer_rows: {int(shortlist_meta.get('filtered_buyer_rows', 0))}")
    lines.append(f"- scored_rows: {int(shortlist_meta.get('scored_rows', 0))}")
    lines.append(f"- shortlist_count: {int(shortlist_meta.get('shortlist_count', 0))}")
    lines.append(f"- candidate_count: {int(shortlist_meta.get('candidate_count', 0))}")
    lines.append(f"- rejected_count: {int(shortlist_meta.get('rejected_count', 0))}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="buyer_candidate / opportunity_item shortlist 진단 리포트")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "output"),
        help="buyer_candidate.csv / opportunity_item.csv 위치",
    )
    parser.add_argument("--target-country", default="미국", help="국가 필터 기준 country_norm")
    parser.add_argument("--target-hs", default="330499", help="HS 코드 기준")
    parser.add_argument("--target-keywords", default="", help="추가 키워드 기준")
    parser.add_argument("--reference-date", default=date.today().isoformat(), help="기준일 YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=20, help="최종 shortlist 반환 상한")
    args = parser.parse_args()

    report = build_diagnostic_report(
        output_dir=Path(args.output_dir),
        target_country_norm=args.target_country,
        target_hs_code_norm=normalize_text(args.target_hs),
        target_keywords_norm=normalize_text(args.target_keywords),
        reference_date=date.fromisoformat(args.reference_date),
        limit=args.limit,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
