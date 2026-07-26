#!/usr/bin/env python3
"""P1/P2 바이어·기회 소스 병합 후 데이터 재확인.

P1 (CONFIRMED 로컬 raw):
  - buyKOREA 화장품 인콰이어리 → opportunity_item
  - GoBizKorea 인콰이어리/구매오퍼 → opportunity_item
  - buyer_candidate에 잘못 들어 있는 무명 인콰이어리 행은 opportunity로 이동

P2 (파일 드롭인 시에만):
  - input/p2_optional/*.csv — 스키마가 COMMON이면 편입
  - TradeKorea/KITA 등 미확인 소스는 파일 없으면 UNKNOWN으로 리포트만

원본 필드를 발명하지 않는다. 스크래핑으로 contact_* 를 채우지 않는다.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREPROCESS = ROOT / "services" / "cosmetics_mvp_preprocess"
RAW_DIR = PREPROCESS / "output" / "raw"
OUT_DIR = PREPROCESS / "output"
P2_DIR = PREPROCESS / "input" / "p2_optional"
REPORT_DIR = ROOT / "tools" / "reports"

COMMON_OUTPUT_COLUMNS = [
    "record_type",
    "source_dataset",
    "source_file",
    "source_row_no",
    "title",
    "normalized_name",
    "country_raw",
    "country_norm",
    "country_iso3",
    "hs_code_raw",
    "hs_code_norm",
    "keywords_raw",
    "keywords_norm",
    "has_contact",
    "contact_name",
    "contact_email",
    "contact_phone",
    "contact_website",
    "valid_until",
]

EXTRA_COLUMNS = [
    "source_snapshot_date",
    "distance_from_kr_km",
    "contact_email_estimated",
]

BUYER_COLUMNS = COMMON_OUTPUT_COLUMNS + EXTRA_COLUMNS

# 표시명 정규화 (raw 표기 흔들림 → 최종 표준명)
SOURCE_CANONICAL = {
    "대한무역투자진흥공사_SNS마케팅수집바이어": "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보",
    "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보": "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보",
    "대한무역투자진흥공사_buyKOREA인콰이어리": "대한무역투자진흥공사_buyKOREA인콰이어리",
    "중소벤처기업진흥공단_GoBizKorea인콰이어리": "중소벤처기업진흥공단_GoBizKorea인콰이어리",
    "중소벤처기업진흥공단_GoBizKorea구매오퍼": "중소벤처기업진흥공단_GoBizKorea구매오퍼",
    "정보통신산업진흥원_글로벌ICT포털해외바이어": "정보통신산업진흥원_글로벌ICT포털해외바이어",
    "한국무역보험공사_화장품 바이어 정보": "한국무역보험공사_화장품 바이어 정보",
    "한국무역보험공사_바이어 검색": "한국무역보험공사_바이어 검색",
    "EC21_GlobalB2B_BuyingLeads": "EC21_GlobalB2B_BuyingLeads",
    "ITC_TradeMap_ImportingCompanies": "ITC_TradeMap_ImportingCompanies",
}

# P1: 인콰이어리/오퍼 → opportunity (회사명 없어도 수요 신호)
P1_OPPORTUNITY_FILES: list[tuple[str, Path]] = [
    ("대한무역투자진흥공사_buyKOREA인콰이어리", RAW_DIR / "buykorea_inquiry_2023_2025_cosmetics.csv"),
    ("중소벤처기업진흥공단_GoBizKorea인콰이어리", RAW_DIR / "gobiz_inquiry_2021_2023.csv"),
    ("중소벤처기업진흥공단_GoBizKorea인콰이어리", RAW_DIR / "gobiz_inquiry_2024.csv"),
    ("중소벤처기업진흥공단_GoBizKorea구매오퍼", RAW_DIR / "gobiz_purchase_offer.csv"),
]

# buyer_candidate에 남아 있으면 opportunity로 이동할 소스
INQUIRY_SOURCES_IN_BUYER = {
    "대한무역투자진흥공사_buyKOREA인콰이어리",
    "중소벤처기업진흥공단_GoBizKorea인콰이어리",
    "중소벤처기업진흥공단_GoBizKorea구매오퍼",
}

# P2 기대 소스 — 2026-07-26 접근 경로 검증 결과.
# 공개 일괄 CSV/API 없음 → 드롭인 파일 없으면 ACCESS_GATED (L002: 무료 덤프 단정 금지)
P2_EXPECTED: list[dict[str, str]] = [
    {
        "key": "tradekorea",
        "label": "TradeKorea_BuyerOrInquiry",
        "status_if_missing": "ACCESS_GATED",
        "note": (
            "일괄 export/API 없음. tradeKorea 셀러 회원 UI에서 바이어 검색·C/L 발송만 가능 "
            "(1일 1회·월 5회, 1회 20개사). 연락처는 개인정보보호로 미제공(국가·회사·품목만). "
            "회원 수령분을 COMMON 스키마 CSV로 변환해 input/p2_optional/tradekorea.csv 드롭인."
        ),
        "access_url": "https://kr.tradekorea.com/seller/buyer/buyerDB.do",
        "verified_at": "2026-07-26",
    },
    {
        "key": "kita",
        "label": "KITA_BuyerOrInquiry",
        "status_if_missing": "ACCESS_GATED",
        "note": (
            "KITA 바이어 DB 일괄 CSV/OpenAPI 없음. tradeKorea(KITA 운영) 회원 매칭·C/L 경로와 동일 계열. "
            "공개 대체는 K-SURE 바이어검색 API(data.go.kr)이며 이미 buyer_candidate에 편입됨. "
            "협회 수령분이 있으면 input/p2_optional/kita.csv 드롭인."
        ),
        "access_url": "https://www.kita.org/info/globalService/tradeKorea.do",
        "verified_at": "2026-07-26",
    },
    {
        "key": "kotra_trade_office",
        "label": "KOTRA_TradeOffice_BuyerList",
        "status_if_missing": "ACCESS_GATED",
        "note": (
            "무역관 바이어 일괄 다운로드 없음. 수출24 잠재바이어 발굴(유료·건당) 또는 "
            "트라이빅/기업회원 맞춤 검색. 무역관 배포분은 재배포 범위 문서화 후 "
            "input/p2_optional/kotra_trade_office.csv 드롭인."
        ),
        "access_url": "https://www.kotra.or.kr",
        "verified_at": "2026-07-26",
    },
]


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return ""
    return text


def _truthy_contact(row: pd.Series) -> bool:
    if _clean(row.get("contact_email")) or _clean(row.get("contact_phone")) or _clean(row.get("contact_website")):
        return True
    flag = _clean(row.get("has_contact")).lower()
    return flag in {"1", "true", "yes"}


def _align_frame(df: pd.DataFrame, record_type: str, source_dataset: str | None = None) -> pd.DataFrame:
    out = df.copy()
    for col in BUYER_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    if source_dataset:
        out["source_dataset"] = source_dataset
    out["source_dataset"] = out["source_dataset"].map(
        lambda v: SOURCE_CANONICAL.get(_clean(v), _clean(v))
    )
    out["record_type"] = record_type
    # has_contact 재계산 (원본 False인데 이메일이 있는 경우 등 보정하지 않고, 빈 연락은 False)
    out["has_contact"] = out.apply(_truthy_contact, axis=1)
    out["contact_email_estimated"] = out["contact_email_estimated"].map(
        lambda v: _clean(v) if _clean(v) else "False"
    )
    if "source_snapshot_date" in out.columns:
        out["source_snapshot_date"] = out["source_snapshot_date"].map(_clean)
    return out[BUYER_COLUMNS]


def _load_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, dtype=str, encoding=enc, low_memory=False)
        except Exception:
            continue
    raise ValueError(f"CSV load failed: {path}")


def _dedupe_buyer(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if df.empty:
        return df.copy(), 0
    work = df.copy()
    work["_name"] = work["normalized_name"].map(lambda v: re.sub(r"\s+", "", _clean(v)).casefold())
    work["_country"] = work["country_norm"].map(lambda v: _clean(v).casefold())
    work["_has"] = work.apply(_truthy_contact, axis=1)
    # 연락처 있는 행 우선
    work = work.sort_values(by=["_has"], ascending=False)
    before = len(work)
    # 이름+국가가 둘 다 있을 때만 키 중복 제거; 이름 없으면 title+country
    named = work[work["_name"].ne("")].copy()
    unnamed = work[work["_name"].eq("")].copy()
    named = named.drop_duplicates(subset=["_name", "_country"], keep="first")
    unnamed["_title"] = unnamed["title"].map(lambda v: re.sub(r"\s+", "", _clean(v)).casefold())
    unnamed = unnamed.drop_duplicates(subset=["_title", "_country"], keep="first")
    merged = pd.concat([named, unnamed], ignore_index=True)
    removed = before - len(merged)
    return merged[BUYER_COLUMNS].reset_index(drop=True), removed


def _dedupe_opportunity(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if df.empty:
        return df.copy(), 0
    work = df.copy()
    work["_title"] = work["title"].map(lambda v: re.sub(r"\s+", "", _clean(v)).casefold())
    work["_country"] = work["country_norm"].map(lambda v: _clean(v).casefold())
    work["_valid"] = work["valid_until"].map(_clean)
    before = len(work)
    work = work.drop_duplicates(subset=["_title", "_country", "_valid"], keep="first")
    return work[BUYER_COLUMNS].reset_index(drop=True), before - len(work)


def _counts(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"rows": 0, "by_source": {}, "with_email": 0, "with_name": 0}
    email = df["contact_email"].map(_clean).ne("")
    name = df["normalized_name"].map(_clean).ne("")
    by_source = df["source_dataset"].fillna("(null)").value_counts().to_dict()
    return {
        "rows": int(len(df)),
        "by_source": {str(k): int(v) for k, v in by_source.items()},
        "with_email": int(email.sum()),
        "with_name": int(name.sum()),
        "email_ratio": round(float(email.mean()), 4),
    }


def _load_p2_optional() -> tuple[list[pd.DataFrame], list[dict[str, Any]]]:
    frames: list[pd.DataFrame] = []
    status: list[dict[str, Any]] = []
    P2_DIR.mkdir(parents=True, exist_ok=True)

    found_labels: set[str] = set()
    for path in sorted(P2_DIR.glob("*.csv")):
        # 스키마 예시(*.csv.example)는 glob에 안 걸리지만, *.example.csv 잔존도 제외
        if path.name.endswith(".example.csv") or ".example." in path.name:
            continue
        df = _load_csv(path)
        # COMMON 최소 컬럼 없으면 스킵
        if "country_norm" not in df.columns and "country_raw" not in df.columns:
            status.append(
                {
                    "file": path.name,
                    "status": "SKIPPED",
                    "reason": "missing country_norm/country_raw",
                }
            )
            continue
        source = _clean(df["source_dataset"].iloc[0]) if "source_dataset" in df.columns and len(df) else path.stem
        # 이름 있으면 buyer, 없으면 opportunity
        aligned_buyerish = _align_frame(df, "buyer_candidate")
        has_names = aligned_buyerish["normalized_name"].map(_clean).ne("").mean() > 0.5
        record_type = "buyer_candidate" if has_names else "opportunity_item"
        aligned = _align_frame(df, record_type, source_dataset=source or path.stem)
        aligned["source_file"] = aligned["source_file"].map(_clean)
        aligned.loc[aligned["source_file"].eq(""), "source_file"] = path.name
        frames.append(aligned)
        found_labels.add(source or path.stem)
        status.append(
            {
                "file": path.name,
                "status": "CONFIRMED",
                "record_type": record_type,
                "rows": len(aligned),
                "source_dataset": source or path.stem,
            }
        )

    for expected in P2_EXPECTED:
        label = expected["label"]
        if any(label.casefold() in f.casefold() for f in found_labels) or any(
            expected["key"] in str(s.get("file", "")).casefold() for s in status if s.get("status") == "CONFIRMED"
        ):
            continue
        # 파일명에 key 포함된 경우도 매칭
        matched = any(expected["key"] in str(s.get("file", "")).casefold() for s in status)
        if matched:
            continue
        entry: dict[str, Any] = {
            "key": expected["key"],
            "label": label,
            "status": expected["status_if_missing"],
            "note": expected["note"],
            "drop_in": str(P2_DIR / f"{expected['key']}.csv"),
        }
        if expected.get("access_url"):
            entry["access_url"] = expected["access_url"]
        if expected.get("verified_at"):
            entry["verified_at"] = expected["verified_at"]
        status.append(entry)
    return frames, status


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    buyer_path = OUT_DIR / "buyer_candidate.csv"
    opp_path = OUT_DIR / "opportunity_item.csv"

    before_buyer = _load_csv(buyer_path) if buyer_path.exists() else pd.DataFrame(columns=BUYER_COLUMNS)
    before_opp = _load_csv(opp_path) if opp_path.exists() else pd.DataFrame(columns=BUYER_COLUMNS)
    # opportunity 파일이 스키마 불일치(빈 껍데기)면 초기화
    if list(before_opp.columns) != BUYER_COLUMNS and "source_dataset" not in before_opp.columns:
        before_opp = pd.DataFrame(columns=BUYER_COLUMNS)

    before_buyer = _align_frame(before_buyer, "buyer_candidate")
    before_opp = _align_frame(before_opp, "opportunity_item") if len(before_opp) else before_opp

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "before": {
            "buyer_candidate": _counts(before_buyer),
            "opportunity_item": _counts(before_opp) if len(before_opp) else {"rows": 0},
        },
        "p1": {"loaded": [], "missing": []},
        "p2": [],
        "actions": [],
    }

    # --- P1 opportunity loads ---
    p1_frames: list[pd.DataFrame] = []
    for source_name, path in P1_OPPORTUNITY_FILES:
        if not path.exists():
            report["p1"]["missing"].append({"source": source_name, "path": str(path), "status": "MISSING"})
            continue
        raw = _load_csv(path)
        aligned = _align_frame(raw, "opportunity_item", source_dataset=source_name)
        aligned["source_file"] = aligned["source_file"].map(_clean)
        aligned.loc[aligned["source_file"].eq(""), "source_file"] = path.name
        p1_frames.append(aligned)
        report["p1"]["loaded"].append(
            {
                "source": source_name,
                "path": path.name,
                "status": "CONFIRMED",
                "rows": len(aligned),
                "with_email": int(aligned["contact_email"].map(_clean).ne("").sum()),
                "with_name": int(aligned["normalized_name"].map(_clean).ne("").sum()),
            }
        )

    # buyer에서 인콰이어리 소스 분리
    mask_inquiry = before_buyer["source_dataset"].isin(INQUIRY_SOURCES_IN_BUYER)
    moved = before_buyer[mask_inquiry].copy()
    buyers_kept = before_buyer[~mask_inquiry].copy()
    if len(moved):
        moved = _align_frame(moved, "opportunity_item")
        p1_frames.append(moved)
        report["actions"].append(
            {
                "action": "move_inquiry_rows_buyer_to_opportunity",
                "rows": int(len(moved)),
                "sources": sorted(moved["source_dataset"].unique().tolist()),
            }
        )

    # P2 optional
    p2_frames, p2_status = _load_p2_optional()
    report["p2"] = p2_status
    p2_buyer = [f for f in p2_frames if (f["record_type"] == "buyer_candidate").all()]
    p2_opp = [f for f in p2_frames if not (f["record_type"] == "buyer_candidate").all()]

    # compose
    buyer_parts = [buyers_kept] + p2_buyer
    opp_parts = [before_opp] + p1_frames + p2_opp
    buyer_combined = pd.concat([p for p in buyer_parts if len(p)], ignore_index=True) if any(len(p) for p in buyer_parts) else pd.DataFrame(columns=BUYER_COLUMNS)
    opp_combined = pd.concat([p for p in opp_parts if len(p)], ignore_index=True) if any(len(p) for p in opp_parts) else pd.DataFrame(columns=BUYER_COLUMNS)

    buyer_final, buyer_dedup = _dedupe_buyer(buyer_combined)
    opp_final, opp_dedup = _dedupe_opportunity(opp_combined)
    report["actions"].append({"action": "dedupe_buyer", "removed": buyer_dedup})
    report["actions"].append({"action": "dedupe_opportunity", "removed": opp_dedup})

    buyer_final.to_csv(buyer_path, index=False, encoding="utf-8-sig")
    opp_final.to_csv(opp_path, index=False, encoding="utf-8-sig")

    report["after"] = {
        "buyer_candidate": _counts(buyer_final),
        "opportunity_item": _counts(opp_final),
        "paths": {"buyer_candidate": str(buyer_path), "opportunity_item": str(opp_path)},
    }

    # 요약 판정
    report["verdict"] = {
        "p1_opportunity_expanded": report["after"]["opportunity_item"]["rows"]
        > report["before"].get("opportunity_item", {}).get("rows", 0),
        "buyer_inquiries_removed": int(len(moved)),
        "p2_confirmed_files": sum(1 for s in p2_status if s.get("status") == "CONFIRMED"),
        "p2_access_gated_sources": sum(1 for s in p2_status if s.get("status") == "ACCESS_GATED"),
        "p2_unknown_sources": sum(1 for s in p2_status if s.get("status") == "UNKNOWN"),
        "note": (
            "P2 TradeKorea/KITA/KOTRA 무역관은 공개 일괄 CSV 없음 → ACCESS_GATED (L002). "
            "회원·무역관 수령 CSV만 드롭인 편입. contact_* 스크래핑 미수행."
        ),
    }

    report_path = REPORT_DIR / "p1_p2_buyer_merge_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nReport written: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
