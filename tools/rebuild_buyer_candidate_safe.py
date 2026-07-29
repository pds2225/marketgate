#!/usr/bin/env python3
"""기존 구매자 스냅샷을 보존하는 안전 재생성 도구.

핵심 원칙:
- Git 기준 스냅샷을 원본으로 사용하고 현재 축소 CSV를 구매자 원본으로 채택하지 않는다.
- 인콰이어리 행만 opportunity 결과로 이동한다.
- 기존 구매자 출처 6종이 모두 남아 있는지 fail-closed로 확인한다.
- 추정 이메일은 안전 구매자 CSV에서 제거하고 별도 CSV에 격리한다.
- 기존 파일은 절대 덮어쓰지 않고 새 output 디렉터리에만 기록한다.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from backfill_buyer_emails import _clean, _has_email, _norm_key
from merge_p1_p2_buyer_sources import (
    BUYER_COLUMNS,
    INQUIRY_SOURCES_IN_BUYER,
    _align_frame,
    _truthy_contact,
)

ROOT = Path(__file__).resolve().parents[1]
BUYER_GIT_PATH = "services/cosmetics_mvp_preprocess/output/buyer_candidate.csv"
DEFAULT_BUYER_PATH = ROOT / BUYER_GIT_PATH
DEFAULT_OPPORTUNITY_PATH = (
    ROOT / "services" / "cosmetics_mvp_preprocess" / "output" / "opportunity_item.csv"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "services" / "cosmetics_mvp_preprocess" / "output" / "safe_rebuild"
)

EXPECTED_BUYER_SOURCES = {
    "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보",
    "정보통신산업진흥원_글로벌ICT포털해외바이어",
    "한국무역보험공사_화장품 바이어 정보",
    "한국무역보험공사_바이어 검색",
    "EC21_GlobalB2B_BuyingLeads",
    "ITC_TradeMap_ImportingCompanies",
}

OUTPUT_NAMES = {
    "buyer": "buyer_candidate_safe.csv",
    "opportunity": "opportunity_item_safe.csv",
    "estimated": "estimated_email_quarantine.csv",
    "restored": "restored_email_assignment_quarantine.csv",
    "report": "safe_buyer_rebuild_report.json",
}


@dataclass(frozen=True)
class RebuildResult:
    buyer: pd.DataFrame
    opportunity: pd.DataFrame
    estimated_quarantine: pd.DataFrame
    restored_assignment_quarantine: pd.DataFrame
    report: dict[str, Any]


def _load_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, dtype=str, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"CSV 인코딩을 확인할 수 없습니다: {path}")


def _load_git_buyer(repo_root: Path, revision: str) -> pd.DataFrame:
    try:
        raw = subprocess.check_output(
            ["git", "show", f"{revision}:{BUYER_GIT_PATH}"],
            cwd=repo_root,
            stderr=subprocess.PIPE,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            f"Git 기준 구매자 CSV를 읽지 못했습니다: {revision}:{BUYER_GIT_PATH}"
        ) from exc
    return pd.read_csv(
        BytesIO(raw),
        dtype=str,
        encoding="utf-8-sig",
        low_memory=False,
    )


def _ensure_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = ""
    return out[list(columns)]


def _source_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["source_dataset"].fillna("(빈 출처)").value_counts()
    return {str(source): int(count) for source, count in counts.items()}


def _email_count(frame: pd.DataFrame) -> int:
    if "contact_email" not in frame.columns:
        return 0
    return int(frame["contact_email"].map(_has_email).sum())


def _estimated_mask(frame: pd.DataFrame) -> pd.Series:
    email = frame["contact_email"].map(_has_email)
    estimated = (
        frame["contact_email_estimated"]
        .map(_clean)
        .str.casefold()
        .eq("true")
    )
    return email & estimated


def _legacy_name(row: pd.Series) -> Any:
    # 기존 backfill 도구와 같은 선택 순서를 유지해야 1,869건 감사 결과가 재현된다.
    return row.get("normalized_name") or row.get("title")


def _legacy_country(row: pd.Series) -> Any:
    return row.get("country_norm") or row.get("country_raw")


def _provenance_map(baseline: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """기존 backfill의 first-hit 규칙을 보존하면서 추정 여부를 함께 기록한다."""
    output: dict[str, dict[str, Any]] = {}
    for _, row in baseline.iterrows():
        email = _clean(row.get("contact_email"))
        if not _has_email(email):
            continue
        name = _legacy_name(row)
        country = _legacy_country(row)
        payload = {
            "email": email,
            "estimated": _clean(row.get("contact_email_estimated")).casefold()
            == "true",
            "source_dataset": _clean(row.get("source_dataset")),
            "source_file": _clean(row.get("source_file")),
            "source_row_no": _clean(row.get("source_row_no")),
        }
        for key in (_norm_key(name, country), _norm_key(name, "")):
            if key and key not in output:
                output[key] = payload
    return output


def identify_restored_estimated_assignments(
    baseline: pd.DataFrame,
    reduced_buyer: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """축소 CSV에 복원된 추정 이메일을 기존 backfill 규칙으로 재현한다."""
    provenance = _provenance_map(baseline)
    quarantined: list[dict[str, Any]] = []
    stats = {
        "matched_total": 0,
        "matched_estimated": 0,
        "matched_non_estimated": 0,
        "exact_name_country": 0,
        "name_only_fallback": 0,
        "cross_source": 0,
    }

    for _, row in reduced_buyer.iterrows():
        assigned_email = _clean(row.get("contact_email"))
        if not _has_email(assigned_email):
            continue

        name = _legacy_name(row)
        country = _legacy_country(row)
        exact_key = _norm_key(name, country)
        name_key = _norm_key(name, "")
        hit = provenance.get(exact_key) if exact_key else None
        match_mode = "exact_name_country"
        if hit is None:
            hit = provenance.get(name_key) if name_key else None
            match_mode = "name_only_fallback"
        if hit is None or assigned_email.casefold() != hit["email"].casefold():
            continue

        stats["matched_total"] += 1
        stats[match_mode] += 1
        same_source = (
            _clean(row.get("source_dataset")) == hit["source_dataset"]
        )
        if not same_source:
            stats["cross_source"] += 1

        if hit["estimated"]:
            stats["matched_estimated"] += 1
            record = row.to_dict()
            record.update(
                {
                    "quarantine_reason": "restored_from_estimated_snapshot_email",
                    "match_mode": match_mode,
                    "origin_source_dataset": hit["source_dataset"],
                    "origin_source_file": hit["source_file"],
                    "origin_source_row_no": hit["source_row_no"],
                }
            )
            quarantined.append(record)
        else:
            stats["matched_non_estimated"] += 1

    extra_columns = [
        "quarantine_reason",
        "match_mode",
        "origin_source_dataset",
        "origin_source_file",
        "origin_source_row_no",
    ]
    columns = list(reduced_buyer.columns) + extra_columns
    return pd.DataFrame(quarantined, columns=columns), stats


def _opportunity_key(row: pd.Series) -> tuple[str, ...]:
    source = _clean(row.get("source_dataset")).casefold()
    source_file = _clean(row.get("source_file")).casefold()
    source_row = _clean(row.get("source_row_no")).casefold()
    if source_file or source_row:
        return ("source", source, source_file, source_row)
    return (
        "content",
        source,
        _clean(row.get("title")).casefold(),
        _clean(row.get("country_norm")).casefold(),
        _clean(row.get("valid_until")).casefold(),
    )


def _append_moved_inquiries(
    opportunity: pd.DataFrame,
    moved: pd.DataFrame,
) -> tuple[pd.DataFrame, int, int]:
    existing = _ensure_columns(opportunity, BUYER_COLUMNS)
    moved_aligned = _align_frame(moved, "opportunity_item")
    known_keys = {
        _opportunity_key(row) for _, row in existing.iterrows()
    }
    appended: list[dict[str, Any]] = []
    already_present = 0
    for _, row in moved_aligned.iterrows():
        key = _opportunity_key(row)
        if key in known_keys:
            already_present += 1
            continue
        known_keys.add(key)
        appended.append(row.to_dict())

    if appended:
        additions = pd.DataFrame(appended, columns=BUYER_COLUMNS)
        output = pd.concat([existing, additions], ignore_index=True)
    else:
        output = existing.copy()
    return output, len(appended), already_present


def rebuild_safe_outputs(
    baseline: pd.DataFrame,
    reduced_buyer: pd.DataFrame,
    opportunity: pd.DataFrame,
    *,
    expected_sources: set[str] | None = None,
) -> RebuildResult:
    """원본을 변경하지 않고 안전 구매자·기회·격리 결과를 메모리에서 만든다."""
    baseline_aligned = _align_frame(baseline, "buyer_candidate")
    reduced_aligned = _ensure_columns(reduced_buyer, BUYER_COLUMNS)
    expected_sources = expected_sources or EXPECTED_BUYER_SOURCES

    inquiry_mask = baseline_aligned["source_dataset"].isin(
        INQUIRY_SOURCES_IN_BUYER
    )
    moved = baseline_aligned[inquiry_mask].copy()
    buyer_safe = baseline_aligned[~inquiry_mask].copy().reset_index(drop=True)

    remaining_sources = set(
        buyer_safe["source_dataset"].map(_clean).loc[lambda values: values.ne("")]
    )
    missing_sources = sorted(expected_sources - remaining_sources)
    if missing_sources:
        raise ValueError(
            "안전 재생성 중 필수 구매자 출처가 누락됐습니다: "
            + ", ".join(missing_sources)
        )

    estimated_mask = _estimated_mask(buyer_safe)
    estimated_quarantine = buyer_safe[estimated_mask].copy()
    estimated_quarantine["quarantine_reason"] = (
        "baseline_contact_email_estimated_true"
    )

    buyer_safe.loc[estimated_mask, "contact_email"] = ""
    buyer_safe.loc[estimated_mask, "contact_email_estimated"] = "False"
    buyer_safe["has_contact"] = buyer_safe.apply(_truthy_contact, axis=1)

    restored_quarantine, restored_stats = (
        identify_restored_estimated_assignments(
            baseline_aligned,
            reduced_aligned,
        )
    )
    opportunity_safe, appended, already_present = _append_moved_inquiries(
        opportunity,
        moved,
    )

    expected_buyer_rows = len(baseline_aligned) - int(inquiry_mask.sum())
    if len(buyer_safe) != expected_buyer_rows:
        raise AssertionError(
            "인콰이어리 외 구매자 행이 손실됐습니다: "
            f"expected={expected_buyer_rows}, actual={len(buyer_safe)}"
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "rows": int(len(baseline_aligned)),
            "sources": _source_counts(baseline_aligned),
            "with_email": _email_count(baseline_aligned),
        },
        "buyer_safe": {
            "rows": int(len(buyer_safe)),
            "sources": _source_counts(buyer_safe),
            "with_email": _email_count(buyer_safe),
            "required_sources_preserved": sorted(expected_sources),
        },
        "inquiry_separation": {
            "moved_from_buyer": int(inquiry_mask.sum()),
            "moved_by_source": _source_counts(moved),
            "appended_to_opportunity": int(appended),
            "already_present_in_opportunity": int(already_present),
            "opportunity_rows_after": int(len(opportunity_safe)),
        },
        "email_quarantine": {
            "baseline_estimated_removed": int(estimated_mask.sum()),
            "restored_assignment_audit": restored_stats,
        },
        "guarantees": {
            "original_files_overwritten": False,
            "buyer_rows_removed_other_than_inquiries": 0,
            "api_schema_changed": False,
        },
    }
    return RebuildResult(
        buyer=buyer_safe,
        opportunity=opportunity_safe,
        estimated_quarantine=estimated_quarantine,
        restored_assignment_quarantine=restored_quarantine,
        report=report,
    )


def validate_expected_counts(
    result: RebuildResult,
    *,
    expected_baseline_rows: int,
    expected_restored_estimated: int,
) -> None:
    actual_baseline = int(result.report["baseline"]["rows"])
    if actual_baseline != expected_baseline_rows:
        raise ValueError(
            "기준 구매자 행 수가 예상과 다릅니다: "
            f"expected={expected_baseline_rows}, actual={actual_baseline}"
        )
    actual_restored = int(
        result.report["email_quarantine"]["restored_assignment_audit"][
            "matched_estimated"
        ]
    )
    if actual_restored != expected_restored_estimated:
        raise ValueError(
            "복원 추정 이메일 수가 예상과 다릅니다: "
            f"expected={expected_restored_estimated}, actual={actual_restored}"
        )


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve()


def write_outputs(
    result: RebuildResult,
    output_dir: Path,
    *,
    protected_inputs: Iterable[Path],
    force: bool = False,
) -> dict[str, str]:
    output_dir = _resolved(output_dir)
    paths = {
        key: output_dir / filename for key, filename in OUTPUT_NAMES.items()
    }
    protected = {_resolved(path) for path in protected_inputs}
    collisions = [
        str(path) for path in paths.values() if _resolved(path) in protected
    ]
    if collisions:
        raise ValueError(
            "원본 입력 경로와 출력 경로가 겹칩니다: " + ", ".join(collisions)
        )
    existing = [str(path) for path in paths.values() if path.exists()]
    if existing and not force:
        raise FileExistsError(
            "기존 안전 출력이 있습니다. --force 없이 덮어쓰지 않습니다: "
            + ", ".join(existing)
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    frames = {
        "buyer": result.buyer,
        "opportunity": result.opportunity,
        "estimated": result.estimated_quarantine,
        "restored": result.restored_assignment_quarantine,
    }
    for key, frame in frames.items():
        final_path = paths[key]
        temp_path = final_path.with_suffix(final_path.suffix + ".tmp")
        frame.to_csv(temp_path, index=False, encoding="utf-8-sig")
        os.replace(temp_path, final_path)

    report_path = paths["report"]
    report_temp = report_path.with_suffix(report_path.suffix + ".tmp")
    report_with_paths = {
        **result.report,
        "outputs": {key: str(path) for key, path in paths.items()},
    }
    report_temp.write_text(
        json.dumps(report_with_paths, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(report_temp, report_path)
    return {key: str(path) for key, path in paths.items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-rev",
        default="HEAD",
        help="보존할 buyer_candidate.csv가 들어 있는 Git 리비전",
    )
    parser.add_argument(
        "--baseline-csv",
        type=Path,
        default=None,
        help="테스트/수동 복구용 기준 CSV. 지정하면 --baseline-rev보다 우선",
    )
    parser.add_argument(
        "--reduced-buyer",
        type=Path,
        required=True,
        help="1,869건 복원 감사를 수행할 축소 buyer_candidate.csv",
    )
    parser.add_argument(
        "--opportunity",
        type=Path,
        default=DEFAULT_OPPORTUNITY_PATH,
        help="기존 opportunity_item.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="원본과 분리된 안전 결과 저장 폴더",
    )
    parser.add_argument("--expected-baseline-rows", type=int, default=36_241)
    parser.add_argument(
        "--expected-restored-estimated",
        type=int,
        default=1_869,
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="검증 후 새 출력 파일을 실제로 작성",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 safe_rebuild 출력만 교체. 원본 입력은 여전히 보호",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.reduced_buyer.exists():
        raise FileNotFoundError(
            f"축소 구매자 CSV가 없습니다: {args.reduced_buyer}"
        )
    baseline = (
        _load_csv(args.baseline_csv)
        if args.baseline_csv
        else _load_git_buyer(ROOT, args.baseline_rev)
    )
    reduced = _load_csv(args.reduced_buyer)
    opportunity = (
        _load_csv(args.opportunity)
        if args.opportunity.exists()
        else pd.DataFrame(columns=BUYER_COLUMNS)
    )

    result = rebuild_safe_outputs(baseline, reduced, opportunity)
    validate_expected_counts(
        result,
        expected_baseline_rows=args.expected_baseline_rows,
        expected_restored_estimated=args.expected_restored_estimated,
    )

    if args.write:
        paths = write_outputs(
            result,
            args.output_dir,
            protected_inputs=[
                DEFAULT_BUYER_PATH,
                args.reduced_buyer,
                args.opportunity,
                *([args.baseline_csv] if args.baseline_csv else []),
            ],
            force=args.force,
        )
        result.report["outputs"] = paths
    else:
        result.report["outputs"] = {}
        result.report["dry_run"] = True

    print(json.dumps(result.report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
