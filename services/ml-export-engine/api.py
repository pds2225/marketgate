"""
VALUE-UP AI 수출 유망국 추천 API 서버
FastAPI 기반
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import os
import sys

# 모델 임포트
from gravity_model import GravityModel
from xgb_model import XGBoostRefinementModel
from data_generator import generate_prediction_data

# FastAPI 앱 생성
app = FastAPI(
    title="VALUE-UP AI Export Recommendation API",
    description="중력모형 + XGBoost 기반 수출 유망국 추천 엔진",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시에는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 모델 변수
gravity_model = None
xgb_model = None


# 요청/응답 스키마
class PredictionRequest(BaseModel):
    """예측 요청 스키마"""
    hs_code: str = Field(..., description="HS 코드 (예: '33')", example="33")
    exporter_country: str = Field(default="KOR", description="수출국 ISO-3 코드", example="KOR")
    top_n: int = Field(default=10, description="상위 N개 국가 반환", example=10)


class CountryRecommendation(BaseModel):
    """국가별 추천 결과"""
    country: str = Field(..., description="국가 코드 (ISO-3)")
    score: float = Field(..., description="추천 점수 (0-1)")
    expected_export_usd: float = Field(..., description="예상 수출액 (USD)")
    explanation: Dict[str, float] = Field(..., description="SHAP 기반 설명")


class PredictionResponse(BaseModel):
    """예측 응답 스키마"""
    top_countries: List[CountryRecommendation]


# 모델 로드 함수
def load_models():
    """학습된 모델 로드"""
    global gravity_model, xgb_model

    # 여러 경로 시도
    possible_dirs = ['models', 'backend/models', 'backend/backend/models']
    model_dir = None

    for dir_path in possible_dirs:
        gravity_check = os.path.join(dir_path, 'gravity_model.pkl')
        xgb_check = os.path.join(dir_path, 'xgboost_model.pkl')
        if os.path.exists(gravity_check) and os.path.exists(xgb_check):
            model_dir = dir_path
            break

    if model_dir is None:
        model_dir = 'backend/models'

    gravity_path = os.path.join(model_dir, 'gravity_model.pkl')
    xgb_path = os.path.join(model_dir, 'xgboost_model.pkl')

    if not os.path.exists(gravity_path) or not os.path.exists(xgb_path):
        print("모델 파일이 없습니다. 학습을 먼저 실행합니다...")
        train_models()

    print("모델 로딩 중...")
    gravity_model = GravityModel.load(gravity_path)
    xgb_model = XGBoostRefinementModel.load(xgb_path)
    print("모델 로딩 완료!")


def train_models():
    """모델 학습 (최초 실행시)"""
    from data_generator import generate_dummy_data
    from gravity_model import train_gravity_model
    from xgb_model import train_xgboost_model

    print("=" * 60)
    print("모델 학습 시작 (최초 실행)")
    print("=" * 60)

    # 디렉토리 생성
    os.makedirs('backend/models', exist_ok=True)

    # 더미 데이터 생성
    df = generate_dummy_data(5000)

    # 중력모형 학습
    grav_model, train_df, test_df = train_gravity_model(df)
    grav_model.save('backend/models/gravity_model.pkl')

    # XGBoost 학습
    xgb_model_trained = train_xgboost_model(train_df, test_df)
    xgb_model_trained.save('backend/models/xgboost_model.pkl')

    print("\n모델 학습 및 저장 완료!")


# API 엔드포인트
@app.on_event("startup")
async def startup_event():
    """서버 시작시 모델 로드"""
    load_models()


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "message": "VALUE-UP AI Export Recommendation API",
        "status": "running",
        "models_loaded": gravity_model is not None and xgb_model is not None
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "gravity_model": gravity_model is not None,
        "xgb_model": xgb_model is not None,
        "data_collector": True,
        "model_version": "1.0.0"
    }


@app.get("/config")
async def get_config():
    """설정 정보 조회"""
    return {
        "use_real_data": False,
        "comtrade_api_configured": False,
        "cache_enabled": False,
        "cache_backend": "none",
        "model_version": "1.0.0",
        "auto_retrain_enabled": False,
        "cors_origins": ["*"]
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict_export_opportunities(request: PredictionRequest):
    """
    수출 유망국 추천 엔드포인트

    중력모형 + XGBoost를 사용하여 상위 N개 유망국을 추천합니다.
    """
    if gravity_model is None or xgb_model is None:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")

    try:
        # 1. 예측용 데이터 생성 (모든 국가에 대해)
        pred_df = generate_prediction_data(request.hs_code)

        # 2. 중력모형 예측
        feature_cols = ['gdp_target', 'distance_km', 'fta', 'lpi_score', 'tariff_rate']
        X_gravity = pred_df[feature_cols]
        pred_df['gravity_pred'] = gravity_model.predict(X_gravity)

        # 3. XGBoost 최종 예측
        final_predictions = xgb_model.predict(pred_df)
        pred_df['final_pred'] = final_predictions

        # 4. 점수 정규화 (0-1 스케일)
        min_pred = pred_df['final_pred'].min()
        max_pred = pred_df['final_pred'].max()
        pred_df['score'] = (pred_df['final_pred'] - min_pred) / (max_pred - min_pred)

        # 5. 상위 N개 국가 선택
        top_countries_df = pred_df.nlargest(request.top_n, 'score')

        # 6. 각 국가별 설명 생성 (SHAP)
        recommendations = []
        for idx, row in top_countries_df.iterrows():
            # SHAP 설명 계산
            row_df = pred_df[pred_df['target_country'] == row['target_country']]
            row_index = row_df.index[0]

            # 원본 데이터프레임에서 인덱스 찾기
            original_index = pred_df.index.get_loc(row_index)
            explanation = xgb_model.explain_prediction(pred_df, index=original_index)

            # 주요 특성만 추출 (gravity_pred 제외하고 비즈니스 의미 있는 것들)
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

        return PredictionResponse(top_countries=recommendations)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 중 오류 발생: {str(e)}")


@app.post("/retrain")
async def retrain_models():
    """
    모델 재학습 엔드포인트 (관리자용)

    실제 운영시에는 인증 추가 필요
    """
    try:
        train_models()
        load_models()
        return {"message": "모델 재학습 완료", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재학습 중 오류 발생: {str(e)}")


# 개발용 실행
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("VALUE-UP AI 수출 유망국 추천 API 서버")
    print("=" * 60)
    print("\nAPI 문서: http://localhost:8000/docs")
    print("헬스 체크: http://localhost:8000/health")
    print("\n서버 시작 중...\n")

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발시 자동 리로드
        log_level="info"
    )
