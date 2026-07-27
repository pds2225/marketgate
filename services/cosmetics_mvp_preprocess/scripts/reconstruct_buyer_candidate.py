"""output/raw/*.csv 에서 buyer_candidate 행만 모아 buyer_candidate.csv 재구성.

사용:
    python scripts/reconstruct_buyer_candidate.py
    python scripts/reconstruct_buyer_candidate.py --raw-dir output/raw --output output/buyer_candidate.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

SERVICE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COLS = [
    "record_type",
    "source_dataset",
    "source_file",
    "source_row_no",
    "title",
    "normalized_name",
    "country_raw",
    "country_norm",
    "country_iso3",
    "hs_code_raw",
    "hs_code_norm",
    "keywords_raw",
    "keywords_norm",
    "has_contact",
    "contact_name",
    "contact_email",
    "contact_phone",
    "contact_website",
    "valid_until",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=SERVICE_ROOT / "output" / "raw")
    parser.add_argument("--output", type=Path, default=SERVICE_ROOT / "output" / "buyer_candidate.csv")
    args = parser.parse_args(argv)

    frames: list[pd.DataFrame] = []
    for path in sorted(args.raw_dir.glob("*.csv")):
        try:
            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", low_memory=False)
        except Exception as exc:  # noqa: BLE001 — 파일별 스킵이 목적
            print("skip", path.name, exc)
            continue
        if "record_type" not in df.columns:
            continue
        buyers = df[df["record_type"] == "buyer_candidate"]
        if buyers.empty:
            continue
        print(path.name, len(buyers))
        frames.append(buyers)

    if not frames:
        print("no frames")
        return 1

    merged = pd.concat(frames, ignore_index=True)
    for col in DEFAULT_COLS:
        if col not in merged.columns:
            merged[col] = ""
    merged = merged[DEFAULT_COLS]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False, encoding="utf-8-sig")
    print("reconstructed", args.output, "rows", len(merged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
