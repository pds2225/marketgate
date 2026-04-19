"""
VALUE-UP AI 수출 유망국 추천 API 서버 v4 (Production)

최종 개선 사항:
- Redis 캐시 통합
- Prometheus 메트릭
- 자동 재학습 스케줄러
- 구조화된 로깅
- A/B 테스팅 지원
"""

from fastapi import FastAPI, HTTPException, Request, Header
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
from datetime import datetime
from dotenv import load_dotenv
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import threading

# .env 파일 로드
load_dotenv(dotenv_path='.env', override=True)

# logs 디렉토리 생성
os.makedirs('logs', exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/api.log')
    ]
)
logger = logging.getLogger(__name__)

# 모델 임포트
from gravity_model import GravityModel
from xgb_model import XGBoostRefinementModel
from real_data_collector import RealDataCollector

# 캐시 임포트 (Redis 또는 SQLite)
USE_REDIS = os.getenv('USE_REDIS_CACHE', 'true').lower() == 'true'
if USE_REDIS:
    from cache_manager_redis import init_redis_cache_from_env
    logger.info("Redis 캐시 활성화")
else:
    from cache_manager import init_cache_from_env
    logger.info("SQLite 캐시 활성화")

# 자동 재학습
from training_pipeline import AutoRetrainingPipeline, ModelVersionManager, schedule_daily_retraining

# ==================== Prometheus 메트릭 ====================

# 요청 카운터
REQUEST_COUNT = Counter(
    'api_requests_total',
    'API 요청 총 수',
    ['method', 'endpoint', 'status']
)

# 응답 시간
REQUEST_LATENCY = Histogram(
    'api_request_duration_ms',
    'API 요청 응답 시간 (밀리초)',
    ['endpoint'],
    buckets=[10, 50, 100, 500, 1000, 5000, 10000, 30000]
)

# 캐시 히트율
CACHE_HIT_RATE = Gauge(
    'cache_hit_rate_percent',
    '캐시 히트율 (%)'
)

# 모델 정확도
MODEL_ACCURACY = Gauge(
    'model_accuracy_score',
    '모델 정확도',
    ['model_version']
)

# 에러 카운터
API_ERRORS = Counter(
    'api_errors_total',
    'API 에러 총 수',
    ['endpoint', 'error_type']
)

# 재학습 메트릭
MODEL_RETRAINING_SUCCESS = Counter(
    'model_retraining_success_total',
    '모델 재학습 성공 횟수'
)

MODEL_RETRAINING_FAILURES = Counter(
    'model_retraining_failures_total',
    '모델 재학습 실패 횟수'
)

# ==================== FastAPI 앱 ====================

app = FastAPI(
    title="VALUE-UP AI Export Recommendation API v4",
    description="Production 버전 - Redis + Prometheus + 자동 재학습",
    version="4.0.0"
)

# CORS 설정
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
version_manager = None
retraining_pipeline = None
model_metadata = {}

# 환경 변수
USE_REAL_DATA = os.getenv('USE_REAL_DATA', 'false').lower() == 'true'
UN_COMTRADE_API_KEY = os.getenv('UN_COMTRADE_API_KEY', '')
ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'
ENABLE_AUTO_RETRAIN = os.getenv('ENABLE_AUTO_RETRAIN', 'false').lower() == 'true'

logger.info(f"[CONFIG] USE_REAL_DATA: {USE_REAL_DATA}")
logger.info(f"[CONFIG] USE_REDIS_CACHE: {USE_REDIS}")
logger.info(f"[CONFIG] ENABLE_AUTO_RETRAIN: {ENABLE_AUTO_RETRAIN}")
logger.info(f"[CONFIG] CORS_ORIGINS: {CORS_ORIGINS}")

# ==================== 요청/응답 스키마 ====================

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
    data_source: str
    cache_hit: bool = False
    model_version: str
    ab_test_group: Optional[str] = None
    request_duration_ms: float


class ConfigResponse(BaseModel):
    use_real_data: bool
    comtrade_api_configured: bool
    cache_enabled: bool
    cache_backend: str  # "redis" or "sqlite"
    model_version: Optional[str] = None
    auto_retrain_enabled: bool
    cors_origins: List[str]


# ==================== 미들웨어 ====================

@app.middleware("http")
async def track_metrics(request: Request, call_next):
    """모든 요청에 대한 메트릭 기록"""
    start_time = time.time()

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # 메트릭 기록
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        REQUEST_LATENCY.labels(
            endpoint=request.url.path
        ).observe(duration_ms)

        # 로깅
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {duration_ms:.2f}ms"
        )

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        API_ERRORS.labels(
            endpoint=request.url.path,
            error_type=type(e).__name__
        ).inc()

        logger.error(
            f"{request.method} {request.url.path} - ERROR - {duration_ms:.2f}ms - {str(e)}",
            exc_info=True
        )

        raise


