#!/usr/bin/env python3
"""
Auto Cosmetics Filter
- 입력: services/cosmetics_mvp_preprocess/output/raw/*.csv
- 출력: services/cosmetics_mvp_preprocess/output/COS_combined_YYYYMMDD.csv
- 동작: 모든 raw CSV를 읽어 화장품 키워드로 필터링 후 통합 저장
"""

import glob
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# 설정
RAW_DIR = Path("services/cosmetics_mvp_preprocess/output/raw")
OUTPUT_DIR = Path("services/cosmetics_mvp_preprocess/output")

# 화장품 키워드 (영문 + 한글)
COSMETICS_KEYWORDS = [
    'cosmetic', 'cosmetics', 'beauty', 'makeup', 'skincare', 'skin care',
    'lipstick', 'lip', 'mascara', 'eyeliner', 'foundation', 'concealer',
    'cream', 'lotion', 'serum', 'essence', 'toner', 'cleanser', 'moisturizer',
    'perfume', 'fragrance', 'cologne', 'deodorant',
    'shampoo', 'conditioner', 'hair', 'scalp',
    'sunscreen', 'spf', 'uv', 'suncare',
    'mask', 'maskpack', 'sheet mask', 'face mask',
    'peeling', 'peel', 'scrub', 'exfoliat',
    'botox', 'filler', 'beauty device', 'derma',
    'essential oil', 'aroma', 'aromatherapy',
    'nail', 'manicure', 'pedicure',
    'body', 'hand cream', 'foot cream', 'body lotion',
    '화장품', '미용', '뷰티', '메이크업', '스킨케어',
    '립스틱', '립', '마스카라', '아이라이너', '파운데이션',
    '크림', '로션', '세럼', '에센스', '토너', '클렌저',
    '향수', '오 드 퍼퓸', '오 드 뚜왈렛',
    '선크림', '자외선', '썬케어', 'spf',
    '마스크팩', '마스크', '필링', '스크럽',
    '보톡스', '필러', '미용기기', '더마',
    '네일', '매니큐어', '페디큐어',
    '바디', '핸드크림', '풋크림',
    '헤어', '샴푸', '린스', '탈모',
    'health & beauty', '건강 및 미용',
]


def is_cosmetics(text: str) -> bool:
    """텍스트가 화장품 관련인지 확인"""
    if pd.isna(text) or not isinstance(text, str):
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in COSMETICS_KEYWORDS)


