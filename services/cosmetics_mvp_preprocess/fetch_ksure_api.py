"""
한국무역보험공사_바이어 검색 API 수집 스크립트
공공데이터포털: https://www.data.go.kr/data/15144480/openapi.do
엔드포인트: https://apis.data.go.kr/B552696/buyer/getBuyerList

사용법:
  1. .env 파일에 KSURE_API_KEY=YOUR_KEY 입력
  2. python fetch_ksure_api.py --output sample_input/한국무역보험공사_바이어 검색_20260426.csv
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

# .env 로드
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

API_KEY = os.getenv("KSURE_API_KEY", "")
ENDPOINT = os.getenv(
    "KSURE_ENDPOINT",
    "https://apis.data.go.kr/B552696/buyer/getBuyerList",
)

PAGE_SIZE = 100
MAX_PAGES = 1000
REQUEST_DELAY = 0.3


def fetch_page(
    endpoint: str,
    service_key: str,
    page_no: int,
    num_of_rows: int,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """한 페이지 요청"""
    req_params: dict[str, Any] = {
        "serviceKey": service_key,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "resultType": "json",
    }
    if params:
        req_params.update(params)

    resp = requests.get(endpoint, params=req_params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_all(
    endpoint: str,
    service_key: str,
    search_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """전체 페이지 순회 수집"""
    all_items: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        data = fetch_page(endpoint, service_key, page, PAGE_SIZE, search_params)

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
    """수집 결과를 CSV로 저장 (원본 그대로)"""
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
    parser = argparse.ArgumentParser(description="한국무역보험공사 바이어 검색 API 수집")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sample_input") / "한국무역보험공사_바이어 검색_20260426.csv",
        help="출력 CSV 경로",
    )
    parser.add_argument(
        "--endpoint",
        default=ENDPOINT,
        help="API 엔드포인트 URL",
    )
    parser.add_argument(
        "--api-key",
        default=API_KEY,
        help="공공데이터포털 API 인증키",
    )
    parser.add_argument(
        "--buyer-nm",
        default="",
        help="바이어명 검색 키워드",
    )
    parser.add_argument(
        "--ctry-cd",
        default="",
        help="국가코드",
    )
    parser.add_argument(
        "--industry-cd",
        default="",
        help="업종 코드 (4단계, 예: 75999)",
    )
    parser.add_argument(
        "--industry-nm",
        default="",
        help="업종명",
    )
    parser.add_argument(
        "--prod-nm",
        default="",
        help="품목명 (예: cosmetics, beauty)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if not args.api_key:
        print(
            "[ERROR] API 키가 없습니다.\n"
            "  1) .env 파일에 KSURE_API_KEY=YOUR_KEY 를 입력하거나\n"
            "  2) --api-key 인자로 직접 전달하세요."
        )
        return 1

    search_params: dict[str, Any] = {}
    if args.buyer_nm:
        search_params["buyerNm"] = args.buyer_nm
    if args.ctry_cd:
        search_params["ctryCd"] = args.ctry_cd
    if args.industry_cd:
        search_params["industryCd"] = args.industry_cd
    if args.industry_nm:
        search_params["industryNm"] = args.industry_nm
    if args.prod_nm:
        search_params["prodNm"] = args.prod_nm

    print(f"[INFO] 엔드포인트: {args.endpoint}")
    print(f"[INFO] 검색 조건: {search_params or '(전체)'}")

    try:
        items = fetch_all(args.endpoint, args.api_key, search_params)
        items_to_csv(items, args.output)
    except requests.HTTPError as exc:
        print(f"[ERROR] API 호출 실패: {exc}")
        print("[HINT] 엔드포인트 URL이나 API 키가 올바른지 Swagger에서 확인하세요.")
        return 1
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
