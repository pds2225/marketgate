"""
P1 수출 추천국 데모 — Streamlit UI
FastAPI 서버(uvicorn main:app --reload)와 별도로 실행:
  streamlit run streamlit_app.py
"""

import json
from typing import Any, Dict, List, Optional
import requests
import streamlit as st

st.set_page_config(page_title="P1 수출 추천국 데모", layout="wide", page_icon="🌏")

SAMPLE_DEMO_PAYLOAD = {
    "hs_code": "330499",
    "exporter_country_iso3": "KOR",
    "top_n": 5,
    "year": 2023,
    "filters": {
        "exclude_countries_iso3": None,
        "min_trade_value_usd": 0.0,
    },
}


def build_payload(
    hs_code: str,
    exporter_iso3: str,
    top_n: int,
    year: int,
    min_trade_value_usd: float,
    exclude_list: Optional[List[str]],
) -> Dict[str, Any]:
    return {
        "hs_code": (hs_code or "").strip(),
        "exporter_country_iso3": (exporter_iso3 or "").strip().upper(),
        "top_n": int(top_n),
        "year": int(year),
        "filters": {
            "exclude_countries_iso3": exclude_list,
            "min_trade_value_usd": float(min_trade_value_usd),
        },
    }


def render_summary_card(payload: Dict[str, Any], results: List[Dict[str, Any]], mode_label: str) -> None:
    if not results:
        return

    top = results[0]
    explanations = [(r.get("explanation") or {}) for r in results]
    fallback_count = sum(1 for item in explanations if item.get("trade_signal_source") == "world_total_allocated")
    avg_score = round(sum(float(r.get("fit_score") or 0.0) for r in results) / len(results), 1)
    top_signal = str((top.get("explanation") or {}).get("trade_signal_source") or "-")
    kotra_weight = (top.get("explanation") or {}).get("kotra_weight_score")
    kotra_weight_text = f"{float(kotra_weight):.4f}" if kotra_weight is not None else "-"

    with st.container(border=True):
        st.markdown("### 📌 결과 요약 카드")
        st.caption(
            f"실행 모드: {mode_label} · 입력값: HS {payload['hs_code']} / {payload['exporter_country_iso3']} / {payload['year']}년 / TOP {payload['top_n']}"
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("1위 국가", str(top.get("partner_country_iso3") or "-"))
        col2.metric("1위 점수", f"{float(top.get('fit_score') or 0.0):.1f}")
        col3.metric("평균 점수", f"{avg_score:.1f}")
        col4.metric("Fallback", f"{fallback_count}/{len(results)}")

        st.write(f"대표 신호: `{top_signal}`")
        st.write(f"KOTRA 가중치: `{kotra_weight_text}`")


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
    st.caption("아래 샘플 버튼은 저장된 예시값으로 바로 호출합니다.")

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

form_payload = build_payload(
    hs_code=hs_code,
    exporter_iso3=exporter_iso3,
    top_n=top_n,
    year=year,
    min_trade_value_usd=min_trade_value_usd,
    exclude_list=exclude_list,
)

# ── 실행 버튼 ─────────────────────────────────────────
button_col1, button_col2 = st.columns(2)
with button_col1:
    sample_demo = st.button("🧪 샘플 데모 실행", use_container_width=True)
with button_col2:
    submit = st.button("🚀 추천 요청 실행", type="primary", use_container_width=True)
st.divider()

preview_payload = SAMPLE_DEMO_PAYLOAD if sample_demo else form_payload
with st.expander("🔍 요청 JSON 미리보기"):
    st.code(json.dumps(preview_payload, ensure_ascii=False, indent=2), language="json")

# ── 응답 처리 ─────────────────────────────────────────
run_payload = SAMPLE_DEMO_PAYLOAD if sample_demo else form_payload
run_mode_label = "샘플 데모" if sample_demo else "사용자 입력"

if sample_demo or submit:
    if not sample_demo and (len((hs_code or "").strip()) != 6 or not (hs_code or "").strip().isdigit()):
        st.error("❌ HS Code는 숫자 6자리여야 합니다.")
        st.stop()
    if not sample_demo and len((exporter_iso3 or "").strip()) != 3:
        st.error("❌ 수출국 ISO3는 영문 3자리여야 합니다.")
        st.stop()

    url = api_base.rstrip("/") + "/v1/predict"
    st.write(f"📡 요청 URL: `{url}`")
    if sample_demo:
        st.info("샘플 데모 입력값으로 즉시 실행합니다.")

    try:
        with st.spinner("API 호출 중..."):
            resp = requests.post(url, json=run_payload, timeout=int(timeout_sec))

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

        render_summary_card(run_payload, results, run_mode_label)

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
