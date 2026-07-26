"""P2 드롭인 폴더 상태 — 허용 소스 파일 존재 여부만 보고, 스크래핑/가상 데이터 없음."""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
P2_DIR = ROOT / "services" / "cosmetics_mvp_preprocess" / "input" / "p2_optional"

# 체크리스트와 동일 키 — 파일이 있으면 drop-in 가능, 없으면 ACCESS_GATED
P2_EXPECTED = (
    ("tradekorea", "tradekorea.csv", "TradeKorea"),
    ("kita", "kita.csv", "KITA"),
    ("kotra_trade_office", "kotra_trade_office.csv", "KOTRA 무역관 리스트"),
)


def get_p2_dropin_status() -> dict[str, Any]:
    items = []
    for key, filename, label in P2_EXPECTED:
        path = P2_DIR / filename
        example = P2_DIR / f"{filename}.example"
        items.append(
            {
                "key": key,
                "label": label,
                "filename": filename,
                "path": str(path.relative_to(ROOT)) if path.exists() or True else filename,
                "present": path.is_file() and path.stat().st_size > 0,
                "example_present": example.is_file(),
                "status": "READY_TO_MERGE" if path.is_file() and path.stat().st_size > 0 else "ACCESS_GATED",
            }
        )
    ready = sum(1 for item in items if item["present"])
    return {
        "folder": str(P2_DIR.relative_to(ROOT)),
        "ready_count": ready,
        "total": len(items),
        "merge_command": "python3 tools/merge_p1_p2_buyer_sources.py",
        "items": items,
        "note": "회원·무역관 수령 CSV만 드롭인. 스크래핑·미확인 무료 덤프 금지(L002).",
    }
