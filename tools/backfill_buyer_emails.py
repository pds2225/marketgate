#!/usr/bin/env python3
"""빈 contact_email만 채우는 안전 backfill (스크래핑/merge 미수정).

우선순위:
  1) --snapshot CSV (기본: git HEAD의 buyer_candidate.csv — 이메일이 있던 스냅샷)
  2) input/p2_optional/*.csv 드롭인 (회원 수령분, 스키마는 example 헤더)

규칙:
  - 이미 이메일이 있으면 덮어쓰지 않음
  - 스냅샷 매칭은 normalized_name(+country_norm) 키
  - P2는 contact_email이 있는 행만 사용
  - 웹 스크래핑/Hunter 호출 없음 (Codex·네트워크 충돌·정책 회피)

사용:
  python tools/backfill_buyer_emails.py --dry-run
  python tools/backfill_buyer_emails.py
  python tools/backfill_buyer_emails.py --snapshot path/to/old_buyer_candidate.csv
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BUYER_CSV = ROOT / "services" / "cosmetics_mvp_preprocess" / "output" / "buyer_candidate.csv"
P2_DIR = ROOT / "services" / "cosmetics_mvp_preprocess" / "input" / "p2_optional"
REPORT_PATH = ROOT / "tools" / "reports" / "buyer_email_backfill_report.json"
GIT_SNAPSHOT_PATH = "services/cosmetics_mvp_preprocess/output/buyer_candidate.csv"


def _clean(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _has_email(value: Any) -> bool:
    return "@" in _clean(value)


def _norm_key(name: Any, country: Any = "") -> str:
    n = "".join(ch for ch in _clean(name).casefold() if ch.isalnum())
    c = _clean(country).casefold()
    return f"{n}|{c}" if n else ""


def _load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", low_memory=False)


def _load_git_snapshot(rev: str = "HEAD") -> pd.DataFrame | None:
    try:
        raw = subprocess.check_output(
            ["git", "show", f"{rev}:{GIT_SNAPSHOT_PATH}"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    from io import BytesIO

    return pd.read_csv(BytesIO(raw), dtype=str, encoding="utf-8-sig", low_memory=False)


def _email_map_from_frame(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    """key -> {email, phone, website, name, source}"""
    out: dict[str, dict[str, str]] = {}
    if df is None or df.empty:
        return out
    for _, row in df.iterrows():
        email = _clean(row.get("contact_email"))
        if not _has_email(email):
            continue
        name = row.get("normalized_name") or row.get("title")
        country = row.get("country_norm") or row.get("country_raw")
        key = _norm_key(name, country)
        key2 = _norm_key(name, "")
        payload = {
            "email": email,
            "phone": _clean(row.get("contact_phone")),
            "website": _clean(row.get("contact_website")),
            "contact_name": _clean(row.get("contact_name")),
            "source": _clean(row.get("source_dataset")) or "snapshot",
        }
        if key and key not in out:
            out[key] = payload
        if key2 and key2 not in out:
            out[key2] = payload
    return out


def _load_p2_maps() -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    status: list[dict[str, Any]] = []
    merged: dict[str, dict[str, str]] = {}
    if not P2_DIR.exists():
        return merged, status
    for path in sorted(P2_DIR.glob("*.csv")):
        if path.name.endswith(".example.csv") or ".example." in path.name:
            continue
        try:
            df = _load_csv(path)
        except Exception as exc:  # noqa: BLE001
            status.append({"file": path.name, "status": "ERROR", "error": str(exc)})
            continue
        m = _email_map_from_frame(df)
        for k, v in m.items():
            if k not in merged:
                merged[k] = {**v, "source": f"p2:{path.name}"}
        status.append({"file": path.name, "status": "LOADED", "email_keys": len(m)})
    return merged, status


def backfill(
    buyer: pd.DataFrame,
    maps: list[tuple[str, dict[str, dict[str, str]]]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = buyer.copy()
    for col in ("contact_email", "contact_phone", "contact_website", "contact_name", "has_contact"):
        if col not in df.columns:
            df[col] = ""

    filled = 0
    by_source: dict[str, int] = {}
    for idx, row in df.iterrows():
        if _has_email(row.get("contact_email")):
            continue
        name = row.get("normalized_name") or row.get("title")
        country = row.get("country_norm") or row.get("country_raw")
        keys = [_norm_key(name, country), _norm_key(name, "")]
        hit = None
        hit_origin = ""
        for origin, mp in maps:
            for k in keys:
                if k and k in mp:
                    hit = mp[k]
                    hit_origin = origin
                    break
            if hit:
                break
        if not hit:
            continue
        df.at[idx, "contact_email"] = hit["email"]
        if not _clean(row.get("contact_phone")) and hit.get("phone"):
            df.at[idx, "contact_phone"] = hit["phone"]
        if not _clean(row.get("contact_website")) and hit.get("website"):
            df.at[idx, "contact_website"] = hit["website"]
        if not _clean(row.get("contact_name")) and hit.get("contact_name"):
            df.at[idx, "contact_name"] = hit["contact_name"]
        df.at[idx, "has_contact"] = "True"
        # 스냅샷/P2는 원본 연락처로 보고 estimated=False
        if "contact_email_estimated" in df.columns:
            df.at[idx, "contact_email_estimated"] = "False"
        filled += 1
        by_source[hit_origin] = by_source.get(hit_origin, 0) + 1

    before_email = int(buyer["contact_email"].map(_has_email).sum()) if "contact_email" in buyer.columns else 0
    after_email = int(df["contact_email"].map(_has_email).sum())
    stats = {
        "rows": int(len(df)),
        "filled": filled,
        "with_email_before": before_email,
        "with_email_after": after_email,
        "by_source": by_source,
    }
    return df, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buyer", type=Path, default=BUYER_CSV)
    parser.add_argument("--snapshot", type=Path, default=None, help="이메일 소스 CSV (미지정 시 git HEAD)")
    parser.add_argument("--git-rev", default="HEAD", help="--snapshot 없을 때 git show 리비전")
    parser.add_argument("--skip-p2", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)

    if not args.buyer.exists():
        print("MISSING buyer", args.buyer)
        return 1

    buyer = _load_csv(args.buyer)
    maps: list[tuple[str, dict[str, dict[str, str]]]] = []

    if args.snapshot:
        snap = _load_csv(args.snapshot)
        maps.append(("snapshot_file", _email_map_from_frame(snap)))
        snap_meta = {"mode": "file", "path": str(args.snapshot), "rows": len(snap)}
    else:
        snap = _load_git_snapshot(args.git_rev)
        if snap is None:
            print("WARN: git snapshot unavailable; continuing with P2 only")
            snap_meta = {"mode": "git", "rev": args.git_rev, "rows": 0}
        else:
            maps.append(("git_snapshot", _email_map_from_frame(snap)))
            snap_meta = {"mode": "git", "rev": args.git_rev, "rows": len(snap)}

    p2_status: list[dict[str, Any]] = []
    if not args.skip_p2:
        p2_map, p2_status = _load_p2_maps()
        if p2_map:
            maps.append(("p2_optional", p2_map))

    out, stats = backfill(buyer, maps)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "buyer_path": str(args.buyer),
        "snapshot": snap_meta,
        "p2": p2_status,
        "stats": stats,
        "dry_run": bool(args.dry_run),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.dry_run:
        print("dry-run: buyer CSV not written")
        return 0

    out.to_csv(args.buyer, index=False, encoding="utf-8-sig")
    print("wrote", args.buyer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
