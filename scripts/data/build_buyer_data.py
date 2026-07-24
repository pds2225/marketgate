"""
build_buyer_data.py
실제 바이어 데이터(buyer_candidate.csv)를 프론트엔드 화면용 JSON으로 변환한다.
- 집계: 국가/품목(HS)/출처/연락처 통계 (전체 36,241건)
- 샘플: 화면 표시용 바이어 카드 (회사명 정리, 연락처 마스킹, 출처기반 신뢰도)

입력 인코딩은 utf-8-sig (replacement-char 0으로 판별됨).
민감정보(이메일/전화)는 반드시 마스킹하여 출력한다.

실행:
  python scripts/data/build_buyer_data.py
출력:
  apps/frontend-react/public/data/summary.json
  apps/frontend-react/public/data/buyers.json
"""
import csv, io, json, os, re
from collections import Counter, defaultdict
from pathlib import Path

# --- paths ---
REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT = Path(
    os.getenv(
        "BUYER_DATA_INPUT",
        str(
            REPO_ROOT
            / "services"
            / "cosmetics_mvp_preprocess"
            / "output"
            / "buyer_candidate.csv"
        ),
    )
)
OUT_DIR = Path(
    os.getenv(
        "BUYER_DATA_OUTPUT_DIR",
        str(REPO_ROOT / "apps" / "frontend-react" / "public" / "data"),
    )
)

# --- lookups ---
ISO3_TO_FLAG = {
    "IND":"🇮🇳","USA":"🇺🇸","PHL":"🇵🇭","PAK":"🇵🇰","VNM":"🇻🇳","IDN":"🇮🇩","NGA":"🇳🇬",
    "CHN":"🇨🇳","ARG":"🇦🇷","GHA":"🇬🇭","JPN":"🇯🇵","BGD":"🇧🇩","MAR":"🇲🇦","ROU":"🇷🇴",
    "MEX":"🇲🇽","KAZ":"🇰🇿","ARE":"🇦🇪","MYS":"🇲🇾","THA":"🇹🇭","RUS":"🇷🇺","TUR":"🇹🇷",
    "EGY":"🇪🇬","GBR":"🇬🇧","DEU":"🇩🇪","FRA":"🇫🇷","ITA":"🇮🇹","ESP":"🇪🇸","BRA":"🇧🇷",
    "KOR":"🇰🇷","TWN":"🇹🇼","SGP":"🇸🇬","SAU":"🇸🇦","ZAF":"🇿🇦","KEN":"🇰🇪","UKR":"🇺🇦",
    "POL":"🇵🇱","NLD":"🇳🇱","AUS":"🇦🇺","CAN":"🇨🇦","COL":"🇨🇴","PER":"🇵🇪","CHL":"🇨🇱",
}
# HS 코드 → 한글 라벨 (상위 품목 위주)
HS_LABEL = {
    "330499":"기초화장품·스킨케어","330410":"색조화장품","330510":"헤어케어","330510":"헤어케어",
    "330520":"퍼머·염색","330590":"기타 두발용품","330590":"기타 두발용품","330610":"치약·구강",
    "330749":"방향·탈취","210690":"건강기능식품","190590":"베이커리·과자","340130":"비누",
    "340130":"비누","340111":"미용비누","854370":"전기기기","854140":"반도체소자","853649":"전기접속기",
    "300490":"의약품","852329":"기록매체","330741":"향","330300":"향수","330590":"두발용품",
}
def hs_label(hs):
    hs6 = (hs or "").strip().replace(".0","")[:6]
    if not hs6 or not hs6.isdigit():
        return "기타"
    if hs6 in HS_LABEL:
        return HS_LABEL[hs6]
    h2 = hs6[:2]
    return {"33":"화장품·향료","21":"식품","34":"비누·세제","85":"전자·전기","30":"의약품",
            "19":"식품(곡물가공)","62":"의류","64":"신발"}.get(h2, "기타")

