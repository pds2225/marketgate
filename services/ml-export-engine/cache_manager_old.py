"""
캐시 관리 시스템
API 호출 결과를 캐싱하여 성능 향상 및 API 비용 절감
"""

import json
import os
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional
import hashlib


class CacheManager:
    """파일 기반 캐시 관리자"""

    def __init__(self,
                 cache_dir: str = "backend/cache",
                 expiry_hours: int = 24):
        """
        Args:
            cache_dir: 캐시 파일 저장 디렉토리
            expiry_hours: 캐시 만료 시간 (시간)
        """
        self.cache_dir = cache_dir
        self.expiry_hours = expiry_hours
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, *args, **kwargs) -> str:
        """
        캐시 키 생성

        Args, kwargs를 해시하여 고유 키 생성
        """
        key_str = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> str:
        """캐시 파일 경로"""
        return os.path.join(self.cache_dir, f"{key}.pkl")

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 데이터 가져오기

        Args:
            key: 캐시 키

        Returns:
            캐시된 데이터 또는 None
        """
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'rb') as f:
                cached = pickle.load(f)

            # 만료 시간 체크
            cached_time = cached.get('timestamp')
            if cached_time:
                expiry_time = cached_time + timedelta(hours=self.expiry_hours)
                if datetime.now() > expiry_time:
                    # 만료됨
                    os.remove(cache_path)
                    return None

            return cached.get('data')

        except Exception as e:
            print(f"[Cache] 읽기 오류: {e}")
            return None

    def set(self, key: str, data: Any):
        """
        캐시에 데이터 저장

        Args:
            key: 캐시 키
            data: 저장할 데이터
        """
        cache_path = self._get_cache_path(key)

        try:
            cached = {
                'timestamp': datetime.now(),
                'data': data
            }

            with open(cache_path, 'wb') as f:
                pickle.dump(cached, f)

        except Exception as e:
            print(f"[Cache] 저장 오류: {e}")

    def clear(self):
        """모든 캐시 삭제"""
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.pkl'):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"[Cache] 삭제 오류: {e}")

        print("[Cache] 모든 캐시 삭제됨")

    def clear_expired(self):
        """만료된 캐시만 삭제"""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.pkl'):
                filepath = os.path.join(self.cache_dir, filename)

                try:
                    with open(filepath, 'rb') as f:
                        cached = pickle.load(f)

                    cached_time = cached.get('timestamp')
                    if cached_time:
                        expiry_time = cached_time + timedelta(hours=self.expiry_hours)
                        if datetime.now() > expiry_time:
                            os.remove(filepath)
                            count += 1

                except Exception:
                    pass

        print(f"[Cache] {count}개 만료된 캐시 삭제됨")


def cached(cache_manager: CacheManager):
    """
    캐시 데코레이터

    함수 결과를 자동으로 캐싱
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = cache_manager._get_cache_key(
                func.__name__,
                *args,
                **kwargs
            )

            # 캐시 확인
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                print(f"[Cache HIT] {func.__name__}")
                return cached_result

            # 캐시 미스 - 실제 함수 실행
            print(f"[Cache MISS] {func.__name__}")
            result = func(*args, **kwargs)

            # 결과 캐싱
            cache_manager.set(cache_key, result)

            return result

        return wrapper
    return decorator


# 전역 캐시 인스턴스
_global_cache = None


def get_cache_manager() -> CacheManager:
    """전역 캐시 매니저 가져오기"""
    global _global_cache

    if _global_cache is None:
        # 환경 변수에서 설정 읽기
        expiry_hours = int(os.getenv('CACHE_EXPIRY_HOURS', '24'))
        _global_cache = CacheManager(expiry_hours=expiry_hours)

    return _global_cache


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("캐시 매니저 테스트")
    print("=" * 60)

    cache = CacheManager(cache_dir="backend/cache", expiry_hours=24)

    # 캐시 저장
    print("\n[테스트 1] 캐시 저장")
    cache.set("test_key", {"data": "test_value", "number": 123})
    print("  저장 완료")

    # 캐시 읽기
    print("\n[테스트 2] 캐시 읽기")
    result = cache.get("test_key")
    print(f"  결과: {result}")

    # 데코레이터 테스트
    print("\n[테스트 3] 데코레이터")

    @cached(cache)
    def expensive_function(x, y):
        print("  -> 실제 함수 실행 중...")
        import time
        time.sleep(1)  # 비싼 작업 시뮬레이션
        return x + y

    print("  첫 번째 호출:")
    result1 = expensive_function(10, 20)
    print(f"    결과: {result1}")

    print("  두 번째 호출 (캐시 사용):")
    result2 = expensive_function(10, 20)
    print(f"    결과: {result2}")

    # 캐시 정리
    print("\n[테스트 4] 캐시 정리")
    cache.clear()
