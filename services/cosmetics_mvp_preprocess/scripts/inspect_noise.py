"""buyer/opportunity CSV에 샘플·디버그 노이즈 마커가 남았는지 검사.

사용:
    python scripts/inspect_noise.py
    python scripts/inspect_noise.py --buyer output/buyer_candidate.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

SERVICE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_ROOT))

from preprocess_cosmetics import NOISE_MARKER_RE  # noqa: E402


def _inspect(path: Path, label: str, cols: list[str]) -> int:
    if not path.exists():
        print(label, "MISSING", path)
        return 0
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", low_memory=False)
    text = df.astype(str).agg(" | ".join, axis=1)
    mask = text.str.contains(NOISE_MARKER_RE, regex=True, na=False)
    print(label, "noise rows", int(mask.sum()), "/", len(df))
    show_cols = [c for c in cols if c in df.columns]
    if mask.any() and show_cols:
        print(df.loc[mask, show_cols].head(10).to_string())
    return int(mask.sum())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buyer", type=Path, default=SERVICE_ROOT / "output" / "buyer_candidate.csv")
    parser.add_argument("--opportunity", type=Path, default=SERVICE_ROOT / "output" / "opportunity_item.csv")
    args = parser.parse_args(argv)

    n1 = _inspect(
        args.buyer,
        "buyer",
        ["normalized_name", "country_norm", "contact_email", "keywords_norm"],
    )
    n2 = _inspect(
        args.opportunity,
        "opp",
        ["title", "country_norm", "source_dataset"],
    )
    return 1 if (n1 + n2) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
