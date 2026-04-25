#!/usr/bin/env python3
"""diagnose_hs_mismatch.py — hs_mismatch 원인 진단 (읽기 전용, task05/06 import 금지)"""
import sys, csv
from pathlib import Path
from datetime import datetime
from collections import Counter

# task05_shortlist.py COSMETICS_HS_RULES / KEYWORD_MATCH_STOPWORDS 독립 복제
COSM_KW = {
    "cosmetic","cosmetics","makeup","skin care","skincare","serum","cream","lotion",
    "moisturizer","emulsion","ampoule","mask","sunscreen","sunblock","sun cream",
    "toner","essence","cleanser","cleansing foam","face cream","eye cream","beauty",
    "세럼","크림","로션","보습","유액","에멀전","앰플","마스크","선크림","선블록",
    "토너","에센스","클렌저","클렌징","페이스크림","아이크림","스킨케어","화장품","메이크업","미용",
}
STOPWORDS = {
    "skin","care","beauty","skincare","beautycare","general","product","products",
    "item","items","goods","offer","inquiry","inquiries","inquire","consultation",
    "consult","request","signal","sample","test","demo","dummy","example",
    "피부","케어","뷰티","일반","상품","제품","오퍼","문의","상담","요청","샘플","테스트","더미",
}
COLS = ["hs_code_norm","keywords_norm","keywords_raw","product_name_norm",
        "product_name_raw","title","description","category","normalized_name"]
REASONS = ["empty_text_signal","missing_hs_only","stopwords_only_keyword",
           "weak_cosmetics_keyword","non_cosmetics_product","country_only_match","unknown"]
DESC = {
    "empty_text_signal":      "모든 텍스트 필드 비어 있음 → HS 추론 불가",
    "missing_hs_only":        "HS 코드 없지만 화장품 키워드 존재",
    "stopwords_only_keyword": "키워드가 STOPWORDS만으로 구성 → task05에서 필터링됨",
    "weak_cosmetics_keyword": "화장품 키워드 부재",
    "non_cosmetics_product":  "HS 코드가 33xx 범주 외",
    "country_only_match":     "국가 정보만 있고 상품 신호 없음",
    "unknown":                "위 패턴 미해당",
}

def hs_norm(v): return "".join(c for c in str(v or "") if c.isdigit())
def is_cosm_hs(h): return bool(h) and h.startswith("33")
def terms(row):
    t = set()
    for c in COLS[1:]:
        for w in str(row.get(c,"") or "").replace("|"," ").replace(","," ").lower().split():
            if len(w) > 1: t.add(w.strip())
    return t
def text_empty(row): return all(not str(row.get(c,"") or "").strip() for c in COLS[1:])
def has_cosm(t): return bool(t & COSM_KW)
def stop_only(t): return bool(t) and not (t - STOPWORDS)

def classify(row):
    h = hs_norm(row.get("hs_code_norm",""))
    cn = str(row.get("country_norm","") or row.get("country","") or "")
    t = terms(row)
    if text_empty(row): return "empty_text_signal"
    if not h and has_cosm(t): return "missing_hs_only"
    if h and not is_cosm_hs(h): return "non_cosmetics_product"
    if stop_only(t): return "stopwords_only_keyword"
    if not has_cosm(t): return "country_only_match" if cn else "weak_cosmetics_keyword"
    return "unknown"

def is_candidate(row):
    h = hs_norm(row.get("hs_code_norm",""))
    return not h or not is_cosm_hs(h)