# 출처 → (짧은 이름, 신뢰 등급 가중)
def source_short(src):
    s = src or ""
    if "대한무역투자진흥공사_SNS" in s: return "KOTRA SNS"
    if "buyKOREA" in s: return "KOTRA buyKOREA"
    if "대한무역투자진흥공사" in s: return "KOTRA"
    if "정보통신산업진흥원" in s: return "NIPA ICT"
    if "한국무역보험공사" in s: return "무역보험공사"
    if "중소벤처기업진흥공단" in s or "GoBiz" in s: return "GoBizKorea"
    if "EC21" in s: return "EC21"
    if "ITC" in s or "TradeMap" in s: return "ITC TradeMap"
    return s[:20] or "기타"

OFFICIAL = {"KOTRA SNS","KOTRA buyKOREA","KOTRA","NIPA ICT","무역보험공사","GoBizKorea","ITC TradeMap"}

def clean_name(title, normalized):
    """공백제거 raw 회사명을 표시용으로 정리(괄호 약칭 우선, 타이틀케이스)."""
    t = (title or "").strip()
    if not t:
        t = (normalized or "").strip()
    # FULLNAME(SHORT) → SHORT 사용 시 더 짧고 읽기 쉬움
    m = re.match(r"^(.*?)\(([^)]+)\)\s*$", t)
    core = t
    if m:
        full, short = m.group(1), m.group(2)
        core = short if 0 < len(short) <= len(full) else full
    core = core.strip()
    # 전부 대문자+무공백이면 타이틀케이스로 가독성↑ (단어분리는 불가하므로 그대로)
    if core and core.upper() == core:
        core = core.title()
    return core[:48] if core else "(이름 미상)"

def mask_email(e):
    e = (e or "").strip()
    if "@" not in e: return ""
    user, _, dom = e.partition("@")
    u = (user[:2] + "***") if len(user) > 2 else (user[:1] + "***")
    parts = dom.split(".")
    tld = parts[-1] if len(parts) > 1 else ""
    return f"{u}@***.{tld}" if tld else f"{u}@***"

def mask_phone(p):
    p = (p or "").strip()
    if not p: return ""
    digits = re.sub(r"\D", "", p)
    if len(digits) < 4: return "***"
    return digits[:3] + "*"*max(0,len(digits)-6) + digits[-2:]

# --- load ---
raw = open(INPUT, "rb").read().decode("utf-8-sig", errors="replace")
rows = list(csv.DictReader(io.StringIO(raw)))
n = len(rows)

# --- aggregates ---
def norm(row, k): return (row.get(k) or "").strip()

country_counter = Counter()
country_iso = {}
for row in rows:
    cn = norm(row, "country_norm")
    if cn:
        country_counter[cn] += 1
        iso = norm(row, "country_iso3")
        if iso and cn not in country_iso:
            country_iso[cn] = iso

hs_counter = Counter()
for row in rows:
    hs6 = norm(row, "hs_code_norm").replace(".0","")[:6]
    if hs6.isdigit():
        hs_counter[hs6] += 1

source_counter = Counter(source_short(norm(row,"source_dataset")) for row in rows)

# 데이터 수집 추이(연도별) — '바이어 데이터 수집' 현황용
year_counter = Counter()
for row in rows:
    sd = norm(row, "source_snapshot_date")
    y = sd[:4] if len(sd) >= 4 and sd[:4].isdigit() else "미상"
    year_counter[y] += 1

has_contact = sum(1 for r in rows if norm(r,"has_contact") in ("1","True","true"))
email = sum(1 for r in rows if norm(r,"contact_email"))
phone = sum(1 for r in rows if norm(r,"contact_phone"))
web = sum(1 for r in rows if norm(r,"contact_website"))
estimated = sum(1 for r in rows if norm(r,"contact_email_estimated").lower()=="true")

