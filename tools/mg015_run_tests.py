"""Run MG-015 backend suites with local-only sockets and worktree-local artifacts.

Use --baseline to execute the changed modules from 09ae2f7, excluding the new
performance tests that intentionally require the optimized implementation.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import secrets
import sys
import time

from mg015_predict_benchmark import BaselineLoader, ROOT


def local_sockets_only(event, args):
    if event not in {"socket.connect", "socket.getaddrinfo"}:
        return
    host = args[1][0] if event == "socket.connect" else args[0]
    if str(host) == "localhost":
        return
    try:
        if ipaddress.ip_address(str(host)).is_loopback:
            return
    except ValueError:
        pass
    raise RuntimeError("MG-015 tests block outbound network connections")


def main() -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("suite", choices=["api", "preprocess"])
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    label = f"resume-{args.suite}-{'before' if args.baseline else 'after'}"
    state = ROOT / "tools/.mg015"
    state.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        APP_ENV="test", DATABASE_URL="", PYTHONUTF8="1",
        PYTHONDONTWRITEBYTECODE="1", TEMP=str(state), TMP=str(state),
        TOSS_SECRET_KEY="", JWT_SECRET=secrets.token_hex(32),
    )
    sys.dont_write_bytecode = True
    sys.addaudithook(local_sockets_only)
    if args.baseline:
        sys.meta_path.insert(0, BaselineLoader())
    directory = ROOT / "services" / (
        "p1-export-fit-api" if args.suite == "api" else "cosmetics_mvp_preprocess"
    )
    os.chdir(directory)
    sys.path.insert(0, str(directory))
    import pytest

    command = [
        "tests", "-q", "-ra", "-p", "no:cacheprovider",
        "--basetemp", str(state / f"{label}-{time.time_ns()}-tmp"),
        "--junitxml", str(state / f"{label}.xml"),
    ]
    if args.baseline:
        command += ["--ignore", "tests/test_predict_performance.py" if args.suite == "api"
                    else "tests/test_keyword_performance.py"]
    return int(pytest.main(command))


if __name__ == "__main__":
    raise SystemExit(main())