def load(path):
    for enc in ("utf-8-sig","utf-8","cp949","euc-kr"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return [{k:(v or "") for k,v in r.items()} for r in csv.DictReader(f)]
        except Exception: pass
    return []

def null_rates(rows):
    n = len(rows)
    return {c:{"e":sum(1 for r in rows if not str(r.get(c,"")).strip()),
               "r":sum(1 for r in rows if not str(r.get(c,"")).strip())/n if n else 0}
            for c in COLS}

def build_md(fp, rows, cands, nr, rc):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n, nc = len(rows), len(cands)
    L = [f"# hs_mismatch 진단 리포트",
         f"> {now} | `{fp.name}` | tools/diagnose_hs_mismatch.py\n",
         "## 1. 요약\n|항목|값|\n|---|---|",
         f"|전체|{n:,}|\n|hs_mismatch 후보|{nc:,} ({nc/n*100:.1f}%)|\n|정상|{n-nc:,}|\n",
         "## 2. 컬럼 빈값 비율\n|컬럼|빈값률|상태|\n|---|---|---|"]
    for c,s in nr.items():
        p=s["r"]*100; f="⚠️위험" if p>70 else("⚠️주의" if p>40 else "✅양호")
        L.append(f"|`{c}`|{p:.1f}%|{f}|")
    L += ["\n## 3. 실패 원인\n|원인|건수|비율|설명|\n|---|---|---|---|"]
    for r in REASONS:
        cnt=rc.get(r,0); p=cnt/nc*100 if nc else 0
        L.append(f"|`{r}`|{cnt}|{p:.1f}%|{DESC[r]}|")
    if rc:
        top,tc=rc.most_common(1)[0]
        L.append(f"\n> **주요 원인:** `{top}` {tc}건 — {DESC[top]}")
    L += ["\n## 4. 상위 20건\n|#|title|hs_code_norm|keywords_norm|실패원인|\n|---|---|---|---|---|"]
    for i,row in enumerate(cands[:20],1):
        ti=(row.get("title") or row.get("normalized_name") or "(없음)")[:35]
        h=row.get("hs_code_norm","") or "—"; kw=(row.get("keywords_norm","") or "")[:25]
        L.append(f"|{i}|{ti}|`{h}`|{kw}|`{row.get('_r','')}`|")
    L += ["\n## 5. Codex 충돌 가능성\n> **없음.** task05/06 import 없음. output CSV 읽기만.",
          "\n## 6. 다음 프롬프트\n```\nTASK-05: KEYWORD_MATCH_STOPWORDS에서 beauty/skincare/skin을\n"
          "화장품 컨텍스트 예외 처리하여 hs_mismatch 감소 시도.\n"
          "tests/test_task05_shortlist.py 전체 통과 필수.\n```"]
    return "\n".join(L)

def main(arg=None):
    base = Path(__file__).parent.parent
    paths = [base/"output"/"buyer_candidate.csv", base/"output"/"opportunity_item.csv"]
    if arg: paths.insert(0, Path(arg))
    fp = next((p for p in paths if p.exists() and p.stat().st_size>0), None)
    if not fp:
        print("[diagnose] output/ 파일 없음. preprocess_cosmetics.py 먼저 실행하세요.")
        skip = {"__pycache__",".git",".test_artifacts"}
        found = [f for f in sorted(base.glob("**/*.csv"))
                 if not any(p in f.parts for p in skip) and f.stat().st_size>100]
        if found:
            print("  발견 후보:"); [print(f"    {f.relative_to(base)}") for f in found]
            print("  실행: python tools/diagnose_hs_mismatch.py <파일경로>")
        sys.exit(1)
    rows = load(fp); print(f"\n[diagnose] {fp.name} — {len(rows):,} 레코드")
    cands=[]; rc=Counter()
    for row in rows:
        if is_candidate(row):
            r=classify(row); row["_r"]=r; rc[r]+=1; cands.append(row)
    print(f"  hs_mismatch 후보: {len(cands):,} ({len(cands)/len(rows)*100:.1f}%)")
    nr = null_rates(rows)
    SEP="="*55
    print(f"\n{SEP}\n 컬럼 빈값 비율\n{SEP}")
    for c,s in nr.items():
        p=s["r"]*100; bar="█"*int(p/5)+"░"*(20-int(p/5))
        print(f"  {c:<28}{p:5.1f}% [{bar}]{'  ⚠' if p>50 else ''}")
    print(f"\n{SEP}\n 실패 원인 분류\n{SEP}")
    for r,cnt in rc.most_common():
        print(f"  {r:<34}{cnt:4d}건 ({cnt/len(cands)*100:.1f}%)")
    print(f"\n{SEP}\n 상위 20건 샘플\n{SEP}")
    for i,row in enumerate(cands[:20],1):
        ti=(row.get("title") or row.get("normalized_name") or "(없음)")[:40]
        print(f"  {i:2d}. [{row.get('_r',''):<28}] {ti}")
    dp = base/"docs"; dp.mkdir(exist_ok=True)
    rp = dp/"hs_mismatch_diagnosis.md"
    rp.write_text(build_md(fp,rows,cands,nr,rc), encoding="utf-8")
    print(f"\n[diagnose] 리포트: {rp}\n")

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else None)
