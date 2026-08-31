#!/usr/bin/env python3
"""Fail-closed validation for legally received P2 buyer CSV drop-ins."""

from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
TRUTHY = {"1", "true", "yes", "y", "on"}
FORMULA_COLUMNS = {
    "source_dataset",
    "title",
    "normalized_name",
    "country_raw",
    "country_norm",
    "keywords_raw",
    "keywords_norm",
    "contact_name",
    "contact_email",
    "contact_website",
}
MAX_DIAGNOSTICS = 50


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    row: int | None = None
    column: str | None = None


@dataclass
class ValidationResult:
    file: str
    valid: bool = False
    rows: int = 0
    encoding: str = ""
    errors: list[Diagnostic] = field(default_factory=list)
    warnings: list[Diagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "valid": self.valid,
            "rows": self.rows,
            "encoding": self.encoding,
            "errors": [asdict(item) for item in self.errors],
            "warnings": [asdict(item) for item in self.warnings],
        }


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _append(items: list[Diagnostic], item: Diagnostic) -> None:
    if len(items) < MAX_DIAGNOSTICS:
        items.append(item)


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]], str]:
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                headers = [_clean(value) for value in (reader.fieldnames or [])]
                rows = [
                    {_clean(key): _clean(value) for key, value in row.items() if key is not None}
                    for row in reader
                ]
            return headers, rows, encoding
        except (UnicodeDecodeError, csv.Error) as exc:
            last_error = exc
    raise ValueError(f"csv_read_failed:{last_error}")


def validate_dropin(path: Path) -> ValidationResult:
    """Validate schema and row invariants without changing the source file."""
    path = Path(path)
    result = ValidationResult(file=path.name)
    if path.suffix.casefold() != ".csv":
        result.errors.append(Diagnostic("invalid_extension", "drop-in must be a .csv file"))
        return result
    if path.is_symlink():
        result.errors.append(Diagnostic("symlink_not_allowed", "drop-in symlinks are not accepted"))
        return result

    try:
        headers, rows, encoding = _read_rows(path)
    except (OSError, ValueError) as exc:
        result.errors.append(Diagnostic("csv_read_failed", str(exc)))
        return result

    result.encoding = encoding
    result.rows = len(rows)
    header_set = set(headers)
    if not ({"country_norm", "country_raw"} & header_set):
        result.errors.append(
            Diagnostic("missing_country_column", "country_norm or country_raw column is required")
        )
    if not ({"normalized_name", "title"} & header_set):
        result.errors.append(
            Diagnostic("missing_identity_column", "normalized_name or title column is required")
        )
    if "source_dataset" not in header_set:
        result.errors.append(
            Diagnostic("missing_source_column", "source_dataset column is required for provenance")
        )
    if not rows:
        result.errors.append(Diagnostic("empty_file", "at least one data row is required"))

    seen: set[tuple[str, str]] = set()
    source_names: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        source_dataset = _clean(row.get("source_dataset"))
        country = _clean(row.get("country_norm") or row.get("country_raw"))
        identity = _clean(row.get("normalized_name") or row.get("title"))
        if not source_dataset:
            _append(
                result.errors,
                Diagnostic("missing_source_dataset", "source_dataset is required", row_number),
            )
        else:
            source_names.add(source_dataset.casefold())
        if not country:
            _append(
                result.errors,
                Diagnostic("missing_country", "country is required for every row", row_number),
            )
        if not identity:
            _append(
                result.errors,
                Diagnostic("missing_identity", "buyer name or opportunity title is required", row_number),
            )

        email = _clean(row.get("contact_email"))
        email_valid = bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email))
        if email and not email_valid:
            _append(
                result.errors,
                Diagnostic("invalid_email", "contact_email is malformed", row_number, "contact_email"),
            )

        has_contact = _clean(row.get("has_contact")).casefold() in TRUTHY
        actual_contact = email_valid or any(
            _clean(row.get(column)) for column in ("contact_phone", "contact_website")
        )
        if has_contact and not actual_contact:
            _append(
                result.errors,
                Diagnostic(
                    "contact_flag_without_evidence",
                    "has_contact cannot be true without an email, phone, or website",
                    row_number,
                    "has_contact",
                ),
            )

        for column in FORMULA_COLUMNS & row.keys():
            value = _clean(row.get(column))
            if value.startswith(("=", "+", "-", "@")):
                _append(
                    result.errors,
                    Diagnostic(
                        "spreadsheet_formula",
                        "formula-like cells are blocked from exported CSVs",
                        row_number,
                        column,
                    ),
                )

        dedupe_key = (re.sub(r"\s+", "", identity).casefold(), country.casefold())
        if all(dedupe_key):
            if dedupe_key in seen:
                _append(
                    result.warnings,
                    Diagnostic("duplicate_identity_country", "duplicate identity and country", row_number),
                )
            seen.add(dedupe_key)

    if len(source_names) > 1:
        result.errors.append(
            Diagnostic("mixed_source_dataset", "one drop-in file must contain one source_dataset")
        )

    result.valid = not result.errors
    return result


__all__ = ["Diagnostic", "ValidationResult", "validate_dropin"]
