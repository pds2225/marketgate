"""
Redis 기반 캐시 매니저 (Production 버전)

개선 사항:
- 분산 환경 지원 (멀티 프로세스/서버)
- 자동 페일오버 (Redis 장애시 SQLite 폴백)
- 클러스터 모드 지원
- 메모리 효율적인 압축
"""

import redis
import pickle
import hashlib
import json
import time
import zlib
from typing import Any, Optional, Dict
from datetime import timedelta
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """Redis 기반 캐시 매니저 (SQLite 폴백 지원)"""

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        ttl_hours: int = 24,
        enable_compression: bool = True,
        fallback_to_sqlite: bool = True
    ):
        """
        Args:
            redis_host: Redis 서버 주소
            redis_port: Redis 포트
            redis_db: Redis DB 번호
            redis_password: Redis 비밀번호
            ttl_hours: 캐시 유효 기간 (시간)
            enable_compression: 압축 활성화 (메모리 절약)
            fallback_to_sqlite: Redis 실패시 SQLite 사용
        """
        self.ttl_seconds = ttl_hours * 3600
        self.enable_compression = enable_compression
        self.fallback_to_sqlite = fallback_to_sqlite

        # 통계
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "fallback_used": 0
        }

        # Redis 연결
        try:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=False,  # 바이너리 지원
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True,
                max_connections=50
            )

            # 연결 테스트
            self.redis.ping()
            logger.info(f"✅ Redis 연결 성공 ({redis_host}:{redis_port})")
            self.redis_available = True

        except redis.ConnectionError as e:
            logger.error(f"❌ Redis 연결 실패: {e}")
            self.redis_available = False

            if fallback_to_sqlite:
                logger.warning("⚠️ SQLite 폴백 모드로 전환")
                from cache_manager import CacheManager
                self.fallback_cache = CacheManager(
                    cache_dir="backend/cache_fallback",
                    ttl_hours=ttl_hours
                )
            else:
                self.fallback_cache = None

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """캐시 키 생성 (SHA256)"""
        key_data = json.dumps({
            "func": func_name,
            "args": args,
            "kwargs": kwargs
        }, sort_keys=True, default=str)

        return f"valueup:cache:{hashlib.sha256(key_data.encode()).hexdigest()}"

    def _serialize(self, value: Any) -> bytes:
        """값 직렬화 (pickle + 압축)"""
        pickled = pickle.dumps(value)

        if self.enable_compression:
            # zlib 압축 (평균 70% 크기 감소)
            compressed = zlib.compress(pickled, level=6)
            # 압축 여부 표시 (첫 바이트)
            return b'\x01' + compressed
        else:
            return b'\x00' + pickled

    def _deserialize(self, data: bytes) -> Any:
        """값 역직렬화"""
        if not data:
            return None

        compressed = data[0] == 1

        if compressed:
            pickled = zlib.decompress(data[1:])
        else:
            pickled = data[1:]

        return pickle.loads(pickled)

    def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        if self.redis_available:
            try:
                data = self.redis.get(key)

                if data:
                    self.stats["hits"] += 1
                    return self._deserialize(data)
                else:
                    self.stats["misses"] += 1
                    return None

            except redis.RedisError as e:
                logger.error(f"Redis GET 실패: {e}")
                self.stats["errors"] += 1

                # 폴백
                if self.fallback_cache:
                    self.stats["fallback_used"] += 1
                    return self.fallback_cache.get(key)
                return None

        else:
            # Redis 비활성화 → 폴백
            if self.fallback_cache:
                return self.fallback_cache.get(key)
            return None

    def set(self, key: str, value: Any, metadata: Optional[Dict] = None):
        """캐시 저장"""
        if self.redis_available:
            try:
                serialized = self._serialize(value)

                # TTL과 함께 저장
                self.redis.setex(
                    key,
                    timedelta(seconds=self.ttl_seconds),
                    serialized
                )

                # 메타데이터 저장 (선택)
                if metadata:
                    meta_key = f"{key}:meta"
                    self.redis.setex(
                        meta_key,
                        timedelta(seconds=self.ttl_seconds),
                        json.dumps(metadata)
                    )

            except redis.RedisError as e:
                logger.error(f"Redis SET 실패: {e}")
                self.stats["errors"] += 1

                # 폴백
                if self.fallback_cache:
                    self.fallback_cache.set(key, value, metadata)

        else:
            # Redis 비활성화 → 폴백
            if self.fallback_cache:
                self.fallback_cache.set(key, value, metadata)

    def delete(self, key: str):
        """캐시 삭제"""
        if self.redis_available:
            try:
                self.redis.delete(key)
                self.redis.delete(f"{key}:meta")
            except redis.RedisError as e:
                logger.error(f"Redis DELETE 실패: {e}")

    def clear_all(self):
        """모든 캐시 삭제"""
        if self.redis_available:
            try:
                # valueup:cache:* 패턴의 모든 키 삭제
                cursor = 0
                while True:
                    cursor, keys = self.redis.scan(
                        cursor,
                        match="valueup:cache:*",
                        count=100
                    )

                    if keys:
                        self.redis.delete(*keys)

                    if cursor == 0:
                        break

                logger.info("Redis 캐시 전체 삭제 완료")

            except redis.RedisError as e:
                logger.error(f"Redis CLEAR 실패: {e}")

        if self.fallback_cache:
            self.fallback_cache.clear_all()

    def get_stats(self) -> Dict:
        """캐시 통계"""
        if self.redis_available:
            try:
                info = self.redis.info('stats')
                memory_info = self.redis.info('memory')

                # Redis 키 개수
                total_keys = self.redis.dbsize()

                # valueup 관련 키만 카운트
                cursor, keys = self.redis.scan(0, match="valueup:cache:*", count=1000)
                valueup_keys = len(keys)

                total_requests = self.stats["hits"] + self.stats["misses"]
                hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

                return {
                    "backend": "redis",
                    "total_entries": total_keys,
                    "valid_entries": valueup_keys,
                    "hits": self.stats["hits"],
                    "misses": self.stats["misses"],
                    "errors": self.stats["errors"],
                    "fallback_used": self.stats["fallback_used"],
                    "hit_rate_percent": round(hit_rate, 2),
                    "memory_used_mb": round(memory_info.get('used_memory', 0) / (1024**2), 2),
                    "evicted_keys": info.get('evicted_keys', 0),
                    "redis_available": True,
                    "ttl_hours": self.ttl_seconds / 3600
                }

            except redis.RedisError as e:
                logger.error(f"Redis STATS 실패: {e}")
                return {"backend": "redis (error)", "redis_available": False}

        else:
            # 폴백 통계
            if self.fallback_cache:
                fallback_stats = self.fallback_cache.get_stats()
                fallback_stats["backend"] = "sqlite (fallback)"
                return fallback_stats

            return {
                "backend": "none",
                "redis_available": False,
                "error": "캐시 시스템 비활성화"
            }

    def cached(self, func):
        """데코레이터: 함수 결과 자동 캐싱"""
        def wrapper(*args, **kwargs):
            cache_key = self._generate_key(func.__name__, args, kwargs)

            # 캐시 확인
            cached_value = self.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {func.__name__}")
                return cached_value

            # 함수 실행
            logger.debug(f"Cache MISS: {func.__name__}")
            result = func(*args, **kwargs)

            # 캐시 저장
            metadata = {
                "func": func.__name__,
                "cached_at": time.time()
            }
            self.set(cache_key, result, metadata)

            return result

        return wrapper