def standardize_columns(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    """다양한 컬럼명을 통합 스키마로 변환"""
    
    # 컬럼명 매핑 (소문자로 변환 후 매칭)
    col_map = {
        '기업명': 'normalized_name',
        'company_name': 'normalized_name',
        'buyer_name': 'normalized_name',
        '기업명(영어)': 'normalized_name',
        '영어기업명': 'normalized_name',
        '업체명': 'normalized_name',
        '바이어명': 'normalized_name',
        '국가': 'country_raw',
        '국가명': 'country_raw',
        'natn_nm': 'country_raw',
        'country': 'country_raw',
        'nation': 'country_raw',
        'nationname': 'country_raw',
        '도시명': 'city',
        'city': 'city',
        '품목명': 'title',
        'item_name': 'title',
        'product_name': 'title',
        'item': 'title',
        '상품명': 'title',
        '관심상품': 'title',
        '관심상품내용': 'title',
        '한글상품명': 'title',
        '영어상품명': 'title',
        '제목': 'title',
        'subject': 'title',
        'hs코드': 'hs_code_raw',
        'hs_code': 'hs_code_raw',
        'hscd': 'hs_code_raw',
        'hs': 'hs_code_raw',
        '키워드': 'keywords_raw',
        'keywords': 'keywords_raw',
        'keyword': 'keywords_raw',
        '이메일': 'contact_email',
        'email': 'contact_email',
        '전화번호': 'contact_phone',
        'phone': 'contact_phone',
        'tel': 'contact_phone',
        '홈페이지': 'contact_website',
        'website': 'contact_website',
        'homepage': 'contact_website',
        '웹사이트': 'contact_website',
        'url': 'contact_website',
    }
    
    # 소문자 컬럼명으로 변환 후 매핑
    lower_cols = {c.lower(): c for c in df.columns}
    new_cols = {}
    
    for lower_name, original_col in lower_cols.items():
        if lower_name in col_map:
            new_cols[original_col] = col_map[lower_name]
    
    df = df.rename(columns=new_cols)
    
    # 통합 스키마 컬럼 추가 (없는 경우 빈값)
    schema_cols = [
        'record_type', 'source_dataset', 'source_file', 'source_row_no',
        'title', 'normalized_name', 'country_raw', 'country_norm', 'country_iso3',
        'hs_code_raw', 'hs_code_norm', 'keywords_raw', 'keywords_norm',
        'has_contact', 'contact_name', 'contact_email', 'contact_phone',
        'contact_website', 'valid_until'
    ]
    
    for col in schema_cols:
        if col not in df.columns:
            df[col] = ''
    
    # 메타데이터 설정
    df['record_type'] = 'buyer_candidate'
    df['source_file'] = Path(filename).name
    df['source_row_no'] = range(1, len(df) + 1)
    
    # keywords_norm 생성
    if 'keywords_raw' in df.columns:
        df['keywords_norm'] = df['keywords_raw'].astype(str).str.lower()
    
    return df[schema_cols]


def filter_cosmetics(df: pd.DataFrame) -> pd.DataFrame:
    """화장품 관련 데이터만 필터링"""
    # 검색할 텍스트 컬럼
    text_cols = ['title', 'keywords_raw', 'normalized_name']
    available_cols = [c for c in text_cols if c in df.columns]
    
    if not available_cols:
        return pd.DataFrame()
    
    # 화장품 여부 판별
    mask = pd.Series(False, index=df.index)
    for col in available_cols:
        mask |= df[col].astype(str).apply(is_cosmetics)
    
    # HS코드 33장도 포함
    if 'hs_code_raw' in df.columns:
        hs_mask = df['hs_code_raw'].astype(str).str.startswith(
            ('3303', '3304', '3305', '3306', '3307'), na=False
        )
        mask |= hs_mask
    
    return df[mask].copy()


def process_all_raw_files():
    """raw 폴더의 모든 CSV를 처리하여 통합 화장품 파일 생성"""
    
    raw_files = sorted(RAW_DIR.glob("*.csv"))
    
    if not raw_files:
        print("[INFO] No CSV files in raw/ folder")
        sys.exit(0)
    
    print(f"[INFO] Found {len(raw_files)} raw files:")
    for f in raw_files:
        print(f"  - {f.name}")
    
    all_cosmetics = []
    
    for csv_file in raw_files:
        try:
            # 인코딩 자동 감지
            for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
                try:
                    df = pd.read_csv(csv_file, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                print(f"[WARN] Failed to decode {csv_file.name}")
                continue
            
            print(f"[INFO] Processing {csv_file.name}: {len(df)} rows")
            
            # 컬럼 통일
            df_std = standardize_columns(df, csv_file.name)
            
            # 화장품 필터링
            df_cos = filter_cosmetics(df_std)
            
            if len(df_cos) > 0:
                all_cosmetics.append(df_cos)
                print(f"  → Cosmetics: {len(df_cos)} rows")
            else:
                print(f"  → No cosmetics found")
                
        except Exception as e:
            print(f"[ERROR] {csv_file.name}: {e}")
            continue
    
    if not all_cosmetics:
        print("[INFO] No cosmetics data found in any file")
        sys.exit(0)
    
    # 통합
    df_merged = pd.concat(all_cosmetics, ignore_index=True)
    
    # 중복 제거 (기업명 + 국가)
    before = len(df_merged)
    df_merged = df_merged.drop_duplicates(
        subset=['normalized_name', 'country_raw'], 
        keep='first'
    )
    after = len(df_merged)
    
    # 출력 파일명
    today = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"COS_combined_{today}.csv"
    
    # 저장
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n{'='*50}")
    print(f"[DONE] Combined cosmetics data saved:")
    print(f"  File: {output_file}")
    print(f"  Total cosmetics: {after} rows (deduped from {before})")
    print(f"  Source files: {len(all_cosmetics)}")
    print(f"{'='*50}")
    
    # GitHub Actions용 출력
    print(f"::set-output name=cosmetics_count::{after}")
    print(f"::set-output name=output_file::{output_file}")


if __name__ == "__main__":
    process_all_raw_files()
