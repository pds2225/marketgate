"""바이어 데이터 수집 → 정제 → 숏리스트 준비까지 한 번에 실행하는 파이프라인.

사용법 예시:
    # dry-run: 실제 실행 없이 수행할 명령만 출력
    python scripts/run_buyer_pipeline.py --dry-run

    # 전체 파이프라인 실행
    python scripts/run_buyer_pipeline.py

    # API 수집은 건 넘기고, 로컬 input 만 처리
    python scripts/run_buyer_pipeline.py --skip-fetch

    # SBC 파일 추가
    python scripts/run_buyer_pipeline.py --sbc-input input/중소벤처기업진흥공단_업종별_해외시장진출_유망상품_현황_20260426.csv
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Sequence


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("buyer_pipeline")


SERVICE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SERVICE_ROOT.parent.parent
PYTHON = sys.executable
DEFAULT_COUNTRIES = ["US", "CN", "JP", "VN", "SG", "TH", "IN", "GB", "DE", "FR", "AU", "CA"]


def _run(
    cmd: Sequence[str | Path],
    *,
    cwd: Path = SERVICE_ROOT,
    dry_run: bool = False,
    check: bool = False,
) -> int:
    cmd_str = " ".join(str(c) for c in cmd)
    if dry_run:
        logger.info(f"[DRY-RUN] {cmd_str}")
        return 0
    logger.info(f"[RUN] {cmd_str}")
    result = subprocess.run(
        [str(c) for c in cmd],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout:
        for line in result.stdout.splitlines():
            logger.info(f"  {line}")
    if result.stderr:
        for line in result.stderr.splitlines():
            logger.warning(f"  {line}")
    if check and result.returncode != 0:
        logger.error(f"Command failed with code {result.returncode}: {cmd_str}")
        raise SystemExit(result.returncode)
    return result.returncode


def _script(name: str) -> Path:
    return SERVICE_ROOT / "scripts" / name


def step_fetch_govdata(
    *,
    countries: list[str],
    targets: list[str] | None = None,
    dry_run: bool = False,
) -> None:
    """공공데이터포털 API 수집 (기본: ksure_buyer)."""
    api_key = os.getenv("API_KEY", "")
    if not api_key:
        logger.warning("API_KEY 환경변수가 없어 공공데이터 수집을 건 넘깁니다.")
        return

    script = _script("fetch_govdata_api.py")
    if not script.exists():
        logger.warning(f"{script} 가 없어 건 넘깁니다.")
        return

    targets = targets or ["ksure_buyer"]
    for target in targets:
        if target == "ksure_buyer":
            for country in countries:
                _run(
                    [PYTHON, script, "--target", target, "--country", country],
                    dry_run=dry_run,
                )
        else:
            _run([PYTHON, script, "--target", target], dry_run=dry_run)


def step_fetch_ksure(
    *,
    countries: list[str],
    output_dir: Path,
    dry_run: bool = False,
) -> None:
    """K-SURE API 바이어 검색 수집."""
    api_key = os.getenv("API_KEY", "")
    if not api_key:
        logger.warning("API_KEY 환경변수가 없어 K-SURE 수집을 건 넘깁니다.")
        return

    script = SERVICE_ROOT / "fetch_ksure_api.py"
    if not script.exists():
        logger.warning(f"{script} 가 없어 건 넘깁니다.")
        return

    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for country in countries:
        out_file = raw_dir / f"ksure_buyer_{country.lower()}.csv"
        _run(
            [
                PYTHON,
                script,
                "--ctry-cd",
                country,
                "--prod-nm",
                "cosmetics",
                "--output",
                out_file,
            ],
            dry_run=dry_run,
        )


def step_buykorea(
    *,
    input_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
) -> None:
    """buyKOREA / SNS 바이어 CSV 처리."""
    script = _script("fetch_buykorea_inquiry.py")
    if not script.exists():
        logger.warning(f"{script} 가 없어 건 넘깁니다.")
        return
    _run(
        [
            PYTHON,
            script,
            "--input_dir",
            input_dir,
            "--output_dir",
            output_dir,
        ],
        dry_run=dry_run,
    )


def step_sbc(
    *,
    sbc_input: Path | None,
    output_dir: Path,
    dry_run: bool = False,
) -> None:
    """SBC 화장품 데이터 필터링."""
    script = SERVICE_ROOT / "fetch_sbc_file.py"
    if not script.exists():
        logger.warning(f"{script} 가 없어 건 넘깁니다.")
        return
    if not sbc_input:
        logger.info("--sbc-input 미지정으로 SBC 처리를 건 넘깁니다.")
        return
    if not sbc_input.exists():
        logger.warning(f"SBC 입력 파일이 없습니다: {sbc_input}")
        return

    out_file = output_dir / "raw" / "sbc_cosmetics.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            PYTHON,
            script,
            "--input",
            sbc_input,
            "--output",
            out_file,
        ],
        dry_run=dry_run,
    )


def step_preprocess(
    *,
    input_dir: Path,
    output_dir: Path,
    sample_fallback: bool = False,
    dry_run: bool = False,
) -> None:
    """preprocess_cosmetics.py 실행."""
    script = SERVICE_ROOT / "preprocess_cosmetics.py"
    _run(
        (
            [PYTHON, script, "--input-dir", input_dir, "--output-dir", output_dir]
            + (["--sample-fallback"] if sample_fallback else [])
        ),
        dry_run=dry_run,
        check=True,
    )


def step_merge_p1_p2(*, dry_run: bool = False) -> None:
    """P1/P2 바이어·기회 소스 병합 (tools/merge_p1_p2_buyer_sources.py)."""
    script = PROJECT_ROOT / "tools" / "merge_p1_p2_buyer_sources.py"
    if not script.exists():
        logger.warning(f"{script} 가 없어 병합을 건 넘깁니다.")
        return
    _run([PYTHON, script], cwd=PROJECT_ROOT, dry_run=dry_run, check=True)


def step_enrich_contacts(*, dry_run: bool = False) -> None:
    """웹 기반 연락처 보강 (tools/enrich_buyer_contacts.py) — 선택."""
    script = PROJECT_ROOT / "tools" / "enrich_buyer_contacts.py"
    if not script.exists():
        logger.warning(f"{script} 가 없어 enrich를 건 넘깁니다.")
        return
    _run([PYTHON, script], cwd=PROJECT_ROOT, dry_run=dry_run, check=False)


def step_shortlist_clean(
    *,
    output_dir: Path,
    reference_date: str,
    dry_run: bool = False,
) -> None:
    """opportunity_item.csv 정제 (task05_shortlist.transform_opportunity_csv 직접 호출)."""
    in_file = output_dir / "opportunity_item.csv"
    out_file = output_dir / "opportunity_item_cleaned.csv"
    if not in_file.exists() and not dry_run:
        logger.warning(f"{in_file} 가 없어 정제를 건 넘깁니다.")
        return
    if dry_run:
        logger.info(f"[DRY-RUN] task05_shortlist.transform_opportunity_csv({in_file}, {out_file})")
        return

    # reference_date는 date 객체로 변환 (task05 날짜 비교용)
    ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()

    # task05_shortlist.py는 CLI보다 라이브러리 API가 주 사용 경로
    sys.path.insert(0, str(SERVICE_ROOT))
    try:
        from task05_shortlist import transform_opportunity_csv

        transform_opportunity_csv(
            input_path=in_file,
            output_path=out_file,
            reference_date=ref_date,
        )
        logger.info(f"정제 완료: {out_file}")
    except Exception as exc:
        logger.error(f"task05_shortlist 정제 실패: {exc}")
        raise
    finally:
        sys.path.pop(0)


def step_validate(
    *,
    output_dir: Path,
    reference_date: str,
    dry_run: bool = False,
) -> None:
    """산출물 품질 검증."""
    script = SERVICE_ROOT / "validate_cosmetics_outputs.py"
    if not script.exists():
        logger.warning(f"{script} 가 없어 검증을 건 넘깁니다.")
        return
    _run(
        [
            PYTHON,
            script,
            "--output-dir",
            output_dir,
            "--reference-date",
            reference_date,
        ],
        dry_run=dry_run,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="바이어 데이터 수집 → 정제 → 숏리스트 준비 파이프라인",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-dir", type=Path, default=SERVICE_ROOT / "input")
    parser.add_argument("--output-dir", type=Path, default=SERVICE_ROOT / "output")
    parser.add_argument(
        "--country-list",
        nargs="+",
        default=DEFAULT_COUNTRIES,
        help="공공데이터/K-SURE 수집 대상 국가 코드",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="API 기반 수집 단계 건 넘기기",
    )
    parser.add_argument(
        "--skip-buykorea",
        action="store_true",
        help="buyKOREA/SNS CSV 처리 건 넘기기",
    )
    parser.add_argument(
        "--skip-merge",
        action="store_true",
        help="P1/P2 소스 병합 건 넘기기",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="웹 연락처 보강(enrich_buyer_contacts.py) 실행",
    )
    parser.add_argument(
        "--sbc-input",
        type=Path,
        default=None,
        help="SBC 원본 CSV 경로 (미지정 시 SBC 단계 생략)",
    )
    parser.add_argument(
        "--reference-date",
        default=str(date.today()),
        help="기회 유효성 판단 기준일",
    )
    parser.add_argument(
        "--sample-fallback",
        action="store_true",
        help="input/ 에 파일이 없을 때 sample_input/ 을 사용 (개발/테스트용)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 실행 없이 수행할 명령만 출력",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="마지막에 validate_cosmetics_outputs.py 실행",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== 바이어 데이터 파이프라인 시작 ===")
    logger.info(f"input_dir={input_dir}")
    logger.info(f"output_dir={output_dir}")

    if not args.skip_fetch:
        step_fetch_govdata(countries=args.country_list, dry_run=args.dry_run)
        step_fetch_ksure(countries=args.country_list, output_dir=output_dir, dry_run=args.dry_run)

    if not args.skip_buykorea:
        step_buykorea(input_dir=input_dir, output_dir=output_dir, dry_run=args.dry_run)

    step_sbc(sbc_input=args.sbc_input, output_dir=output_dir, dry_run=args.dry_run)

    step_preprocess(
        input_dir=input_dir,
        output_dir=output_dir,
        sample_fallback=args.sample_fallback,
        dry_run=args.dry_run,
    )

    if not args.skip_merge:
        step_merge_p1_p2(dry_run=args.dry_run)

    if args.enrich:
        step_enrich_contacts(dry_run=args.dry_run)

    step_shortlist_clean(output_dir=output_dir, reference_date=args.reference_date, dry_run=args.dry_run)

    if args.validate:
        step_validate(output_dir=output_dir, reference_date=args.reference_date, dry_run=args.dry_run)

    logger.info("=== 바이어 데이터 파이프라인 완료 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
