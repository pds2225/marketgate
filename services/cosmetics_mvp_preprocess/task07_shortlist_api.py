from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shortlist_service import build_supplier_profile, shortlist_buyers  # noqa: E402
from task05_shortlist import parse_date  # noqa: E402


DEFAULT_REFERENCE_DATE = "2025-06-01"
DEFAULT_SHORTLIST_QUERY = {
    "supplier_name": "MarketGate Cosmetics Supplier",
    "target_country_norm": "미국",
    "target_hs_code_norm": "3304",
    "target_keywords_norm": "cosmetics | serum | cream | mask | ampoule | makeup",
    "target_product_name_norm": "cosmetics",
    "opportunity_title_contains": "ampoule",
    "opportunity_country_norm": "미국",
    "limit": 20,
}


def _parse_reference_date(value: str) -> date:
    parsed = parse_date(value)
    if parsed is None:
        raise HTTPException(status_code=400, detail=f"reference_date 형식이 잘못되었습니다: {value}")
    return parsed


def _shortlist_item_passes_policy(item: dict[str, Any]) -> bool:
    if item.get("decision") == "rejected":
        return False
    return True


def _apply_task05_06_policy_filter(result: dict[str, Any], *, include_rejected: bool) -> dict[str, Any]:
    filtered = dict(result)
    original_items = result.get("items", [])
    items = list(original_items) if include_rejected else [item for item in original_items if _shortlist_item_passes_policy(item)]
    filtered["items"] = items

    meta = dict(result.get("meta", {}))
    meta["returned_count"] = len(items)
    meta["shortlist_count"] = sum(1 for item in items if item.get("decision") == "shortlist")
    meta["candidate_count"] = sum(1 for item in items if item.get("decision") == "candidate")
    meta.pop("rejected_count", None)
    meta["pre_filter_rejected_count"] = sum(1 for item in original_items if item.get("decision") == "rejected")
    filtered["meta"] = meta
    return filtered


def create_app(output_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="MarketGate Shortlist API", version="0.1.0")
    app.state.output_dir = output_dir or (ROOT / "output")

    @app.get("/buyers/shortlist")
    def get_buyers_shortlist(
        supplier_name: str = Query("MarketGate Supplier"),
        target_country_norm: str = Query(""),
        target_hs_code_norm: str = Query(""),
        target_keywords_norm: str = Query(""),
        target_product_name_norm: str = Query(""),
        required_capacity: float | None = Query(default=None),
        banned_countries: str = Query(""),
        opportunity_title_contains: str = Query(""),
        opportunity_country_norm: str = Query(""),
        reference_date: str = Query(DEFAULT_REFERENCE_DATE),
        limit: int = Query(default=20, ge=1, le=100),
        include_rejected: bool = Query(default=False),
    ) -> dict[str, Any]:
        ref = _parse_reference_date(reference_date)
        supplier_profile = build_supplier_profile(
            supplier_name=supplier_name,
            target_country_norm=target_country_norm,
            target_hs_code_norm=target_hs_code_norm,
            target_keywords_norm=target_keywords_norm,
            target_product_name_norm=target_product_name_norm,
            required_capacity=required_capacity,
            banned_countries=banned_countries,
        )

        try:
            result = shortlist_buyers(
                output_dir=app.state.output_dir,
                supplier_profile=supplier_profile,
                reference_date=ref,
                limit=limit,
                opportunity_title_contains=opportunity_title_contains,
                opportunity_country_norm=opportunity_country_norm,
                include_rejected=include_rejected,
            )
            return _apply_task05_06_policy_filter(result, include_rejected=include_rejected)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()


def api_demo_request(
    output_dir: Path | None = None,
    *,
    reference_date: str = DEFAULT_REFERENCE_DATE,
) -> dict[str, Any]:
    client = TestClient(create_app(output_dir=output_dir))
    response = client.get(
        "/buyers/shortlist",
        params={**DEFAULT_SHORTLIST_QUERY, "reference_date": reference_date},
    )
    if response.status_code != 200:
        raise RuntimeError(f"API demo failed: {response.status_code} {response.text}")
    return response.json()


def _demo(output_dir: Path | None, reference_date: str) -> None:
    result = api_demo_request(output_dir=output_dir, reference_date=reference_date)
    print("[task07-demo] meta =", result["meta"])
    print("[task07-demo] first_item =", result["items"][0] if result["items"] else {})


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TASK-07 FastAPI GET /buyers/shortlist")
    parser.add_argument("--serve", action="store_true", help="FastAPI 서버를 실행한다.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="바인드 host")
    parser.add_argument("--port", type=int, default=8000, help="바인드 port")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output", help="output CSV 폴더")
    parser.add_argument(
        "--reference-date",
        type=str,
        default=DEFAULT_REFERENCE_DATE,
        help="demo / shortlist 기준일",
    )
    parser.add_argument("--demo-request", action="store_true", help="내장 TestClient로 API 응답 예시를 출력한다.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.serve:
        uvicorn.run(create_app(output_dir=args.output_dir), host=args.host, port=args.port)
        return 0
    _demo(output_dir=args.output_dir, reference_date=args.reference_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
