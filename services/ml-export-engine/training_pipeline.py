"""
자동 재학습 파이프라인

기능:
- 스케줄 기반 자동 재학습 (매일 자정)
- 백테스트 검증 (성능 개선 확인)
- 모델 버전 관리
- A/B 테스팅 지원
- 알림 통합
"""

import schedule
import pickle
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np
import logging

from gravity_model import GravityModel, train_gravity_model
from xgb_model import XGBoostRefinementModel, train_xgboost_model
from real_data_collector import RealDataCollector

logger = logging.getLogger(__name__)


class ModelVersionManager:
    """모델 버전 관리자"""

    def __init__(self, models_dir: str = "backend/models"):
        self.models_dir = Path(models_dir)
        self.versions_dir = self.models_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        # 현재 프로덕션 모델
        self.current_gravity_path = self.models_dir / "gravity_model.pkl"
        self.current_xgb_path = self.models_dir / "xgboost_model.pkl"

    def get_current_version(self) -> Optional[str]:
        """현재 프로덕션 버전 조회"""
        if self.current_xgb_path.exists():
            mtime = self.current_xgb_path.stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime('%Y%m%d_%H%M%S')
        return None

    def save_version(
        self,
        gravity_model: GravityModel,
        xgb_model: XGBoostRefinementModel,
        metadata: Dict
    ) -> str:
        """새 버전 저장"""
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_dir = self.versions_dir / version
        version_dir.mkdir()

        # 모델 저장
        gravity_path = version_dir / "gravity_model.pkl"
        xgb_path = version_dir / "xgboost_model.pkl"

        gravity_model.save(str(gravity_path))
        xgb_model.save(str(xgb_path))

        # 메타데이터 저장
        metadata_path = version_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump({
                "version": version,
                "created_at": datetime.now().isoformat(),
                **metadata
            }, f, indent=2)

        logger.info(f"✅ 모델 버전 {version} 저장 완료")
        return version

    def promote_to_production(self, version: str):
        """특정 버전을 프로덕션으로 승격"""
        version_dir = self.versions_dir / version

        if not version_dir.exists():
            raise ValueError(f"버전 {version}이 존재하지 않습니다")

        # 기존 모델 백업
        if self.current_gravity_path.exists():
            backup_dir = self.models_dir / f"backup_{self.get_current_version()}"
            backup_dir.mkdir(exist_ok=True)
            shutil.copy(self.current_gravity_path, backup_dir / "gravity_model.pkl")
            shutil.copy(self.current_xgb_path, backup_dir / "xgboost_model.pkl")

        # 새 모델 복사
        shutil.copy(
            version_dir / "gravity_model.pkl",
            self.current_gravity_path
        )
        shutil.copy(
            version_dir / "xgboost_model.pkl",
            self.current_xgb_path
        )

        logger.info(f"🚀 모델 버전 {version}이 프로덕션으로 승격되었습니다")

    def list_versions(self) -> list:
        """모든 버전 목록"""
        versions = []
        for version_dir in self.versions_dir.iterdir():
            if version_dir.is_dir():
                metadata_path = version_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    versions.append(metadata)

        return sorted(versions, key=lambda x: x['version'], reverse=True)