# ==================== 모델 로딩 ====================

def load_models():
    """모델 및 캐시 초기화"""
    global gravity_model, xgb_model, data_collector, cache_manager
    global version_manager, retraining_pipeline, model_metadata

    # 버전 관리자
    version_manager = ModelVersionManager()

    # 모델 로드
    # 모델 경로 - 여러 경로 시도
    possible_model_dirs = ['models', 'backend/models', 'backend/backend/models']
    model_dir = None
    for dir_path in possible_model_dirs:
        gravity_check = os.path.join(dir_path, 'gravity_model.pkl')
        xgb_check = os.path.join(dir_path, 'xgboost_model.pkl')
        if os.path.exists(gravity_check) and os.path.exists(xgb_check):
            model_dir = dir_path
            break
    if model_dir is None:
        model_dir = 'backend/models'  # fallback
    gravity_path = os.path.join(model_dir, 'gravity_model.pkl')
    xgb_path = os.path.join(model_dir, 'xgboost_model.pkl')

    if os.path.exists(gravity_path) and os.path.exists(xgb_path):
        logger.info("모델 로딩 중...")
        gravity_model = GravityModel.load(gravity_path)
        xgb_model = XGBoostRefinementModel.load(xgb_path)

        # 메타데이터
        current_version = version_manager.get_current_version()
        model_metadata = {
            "version": current_version,
            "loaded_at": datetime.now().isoformat()
        }

        logger.info(f"모델 로딩 완료! 버전: {current_version}")
    else:
        logger.warning("모델 파일이 없습니다")

    # 데이터 수집기
    data_collector = RealDataCollector(
        use_real_data=USE_REAL_DATA,
        comtrade_api_key=UN_COMTRADE_API_KEY
    )

    # 캐시
    if ENABLE_CACHE:
        if USE_REDIS:
            cache_manager = init_redis_cache_from_env()
        else:
            from cache_manager import init_cache_from_env
            cache_manager = init_cache_from_env()

        logger.info(f"캐시 활성화 ({'Redis' if USE_REDIS else 'SQLite'})")
    else:
        cache_manager = None

    # 자동 재학습 파이프라인
    if ENABLE_AUTO_RETRAIN and data_collector:
        retraining_pipeline = AutoRetrainingPipeline(
            data_collector=data_collector,
            version_manager=version_manager,
            min_accuracy_improvement=0.02
        )

        # 스케줄러 시작 (백그라운드 스레드)
        scheduler_thread = threading.Thread(
            target=schedule_daily_retraining,
            args=(retraining_pipeline,),
            daemon=True
        )
        scheduler_thread.start()
        logger.info("⏰ 자동 재학습 스케줄러 시작 (매일 00:00)")


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    load_models()


# ==================== 엔드포인트 ====================

@app.get("/")
async def root():
    return {
        "message": "VALUE-UP AI Export Recommendation API v4",
        "status": "running",
        "version": "4.0.0",
        "features": [
            "redis_cache",
            "prometheus_metrics",
            "auto_retraining",
            "ab_testing"
        ]
    }


@app.get("/metrics")

