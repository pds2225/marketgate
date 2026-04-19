"""
VALUE-UP AI 수출 유망국 추천 API 서버 v2
실데이터 연동 버전
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import os
import sys
from dotenv import load_dotenv

# .env 파일 로드 (현재 작업 디렉토리에서 찾기)
load_dotenv(dotenv_path='.env', override=True)

# 모델 임포트
from gravity_model import GravityModel
from xgb_model import XGBoostRefinementModel
from real_data_collector import RealDataCollector

# FastAPI 앱 생성
app = FastAPI(
    title="VALUE-UP AI Export Recommendation API v2",
    description="실데이터 연동 - 중력모형 + XGBoost 기반 수출 유망국 추천 엔진",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
gravity_model = None
xgb_model = None
data_collector = None

# 환경 변수 (시작 시 한 번만 로드)
USE_REAL_DATA = os.getenv('USE_REAL_DATA', 'false').lower() == 'true'
UN_COMTRADE_API_KEY = os.getenv('UN_COMTRADE_API_KEY', '')
ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'

print(f"[CONFIG] USE_REAL_DATA: {USE_REAL_DATA}")
print(f"[CONFIG] UN_COMTRADE_API_KEY: {'설정됨' if UN_COMTRADE_API_KEY else '미설정'}")
print(f"[CONFIG] ENABLE_CACHE: {ENABLE_CACHE}")


# 요청/응답 스키마
class PredictionRequest(BaseModel):
    hs_code: str = Field(..., description="HS 코드", json_schema_extra={"example": "33"})
    exporter_country: str = Field(default="KOR", description="수출국", json_schema_extra={"example": "KOR"})
    top_n: int = Field(default=10, description="상위 N개 국가", json_schema_extra={"example": 10})
    use_real_data: bool = Field(default=False, description="실데이터 사용 여부", json_schema_extra={"example": False})


class CountryRecommendation(BaseModel):
    country: str
    score: float
    expected_export_usd: float
    explanation: Dict[str, float]


class PredictionResponse(BaseModel):
    top_countries: List[CountryRecommendation]
    data_source: str  # "real" or "dummy"


class ConfigResponse(BaseModel):
    use_real_data: bool
    comtrade_api_configured: bool
    cache_enabled: bool


def load_models():
    """학습된 모델 로드"""
    global gravity_model, xgb_model, data_collector

    model_dir = 'backend/models'
    gravity_path = os.path.join(model_dir, 'gravity_model.pkl')
    xgb_path = os.path.join(model_dir, 'xgboost_model.pkl')

    if os.path.exists(gravity_path) and os.path.exists(xgb_path):
        print("모델 로딩 중...")
        gravity_model = GravityModel.load(gravity_path)
        xgb_model = XGBoostRefinementModel.load(xgb_path)
        print("모델 로딩 완료!")
    else:
        print("모델 파일이 없습니다.")
        gravity_model = None
        xgb_model = None

    # 데이터 수집기 초기화 (전역 변수 사용)
    data_collector = RealDataCollector(
        use_real_data=USE_REAL_DATA,
        comtrade_api_key=UN_COMTRADE_API_KEY
    )


@app.on_event("startup")
async def startup_event():
    """서버 시작시 모델 로드"""
    load_models()


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "message": "VALUE-UP AI Export Recommendation API v2",
        "status": "running",
        "version": "2.0.0",
        "features": ["real_data_support", "caching", "multiple_sources"]
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "gravity_model": gravity_model is not None,
        "xgb_model": xgb_model is not None,
        "data_collector": data_collector is not None
    }


@app.get("/config", response_model=ConfigResponse)
async def get_config():
    """현재 설정 조회 (전역 변수 사용)"""
    return ConfigResponse(
        use_real_data=USE_REAL_DATA,
        comtrade_api_configured=bool(UN_COMTRADE_API_KEY),
        cache_enabled=ENABLE_CACHE
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict_export_opportunities(request: PredictionRequest):
    """
    수출 유망국 추천 엔드포인트 (v2)

    실데이터 또는 더미 데이터를 사용하여 예측
    """
    if gravity_model is None or xgb_model is None:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")

    if data_collector is None:
        raise HTTPException(status_code=503, detail="데이터 수집기가 초기화되지 않았습니다.")

    try:
        # 1. 예측용 데이터 수집 (실데이터 또는 더미)
        pred_df = data_collector.collect_prediction_data(
            exporter=request.exporter_country,
            hs_code=request.hs_code,
            year=2023
        )

        data_source = "real" if data_collector.use_real_data else "dummy"

        # 2. 중력모형 예측
        feature_cols = ['gdp_target', 'distance_km', 'fta', 'lpi_score', 'tariff_rate']
        X_gravity = pred_df[feature_cols]
        pred_df['gravity_pred'] = gravity_model.predict(X_gravity)

        # 3. XGBoost 최종 예측
        final_predictions = xgb_model.predict(pred_df)
        pred_df['final_pred'] = final_predictions

        # 4. 점수 정규화
        min_pred = pred_df['final_pred'].min()
        max_pred = pred_df['final_pred'].max()

        if max_pred > min_pred:
            pred_df['score'] = (pred_df['final_pred'] - min_pred) / (max_pred - min_pred)
        else:
            pred_df['score'] = 0.5

        # 5. 상위 N개 국가
        top_countries_df = pred_df.nlargest(request.top_n, 'score')

        # 6. 각 국가별 설명 생성
        recommendations = []
        for idx, row in top_countries_df.iterrows():
            row_df = pred_df[pred_df['target_country'] == row['target_country']]
            row_index = row_df.index[0]
            original_index = pred_df.index.get_loc(row_index)

            explanation = xgb_model.explain_prediction(pred_df, index=original_index)

            simplified_explanation = {
                'gravity_baseline': explanation.get('gravity_pred', 0.0),
                'growth_potential': explanation.get('gdp_growth', 0.0),
                'culture_fit': explanation.get('culture_index', 0.0),
                'regulation_ease': explanation.get('regulation_index', 0.0),
                'logistics': explanation.get('lpi_score', 0.0),
                'tariff_impact': explanation.get('tariff_rate', 0.0)
            }

            recommendations.append(CountryRecommendation(
                country=row['target_country'],
                score=float(row['score']),
                expected_export_usd=float(row['final_pred']),
                explanation=simplified_explanation
            ))

        return PredictionResponse(
            top_countries=recommendations,
            data_source=data_source
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 중 오류 발생: {str(e)}")


@app.post("/retrain")
async def retrain_models(use_real_data: bool = False):
    """
    모델 재학습 엔드포인트

    Args:
        use_real_data: True면 실데이터로 재학습
    """
    try:
        print(f"\n모델 재학습 시작 (use_real_data={use_real_data})")

        # 데이터 수집
        collector = RealDataCollector(
            use_real_data=use_real_data,
            comtrade_api_key=os.getenv('UN_COMTRADE_API_KEY')
        )

        df = collector.collect_training_data(
            exporter="KOR",
            hs_codes=['33', '84', '85'],  # 주요 HS 코드만
            year=2023
        )

        # 모델 재학습
        from gravity_model import train_gravity_model
        from xgb_model import train_xgboost_model

        grav_model, train_df, test_df = train_gravity_model(df)
        xgb_trained = train_xgboost_model(train_df, test_df)

        # 저장
        grav_model.save('backend/models/gravity_model.pkl')
        xgb_trained.save('backend/models/xgboost_model.pkl')

        # 재로드
        load_models()

        return {
            "message": "모델 재학습 완료",
            "status": "success",
            "data_source": "real" if use_real_data else "dummy",
            "training_samples": len(df)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재학습 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("VALUE-UP AI 수출 유망국 추천 API 서버 v2")
    print("실데이터 연동 버전")
    print("=" * 60)
    print("\nAPI 문서: http://localhost:8000/docs")
    print("설정 확인: http://localhost:8000/config")
    print("\n서버 시작 중...\n")

    uvicorn.run(
        "api_v2:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