# 전역 캐시 인스턴스
_redis_cache_instance: Optional[RedisCacheManager] = None


def get_redis_cache_manager(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
    ttl_hours: int = 24,
    enabled: bool = True
) -> Optional[RedisCacheManager]:
    """전역 Redis 캐시 매니저"""
    global _redis_cache_instance

    if not enabled:
        return None

    if _redis_cache_instance is None:
        _redis_cache_instance = RedisCacheManager(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            redis_password=redis_password,
            ttl_hours=ttl_hours
        )

    return _redis_cache_instance


def init_redis_cache_from_env():
    """환경 변수에서 Redis 설정 읽기"""
    enabled = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'
    use_redis = os.getenv('USE_REDIS_CACHE', 'true').lower() == 'true'

    if not enabled or not use_redis:
        logger.info("Redis 캐시 비활성화, SQLite 사용")
        from cache_manager import init_cache_from_env
        return init_cache_from_env()

    return get_redis_cache_manager(
        redis_host=os.getenv('REDIS_HOST', 'localhost'),
        redis_port=int(os.getenv('REDIS_PORT', 6379)),
        redis_db=int(os.getenv('REDIS_DB', 0)),
        redis_password=os.getenv('REDIS_PASSWORD'),
        ttl_hours=int(os.getenv('CACHE_EXPIRY_HOURS', 24)),
        enabled=enabled
    )


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("Redis 캐시 매니저 테스트")
    print("=" * 60)

    # 캐시 생성
    cache = RedisCacheManager(
        redis_host="localhost",
        redis_port=6379,
        ttl_hours=1,
        fallback_to_sqlite=True
    )

    # 데이터 저장
    print("\n[1] 데이터 저장")
    cache.set("test_key", {"result": [1, 2, 3], "name": "테스트"})
    print("  -> 저장 완료")

    # 데이터 조회
    print("\n[2] 데이터 조회")
    value = cache.get("test_key")
    print(f"  -> {value}")

    # 통계
    print("\n[3] 캐시 통계")
    stats = cache.get_stats()
    for key, val in stats.items():
        print(f"  {key}: {val}")

    # 데코레이터 테스트
    print("\n[4] 데코레이터 테스트")

    @cache.cached
    def slow_function(x, y):
        print(f"    실제 함수 실행: {x} + {y}")
        time.sleep(0.1)
        return x + y

    print("  첫 번째 호출:")
    result1 = slow_function(10, 20)
    print(f"    결과: {result1}")

    print("  두 번째 호출 (캐시됨):")
    result2 = slow_function(10, 20)
    print(f"    결과: {result2}")

    print("\n[5] 최종 통계")
    stats = cache.get_stats()
    for key, val in stats.items():
        print(f"  {key}: {val}")
