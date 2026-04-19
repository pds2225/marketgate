"""
P1 수출 추천국 데모 — Streamlit UI
FastAPI 서버(uvicorn main:app --reload)와 별도로 실행:
  streamlit run streamlit_app.py
"""

import json
from typing import List, Optional
import requests
import streamlit as st

st.set_page_config(page_title="P1 수출 추천국 데모", layout="wide", page_icon="🌏")

# ── 헤더 ──────────────────────────────────────────────
st.title("🌏 수출 추천국 데모 (P1)")
st.caption("HS Code와 수출국을 입력하면 AI가 최적 수출 대상국을 점수화하여 추천합니다.")

# ── 사이드바: API 설정 ────────────────────────────────
with st.sidebar:
    st.header("⚙️ API 설정")
    api_base = st.text_input("API Base URL", value="http://localhost:8000")
    timeout_sec = st.number_input("Timeout (sec)", min_value=1, max_value=120, value=30)

    st.divider()
    st.subheader("📌 자주 쓰는 HS Code")
    presets = {
        "화장품 (330499)": "330499",
        "반도체 (854231)": "854231",
        "자동차부품 (870899)": "870899",
        "라면/식품 (190230)": "190230",
        "배터리 (850650)": "850650",
    }
    preset = st.selectbox("프리셋 선택", ["직접 입력"] + list(presets.keys()))

# ── 입력 폼 ───────────────────────────────────────────
st.subheader("📋 요청 입력")

col1, col2, col3 = st.columns(3)

with col1:
    default_hs = presets.get(preset, "330499") if preset != "직접 입력" else "330499"
    hs_code = st.text_input("HS Code (6자리, 필수)", value=default_hs, max_chars=6)
    year = st.number_input("기준 연도", min_value=2000, max_value=2100, value=2023, step=1)

with col2:
    exporter_iso3 = st.text_input("수출국 ISO3 (필수)", value="KOR", max_chars=3,
                                   help="KOR=한국, USA=미국, JPN=일본, CHN=중국")
    top_n = st.slider("추천 국가 수 (top_n)", min_value=1, max_value=20, value=10)

with col3:
    min_trade_value_usd = st.number_input("최소 무역액 (USD)", min_value=0.0, value=0.0, step=10000.0)
    exclude_iso3_text = st.text_input("제외 국가 ISO3 (쉼표 구분)", value="",
                                       placeholder="예: PRK,IRN,RUS")

def parse_exclude_list(text: str) -> Optional[List[str]]:
    text = (text or "").strip()
    if not text:
        return None
    parts = [p.strip().upper() for p in text.split(",") if p.strip()]
    return parts or None

exclude_list = parse_exclude_list(exclude_iso3_text)

payload = {
    "hs_code": (hs_code or "").strip(),
    "exporter_country_iso3": (exporter_iso3 or "").strip().upper(),
    "top_n": int(top_n),
    "year": int(year),
    "filters": {
        "exclude_countries_iso3": exclude_list,
        "min_trade_value_usd": float(min_trade_value_usd),
    },
}

with st.expander("🔍 요청 JSON 미리보기"):
    st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")

# ── 실행 버튼 ─────────────────────────────────────────
submit = st.button("🚀 추천 요청 실행", type="primary", use_container_width=True)
st.divider()

# ── 응답 처리 ─────────────────────────────────────────
if submit:
    if len((hs_code or "").strip()) != 6 or not (hs_code or "").strip().isdigit():
        st.error("❌ HS Code는 숫자 6자리여야 합니다.")
        st.stop()
    if len((exporter_iso3 or "").strip()) != 3:
        st.error("❌ 수출국 ISO3는 영문 3자리여야 합니다.")
        st.stop()

    url = api_base.rstrip("/") + "/v1/predict"
    st.write(f"📡 요청 URL: `{url}`")

    try:
        with st.spinner("API 호출 중..."):
            resp = requests.post(url, json=payload, timeout=int(timeout_sec))

        st.write(f"HTTP Status: **{resp.status_code}**")

        try:
            data = resp.json()
        except Exception:
            st.error("응답이 JSON이 아닙니다.")
            st.text(resp.text)
            st.stop()

        if resp.status_code != 200:
            st.error("요청 실패")
            st.json(data)
            st.stop()

        st.success("✅ 요청 성공")

        results = (((data or {}).get("data") or {}).get("results")) or []
        if not results:
            st.info("결과가 비어 있습니다. (후보 없음 또는 필터로 모두 제외)")
            st.stop()

        # ── 요약 테이블 ───────────────────────────────
        st.subheader(f"🏆 추천 결과 TOP {len(results)}")

        rows = []
        for r in results:
            sc = r.get("score_components") or {}
            rows.append({
                "순위": r.get("rank"),
                "국가(ISO3)": r.get("partner_country_iso3"),
                "종합점수": r.get("fit_score"),
                "무역량점수": sc.get("trade_volume_score"),
                "성장률점수": sc.get("growth_score"),
                "GDP점수": sc.get("gdp_score"),
                "거리점수": sc.get("distance_score"),
                "소프트패널티": sc.get("soft_adjustment"),
            })

        st.dataframe(rows, use_container_width=True)

        # ── 점수 바 차트 ──────────────────────────────
        st.subheader("📊 종합 적합도 점수 비교")
        chart_data = {r["국가(ISO3)"]: r["종합점수"] for r in rows}
        st.bar_chart(chart_data)

        # ── 상세 보기 ─────────────────────────────────
        st.subheader("🔎 국가별 상세 보기")
        for r in results:
            score = r.get("fit_score")
            iso3 = r.get("partner_country_iso3")
            rank = r.get("rank")
            with st.expander(f"#{rank}  {iso3}  — 종합점수: {score}점"):
                st.json(r)

    except requests.exceptions.ConnectionError:
        st.error("❌ API 서버에 연결할 수 없습니다. `uvicorn main:app --reload` 실행 여부를 확인하세요.")
    except requests.exceptions.Timeout:
        st.error("❌ 요청 시간이 초과됐습니다. Timeout 값을 늘려보세요.")
    except requests.exceptions.RequestException as e:
        st.error("API 호출 오류")
        st.code(str(e))
