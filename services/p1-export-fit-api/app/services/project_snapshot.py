from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[4]


def _run_git(args: list[str], cwd: Path) -> Optional[str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    return completed.stdout.strip()


def build_project_snapshot(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT).resolve()
    is_git_repo = _run_git(["rev-parse", "--is-inside-work-tree"], root) == "true"

    if not is_git_repo:
        return {
            "repo_root": str(root),
            "is_git_repo": False,
            "status_key": "non-git",
            "status_label": "Git 저장소 아님",
            "branch": None,
            "head": None,
            "remote": None,
            "dirty": None,
            "status_text": "Git 저장소가 아닙니다.",
        }

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root) or "unknown"
    head = _run_git(["rev-parse", "--short", "HEAD"], root) or "unknown"
    remote = _run_git(["remote", "get-url", "origin"], root)
    dirty = bool(_run_git(["status", "--porcelain"], root))

    if dirty:
        status_key = "dirty"
        status_label = "변경 사항 있음"
    elif remote:
        status_key = "clean"
        status_label = "정상"
    else:
        status_key = "remote-missing"
        status_label = "remote 없음"

    status_text = " / ".join(
        [
            f"branch={branch}",
            f"HEAD={head}",
            f"remote={remote or '없음'}",
            f"dirty={'yes' if dirty else 'no'}",
        ]
    )
    if not remote:
        status_text += " / remote 없음"

    return {
        "repo_root": str(root),
        "is_git_repo": True,
        "status_key": status_key,
        "status_label": status_label,
        "branch": branch,
        "head": head,
        "remote": remote,
        "dirty": dirty,
        "status_text": status_text,
    }
