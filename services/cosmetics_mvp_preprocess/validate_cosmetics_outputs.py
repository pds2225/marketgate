from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from preprocess_cosmetics import NOISE_MARKER_RE  # noqa: E402
from task05_shortlist import opportunity_hard_gate  # noqa: E402


def _read_output(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"출력 파일이 없습니다: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _true_ratio(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    normalized = series.astype(str).str.strip().str.lower()
    return float((normalized == "true").mean())


def _signal_ratio(df: pd.DataFrame) -> tuple[str, float]:
    if "signal_usable" in df.columns:
        return "signal_usable", _true_ratio(df["signal_usable"])
    if "has_contact" in df.columns:
        return "has_contact", _true_ratio(df["has_contact"])
    return "signal_usable", 0.0


def _top_countries(df: pd.DataFrame, n: int = 10) -> pd.Series:
    if "country_norm" not in df.columns or df.empty:
        return pd.Series(dtype=int)
    return df["country_norm"].astype(str).str.strip().replace("", pd.NA).dropna().value_counts().head(n)


def _sample_trace_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    text = df.astype(str).agg(" | ".join, axis=1)
    return int(text.str.contains(NOISE_MARKER_RE, regex=True).sum())


def _domestic_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    country = df.get("country_iso3", pd.Series(dtype=str)).astype(str).str.upper()
    return int((country == "KOR").sum())


def _sample_frame(df: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    if df.empty:
        return df
    if sample_size <= 0:
        return df.iloc[0:0].copy()
    size = min(sample_size, len(df))
    if size == len(df):
        return df.copy()
    return df.sample(n=size, random_state=seed)


def _opportunity_smoke_pass_rate(
    df: pd.DataFrame,
    sample_size: int,
    reference_date: date,
    seed: int,
) -> tuple[float, int, Counter[str]]:
    sample = _sample_frame(df, sample_size=sample_size, seed=seed)
    if sample.empty:
        return 0.0, 0, Counter()

    gate_passed = 0
    reasons: Counter[str] = Counter()
    for _, row in sample.iterrows():
        result = opportunity_hard_gate(row.to_dict(), reference_date=reference_date)
        if result["passed"]:
            gate_passed += 1
        reasons.update(result["gate_reason"])

    return gate_passed / len(sample), len(sample), reasons


def _print_report(name: str, df: pd.DataFrame) -> None:
    print(f"[{name}] rows={len(df)}")
    signal_col, signal_ratio = _signal_ratio(df)
    print(f"[{name}] {signal_col}_true_ratio={signal_ratio:.3f}")
    print(f"[{name}] sample_trace_rows={_sample_trace_count(df)}")
    print(f"[{name}] domestic_rows={_domestic_count(df)}")
    top = _top_countries(df)
    if top.empty:
        print(f"[{name}] country_top=[]")
    else:
        print(f"[{name}] country_top={top.to_dict()}")


def validate(
    output_dir: Path,
    min_buyer_rows: int,
    min_opportunity_rows: int,
    min_contact_ratio: float,
    required_countries: Iterable[str],
    allow_domestic_rows: bool,
    fail_on_sample_traces: bool,
    smoke_sample_size: int,
    smoke_pass_rate_min: float,
    smoke_pass_rate_max: float,
    reference_date: date,
    smoke_seed: int,
) -> int:
    buyer = _read_output(output_dir / "buyer_candidate.csv")
    opportunity = _read_output(output_dir / "opportunity_item.csv")

    _print_report("buyer_candidate", buyer)
    _print_report("opportunity_item", opportunity)

    failures: list[str] = []
    if len(buyer) < min_buyer_rows:
        failures.append(f"buyer_candidate rows {len(buyer)} < {min_buyer_rows}")
    if len(opportunity) < min_opportunity_rows:
        failures.append(f"opportunity_item rows {len(opportunity)} < {min_opportunity_rows}")

    buyer_col, buyer_ratio = _signal_ratio(buyer)
    opportunity_col, opportunity_ratio = _signal_ratio(opportunity)
    if buyer_ratio < min_contact_ratio:
        failures.append(f"buyer_candidate {buyer_col} ratio {buyer_ratio:.3f} < {min_contact_ratio:.3f}")
    if opportunity_ratio < min_contact_ratio:
        failures.append(f"opportunity_item {opportunity_col} ratio {opportunity_ratio:.3f} < {min_contact_ratio:.3f}")

    required = [country.strip() for country in required_countries if country.strip()]
    buyer_countries = set(buyer.get("country_norm", pd.Series(dtype=str)).astype(str).str.strip().tolist())
    opportunity_countries = set(opportunity.get("country_norm", pd.Series(dtype=str)).astype(str).str.strip().tolist())
    combined_countries = buyer_countries | opportunity_countries
    missing = [country for country in required if country not in combined_countries]
    if missing:
        failures.append(f"missing required countries: {missing}")

    if not allow_domestic_rows:
        if _domestic_count(buyer) > 0:
            failures.append("buyer_candidate contains domestic rows")
        if _domestic_count(opportunity) > 0:
            failures.append("opportunity_item contains domestic rows")

    if fail_on_sample_traces:
        if _sample_trace_count(buyer) > 0:
            failures.append("buyer_candidate contains sample/test traces")
        if _sample_trace_count(opportunity) > 0:
            failures.append("opportunity_item contains sample/test traces")

    smoke_rate, smoke_rows, smoke_reasons = _opportunity_smoke_pass_rate(
        opportunity,
        sample_size=smoke_sample_size,
        reference_date=reference_date,
        seed=smoke_seed,
    )
    print(
        f"[opportunity_smoke] sample_rows={smoke_rows} gate_pass_rate={smoke_rate:.3f} "
        f"target_range={smoke_pass_rate_min:.3f}-{smoke_pass_rate_max:.3f}"
    )
    if smoke_reasons:
        print(f"[opportunity_smoke] gate_reason_top={smoke_reasons.most_common(5)}")

    if smoke_rate < smoke_pass_rate_min or smoke_rate > smoke_pass_rate_max:
        failures.append(
            f"opportunity gate pass_rate {smoke_rate:.3f} outside "
            f"{smoke_pass_rate_min:.3f}-{smoke_pass_rate_max:.3f}"
        )

    if failures:
        print("[HARD_GATE] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("[HARD_GATE] PASS")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cosmetics MVP 전처리 결과 검증")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output",
        help="buyer_candidate.csv / opportunity_item.csv 위치",
    )
    parser.add_argument("--min-buyer-rows", type=int, default=200)
    parser.add_argument("--min-opportunity-rows", type=int, default=200)
    parser.add_argument("--min-contact-ratio", type=float, default=0.10)
    parser.add_argument(
        "--required-country",
        action="append",
        default=["미국", "베트남"],
        help="존재해야 하는 country_norm 값. 여러 번 지정 가능",
    )
    parser.add_argument(
        "--allow-domestic-rows",
        action="store_true",
        help="국내 행을 허용할 때 사용",
    )
    parser.add_argument(
        "--allow-sample-traces",
        action="store_true",
        help="샘플/테스트 흔적을 허용할 때 사용",
    )
    parser.add_argument(
        "--smoke-sample-size",
        type=int,
        default=200,
        help="opportunity_item에서 뽑을 실데이터 smoke sample 수",
    )
    parser.add_argument(
        "--smoke-pass-rate-min",
        type=float,
        default=0.15,
        help="opportunity smoke pass rate 최소값",
    )
    parser.add_argument(
        "--smoke-pass-rate-max",
        type=float,
        default=0.35,
        help="opportunity smoke pass rate 최대값",
    )
    parser.add_argument(
        "--reference-date",
        type=str,
        default=None,
        help="smoke test 기준일. 미지정 시 오늘 날짜 사용",
    )
    parser.add_argument(
        "--smoke-seed",
        type=int,
        default=42,
        help="smoke sample 재현성 시드",
    )
    return parser


def _parse_reference_date(value: str | None) -> date:
    if not value:
        return date(2024, 12, 31)
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    reference_date = _parse_reference_date(args.reference_date)
    return validate(
        output_dir=args.output_dir,
        min_buyer_rows=args.min_buyer_rows,
        min_opportunity_rows=args.min_opportunity_rows,
        min_contact_ratio=args.min_contact_ratio,
        required_countries=args.required_country,
        allow_domestic_rows=args.allow_domestic_rows,
        fail_on_sample_traces=not args.allow_sample_traces,
        smoke_sample_size=args.smoke_sample_size,
        smoke_pass_rate_min=args.smoke_pass_rate_min,
        smoke_pass_rate_max=args.smoke_pass_rate_max,
        reference_date=reference_date,
        smoke_seed=args.smoke_seed,
    )


if __name__ == "__main__":
    raise SystemExit(main())
