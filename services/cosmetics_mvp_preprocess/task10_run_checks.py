from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_REFERENCE_DATE = "2025-06-01"


@dataclass(frozen=True)
class CheckCommand:
    name: str
    command: list[str]


def run_check_command(check: CheckCommand, *, workdir: Path) -> dict[str, Any]:
    completed = subprocess.run(
        check.command,
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "name": check.name,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "passed": completed.returncode == 0,
        "command": check.command,
    }


def build_default_checks(*, reference_date: str, output_dir: Path) -> list[CheckCommand]:
    return [
        CheckCommand("pytest", [sys.executable, "-m", "pytest", "-q"]),
        CheckCommand("validate_outputs", [sys.executable, "validate_cosmetics_outputs.py"]),
        CheckCommand(
            "task07_api_demo",
            [
                sys.executable,
                "task07_shortlist_api.py",
                "--demo-request",
                "--output-dir",
                str(output_dir),
                "--reference-date",
                reference_date,
            ],
        ),
        CheckCommand(
            "task09_top20",
            [
                sys.executable,
                "task09_validate_top20.py",
                "--output-dir",
                str(output_dir),
                "--reference-date",
                reference_date,
            ],
        ),
    ]


def summarize_check_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [item for item in results if item["passed"]]
    failed = [item for item in results if not item["passed"]]
    return {
        "passed": len(failed) == 0,
        "passed_count": len(passed),
        "failed_count": len(failed),
        "failed_names": [item["name"] for item in failed],
    }


def run_all_checks(*, reference_date: str = DEFAULT_REFERENCE_DATE, output_dir: Path | None = None) -> dict[str, Any]:
    base_dir = output_dir or (ROOT / "output")
    results = [
        run_check_command(check, workdir=ROOT)
        for check in build_default_checks(reference_date=reference_date, output_dir=base_dir)
    ]
    return {
        "reference_date": reference_date,
        "output_dir": str(base_dir),
        "results": results,
        "summary": summarize_check_results(results),
    }


def _print_report(report: dict[str, Any]) -> None:
    encoding = sys.stdout.encoding or "utf-8"

    def safe_print(text: str) -> None:
        sys.stdout.buffer.write((text + "\n").encode(encoding, errors="replace"))

    print("[task10] reference_date =", report["reference_date"])
    print("[task10] output_dir =", report["output_dir"])
    for result in report["results"]:
        print(
            f"[task10] {result['name']} "
            f"status={'PASS' if result['passed'] else 'FAIL'} "
            f"returncode={result['returncode']}"
        )
        if result["stdout"]:
            safe_print(result["stdout"])
        if result["stderr"]:
            safe_print(result["stderr"])
    print("[task10] summary =", report["summary"])


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TASK-10 로그/테스트 자동화")
    parser.add_argument("--reference-date", type=str, default=DEFAULT_REFERENCE_DATE, help="검증 기준일")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output", help="output CSV 폴더")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = run_all_checks(reference_date=args.reference_date, output_dir=args.output_dir)
    _print_report(report)
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
