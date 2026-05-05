"""
buyKOREA 인콰이어리(RFQ) 데이터 수집
- 대한무역투자진흥공사_인콰이어리 정보 (data.go.kr/data/15155499)
- 대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보 (data.go.kr/data/15155497)

수집 방법:
  1. 공공데이터포털에서 파일 데이터 직접 다운로드
  2. 화장품 관련 인콰이어리 필터링
  3. buyer_candidate.csv 통합 스키마로 변환

사용법:
  python fetch_buykorea_inquiry.py --input_dir ./input --output_dir ./output
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("buykorea_inquiry")

# 화장품 키워드 필터
COSMETICS_KEYWORDS = [
    "cosmetic", "cosmetics", "makeup", "skin care", "skincare",
    "serum", "cream", "lotion", "ampoule", "mask", "maskpack",
    "sunscreen", "sun care", "toner", "essence", "beauty",
    "페이셜", "세럼", "크림", "로션", "앰플", "마스크",
    "선크림", "토너", "에센스", "스킨케어", "화장품", "메이크업", "미용"
]

HS_COSMETICS = ["3304", "3303", "3307", "330499"]  # 화장품 HS 코드


def is_cosmetics_related(text: str) -> bool:
    """화장품 관련 인콰이어리 여부 확인"""
    if not text:
        return False
    text_lower = str(text).lower()
    return any(kw.lower() in text_lower for kw in COSMETICS_KEYWORDS)


def load_inquiry_csv(file_path: Path) -> pd.DataFrame:
    """인콰이어리 CSV 로드 (인코딩 자동 감지)"""
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            logger.info(f"  로드 완료: {file_path.name} ({enc}, {len(df)}행)")
            return df
        except Exception:
            continue

    raise ValueError(f"CSV 로드 실패: {file_path}")


def filter_cosmetics_inquiry(df: pd.DataFrame, text_columns: list[str]) -> pd.DataFrame:
    """화장품 관련 인콰이어리 필터링"""
    if df.empty:
        return df

    # 검색할 텍스트 컬럼 결정
    available_cols = [c for c in text_columns if c in df.columns]
    if not available_cols:
        logger.warning("  필터링할 텍스트 컬럼이 없습니다")
        return df

    # 화장품 관련 여부 확인
    mask = pd.Series(False, index=df.index)
    for col in available_cols:
        mask |= df[col].astype(str).apply(is_cosmetics_related)

    filtered = df[mask].copy()
    logger.info(f"  화장품 필터링: {len(df)} → {len(filtered)}건")
    return filtered


def transform_to_buyer_candidate(
    df: pd.DataFrame, 
    source_name: str,
    column_mapping: dict[str, str]
) -> pd.DataFrame:
    """
    buyer_candidate.csv 통합 스키마로 변환

    Args:
        df: 원본 데이터프레임
        source_name: 데이터셋명 (예: "buyKOREA_인콰이어리")
        column_mapping: {원본컬럼: 타겟컬럼} 매핑
    """
    result = pd.DataFrame()

    # 기본 메타데이터
    result["record_type"] = "buyer_candidate"
    result["source_dataset"] = source_name
    result["source_file"] = source_name
    result["source_row_no"] = range(1, len(df) + 1)

    # 매핑된 컬럼 복사
    for src_col, tgt_col in column_mapping.items():
        if src_col in df.columns:
            result[tgt_col] = df[src_col]
        else:
            result[tgt_col] = ""

    # 연락처 정보 통합
    result["has_contact"] = ""
    result["contact_name"] = ""
    result["contact_email"] = ""
    result["contact_phone"] = ""
    result["contact_website"] = ""
    result["valid_until"] = ""

    return result


def process_buykorea_inquiry(input_file: Path, output_dir: Path):
    """buyKOREA 인콰이어리 처리"""
    logger.info(f"=== buyKOREA 인콰이어리 처리 ===")
    logger.info(f"  Input: {input_file}")

    # 1. 로드
    df = load_inquiry_csv(input_file)

    # 2. 화장품 필터링 (제목, 내용, 품목 컬럼 검색)
    text_cols = ["title", "subject", "content", "item_name", "product_name", 
                 "인콰이어리제목", "관심상품내용", "요약", "문의제목"]
    df_filtered = filter_cosmetics_inquiry(df, text_cols)

    # 3. 통합 스키마로 변환
    column_mapping = {
        # buyKOREA 인콰이어리 컬럼 → 통합 스키마 컬럼
        "title": "title",
        "subject": "title", 
        "company_name": "normalized_name",
        "buyer_name": "normalized_name",
        "country": "country_raw",
        "country_name": "country_raw",
        "item_name": "keywords_raw",
        "product_name": "keywords_raw",
        "email": "contact_email",
        "phone": "contact_phone",
        "website": "contact_website",
        "inquiry_date": "valid_until",
    }

    df_transformed = transform_to_buyer_candidate(
        df_filtered, "buyKOREA_인콰이어리", column_mapping
    )

    # 4. 저장
    output_file = output_dir / "buykorea_inquiry_cosmetics.csv"
    df_transformed.to_csv(output_file, index=False, encoding="utf-8-sig")
    logger.info(f"  Output: {output_file} ({len(df_transformed)}행)")

    return df_transformed


def process_sns_buyer(input_file: Path, output_dir: Path):
    """SNS 마케팅 수집 바이어 처리"""
    logger.info(f"=== SNS 마케팅 수집 바이어 처리 ===")
    logger.info(f"  Input: {input_file}")

    # 1. 로드
    df = load_inquiry_csv(input_file)

    # 2. 화장품 필터링
    text_cols = ["title", "subject", "content", "item_name", "product_name",
                 "keywords", "관심품목", "관심상품"]
    df_filtered = filter_cosmetics_inquiry(df, text_cols)

    # 3. 통합 스키마로 변환
    column_mapping = {
        "title": "title",
        "company_name": "normalized_name",
        "buyer_name": "normalized_name", 
        "country": "country_raw",
        "country_name": "country_raw",
        "item_name": "keywords_raw",
        "keywords": "keywords_raw",
        "email": "contact_email",
        "phone": "contact_phone",
        "website": "contact_website",
        "collect_date": "valid_until",
    }

    df_transformed = transform_to_buyer_candidate(
        df_filtered, "SNS_마케팅_바이어", column_mapping
    )

    # 4. 저장
    output_file = output_dir / "sns_buyer_cosmetics.csv"
    df_transformed.to_csv(output_file, index=False, encoding="utf-8-sig")
    logger.info(f"  Output: {output_file} ({len(df_transformed)}행)")

    return df_transformed


def merge_with_buyer_candidate(
    new_dfs: list[pd.DataFrame],
    existing_file: Path,
    output_file: Path
):
    """기존 buyer_candidate.csv와 병합"""
    logger.info(f"=== buyer_candidate.csv 병합 ===")

    # 기존 파일 로드
    if existing_file.exists():
        existing = pd.read_csv(existing_file, encoding="utf-8-sig")
        logger.info(f"  기존: {len(existing)}행")
    else:
        existing = pd.DataFrame()
        logger.info(f"  기존 파일 없음, 신규 생성")

    # 새 데이터 병합
    all_dfs = [existing] + new_dfs if not existing.empty else new_dfs
    merged = pd.concat(all_dfs, ignore_index=True)

    # 중복 제거 (normalized_name + country_raw 기준)
    before_dedup = len(merged)
    merged = merged.drop_duplicates(subset=["normalized_name", "country_raw"], keep="first")
    after_dedup = len(merged)

    logger.info(f"  병합: {before_dedup} → {after_dedup}건 (중복 제거: {before_dedup - after_dedup})")

    # 저장
    merged.to_csv(output_file, index=False, encoding="utf-8-sig")
    logger.info(f"  Output: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="buyKOREA 인콰이어리 수집")
    parser.add_argument("--input_dir", default="./input", help="원본 데이터 디렉토리")
    parser.add_argument("--output_dir", default="./output", help="출력 디렉토리")
    parser.add_argument("--buyer_candidate", default="", help="기존 buyer_candidate.csv 경로")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    new_dfs = []

    # 1. buyKOREA 인콰이어리 처리
    buykorea_file = input_dir / "대한무역투자진흥공사_인콰이어리 정보_20251127.csv"
    if buykorea_file.exists():
        df = process_buykorea_inquiry(buykorea_file, output_dir)
        new_dfs.append(df)
    else:
        logger.warning(f"파일 없음: {buykorea_file}")
        logger.info("  공공데이터포털에서 다운로드 필요:")
        logger.info("  https://www.data.go.kr/data/15155499/fileData.do")

    # 2. SNS 마케팅 바이어 처리
    sns_file = input_dir / "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보_20251127.csv"
    if sns_file.exists():
        df = process_sns_buyer(sns_file, output_dir)
        new_dfs.append(df)
    else:
        logger.warning(f"파일 없음: {sns_file}")
        logger.info("  공공데이터포털에서 다운로드 필요:")
        logger.info("  https://www.data.go.kr/data/15155497/fileData.do")

    # 3. 기존 buyer_candidate와 병합
    if new_dfs and args.buyer_candidate:
        existing_file = Path(args.buyer_candidate)
        output_file = output_dir / "buyer_candidate_merged.csv"
        merge_with_buyer_candidate(new_dfs, existing_file, output_file)

    logger.info("\n=== 완료 ===")
    logger.info("다음 단계:")
    logger.info("1. 공공데이터포털에서 인콰이어리 파일 다운로드")
    logger.info("2. python fetch_buykorea_inquiry.py --input_dir ./input --output_dir ./output")
    logger.info("3. buyer_candidate.csv와 병합하여 통합 바이어 리스트 생성")


if __name__ == "__main__":
    main()