summary = {
    "total": n,
    "generatedFrom": "buyer_candidate.csv",
    "byCountry": [
        {"name": cn, "iso3": country_iso.get(cn,""), "flag": ISO3_TO_FLAG.get(country_iso.get(cn,""),"🌐"),
         "count": ct}
        for cn, ct in country_counter.most_common(12)
    ],
    "byHs": [
        {"hs": hs, "label": hs_label(hs), "count": ct}
        for hs, ct in hs_counter.most_common(10)
    ],
    "bySource": [
        {"name": s, "count": ct, "official": s in OFFICIAL}
        for s, ct in source_counter.most_common(10)
    ],
    "contact": {
        "hasContact": has_contact, "hasContactPct": round(has_contact*100/n,1),
        "email": email, "phone": phone, "website": web, "emailEstimated": estimated,
    },
    "countryCount": len({norm(r,"country_iso3") for r in rows
                         if re.fullmatch(r"[A-Z]{3}", norm(r,"country_iso3") or "")}),
    "bySnapshotYear": [
        {"year": y, "count": ct}
        for y, ct in sorted(year_counter.items()) if y != "미상"
    ],
}

# --- sample buyers for the list view ---
# 다양성: 연락처 보유 레코드 우선 + 국가/품목 다양화
def trust_level(row):
    src = source_short(norm(row,"source_dataset"))
    hc = norm(row,"has_contact") in ("1","True","true")
    est = norm(row,"contact_email_estimated").lower()=="true"
    if src in OFFICIAL and hc and not est: return "platinum"
    if src in OFFICIAL and hc: return "gold"
    if src in OFFICIAL: return "gold"
    return "silver"

# 연락처 보유 + HS 유효 레코드를 우선 채택, 국가별 골고루
contactful = [r for r in rows if norm(r,"has_contact") in ("1","True","true") and norm(r,"country_iso3")]
by_country = defaultdict(list)
for r in contactful:
    by_country[norm(r,"country_norm")].append(r)

# 라운드로빈으로 국가 다양성 확보, 최대 60건
SAMPLE_N = 240  # 필터·매칭이 의미있게 동작하도록 국가 다양성 확보한 샘플 수
selected = []
order = [cn for cn,_ in country_counter.most_common() if cn in by_country]
idx = defaultdict(int)
while len(selected) < SAMPLE_N:
    progressed = False
    for cn in order:
        lst = by_country[cn]
        i = idx[cn]
        if i < len(lst):
            selected.append(lst[i]); idx[cn]+=1; progressed=True
            if len(selected) >= SAMPLE_N: break
    if not progressed: break

def kw_product(row):
    kw = norm(row,"keywords_norm")
    first = kw.split("|")[0].strip() if kw else ""
    return first[:24] if first else "화장품"

buyers = []
for i, row in enumerate(selected):
    cn = norm(row,"country_norm"); iso = norm(row,"country_iso3")
    hs6 = norm(row,"hs_code_norm").replace(".0","")[:6]
    dist = norm(row,"distance_from_kr_km")
    try: dist_km = round(float(dist)) if dist else None
    except: dist_km = None
    buyers.append({
        "id": f"BC-{i+1:03d}",
        "name": clean_name(norm(row,"title"), norm(row,"normalized_name")),
        "country": cn, "iso3": iso, "flag": ISO3_TO_FLAG.get(iso,"🌐"),
        "industry": kw_product(row),
        "hs": hs6 if (len(hs6) == 6 and hs6.isdigit()) else "",
        "hsLabel": hs_label(hs6) if (len(hs6) == 6 and hs6.isdigit()) else "",
        "source": source_short(norm(row,"source_dataset")),
        "trust": trust_level(row),
        "hasContact": True,
        "emailMasked": mask_email(norm(row,"contact_email")),
        "phoneMasked": mask_phone(norm(row,"contact_phone")),
        "website": norm(row,"contact_website")[:40],
        "emailEstimated": norm(row,"contact_email_estimated").lower()=="true",
        "distanceKm": dist_km,
    })

OUT_DIR.mkdir(parents=True, exist_ok=True)
with (OUT_DIR / "summary.json").open("w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
with (OUT_DIR / "buyers.json").open("w", encoding="utf-8") as f:
    json.dump(buyers, f, ensure_ascii=False, indent=2)

print(f"rows={n}  countries={summary['countryCount']}  buyers_sampled={len(buyers)}")
print("wrote:", OUT_DIR / "summary.json")
print("wrote:", OUT_DIR / "buyers.json")
