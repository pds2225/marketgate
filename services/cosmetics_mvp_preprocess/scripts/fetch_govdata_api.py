"""
공공데이터포털 API 데이터 수집 파이프라인
marketgate 프로젝트용

사용법:
  1. .env 파일에 API_KEY=your_key 입력
  2. python fetch_govdata_api.py --target all
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("govdata_api")

# 환경 변수 로드
load_dotenv()
API_KEY = os.getenv("API_KEY", "")

# 출력 디렉토리
OUTPUT_DIR = Path("services/cosmetics_mvp_preprocess/input")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# API 설정
API_CONFIGS = {
    # 1. 한국무역보험공사_바이어 검색 (반영완료 - 추가 수집용)
    "ksure_buyer": {
        "name": "한국무역보험공사_바이어 검색",
        "endpoint": "https://apis.data.go.kr/B552696/buyer/getBuyerList",
        "method": "GET",
        "params": {
            "serviceKey": API_KEY,
            "pageNo": 1,
            "numOfRows": 100,
            "resultType": "json",
            # 필수: country (국가코드: US, CN, JP 등)
            # 선택: itemName, buyerName, hsCode, industry
        },
        "required_params": ["country"],  # 국가코드 필수
        "output_file": "한국무역보험공사_바이어 검색_20260430.csv",
    },

    # 2. KOTRA 국가정보 (미반영)
    "kotra_country": {
        "name": "대한무역투자진흥공사_국가정보",
        "endpoint": "https://apis.data.go.kr/B490001/cntrktInfoService/cntrktInfoList",
        "method": "GET", 
        "params": {
            "serviceKey": API_KEY,
            "pageNo": 1,
            "numOfRows": 100,
            "returnType": "JSON",
        },
        "output_file": "대한무역투자진흥공사_국가정보_20260430.csv",
    },

    # 3. KOTRA 해외시장뉴스 (미반영)
    "kotra_news": {
        "name": "대한무역투자진흥공사_해외시장뉴스",
        "endpoint": "https://apis.data.go.kr/B490001/newsService/newsList",
        "method": "GET",
        "params": {
            "serviceKey": API_KEY,
            "pageNo": 1,
            "numOfRows": 100,
            "returnType": "JSON",
            # 선택: cntryCd (국가코드), category (카테고리)
        },
        "output_file": "대한무역투자진흥공사_해외시장뉴스_20260430.csv",
    },

    # 4. KOTRA 상품DB (미반영)
    "kotra_product": {
        "name": "대한무역투자진흥공사_상품DB",
        "endpoint": "https://apis.data.go.kr/B490001/prdctDBService/prdctDBList",
        "method": "GET",
        "params": {
            "serviceKey": API_KEY,
            "pageNo": 1,
            "numOfRows": 100,
            "returnType": "JSON",
            # 선택: cntryCd, itemNm (품목명)
        },
        "output_file": "대한무역투자진흥공사_상품DB_20260430.csv",
    },

    # 5. NIPA 글로벌ICT포털 해외바이어정보 (미반영)
    "nipa_buyer": {
        "name": "정보통신산업진흥원_글로벌ICT포털_해외바이어정보",
        "endpoint": "https://apis.data.go.kr/...",  # 활용신청 후 확인
        "method": "GET",
        "params": {
            "serviceKey": API_KEY,
            # 파라미터는 활용가이드 확인 필요
        },
        "output_file": "정보통신산업진흥원_글로벌ICT포털_해외바이어정보_20260430.csv",
    },
}


def fetch_api_data(config_name: str, extra_params: Optional[dict] = None) -> list[dict]:
    """
    API 데이터 수집

    Args:
        config_name: API_CONFIGS의 키명
        extra_params: 추가 파라미터 (예: {"country": "US"})

    Returns:
        수집된 아이템 리스트
    """
    config = API_CONFIGS.get(config_name)
    if not config:
        logger.error(f"Unknown config: {config_name}")
        return []

    if not API_KEY:
        logger.error("API_KEY not found in environment")
        return []

    items = []
    page = 1
    max_pages = 1000

    params = config["params"].copy()
    if extra_params:
        params.update(extra_params)

    logger.info(f"[{config['name']}] 수집 시작...")

    while page <= max_pages:
        params["pageNo"] = page

        try:
            resp = requests.get(
                config["endpoint"], 
                params=params, 
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            if resp.status_code != 200:
                logger.warning(f"  Page {page}: HTTP {resp.status_code}")
                break

            # JSON 응답 처리
            try:
                data = resp.json()
            except:
                logger.warning(f"  Page {page}: JSON 파싱 실패")
                break

            # 공공데이터포털 표준 응답
            header = data.get("response", {}).get("header", {})
            body = data.get("response", {}).get("body", {}) or {}

            result_code = str(header.get("resultCode", ""))
            result_msg = header.get("resultMsg", "")

            if result_code not in ["00", "0"]:
                logger.warning(f"  API 오류: {result_msg} (code={result_code})")
                break

            # 아이템 추출
            items_raw = body.get("items", {})
            if isinstance(items_raw, dict):
                page_items = items_raw.get("item", [])
            elif isinstance(items_raw, list):
                page_items = items_raw
            else:
                page_items = []

            if not page_items:
                logger.info(f"  Page {page}: 데이터 없음, 종료")
                break

            # 단일 아이템인 경우 리스트로 변환
            if isinstance(page_items, dict):
                page_items = [page_items]

            items.extend(page_items)
            logger.info(f"  Page {page}: {len(page_items)}건 수집 (누적: {len(items)})")

            # 다음 페이지 확인
            total = body.get("totalCount", 0)
            if page * params.get("numOfRows", 100) >= total:
                break

            page += 1
            time.sleep(0.3)  # API 호출 간격

        except Exception as e:
            logger.error(f"  Page {page}: 예외 발생 - {e}")
            break

    logger.info(f"[{config['name']}] 총 {len(items)}건 수집 완료")
    return items


def save_to_csv(items: list[dict], filename: str):
    """CSV 파일로 저장"""
    if not items:
        logger.warning(f"저장할 데이터가 없습니다: {filename}")
        return

    output_path = OUTPUT_DIR / filename

    # 컬럼 추출
    columns = list(items[0].keys())

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(items)

    logger.info(f"Saved: {output_path} ({len(items)} rows)")


def main():
    parser = argparse.ArgumentParser(description="공공데이터포털 API 수집")
    parser.add_argument("--target", default="ksure_buyer", 
                       help="수집 대상 (ksure_buyer/kotra_country/kotra_news/kotra_product/nipa_buyer/all)")
    parser.add_argument("--country", default="US", help="국가코드 (예: US, CN, JP)")
    args = parser.parse_args()

    targets = list(API_CONFIGS.keys()) if args.target == "all" else [args.target]

    for target in targets:
        if target == "ksure_buyer":
            # 한국무역보험공사는 국가코드 필수
            items = fetch_api_data(target, {"country": args.country})
        else:
            items = fetch_api_data(target)

        if items:
            config = API_CONFIGS[target]
            save_to_csv(items, config["output_file"])


if __name__ == "__main__":
    main()