class AutoRetrainingPipeline:
    """자동 재학습 파이프라인"""

    def __init__(
        self,
        data_collector: RealDataCollector,
        version_manager: ModelVersionManager,
        min_accuracy_improvement: float = 0.02  # 2% 이상 개선 필요
    ):
        self.data_collector = data_collector
        self.version_manager = version_manager
        self.min_accuracy_improvement = min_accuracy_improvement

        # 현재 프로덕션 모델
        self.current_gravity = None
        self.current_xgb = None
        self._load_current_models()

    def _load_current_models(self):
        """현재 프로덕션 모델 로드"""
        try:
            self.current_gravity = GravityModel.load(
                str(self.version_manager.current_gravity_path)
            )
            self.current_xgb = XGBoostRefinementModel.load(
                str(self.version_manager.current_xgb_path)
            )
            logger.info("현재 프로덕션 모델 로드 완료")
        except Exception as e:
            logger.warning(f"프로덕션 모델 로드 실패: {e}")

    def collect_training_data(self, days: int = 30) -> pd.DataFrame:
        """학습 데이터 수집"""
        logger.info(f"최근 {days}일 데이터 수집 중...")

        # 주요 HS 코드
        hs_codes = ['33', '84', '85', '87', '27', '39', '90', '30']

        df = self.data_collector.collect_training_data(
            exporter="KOR",
            hs_codes=hs_codes,
            year=2023
        )

        logger.info(f"수집 완료: {len(df)}개 데이터 포인트")
        return df

    def validate_models(
        self,
        new_gravity: GravityModel,
        new_xgb: XGBoostRefinementModel,
        test_data: pd.DataFrame
    ) -> Dict:
        """백테스트: 새 모델 vs 현재 모델"""
        logger.info("백테스트 검증 중...")

        # 현재 모델 성능
        if self.current_gravity and self.current_xgb:
            old_predictions = self.current_xgb.predict(test_data)
            old_mse = np.mean((test_data['export_value_usd'].values - old_predictions) ** 2)
            old_mae = np.mean(np.abs(test_data['export_value_usd'].values - old_predictions))
        else:
            old_mse = float('inf')
            old_mae = float('inf')

        # 새 모델 성능
        new_predictions = new_xgb.predict(test_data)
        new_mse = np.mean((test_data['export_value_usd'].values - new_predictions) ** 2)
        new_mae = np.mean(np.abs(test_data['export_value_usd'].values - new_predictions))

        # 개선율 계산
        mse_improvement = (old_mse - new_mse) / old_mse if old_mse != float('inf') else 0
        mae_improvement = (old_mae - new_mae) / old_mae if old_mae != float('inf') else 0

        metrics = {
            "old_mse": float(old_mse),
            "new_mse": float(new_mse),
            "old_mae": float(old_mae),
            "new_mae": float(new_mae),
            "mse_improvement": float(mse_improvement),
            "mae_improvement": float(mae_improvement),
            "test_samples": len(test_data)
        }

        logger.info(f"검증 결과: MSE 개선 {mse_improvement:.2%}, MAE 개선 {mae_improvement:.2%}")
        return metrics

    def retrain(self, auto_promote: bool = True) -> Dict:
        """재학습 실행"""
        logger.info("=" * 60)
        logger.info("자동 재학습 시작")
        logger.info("=" * 60)

        try:
            # 1. 데이터 수집
            df = self.collect_training_data(days=30)

            if len(df) < 100:
                logger.warning(f"데이터 부족 ({len(df)}개), 재학습 스킵")
                return {"status": "skipped", "reason": "insufficient_data"}

            # 2. 모델 학습
            logger.info("모델 학습 중...")
            new_gravity, train_df, test_df = train_gravity_model(df)
            new_xgb = train_xgboost_model(train_df, test_df)

            # 3. 백테스트 검증
            metrics = self.validate_models(new_gravity, new_xgb, test_df)

            # 4. 성능 개선 여부 확인
            improvement = metrics['mae_improvement']

            if improvement >= self.min_accuracy_improvement or not self.current_xgb:
                # 새 버전 저장
                version = self.version_manager.save_version(
                    new_gravity,
                    new_xgb,
                    metadata={
                        "training_samples": len(df),
                        "test_samples": len(test_df),
                        "metrics": metrics,
                        "hs_codes_used": ['33', '84', '85', '87', '27', '39', '90', '30']
                    }
                )

                # 프로덕션 승격
                if auto_promote:
                    self.version_manager.promote_to_production(version)

                    # 현재 모델 업데이트
                    self.current_gravity = new_gravity
                    self.current_xgb = new_xgb

                logger.info(f"✅ 재학습 완료: 버전 {version} (개선율: {improvement:.2%})")

                return {
                    "status": "success",
                    "version": version,
                    "promoted": auto_promote,
                    "improvement": improvement,
                    "metrics": metrics
                }

            else:
                logger.warning(f"⚠️ 성능 개선 불충분 ({improvement:.2%} < {self.min_accuracy_improvement:.2%})")
                return {
                    "status": "skipped",
                    "reason": "insufficient_improvement",
                    "improvement": improvement,
                    "threshold": self.min_accuracy_improvement
                }

        except Exception as e:
            logger.error(f"❌ 재학습 실패: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }


def schedule_daily_retraining(pipeline: AutoRetrainingPipeline):
    """매일 자정에 자동 재학습 스케줄"""

    def job():
        logger.info("📅 스케줄된 재학습 실행")
        result = pipeline.retrain(auto_promote=True)

        # 결과 로깅
        if result['status'] == 'success':
            logger.info(f"✅ 재학습 성공: {result['version']}")
        elif result['status'] == 'skipped':
            logger.info(f"⏭️ 재학습 스킵: {result.get('reason')}")
        else:
            logger.error(f"❌ 재학습 실패: {result.get('error')}")

    # 매일 자정 실행
    schedule.every().day.at("00:00").do(job)

    logger.info("⏰ 자동 재학습 스케줄 등록 완료 (매일 00:00)")

    # 스케줄 실행
    while True:
        schedule.run_pending()
        import time
        time.sleep(60)  # 1분마다 체크


if __name__ == '__main__':
    # 테스트
    import os
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(level=logging.INFO)

    # 데이터 수집기
    collector = RealDataCollector(
        use_real_data=False,  # 테스트용 더미 데이터
        comtrade_api_key=os.getenv('UN_COMTRADE_API_KEY')
    )

    # 버전 관리자
    version_manager = ModelVersionManager()

    # 파이프라인
    pipeline = AutoRetrainingPipeline(
        data_collector=collector,
        version_manager=version_manager,
        min_accuracy_improvement=0.01  # 테스트용 1%
    )

    # 수동 재학습
    print("\n수동 재학습 테스트...")
    result = pipeline.retrain(auto_promote=False)

    print("\n결과:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 버전 목록
    print("\n저장된 버전:")
    for v in version_manager.list_versions():
        print(f"  - {v['version']}: {v.get('metrics', {}).get('mae_improvement', 0):.2%} 개선")
