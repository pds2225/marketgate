"""merge_p1_p2 의 INQUIRY_SOURCES_IN_BUYER 분리 마스크를 디버그.

사용:
    python scripts/debug_merge.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SERVICE_ROOT.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from merge_p1_p2_buyer_sources import (  # noqa: E402
    INQUIRY_SOURCES_IN_BUYER,
    _align_frame,
    _load_csv,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--buyer",
        type=Path,
        default=SERVICE_ROOT / "output" / "buyer_candidate.csv",
    )
    args = parser.parse_args(argv)

    before = _load_csv(args.buyer)
    print("raw unique source_dataset:", list(before["source_dataset"].dropna().unique()[:10]))
    aligned = _align_frame(before, "buyer_candidate")
    print("aligned unique source_dataset:", list(aligned["source_dataset"].unique()[:10]))
    mask = aligned["source_dataset"].isin(INQUIRY_SOURCES_IN_BUYER)
    print("inquiry-in-buyer mask sum", int(mask.sum()))
    print("INQUIRY_SOURCES_IN_BUYER", sorted(INQUIRY_SOURCES_IN_BUYER))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
