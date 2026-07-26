#!/usr/bin/env python3
"""우선 풀 바이어 contact enrichment (웹 URL → mailto/전화).

흐름 요약:
  1) 대상 행 고르기 (K-SURE/EC21/ITC/SNS, 웹 비어 있음)
  2) 회사명으로 Clearbit에서 공식 도메인 후보 검색
  3) 사이트·Contact/About에서 mailto 이메일·공개 전화 추출
  4) 빈 칸만 채움. 새 이메일은 contact_email_estimated=True

주의:
  - 스크래핑 값은 추정이다. 자동 발송에 확정 연락처처럼 쓰지 말 것.
  - SNS는 제외 필수가 아님. 포함 시 대상 건수·오탐·소요시간이 커진다.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# 경로·상수
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
# 채울 대상 CSV (gitignore). 실행 결과가 여기 저장된다.
BUYER_CSV = ROOT / "services" / "cosmetics_mvp_preprocess" / "output" / "buyer_candidate.csv"
# 집계 리포트 / 건별 체크포인트 (재현·오탐 롤백용)
REPORT_PATH = ROOT / "tools" / "reports" / "buyer_contact_enrich_report.json"
CHECKPOINT_PATH = ROOT / "tools" / "reports" / "buyer_contact_enrich_checkpoint.jsonl"

# SNS도 포함 가능(필수 제외 아님). 이름 노이즈↑ → 매칭 성공률↓·오탐↑·소요시간↑.
PRIORITY_SOURCES = {
    "한국무역보험공사_화장품 바이어 정보",
    "한국무역보험공사_바이어 검색",
    "EC21_GlobalB2B_BuyingLeads",
    "ITC_TradeMap_ImportingCompanies",
    "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보",
}

# 붙여 쓴 상호(예: FOOLTD)에서 떼어낼 법인식 접미사
SUFFIX_TOKENS = [
    "JOINTSTOCKCOMPANY",
    "JOINTSTOCK",
    "PRIVATE LIMITED",
    "PRIVATELIMITED",
    "SDNBHD",
    "SDN BHD",
    "BHD",
    "PTYLTD",
    "PTY LTD",
    "PTY",
    "LIMITED",
    "LTD",
    "LLC",
    "LLP",
    "INC",
    "CORP",
    "COMPANY",
    "CO",
    "GMBH",
    "SARL",
    "SPA",
    "SRL",
    "BV",
    "NV",
    "AG",
    "PLC",
    "JSC",
    "OJSC",
    "CJSC",
]

# SNS·디렉터리·뉴스 등 "회사 공식 사이트"가 아닌 도메인은 후보에서 제외
BLOCKED_DOMAINS = {
    "facebook.com",
    "linkedin.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "wikipedia.org",
    "crunchbase.com",
    "bloomberg.com",
    "yellowpages",
    "google.com",
    "amazon.com",
    "alibaba.com",
    "made-in-china.com",
    "newspost.com",
    "edu",
}

# 학교/정부 도메인은 뷰티 바이어 매칭 오탐이 많아 점수 0 처리
BLOCKED_TLDS = {".edu", ".gov", ".mil"}

# 홈 → Contact/About 순으로 공개 연락처 페이지를 순회
CONTACT_PATHS = (
    "",
    "/contact",
    "/contact-us",
    "/contactus",
    "/about",
    "/about-us",
    "/aboutus",
    "/company",
    "/en/contact",
    "/en/about",
)

# HTML에서 이메일·전화 뽑는 정규식
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+|00)?\d[\d\-\s().]{7,}\d")
MAILTO_RE = re.compile(r"mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", re.I)

# 외부 HTTP 공통 세션 (User-Agent에 봇 식별 포함)
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "MarketGateBot/0.1 (+https://marketgate.vercel.app; research enrichment)",
        "Accept": "text/html,application/json",
    }
)


# ---------------------------------------------------------------------------
# 이름 전처리 · 매칭 점수
# ---------------------------------------------------------------------------
def _clean(value: Any) -> str:
    """빈값·nan·none 문자열을 통일해 '' 로 만든다."""
    text = str(value or "").strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return ""
    return text


def humanize_company_name(raw: str) -> str:
    """붙여 쓴 대문자 상호를 검색용으로 느슨히 분리.

    예: 접미사 LTD/JSC 등을 띄어 Clearbit 검색 성공률을 높인다.
    """
    name = _clean(raw)
    if not name:
        return ""
    if " " in name:
        return re.sub(r"\s+", " ", name).strip()
    upper = name.upper()
    for token in sorted(SUFFIX_TOKENS, key=len, reverse=True):
        compact = token.replace(" ", "")
        if compact in upper and len(upper) > len(compact) + 2:
            upper = upper.replace(compact, " " + token + " ", 1)
    upper = re.sub(r"\s+", " ", upper).strip()
    parts = upper.split()
    if parts:
        return " ".join(p.title() if p.isalpha() else p for p in parts)
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    return spaced if spaced != raw else name


def build_queries(raw: str) -> list[str]:
    """Clearbit에 넣을 검색어 후보를 최대 6개까지 만든다.

    순서: 분리명 → 원문 → LTD 등 제거 코어 → 첫 토큰 → 앞 12~20자.
    하나가 실패해도 다음 변형으로 도메인을 찾을 여지를 남긴다.
    """
    human = humanize_company_name(raw)
    queries: list[str] = []
    for q in (human, raw[:60]):
        q = _clean(q)
        if q and q.casefold() not in {x.casefold() for x in queries}:
            queries.append(q)
    core = human
    for token in SUFFIX_TOKENS:
        core = re.sub(rf"\b{re.escape(token)}\b", " ", core, flags=re.I)
    core = re.sub(r"\s+", " ", core).strip()
    if core and core.casefold() not in {x.casefold() for x in queries}:
        queries.append(core)
    if core:
        first = core.split()[0]
        if len(first) >= 4:
            queries.append(first)
    compact = re.sub(r"[^a-zA-Z]", "", raw)
    if len(compact) >= 8:
        for n in (12, 16, 20):
            if len(compact) >= n:
                chunk = compact[:n]
                if chunk.casefold() not in {x.casefold() for x in queries}:
                    queries.append(chunk)
                break
    return queries[:6]


def _name_tokens(text: str) -> set[str]:
    """매칭용 의미 토큰. LTD/BEAUTY 등 흔한 단어는 제외, 4글자 이상만."""
    raw = re.sub(r"[^a-zA-Z0-9]+", " ", _clean(text).upper())
    stop = {
        "CO", "LTD", "LLC", "INC", "CORP", "COMPANY", "THE", "AND", "OF",
        "PTY", "SDN", "BHD", "JSC", "LIMITED", "PRIVATE", "JOINT", "STOCK",
        "GROUP", "BEAUTY", "LABS", "LAB", "SKIN", "CARE", "COSMETIC", "COSMETICS",
    }
    return {t for t in raw.split() if len(t) >= 4 and t not in stop}


def domain_match_score(company: str, domain: str, clearbit_name: str = "") -> float:
    """회사명 ↔ 도메인/Clearbit명 토큰 겹침 점수 (0~1).

    동명·엉뚱한 도메인(대학 .edu, 신문사 등)을 걸러내는 핵심 가드.
    0.3 미만은 후보에서 버린다.
    """
    tokens = _name_tokens(company) | _name_tokens(humanize_company_name(company))
    if not tokens:
        # REVLON 처럼 짧은 브랜드명
        compact = re.sub(r"[^a-zA-Z0-9]", "", company).upper()
        if len(compact) >= 4:
            tokens = {compact}
        else:
            return 0.0
    dom = domain.lower().split(":")[-1]
    if any(dom.endswith(tld) for tld in BLOCKED_TLDS):
        return 0.0
    if any(b in dom for b in BLOCKED_DOMAINS):
        return 0.0
    label = dom.split(".")[0].upper()
    label_tokens = _name_tokens(label.replace("-", " ")) | ({label} if len(label) >= 4 else set())
    cb_tokens = _name_tokens(clearbit_name)
    overlap = tokens & (label_tokens | cb_tokens)
    contains = {t for t in tokens if t in label or label in t}
    hits = overlap | contains
    if not hits:
        return 0.0
    score = len(hits) / max(len(tokens), 1)
    # 토큰 길이≥5 이고 도메인 라벨과 강하게 일치하면 가점
    if any(len(t) >= 5 and (t == label or t in label) for t in tokens):
        score = max(score, 0.67)
    return min(score, 1.0)


# ---------------------------------------------------------------------------
# 외부 호출: Clearbit · HTML 가져오기 · 연락처 추출
# ---------------------------------------------------------------------------
def clearbit_domains(query: str, company: str, limit: int = 5) -> list[dict[str, Any]]:
    """Clearbit 회사 자동완성으로 공식 도메인 후보를 가져온다.

    점수가 낮은 후보는 버리고, 브랜드와 맞는 .com 은 가산점.
    """
    if not query or len(query) < 2:
        return []
    try:
        resp = SESSION.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": query[:60]},
            timeout=12,
        )
        if not resp.ok:
            return []
        out = []
        for item in resp.json()[:limit]:
            domain = _clean(item.get("domain")).lower()
            cb_name = _clean(item.get("name"))
            if not domain:
                continue
            score = domain_match_score(company, domain, cb_name)
            if score < 0.3:
                continue
            label = domain.split(".")[0].upper()
            tokens = _name_tokens(company) | _name_tokens(humanize_company_name(company))
            if domain.endswith(".com") and any(
                t == label or label.startswith(t) for t in tokens if len(t) >= 5
            ):
                score = min(1.0, score + 0.15)
            out.append({"name": cb_name, "domain": domain, "score": score})
        out.sort(key=lambda x: x["score"], reverse=True)
        return out
    except Exception:
        return []


def fetch_html(url: str) -> str:
    """URL HTML을 가져온다. 실패·비HTML이면 ''.

    응답은 50만자까지만 잘라 메모리·정규식 비용을 제한한다.
    """
    try:
        resp = SESSION.get(url, timeout=12, allow_redirects=True)
        if not resp.ok:
            return ""
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "html" not in ctype and "text" not in ctype:
            return ""
        return resp.text[:500_000]
    except Exception:
        return ""


def extract_emails(html: str, domain: str) -> list[str]:
    """페이지에서 공개 이메일을 추출·정렬한다.

    우선순위: 같은 도메인 → info/contact/sales → 기타.
    noreply·이미지 확장자 오탐은 제거.
    """
    if not html:
        return []
    found: list[str] = []
    for m in MAILTO_RE.findall(html):
        found.append(m.lower())
    for m in EMAIL_RE.findall(html):
        found.append(m.lower())
    bad = (
        "noreply", "no-reply", "example.com", "domain.com",
        "email.com", "sentry.io", "wixpress", "cloudflare",
    )
    cleaned = []
    for email in found:
        if any(b in email for b in bad):
            continue
        if email.endswith((".png", ".jpg", ".gif", ".webp")):
            continue
        cleaned.append(email)

    def rank(e: str) -> tuple[int, int, str]:
        host = e.split("@")[-1]
        local = e.split("@")[0]
        same = 0 if domain and (host == domain or host.endswith("." + domain)) else 1
        role = 0 if local in {
            "info", "contact", "sales", "hello", "office", "enquiry", "inquiry"
        } else 1
        return (same, role, e)

    return sorted(set(cleaned), key=rank)


def extract_phones(html: str) -> list[str]:
    """페이지에서 대표번호 후보를 추출한다.

    날짜(2026-06-01)·반복 숫자·너무 짧은 숫자열 등 오탐을 걸러낸다.
    """
    if not html:
        return []
    phones = []
    for m in PHONE_RE.findall(html):
        text = re.sub(r"\s+", " ", m.strip())
        digits = re.sub(r"\D", "", text)
        if len(digits) < 8 or len(digits) > 15:
            continue
        if re.search(r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}", text):
            continue
        if digits.startswith("20") and len(digits) <= 10:
            continue
        if len(set(digits)) <= 2:
            continue
        # +, (), 공백, 하이픈 없는 짧은 숫자열은 제외
        if not re.search(r"[\+()]", text) and " " not in text and "-" not in text:
            if len(digits) < 10:
                continue
        phones.append(text)
    seen: set[str] = set()
    out = []
    for p in phones:
        key = re.sub(r"\D", "", p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= 3:
            break
    return out


# ---------------------------------------------------------------------------
# 바이어 1건 enrichment
# ---------------------------------------------------------------------------
def enrich_one(name: str, country: str) -> dict[str, Any]:
    """바이어 1건: 도메인 찾기 → 사이트 접속 → 이메일/전화 추출.

    반환: website, email, phone, method, score, candidates
    method 예: clearbit+scrape / no_domain / domain_unreachable
    """
    raw = _clean(name)
    queries = build_queries(raw)

    # Clearbit에 회사명 변형을 여러 번 보내 도메인 후보를 모은다.
    domains: list[dict[str, Any]] = []
    for q in queries:
        for item in clearbit_domains(q, company=raw):
            if item["domain"] not in {d["domain"] for d in domains}:
                domains.append(item)
        if len(domains) >= 3:
            break
        # 요청 속도 제한: Clearbit 연속 호출 사이 0.12초 대기 (차단 완화)
        time.sleep(0.12)
    # 점수 높은 순, 동점이면 .com 우선
    domains.sort(key=lambda x: (x.get("score", 0), x["domain"].endswith(".com")), reverse=True)

    result: dict[str, Any] = {
        "website": "",
        "email": "",
        "phone": "",
        "method": "",
        "score": 0.0,
        "clearbit_query": queries[0] if queries else "",
        "candidates": [f"{d['domain']}({d.get('score', 0):.2f})" for d in domains],
    }
    if not domains:
        result["method"] = "no_domain"
        return result

    # 상위 3개 중 실제로 열리는 첫 사이트를 공식 웹으로 채택
    picked = None
    html_home = ""
    base = ""
    for cand in domains[:3]:
        domain = cand["domain"]
        base_try = f"https://{domain}"
        html_try = fetch_html(base_try)
        if not html_try:
            html_try = fetch_html(f"http://{domain}")
            if html_try:
                base_try = f"http://{domain}"
        if not html_try:
            continue
        picked = cand
        html_home = html_try
        base = base_try
        break

    if not picked:
        result["method"] = "domain_unreachable"
        return result

    domain = picked["domain"]
    result["website"] = base
    result["score"] = float(picked.get("score") or 0)
    emails: list[str] = extract_emails(html_home, domain)
    phones: list[str] = extract_phones(html_home)

    # 홈에 없으면 /contact, /about 등 공개 페이지를 추가로 본다.
    for path in CONTACT_PATHS[1:]:
        if emails and phones:
            break
        html = fetch_html(urljoin(base + "/", path.lstrip("/")))
        if not html:
            continue
        if not emails:
            emails = extract_emails(html, domain)
        if not phones:
            phones = extract_phones(html)
        # 대상 사이트 연속 요청 간격 0.1초
        time.sleep(0.1)

    # 이메일은 동일 도메인만 확정 채움 (외부 도메인 메일은 오탐 많아 제외)
    same_domain_emails = [
        e
        for e in emails
        if e.split("@")[-1] == domain or e.split("@")[-1].endswith("." + domain)
    ]
    if same_domain_emails:
        result["email"] = same_domain_emails[0]
    if phones:
        result["phone"] = phones[0]
    result["method"] = "clearbit+scrape"
    return result


def select_targets(df: pd.DataFrame, limit: int | None) -> pd.DataFrame:
    """enrich 대상: 우선 소스 ∩ 회사명 있음 ∩ 웹사이트 비어 있음."""
    mask_src = df["source_dataset"].isin(PRIORITY_SOURCES)
    mask_name = df["normalized_name"].map(_clean).ne("")
    mask_no_web = df["contact_website"].map(_clean).eq("")
    targets = df[mask_src & mask_name & mask_no_web].copy()
    if limit is not None:
        targets = targets.head(limit)
    return targets


# ---------------------------------------------------------------------------
# 메인 루프: CSV 읽고 → 한 행씩 채움 → 리포트
# ---------------------------------------------------------------------------
def main(limit: int | None = None, sleep_s: float = 0.35) -> int:
    """우선 풀 바이어를 한 행씩 enrichment한다.

    - 원본에 이미 값이 있으면 덮어쓰지 않음
    - 새로 채운 이메일은 contact_email_estimated=True
    - sleep_s: 바이어 행과 다음 행 사이 대기 초 (CLI --sleep)
    """
    df = pd.read_csv(BUYER_CSV, dtype=str, encoding="utf-8-sig", low_memory=False)
    for col in (
        "contact_website", "contact_email", "contact_phone",
        "has_contact", "contact_email_estimated",
    ):
        if col not in df.columns:
            df[col] = ""

    targets = select_targets(df, limit)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_rows": int(len(targets)),
        "website_filled": 0,
        "email_filled": 0,
        "phone_filled": 0,
        "no_domain": 0,
        "unreachable": 0,
        "errors": 0,
        "samples": [],
    }

    for i, (idx, row) in enumerate(targets.iterrows(), start=1):
        name = _clean(row.get("normalized_name"))
        country = _clean(row.get("country_norm"))
        try:
            got = enrich_one(name, country)
        except Exception as exc:  # noqa: BLE001
            stats["errors"] += 1
            got = {
                "website": "", "email": "", "phone": "",
                "method": f"error:{type(exc).__name__}",
            }

        # --- 빈 칸만 채움 (기존 값 보존) ---
        changed = {}
        if got.get("website") and not _clean(df.at[idx, "contact_website"]):
            df.at[idx, "contact_website"] = got["website"]
            stats["website_filled"] += 1
            changed["contact_website"] = got["website"]
        if got.get("email") and not _clean(df.at[idx, "contact_email"]):
            df.at[idx, "contact_email"] = got["email"]
            # 스크래핑 메일은 '추정/보강' → 자동발송에 확정값처럼 쓰지 말 것
            df.at[idx, "contact_email_estimated"] = "True"
            stats["email_filled"] += 1
            changed["contact_email"] = got["email"]
        if got.get("phone") and not _clean(df.at[idx, "contact_phone"]):
            df.at[idx, "contact_phone"] = got["phone"]
            stats["phone_filled"] += 1
            changed["contact_phone"] = got["phone"]

        if (
            _clean(df.at[idx, "contact_email"])
            or _clean(df.at[idx, "contact_phone"])
            or _clean(df.at[idx, "contact_website"])
        ):
            df.at[idx, "has_contact"] = "True"

        if got.get("method") == "no_domain":
            stats["no_domain"] += 1
        elif got.get("method") == "domain_unreachable":
            stats["unreachable"] += 1

        # 건별 로그. 오탐 시 changed 기준으로 롤백 가능
        rec = {
            "i": i,
            "idx": int(idx) if isinstance(idx, int) else str(idx),
            "name": name[:80],
            "country": country,
            "method": got.get("method"),
            "candidates": got.get("candidates", []),
            "changed": changed,
        }
        with CHECKPOINT_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if len(stats["samples"]) < 25 and changed:
            stats["samples"].append(rec)

        # 25건마다 CSV·리포트 중간 저장 (중단돼도 진행분 보존)
        if i % 25 == 0 or i == len(targets):
            print(
                f"[{i}/{len(targets)}] web={stats['website_filled']} "
                f"email={stats['email_filled']} phone={stats['phone_filled']} "
                f"no_domain={stats['no_domain']}"
            )
            df.to_csv(BUYER_CSV, index=False, encoding="utf-8-sig")
            REPORT_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

        # 바이어 1건 후 다음 건까지 대기 (기본 0.35초). 분당 요청 수 제한.
        time.sleep(sleep_s)

    df.to_csv(BUYER_CSV, index=False, encoding="utf-8-sig")

    prio = df[df["source_dataset"].isin(PRIORITY_SOURCES)]
    stats["after_priority"] = {
        "rows": int(len(prio)),
        "with_website": int(prio["contact_website"].map(_clean).ne("").sum()),
        "with_email": int(prio["contact_email"].map(_clean).ne("").sum()),
        "with_phone": int(prio["contact_phone"].map(_clean).ne("").sum()),
    }
    stats["after_all"] = {
        "rows": int(len(df)),
        "with_website": int(df["contact_website"].map(_clean).ne("").sum()),
        "with_email": int(df["contact_email"].map(_clean).ne("").sum()),
        "with_phone": int(df["contact_phone"].map(_clean).ne("").sum()),
    }
    REPORT_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="우선 풀 바이어 웹/이메일/전화 enrichment (원본 값 덮어쓰기 안 함)"
    )
    parser.add_argument("--limit", type=int, default=None, help="최대 처리 건수 (테스트용)")
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.35,
        help="바이어 행 사이 대기 초(기본 0.35). 작을수록 빠르지만 차단 위험↑",
    )
    args = parser.parse_args()
    raise SystemExit(main(limit=args.limit, sleep_s=args.sleep))