# === 추가 엔드포인트 (api_v4_production.py의 @app.get("/metrics") 이전에 삽입) ===

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 - 시스템 상태 확인"""
    return {
        "status": "healthy",
        "gravity_model": gravity_model is not None,
        "xgb_model": xgb_model is not None,
        "data_collector": data_collector is not None,
        "cache_enabled": cache_manager is not None,
        "model_version": model_metadata.get("version", "unknown"),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/cache/stats")
async def cache_stats():
    """캐시 통계 조회"""
    if cache_manager is None:
        raise HTTPException(status_code=404, detail="캐시가 비활성화되어 있습니다")
    stats = cache_manager.get_stats()
    return stats


@app.post("/retrain")
async def retrain_models_endpoint():
    """모델 재학습 트리거"""
    global gravity_model, xgb_model, model_metadata

    if retraining_pipeline is None:
        raise HTTPException(status_code=503, detail="자동 재학습이 비활성화되어 있습니다. ENABLE_AUTO_RETRAIN=true 설정 필요")

    try:
        logger.info("수동 재학습 시작...")
        result = retraining_pipeline.run_retraining()

        possible_model_dirs = ['models', 'backend/models', 'backend/backend/models']
        for dir_path in possible_model_dirs:
            gravity_path = os.path.join(dir_path, 'gravity_model.pkl')
            xgb_path = os.path.join(dir_path, 'xgboost_model.pkl')
            if os.path.exists(gravity_path) and os.path.exists(xgb_path):
                gravity_model = GravityModel.load(gravity_path)
                xgb_model = XGBoostRefinementModel.load(xgb_path)
                model_metadata["version"] = version_manager.get_current_version()
                model_metadata["loaded_at"] = datetime.now().isoformat()
                break

        MODEL_RETRAINING_SUCCESS.inc()
        logger.info("수동 재학습 완료!")

        return {
            "status": "success",
            "message": "모델 재학습 완료",
            "new_version": model_metadata.get("version"),
            "training_samples": result.get("samples", 0)
        }
    except Exception as e:
        MODEL_RETRAINING_FAILURES.inc()
        logger.error(f"재학습 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    # 캐시 히트율 업데이트
    if cache_manager:
        stats = cache_manager.get_stats()
        CACHE_HIT_RATE.set(stats.get('hit_rate_percent', 0))

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/config", response_model=ConfigResponse)
async def get_config():
    """현재 설정 조회"""
    cache_backend = "redis" if USE_REDIS else "sqlite"

    return ConfigResponse(
        use_real_data=USE_REAL_DATA,
        comtrade_api_configured=bool(UN_COMTRADE_API_KEY),
        cache_enabled=ENABLE_CACHE and cache_manager is not None,
        cache_backend=cache_backend,
        model_version=model_metadata.get("version"),
        auto_retrain_enabled=ENABLE_AUTO_RETRAIN,
        cors_origins=CORS_ORIGINS
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, user_id: Optional[str] = Header(None)):
    """
    수출 유망국 추천 (Production 버전)

    - Redis 캐시 지원
    - A/B 테스팅
    - Prometheus 메트릭
    """
    start_time = time.time()
    cache_hit = False
    ab_group = None

    # A/B 테스팅 (user_id 기반)
    if user_id and ENABLE_AUTO_RETRAIN:
        user_hash = hash(user_id) % 100
        ab_group = "A" if user_hash < 50 else "B"
        logger.info(f"A/B Test: user={user_id}, group={ab_group}")

    # 모델 체크
    if gravity_model is None or xgb_model is None:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다")

    # 캐시 키
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

        cached = cache_manager.get(cache_key)
        if cached:
            cache_hit = True
            duration_ms = (time.time() - start_time) * 1000
            cached["request_duration_ms"] = duration_ms
            cached["cache_hit"] = True
            logger.info(f"Cache HIT - {duration_ms:.2f}ms")
            return PredictionResponse(**cached)

    try:
        # 예측 실행 (기존 로직)
        pred_df = data_collector.collect_prediction_data(
            exporter=request.exporter_country,
            hs_code=request.hs_code,
            year=2023
        )

        data_source = "real" if data_collector.use_real_data else "dummy"

        # 중력모형
        feature_cols = ['gdp_target', 'distance_km', 'fta', 'lpi_score', 'tariff_rate']
        X_gravity = pred_df[feature_cols]
        pred_df['gravity_pred'] = gravity_model.predict(X_gravity)

        # XGBoost
        final_predictions = xgb_model.predict(pred_df)
        pred_df['final_pred'] = final_predictions

        # 점수 정규화
        min_pred, max_pred = pred_df['final_pred'].min(), pred_df['final_pred'].max()
        if max_pred > min_pred:
            pred_df['score'] = (pred_df['final_pred'] - min_pred) / (max_pred - min_pred)
        else:
            pred_df['score'] = 0.5

        # Top N
        top_countries_df = pred_df.nlargest(request.top_n, 'score')

        # 설명 생성
        recommendations = []
        for idx, row in top_countries_df.iterrows():
            row_df = pred_df[pred_df['target_country'] == row['target_country']]
            original_index = pred_df.index.get_loc(row_df.index[0])

            explanation = xgb_model.explain_prediction(pred_df, index=original_index)

            recommendations.append(CountryRecommendation(
                country=row['target_country'],
                score=float(row['score']),
                expected_export_usd=float(row['final_pred']),
                explanation={
                    'gravity_baseline': explanation.get('gravity_pred', 0.0),
                    'growth_potential': explanation.get('gdp_growth', 0.0),
                    'culture_fit': explanation.get('culture_index', 0.0),
                    'regulation_ease': explanation.get('regulation_index', 0.0),
                    'logistics': explanation.get('lpi_score', 0.0),
                    'tariff_impact': explanation.get('tariff_rate', 0.0)
                }
            ))

        duration_ms = (time.time() - start_time) * 1000

        response_data = {
            "top_countries": recommendations,
            "data_source": data_source,
            "cache_hit": False,
            "model_version": model_metadata.get("version", "unknown"),
            "ab_test_group": ab_group,
            "request_duration_ms": duration_ms
        }

        # 캐시 저장
        if cache_manager and cache_key:
            cache_manager.set(cache_key, response_data)

        logger.info(f"Prediction success - {duration_ms:.2f}ms")
        return PredictionResponse(**response_data)

    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("VALUE-UP AI API v4 (Production)")
    print("=" * 60)

    uvicorn.run(
        "api_v4_production:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
