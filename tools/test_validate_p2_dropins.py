"""P2 drop-in validation and merge fail-closed tests."""

from __future__ import annotations

import csv

import merge_p1_p2_buyer_sources as merge
from validate_p2_dropins import validate_dropin


FIELDS = [
    "source_dataset",
    "title",
    "normalized_name",
    "country_raw",
    "country_norm",
    "has_contact",
    "contact_email",
    "contact_phone",
    "contact_website",
]


def _write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_valid_dropin_passes_and_duplicate_is_warning(tmp_path):
    path = tmp_path / "tradekorea.csv"
    row = {
        "source_dataset": "TradeKorea_BuyerOrInquiry",
        "normalized_name": "Acme Beauty",
        "country_norm": "미국",
        "has_contact": "false",
    }
    _write(path, [row, row])

    result = validate_dropin(path)

    assert result.valid
    assert result.rows == 2
    assert [warning.code for warning in result.warnings] == ["duplicate_identity_country"]


def test_invalid_rows_report_all_safety_failures(tmp_path):
    path = tmp_path / "kita.csv"
    _write(
        path,
        [
            {
                "source_dataset": "KITA_BuyerOrInquiry",
                "title": "=HYPERLINK(\"https://invalid\")",
                "country_norm": "",
                "has_contact": "true",
                "contact_email": "not-an-email",
            }
        ],
    )

    result = validate_dropin(path)
    codes = {error.code for error in result.errors}

    assert not result.valid
    assert {
        "missing_country",
        "invalid_email",
        "contact_flag_without_evidence",
        "spreadsheet_formula",
    } <= codes


def test_merge_skips_invalid_dropin_and_reports_reason(tmp_path, monkeypatch):
    path = tmp_path / "tradekorea.csv"
    _write(path, [{"source_dataset": "TradeKorea_BuyerOrInquiry"}])
    monkeypatch.setattr(merge, "P2_DIR", tmp_path)

    frames, status = merge._load_p2_optional()

    assert frames == []
    failure = next(item for item in status if item.get("file") == path.name)
    assert failure["status"] == "VALIDATION_FAILED"
    assert failure["validation"]["valid"] is False
    assert "missing_source_dataset" in {
        error["code"] for error in failure["validation"]["errors"]
    }
