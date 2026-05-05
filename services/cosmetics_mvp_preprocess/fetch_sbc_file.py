"""
중소벤처기업진흥공단_업종별 해외시장진출 유망상품 현황
파일 다운로드 및 화장품 업종 필터링 스크립트

사용법:
  1. 공공데이터포털(https://www.data.go.kr/data/15020678/fileData.do)에서 CSV 다운로드
  2. 다운로드한 파일을 sample_input/ 에 복사
     (예: sample_input/중소벤처기업진흥공단_업종별 해외시장진출 유망상품 현황_20260426.csv)
  3. python fetch_sbc_file.py --input <다운로드파일> --output sample_input/<필터링파일>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent

# 화장품 관련 업종/키워드 필터
COSMETICS_KEYWORDS = {
    "화장품", "cosmetic", "cosmetics", "makeup", "skin care", "skincare",
    "serum", "cream", "lotion", "ampoule", "mask", "maskpack", "sunscreen",
    "toner", "essence", "beauty", "k-beauty", "메이크업", "스킨케어", "세럼",
    "크림", "로션", "앰플", "마스크", "선크림", "토너", "에센스",
}


def is_cosmetics_row(row: pd.Series) -> bool:
    """행의 텍스트에서 화장품 관련 키워드가 포함되는지 검사"""
    text = " ".join(str(v).casefold() for v in row.values if pd.notna(v))
    return any(kw.casefold() in text for kw in COSMETICS_KEYWORDS)


def filter_cosmetics(df: pd.DataFrame) -> pd.DataFrame:
    """화장품 업종 행만 필터링"""
    mask = df.apply(is_cosmetics_row, axis=1)
    filtered = df[mask].copy()
    print(f"[FILTER] 전체 {len(df)}행 → 화장품 필터 {len(filtered)}행")
    return filtered


def normalize_for_output(df: pd.DataFrame) -> pd.DataFrame:
    """
    preprocess_cosmetics.py의 COMMON_OUTPUT_COLUMNS에 맞춰 기본 정규화
    실제 컬럼 매핑은 원본 CSV 컬럼 확인 후 수동 조정 필요
    """
    # 원본 컬럼명을 소문자로 변환하여 매핑 용이하게
    df = df.rename(columns=lambda x: str(x).strip())
    return df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="중진공 유망상품 화장품 필터링")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="원본 CSV 파일 경로 (공공데이터포털 다운로드)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "sample_input" / "중소벤처기업진흥공단_업종별 해외시장진출 유망상품 현황_20260426.csv",
        help="화장품 필터링 후 저장할 CSV 경로",
    )
    parser.add_argument(
        "--skip-filter",
        action="store_true",
        help="화장품 필터링 없이 전체 데이터를 그대로 복사",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if not args.input.exists():
        print(f"[ERROR] 입력 파일이 없습니다: {args.input}")
        print("[HINT] 공공데이터포털(https://www.data.go.kr/data/15020678/fileData.do)에서 CSV를 다운로드하세요.")
        return 1

    try:
        # 공공데이터포털 파일은 주로 cp949/euc-kr 인코딩
        df = pd.read_csv(args.input, dtype=str, keep_default_na=False, encoding="cp949")
    except UnicodeDecodeError:
        for enc in ("euc-kr", "utf-8-sig", "utf-8"):
            try:
                df = pd.read_csv(args.input, dtype=str, keep_default_na=False, encoding=enc)
                print(f"[INFO] 인코딩 감지: {enc}")
                break
            except UnicodeDecodeError:
                continue
        else:
            print("[ERROR] CSV 인코딩을 알 수 없습니다. (cp949/euc-kr/utf-8 시도 모두 실패)")
            return 1
    except Exception as exc:
        print(f"[ERROR] CSV 읽기 실패: {exc}")
        return 1

    print(f"[INFO] 원본 컬럼: {df.columns.tolist()}")
    print(f"[INFO] 원본 행수: {len(df)}")

    if args.skip_filter:
        result = df
    else:
        result = filter_cosmetics(df)

    result = normalize_for_output(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"[DONE] {args.output} 저장 완료 ({len(result)}행)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
