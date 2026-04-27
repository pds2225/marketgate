"""
한국무역보험공사_바이어 검색 API 수집 스크립트
공공데이터포털: https://www.data.go.kr/data/15144480/openapi.do

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

# .env 로드 (프로젝트 루트 또는 현재 디렉토리)
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

API_KEY = os.getenv("KSURE_API_KEY", "")
# 공공데이터포털 표준 엔드포인트 (실제 엔드포인트는 Swagger 확인 후 수정 필요)
DEFAULT_ENDPOINT = os.getenv(
    "KSURE_ENDPOINT",
    "https://apis.data.go.kr/B552696/buyer",
)

# 요청당 최대 페이지/건수 (공공데이터포털 일반 제한)
PAGE_SIZE = 100
MAX_PAGES = 100
REQUEST_DELAY = 0.3  # 초당 3~4회 제한 대응


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

        # 응답 구조는 실제 Swagger 테스트 후에 맞춰야 함
        # 일반적인 공공데이터포털 JSON 형식 가정
        body = data.get("response", {}).get("body", {})
        items = body.get("items", {}).get("item", [])
        total_count = int(body.get("totalCount", 0))

        if isinstance(items, dict):
            items = [items]

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
        default=DEFAULT_ENDPOINT,
        help="API 엔드포인트 URL (Swagger 확인 후 수정)",
    )
    parser.add_argument(
        "--api-key",
        default=API_KEY,
        help="공공데이터포털 API 인증키 (미입력 시 .env의 KSURE_API_KEY 사용)",
    )
    parser.add_argument(
        "--keyword",
        default="",
        help="검색 키워드 (예: 화장품, cosmetics 등)",
    )
    parser.add_argument(
        "--country",
        default="",
        help="국가 필터 (ISO2 또는 한글 국가명, API 스펙 확인 필요)",
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
    if args.keyword:
        search_params["keyword"] = args.keyword
    if args.country:
        search_params["country"] = args.country

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
