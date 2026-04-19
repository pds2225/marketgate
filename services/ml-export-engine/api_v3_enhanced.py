"""
VALUE-UP AI 수출 유망국 추천 API 서버 v3 (강화 버전)

개선 사항:
- SQLite 캐시 통합 (TTL, cache_hit 응답)
- 모델 버전 관리 및 메타데이터 반환
- 요청 로깅 및 에러 추적
- 표준화된 에러 응답
- 보안 강화 (API 키 마스킹, CORS whitelist)
- 성능 모니터링
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import os
import sys
import time
import hashlib
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# .env 파일 로드
load_dotenv(dotenv_path='.env', override=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 모델 임포트
from gravity_model import GravityModel
from xgb_model import XGBoostRefinementModel
from real_data_collector import RealDataCollector
from cache_manager import init_cache_from_env

# FastAPI 앱 생성
app = FastAPI(
    title="VALUE-UP AI Export Recommendation API v3",
    description="강화 버전 - 캐시 + 모델버전 + 로깅 + 보안",
    version="3.0.0"
)

# CORS 설정 (production에서는 whitelist 사용)
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
gravity_model = None
xgb_model = None
data_collector = None
cache_manager = None
model_metadata = {}

# 환경 변수
USE_REAL_DATA = os.getenv('USE_REAL_DATA', 'false').lower() == 'true'
UN_COMTRADE_API_KEY = os.getenv('UN_COMTRADE_API_KEY', '')
ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'

logger.info(f"[CONFIG] USE_REAL_DATA: {USE_REAL_DATA}")
logger.info(f"[CONFIG] UN_COMTRADE_API_KEY: {'설정됨' if UN_COMTRADE_API_KEY else '미설정'}")
logger.info(f"[CONFIG] ENABLE_CACHE: {ENABLE_CACHE}")
logger.info(f"[CONFIG] CORS_ORIGINS: {CORS_ORIGINS}")


# ==================== 요청/응답 스키마 ====================

class ErrorResponse(BaseModel):
    """표준 에러 응답"""
    error: Dict[str, str]  # {code, message, detail}


class PredictionRequest(BaseModel):
    hs_code: str = Field(..., description="HS 코드", examples=["33"])
    exporter_country: str = Field(default="KOR", description="수출국", examples=["KOR"])
    top_n: int = Field(default=10, description="상위 N개 국가", examples=[10])


class CountryRecommendation(BaseModel):
    country: str
    score: float
    expected_export_usd: float
    explanation: Dict[str, float]


class PredictionResponse(BaseModel):
    top_countries: List[CountryRecommendation]
    data_source: str  # "real" or "dummy"
    cache_hit: bool = False
    model_version: str
    data_version: Optional[str] = None
    request_duration_ms: float


class ConfigResponse(BaseModel):
    use_real_data: bool
    comtrade_api_configured: bool
    cache_enabled: bool
    model_version: Optional[str] = None
    cors_origins: List[str]


class CacheStatsResponse(BaseModel):
    total_entries: int
    valid_entries: int
    hits: int
    misses: int
    hit_rate_percent: float


# ==================== 모델 로딩 ====================

def get_model_version(model_path: str) -> str:
    """모델 파일의 수정 시각을 버전으로 사용"""
    if os.path.exists(model_path):
        mtime = os.path.getmtime(model_path)
        return datetime.fromtimestamp(mtime).strftime('%Y%m%d_%H%M%S')
    return "unknown"


def load_models():
    """학습된 모델 로드 + 메타데이터"""
    global gravity_model, xgb_model, data_collector, cache_manager, model_metadata

    model_dir = 'backend/models'
    gravity_path = os.path.join(model_dir, 'gravity_model.pkl')
    xgb_path = os.path.join(model_dir, 'xgboost_model.pkl')

    if os.path.exists(gravity_path) and os.path.exists(xgb_path):
        logger.info("모델 로딩 중...")
        gravity_model = GravityModel.load(gravity_path)
        xgb_model = XGBoostRefinementModel.load(xgb_path)

        # 모델 메타데이터
        model_metadata = {
            "version": get_model_version(xgb_path),
            "gravity_path": gravity_path,
            "xgb_path": xgb_path,
            "loaded_at": datetime.now().isoformat()
        }

        logger.info(f"모델 로딩 완료! 버전: {model_metadata['version']}")
    else:
        logger.warning("모델 파일이 없습니다.")
        gravity_model = None
        xgb_model = None
        model_metadata = {"version": "not_loaded"}

    # 데이터 수집기 초기화
    data_collector = RealDataCollector(
        use_real_data=USE_REAL_DATA,
        comtrade_api_key=UN_COMTRADE_API_KEY
    )

    # 캐시 초기화
    if ENABLE_CACHE:
        cache_manager = init_cache_from_env()
        logger.info("캐시 활성화")
    else:
        cache_manager = None
        logger.info("캐시 비활성화")


@app.on_event("startup")
async def startup_event():
    """서버 시작시 모델 로드"""
    load_models()


# ==================== 엔드포인트 ====================

@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "message": "VALUE-UP AI Export Recommendation API v3",
        "status": "running",
        "version": "3.0.0",
        "features": [
            "real_data_support",
            "sqlite_caching",
            "model_versioning",
            "request_logging",
            "error_tracking"
        ]
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "gravity_model": gravity_model is not None,
        "xgb_model": xgb_model is not None,
        "data_collector": data_collector is not None,
        "cache_manager": cache_manager is not None,
        "model_version": model_metadata.get("version", "unknown")
    }


@app.get("/config", response_model=ConfigResponse)
async def get_config():
    """현재 설정 조회"""
    return ConfigResponse(
        use_real_data=USE_REAL_DATA,
        comtrade_api_configured=bool(UN_COMTRADE_API_KEY),
        cache_enabled=ENABLE_CACHE and cache_manager is not None,
        model_version=model_metadata.get("version"),
        cors_origins=CORS_ORIGINS
    )


@app.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """캐시 통계 조회"""
    if not cache_manager:
        raise HTTPException(status_code=404, detail="캐시가 비활성화되어 있습니다")

    stats = cache_manager.get_stats()
    return CacheStatsResponse(**stats)


@app.post("/cache/clear")
async def clear_cache():
    """캐시 전체 삭제"""
    if not cache_manager:
        raise HTTPException(status_code=404, detail="캐시가 비활성화되어 있습니다")

    cache_manager.clear_all()
    return {"message": "캐시가 모두 삭제되었습니다"}


@app.post("/predict", response_model=PredictionResponse)
async def predict_export_opportunities(request: PredictionRequest, req: Request):
    """
    수출 유망국 추천 엔드포인트 (v3 강화 버전)

    개선 사항:
    - 캐시 적용 (동일 요청은 캐시에서 반환)
    - 모델 버전 포함
    - 요청 로깅
    - 성능 측정
    """
    start_time = time.time()
    cache_hit = False

    # 요청 로깅
    logger.info(f"[PREDICT] hs_code={request.hs_code}, exporter={request.exporter_country}, top_n={request.top_n}")

    # 모델 체크
    if gravity_model is None or xgb_model is None:
        logger.error("[ERROR] 모델이 로드되지 않았습니다")
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODEL_NOT_LOADED",
                "message": "모델이 로드되지 않았습니다",
                "detail": "서버를 재시작하거나 /retrain 엔드포인트를 호출하세요"
            }
        )

    if data_collector is None:
        raise HTTPException(status_code=503, detail="데이터 수집기가 초기화되지 않았습니다")

    # 캐시 키 생성
    cache_key = None
    if cache_manager:
        cache_key = cache_manager._generate_key(
            "predict",
            (),
            {
                "hs_code": request.hs_code,
                "exporter": request.exporter_country,
                "top_n": request.top_n
            }
        )

        # 캐시 조회
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            cache_hit = True
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"[CACHE HIT] duration={duration_ms:.2f}ms")

            # duration만 업데이트해서 반환
            cached_result["request_duration_ms"] = duration_ms
            cached_result["cache_hit"] = True
            return PredictionResponse(**cached_result)

    try:
        # 1. 예측용 데이터 수집
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

        # 4. 점수 정규화 (minmax)
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

        duration_ms = (time.time() - start_time) * 1000

        # 응답 생성
        response_data = {
            "top_countries": recommendations,
            "data_source": data_source,
            "cache_hit": cache_hit,
            "model_version": model_metadata.get("version", "unknown"),
            "data_version": None,
            "request_duration_ms": duration_ms
        }

        # 캐시 저장
        if cache_manager and cache_key:
            cache_manager.set(
                cache_key,
                response_data,
                metadata={
                    "hs_code": request.hs_code,
                    "exporter": request.exporter_country
                }
            )

        logger.info(f"[SUCCESS] duration={duration_ms:.2f}ms, cache_hit={cache_hit}")
        return PredictionResponse(**response_data)

    except Exception as e:
        logger.error(f"[ERROR] 예측 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PREDICTION_ERROR",
                "message": "예측 중 오류가 발생했습니다",
                "detail": str(e)
            }
        )


@app.post("/retrain")
async def retrain_models(use_real_data: bool = False):
    """
    모델 재학습 엔드포인트

    Args:
        use_real_data: True면 실데이터로 재학습
    """
    try:
        logger.info(f"모델 재학습 시작 (use_real_data={use_real_data})")

        # 데이터 수집
        collector = RealDataCollector(
            use_real_data=use_real_data,
            comtrade_api_key=UN_COMTRADE_API_KEY
        )

        df = collector.collect_training_data(
            exporter="KOR",
            hs_codes=['33', '84', '85'],
            year=2023
        )

        # 모델 재학습
        from gravity_model import train_gravity_model
        from xgb_model import train_xgboost_model

        grav_model, train_df, test_df = train_gravity_model(df)
        xgb_trained = train_xgboost_model(train_df, test_df)

        # 버전 포함 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_dir = 'backend/models'

        grav_path = os.path.join(model_dir, f'gravity_model_{timestamp}.pkl')
        xgb_path = os.path.join(model_dir, f'xgboost_model_{timestamp}.pkl')

        grav_model.save(grav_path)
        xgb_trained.save(xgb_path)

        # 최신 버전으로 심볼릭 링크 (또는 복사)
        import shutil
        shutil.copy(grav_path, os.path.join(model_dir, 'gravity_model.pkl'))
        shutil.copy(xgb_path, os.path.join(model_dir, 'xgboost_model.pkl'))

        # 재로드
        load_models()

        # 캐시 초기화 (새 모델이므로)
        if cache_manager:
            cache_manager.clear_all()
            logger.info("캐시 초기화 완료")

        logger.info("모델 재학습 완료")

        return {
            "message": "모델 재학습 완료",
            "status": "success",
            "data_source": "real" if use_real_data else "dummy",
            "training_samples": len(df),
            "model_version": model_metadata.get("version")
        }

    except Exception as e:
        logger.error(f"재학습 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"재학습 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("VALUE-UP AI 수출 유망국 추천 API 서버 v3")
    print("강화 버전 (캐시 + 모델버전 + 로깅)")
    print("=" * 60)
    print("\nAPI 문서: http://localhost:8001/docs")
    print("설정 확인: http://localhost:8001/config")
    print("캐시 통계: http://localhost:8001/cache/stats")
    print("\n서버 시작 중...\n")

    uvicorn.run(
        "api_v3_enhanced:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
