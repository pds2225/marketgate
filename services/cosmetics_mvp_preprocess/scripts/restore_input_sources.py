"""아카이브 폴더의 원본 CSV를 cosmetics input/ 으로 복원.

사용:
    python scripts/restore_input_sources.py
    python scripts/restore_input_sources.py --archive D:/marketgate/00_관련자료_모음/05_데이터_시장자료
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE = Path("D:/marketgate/00_관련자료_모음/05_데이터_시장자료")

MAPPING = {
    "한국무역보험공사_화장품 바이어 정보_20200812.csv": "한국무역보험공사_화장품 바이어 정보_20200812.csv",
    "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보_20251127": "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보_20251127.csv",
    "대한무역투자진흥공사_인콰이어리 정보_20251127.csv": "대한무역투자진흥공사_인콰이어리 정보_20251127.csv",
    "중소벤처기업진흥공단_해외바이어 인콰이어리 신청_20241230.csv": "중소벤처기업진흥공단_해외바이어 인콰이어리 신청_20241230.csv",
    "중소벤처기업진흥공단_해외바이어 구매오퍼 정보_20241231.csv": "중소벤처기업진흥공단_해외바이어 구매오퍼 정보_20241231.csv",
    "중소벤처기업진흥공단_업종별 해외시장진출 유망상품 현황": "중소벤처기업진흥공단_업종별 해외시장진출 유망상품 현황.csv",
    "kotra_export_recommend_all.csv": "kotra_export_recommend_all.csv",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--input-dir", type=Path, default=SERVICE_ROOT / "input")
    args = parser.parse_args(argv)

    if not args.archive.exists():
        print("MISSING archive", args.archive)
        return 1

    args.input_dir.mkdir(parents=True, exist_ok=True)
    missing = 0
    for needle, dest_name in MAPPING.items():
        matches = [f for f in args.archive.glob("*.csv") if needle in f.name]
        if not matches:
            print("MISSING", needle)
            missing += 1
            continue
        src = matches[0]
        dest = args.input_dir / dest_name
        shutil.copy2(src, dest)
        print("copied", src.name, "->", dest, "size", dest.stat().st_size)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
