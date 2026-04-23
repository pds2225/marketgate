from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task10_run_checks import CheckCommand, run_check_command, summarize_check_results  # noqa: E402


def test_run_check_command_captures_success() -> None:
    result = run_check_command(
        CheckCommand("echo", [sys.executable, "-c", "print('ok')"]),
        workdir=ROOT,
    )

    assert result["passed"] is True
    assert result["stdout"] == "ok"


def test_summarize_check_results_detects_failure() -> None:
    summary = summarize_check_results(
        [
            {"name": "a", "passed": True},
            {"name": "b", "passed": False},
        ]
    )

    assert summary["passed"] is False
    assert summary["failed_names"] == ["b"]
