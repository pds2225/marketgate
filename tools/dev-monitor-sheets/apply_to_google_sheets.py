#!/usr/bin/env python3
"""Apply section CSVs to an existing Google Spreadsheet (11 tabs).

Auth (pick one):
  GOOGLE_SERVICE_ACCOUNT_JSON  — raw JSON string of a GCP service account key
  GOOGLE_SERVICE_ACCOUNT_FILE  — path to the same JSON file

Share the target spreadsheet with the service account email as Editor.

Env:
  SPREADSHEET_ID  — default: MarketGate 개발 모니터링 v3 id
  DRY_RUN=1       — print planned ops only

After write, re-reads sheet titles + sample cells (LESSONS L003).
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import jwt
import requests

HERE = Path(__file__).resolve().parent
DEFAULT_SPREADSHEET_ID = "1lmzSGu0fPYwVaoP82n-9tbMGtUmzE_G1j2wcblZldQg"
SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_URI = "https://oauth2.googleapis.com/token"

SHEETS = [
    ("개요", "01_개요.csv"),
    ("개발과제", "02_개발과제.csv"),
    ("작업분해", "03_작업분해.csv"),
    ("아키텍처", "04_아키텍처.csv"),
    ("수집소스", "05_수집소스.csv"),
    ("상품가격", "06_상품가격.csv"),
    ("법률규제", "07_법률규제.csv"),
    ("검증기록", "08_검증기록.csv"),
    ("KPI기준", "09_KPI기준.csv"),
    ("오답노트", "10_오답노트.csv"),
    ("원문목록", "11_원문목록.csv"),
]


def load_sa() -> dict:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        return json.loads(raw)
    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    print(
        "ERROR: set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE",
        file=sys.stderr,
    )
    sys.exit(2)


def access_token(sa: dict) -> str:
    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": sa["client_email"],
            "scope": SCOPE,
            "aud": TOKEN_URI,
            "iat": now,
            "exp": now + 3600,
        },
        sa["private_key"],
        algorithm="RS256",
    )
    r = requests.post(
        TOKEN_URI,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def api(token: str, method: str, url: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    r = requests.request(method, url, headers=headers, timeout=120, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {url} -> {r.status_code}: {r.text[:800]}")
    return r.json() if r.content else {}


def read_csv(name: str) -> list[list[str]]:
    path = HERE / name
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [list(row) for row in csv.reader(f)]


def col_a1(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def main() -> int:
    dry = os.environ.get("DRY_RUN", "").strip() in {"1", "true", "TRUE", "yes"}
    sid = os.environ.get("SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID).strip()
    sa = load_sa()
    print(f"SA: {sa.get('client_email')}")
    print(f"Spreadsheet: {sid}")
    print(f"DRY_RUN={dry}")

    payloads = [(title, read_csv(fname)) for title, fname in SHEETS]
    for title, rows in payloads:
        cols = max((len(r) for r in rows), default=0)
        print(f"  plan: [{title}] {len(rows)} rows x {cols} cols")

    if dry:
        print("DRY_RUN done — no write")
        return 0

    token = access_token(sa)
    meta = api(
        token,
        "GET",
        f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
        "?fields=sheets.properties(sheetId,title,index)",
    )
    existing = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in meta.get("sheets", [])
    }
    print("existing tabs:", sorted(existing))

    requests_body: list[dict] = []
    # Ensure target tabs exist (create missing)
    for title, _ in payloads:
        if title not in existing:
            requests_body.append(
                {"addSheet": {"properties": {"title": title}}}
            )

    if requests_body:
        resp = api(
            token,
            "POST",
            f"https://sheets.googleapis.com/v4/spreadsheets/{sid}:batchUpdate",
            json={"requests": requests_body},
        )
        for rep in resp.get("replies", []):
            props = rep.get("addSheet", {}).get("properties", {})
            if props:
                existing[props["title"]] = props["sheetId"]
                print(f"created tab: {props['title']} id={props['sheetId']}")

    # Clear + write each tab. valueInputOption=RAW avoids date auto-parse (L003).
    for title, rows in payloads:
        clear_range = quote(f"'{title}'", safe="")
        api(
            token,
            "POST",
            f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/"
            f"{clear_range}:clear",
            json={},
        )
        if not rows:
            continue
        cols = max(len(r) for r in rows)
        end = f"{col_a1(cols)}{len(rows)}"
        range_a1 = f"'{title}'!A1:{end}"
        api(
            token,
            "PUT",
            f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/"
            f"{quote(range_a1, safe='!:')}"
            "?valueInputOption=RAW",
            json={"range": range_a1, "majorDimension": "ROWS", "values": rows},
        )
        print(f"wrote [{title}] -> {range_a1}")

    # L003 re-read
    meta2 = api(
        token,
        "GET",
        f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
        "?fields=sheets.properties(title)",
    )
    titles = [s["properties"]["title"] for s in meta2.get("sheets", [])]
    print("re-read titles:", titles)
    missing = [t for t, _ in payloads if t not in titles]
    if missing:
        raise RuntimeError(f"missing tabs after write: {missing}")

    sample = api(
        token,
        "GET",
        f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/"
        f"{quote(chr(39) + '개발과제' + chr(39) + '!A1:C2', safe='!:')}",
    )
    values = sample.get("values", [])
    print("re-read 개발과제 A1:C2:", values)
    local = payloads[1][1]
    if not values or values[0][:3] != local[0][:3]:
        raise RuntimeError("header mismatch after write")
    if len(values) < 2 or values[1][0] != local[1][0]:
        raise RuntimeError("row1 mismatch after write")
    # related-source field must keep middle-dot, not become a date
    if len(values[1]) > 2 and "·" not in values[1][2]:
        raise RuntimeError(f"L003 date-coerce suspected: {values[1][2]!r}")

    print("VERIFY_OK")
    print(f"URL: https://docs.google.com/spreadsheets/d/{sid}/edit")
    return 0


if __name__ == "__main__":
    # requests.utils used above
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)
