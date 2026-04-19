from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.models import PredictRequest, PredictResponse
from app.services.scoring import recommend_countries
from app.utils import now_seoul_iso, new_request_id

app = FastAPI(title="Export Fit Score API(P1)", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return """
    <html><head><title>Export Fit Score API</title></head>
    <body style="font-family:sans-serif;padding:40px;background:#0d1117;color:#e6edf3;">
        <h2>🚀 Export Fit Score API (P1)</h2>
        <p style="color:#7d8590;">수출 대상 국가 추천 시스템 — 정상 운영 중</p>
        <hr style="border-color:#30363d;">
        <ul>
            <li><a href="/docs" style="color:#58a6ff;">📄 Swagger UI (API 테스트)</a></li>
            <li><a href="/redoc" style="color:#58a6ff;">📘 ReDoc (API 문서)</a></li>
            <li><a href="/v1/health" style="color:#58a6ff;">❤️ Health Check</a></li>
        </ul>
        <h4>빠른 테스트 예시 (POST /v1/predict)</h4>
        <pre style="background:#161b22;padding:16px;border-radius:6px;color:#79c0ff;">
{
  "hs_code": "330499",
  "exporter_country_iso3": "KOR",
  "top_n": 5,
  "year": 2023
}</pre>
    </body></html>
    """


@app.get("/v1/health")
def health():
    return {"status": "ok", "timestamp": now_seoul_iso()}


@app.post("/v1/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    request_id = new_request_id()
    results, input_echo = recommend_countries(req)

    return {
        "request_id": request_id,
        "status": "ok",
        "timestamp": now_seoul_iso(),
        "data": {
            "input": input_echo,
            "results": results,
        },
    }
