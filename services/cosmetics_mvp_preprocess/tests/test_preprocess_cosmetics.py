import sys
import shutil
from uuid import uuid4
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ARTIFACT_ROOT = ROOT / ".test_artifacts"

from preprocess_cosmetics import (
    COMMON_OUTPUT_COLUMNS,
    SOURCE_SPECS,
    _build_country_lookup,
    _locate_country_code_file,
    _normalize_company_name,
    _normalize_hs_code,
    _normalize_valid_until,
    _read_csv_with_fallback,
    process_pipeline,
)


def _write_source_csvs(input_dir: Path) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    for spec in SOURCE_SPECS:
        df = pd.DataFrame(list(spec.sample_rows))
        df.to_csv(input_dir / f"{spec.label}.csv", index=False, encoding="utf-8-sig")


def test_normalizers_and_country_lookup() -> None:
    country_path = _locate_country_code_file()
    country_df = _read_csv_with_fallback(country_path).dataframe
    lookup = _build_country_lookup(country_df)

    assert _normalize_company_name("주식회사 아모레퍼시픽 ㈜") == "아모레퍼시픽"
    assert _normalize_company_name("Amore Pacific Co., Ltd.") == "AMOREPACIFIC"
    assert _normalize_hs_code("33-04.99") == "330499"
    assert _normalize_valid_until("2026/07/15") == "2026-07-15"
    assert lookup.resolve("USA")[0] == "미국"
    assert lookup.resolve("Korea")[0] == "대한민국"


def test_pipeline_end_to_end_deduplicates_and_saves() -> None:
    workspace = ARTIFACT_ROOT / f"pipeline_{uuid4().hex}"
    input_dir = workspace / "input"
    output_dir = workspace / "output"

    try:
        _write_source_csvs(input_dir)

        summary = process_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            allow_sample_fallback=False,
        )

        buyer_path = output_dir / "buyer_candidate.csv"
        opportunity_path = output_dir / "opportunity_item.csv"

        assert buyer_path.exists()
        assert opportunity_path.exists()

        buyer_df = pd.read_csv(buyer_path, dtype=str, keep_default_na=False)
        opportunity_df = pd.read_csv(opportunity_path, dtype=str, keep_default_na=False)

        assert list(buyer_df.columns) == COMMON_OUTPUT_COLUMNS
        assert list(opportunity_df.columns) == COMMON_OUTPUT_COLUMNS

        assert len(buyer_df) == 1
        assert len(opportunity_df) == 3

        assert buyer_df.duplicated(subset=["normalized_name", "country_norm"]).sum() == 0
        assert opportunity_df.duplicated(subset=["title", "country_norm", "valid_until"]).sum() == 0
        assert buyer_df["has_contact"].isin(["True", "False"]).all()
        assert summary["targets"]["buyer_candidate"]["final_rows"] == 1
        assert summary["targets"]["opportunity_item"]["final_rows"] == 3
        assert "example.com" not in buyer_df.to_string().lower()
        assert "example.com" not in opportunity_df.to_string().lower()
    finally:
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)


def test_missing_input_without_fallback_raises() -> None:
    workspace = ARTIFACT_ROOT / f"missing_{uuid4().hex}"
    input_dir = workspace / "empty_input"
    output_dir = workspace / "output"

    try:
        with pytest.raises(FileNotFoundError):
            process_pipeline(
                input_dir=input_dir,
                output_dir=output_dir,
                allow_sample_fallback=False,
            )
    finally:
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
