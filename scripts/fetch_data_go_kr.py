"""
공공데이터포털(data.go.kr) API 통합 수집 스크립트

지원 API:
- KOTRA 수출유망추천정보
- KOTRA 국가정보
- KOTRA 상품DB
- KOTRA 해외시장뉴스
- KOTRA 무역사기사례
- KOTRA 기업성공사례
- NIPA 글로벌ICT포털 해외바이어정보

사용법:
  1. .env 파일에 각 API의 SERVICE_KEY 와 ENDPOINT 입력
  2. python scripts/fetch_data_go_kr.py --api 수출유망추천정보 --output data/수출유망추천정보.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PAGE_SIZE = 100
MAX_PAGES = 1000
REQUEST_DELAY = 0.3


API_CONFIGS: dict[str, dict[str, Any]] = {
    "수출유망추천정보": {
        "key_env": "KOTRA_PROSPECT_API_KEY",
        "endpoint_env": "KOTRA_PROSPECT_ENDPOINT",
        "default_endpoint": "https://apis.data.go.kr/1262000/ExportProspectRecomInfoService/getExportProspectRecomInfoList",
        "required_params": ["serviceKey", "numOfRows", "pageNo"],
        "optional_params": ["hsCode", "cntyCd", "year"],
    },
    "국가정보": {
        "key_env": "KOTRA_COUNTRY_API_KEY",
        "endpoint_env": "KOTRA_COUNTRY_ENDPOINT",
        "default_endpoint": "https://apis.data.go.kr/1262000/CountryInfoService/getCountryInfoList",
        "required_params": ["serviceKey", "numOfRows", "pageNo"],
        "optional_params": ["cntyCd", "cntyNm"],
    },
    "상품DB": {
        "key_env": "KOTRA_PRODUCT_API_KEY",
        "endpoint_env": "KOTRA_PRODUCT_ENDPOINT",
        "default_endpoint": "https://apis.data.go.kr/1262000/ProductDBService/getProductDBList",
        "required_params": ["serviceKey", "numOfRows", "pageNo"],
        "optional_params": ["hsCode", "prodNm"],
    },
    "해외시장뉴스": {
        "key_env": "KOTRA_NEWS_API_KEY",
        "endpoint_env": "KOTRA_NEWS_ENDPOINT",
        "default_endpoint": "https://apis.data.go.kr/1262000/OverseasMarketNewsService/getOverseasMarketNewsList",
        "required_params": ["serviceKey", "numOfRows", "pageNo"],
        "optional_params": ["cntyCd", "searchKeyword"],
    },
    "무역사기사례": {
        "key_env": "KOTRA_FRAUD_API_KEY",
        "endpoint_env": "KOTRA_FRAUD_ENDPOINT",
        "default_endpoint": "https://apis.data.go.kr/1262000/TradeFraudCaseService/getTradeFraudCaseList",
        "required_params": ["serviceKey", "numOfRows", "pageNo"],
        "optional_params": ["cntyCd", "searchKeyword"],
    },
    "기업성공사례": {
        "key_env": "KOTRA_SUCCESS_API_KEY",
        "endpoint_env": "KOTRA_SUCCESS_ENDPOINT",
        "default_endpoint": "https://apis.data.go.kr/1262000/CompanySuccessStoryService/getCompanySuccessStoryList",
        "required_params": ["serviceKey", "numOfRows", "pageNo"],
        "optional_params": ["cntyCd", "searchKeyword"],
    },
    "해외바이어정보": {
        "key_env": "NIPA_BUYER_API_KEY",
        "endpoint_env": "NIPA_BUYER_ENDPOINT",
        "default_endpoint": "https://apis.data.go.kr/1383000/GlobalICTPortalBuyerInfoService/getGlobalICTPortalBuyerInfoList",
        "required_params": ["serviceKey", "numOfRows", "pageNo"],
        "optional_params": ["cntyCd", "buyerNm", "prodNm"],
    },
}


def fetch_page(endpoint: str, service_key: str, page_no: int, num_of_rows: int, extra_params: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {
        "serviceKey": service_key,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "resultType": "json",
    }
    if extra_params:
        params.update({k: v for k, v in extra_params.items() if v is not None and v != ""})

    resp = requests.get(endpoint, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_all(endpoint: str, service_key: str, extra_params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        data = fetch_page(endpoint, service_key, page, PAGE_SIZE, extra_params)

        header = data.get("response", {}).get("header", {})
        result_code = int(header.get("resultCode", -1))
        result_msg = header.get("resultMsg", "")

        if result_code != 0:
            print(f"[WARN] API 오류: code={result_code}, msg={result_msg}")
            break

        body = data.get("response", {}).get("body", {}) or {}
        items_raw = body.get("items", {})
        if items_raw is None:
            print(f"[INFO] 페이지 {page}: 데이터 없음. 수집 종료.")
            break

        items = items_raw.get("item", [])
        if isinstance(items, dict):
            items = [items]
        total_count = int(body.get("totalCount", 0))

        if not items:
            print(f"[INFO] 페이지 {page}: 데이터 없음. 수집 종료.")
            break

        all_items.extend(items)
        print(f"[INFO] 페이지 {page} 수집: {len(items)}건 (누계 {len(all_items)}/{total_count})")

        if len(all_items) >= total_count:
            break

        time.sleep(REQUEST_DELAY)

    return all_items


def items_to_csv(items: list[dict[str, Any]], output_path: Path) -> None:
    if not items:
        print("[WARN] 저장할 데이터가 없습니다.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(items[0].keys())

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(items)

    print(f"[DONE] {output_path} 에 {len(items)}건 저장 완료")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="공공데이터포털 API 통합 수집")
    parser.add_argument("--api", required=True, choices=list(API_CONFIGS.keys()), help="수집할 API 이름")
    parser.add_argument("--output", type=Path, required=True, help="출력 CSV 경로")
    parser.add_argument("--api-key", default="", help="API 인증키 (미입력 시 .env에서 로드)")
    parser.add_argument("--endpoint", default="", help="엔드포인트 URL (미입력 시 .env 또는 기본값)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = API_CONFIGS[args.api]

    api_key = args.api_key or os.getenv(config["key_env"], "")
    endpoint = args.endpoint or os.getenv(config["endpoint_env"], "") or config["default_endpoint"]

    if not api_key:
        print(f"[ERROR] API 키가 없습니다. .env 파일에 {config['key_env']}=YOUR_KEY 를 입력하거나 --api-key 로 전달하세요.")
        return 1

    print(f"[INFO] API: {args.api}")
    print(f"[INFO] 엔드포인트: {endpoint}")

    try:
        items = fetch_all(endpoint, api_key)
        items_to_csv(items, args.output)
    except requests.HTTPError as exc:
        print(f"[ERROR] API 호출 실패: {exc}")
        print("[HINT] 공공데이터포털(data.go.kr)에서 해당 API 상세 페이지 > Open API 탭을 확인하여")
        print("       정확한 엔드포인트 URL과 필수 파라미터를 .env 에 설정하세요.")
        return 1
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
