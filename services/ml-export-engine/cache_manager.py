"""
캐시 매니저 (강화 버전)
SQLite 기반 영구 캐시 + TTL + 캐시 히트 추적

개선 사항:
- SQLite로 영구 저장 (재시작해도 캐시 유지)
- TTL(Time To Live) 자동 만료
- 캐시 히트/미스 통계
- 해시 기반 키 관리
"""

import sqlite3
import pickle
import hashlib
import json
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
import os


class CacheManager:
    """SQLite 기반 캐시 매니저"""

    def __init__(self, cache_dir: str = "backend/cache", ttl_hours: int = 24):
        """
        Args:
            cache_dir: 캐시 DB 저장 경로
            ttl_hours: 캐시 유효 기간 (시간)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "cache.db"
        self.ttl_seconds = ttl_hours * 3600

        # 통계
        self.stats = {
            "hits": 0,
            "misses": 0,
            "expired": 0
        }

        self._init_db()

    def _init_db(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB,
                created_at REAL,
                expires_at REAL,
                metadata TEXT
            )
        """)

        # 인덱스 생성
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON cache(expires_at)
        """)

        conn.commit()
        conn.close()

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """
        함수 이름 + 인자로 캐시 키 생성

        Returns:
            해시 문자열
        """
        # 인자를 JSON으로 직렬화
        args_str = json.dumps({
            "func": func_name,
            "args": args,
            "kwargs": {k: v for k, v in kwargs.items()}
        }, sort_keys=True, default=str)

        # SHA256 해시
        return hashlib.sha256(args_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Returns:
            캐시된 값 또는 None (없거나 만료됨)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?",
            (key,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            self.stats["misses"] += 1
            return None

        value_blob, expires_at = row

        # TTL 체크
        if time.time() > expires_at:
            self.stats["expired"] += 1
            self.delete(key)
            return None

        # 역직렬화
        try:
            value = pickle.loads(value_blob)
            self.stats["hits"] += 1
            return value
        except Exception as e:
            print(f"[캐시 오류] 역직렬화 실패: {e}")
            self.delete(key)
            return None

    def set(self, key: str, value: Any, metadata: Optional[Dict] = None):
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값 (pickle 가능한 객체)
            metadata: 메타데이터 (선택)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 직렬화
        value_blob = pickle.dumps(value)
        created_at = time.time()
        expires_at = created_at + self.ttl_seconds
        metadata_json = json.dumps(metadata) if metadata else "{}"

        cursor.execute("""
            INSERT OR REPLACE INTO cache (key, value, created_at, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (key, value_blob, created_at, expires_at, metadata_json))

        conn.commit()
        conn.close()

    def delete(self, key: str):
        """캐시 삭제"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    def clear_expired(self):
        """만료된 캐시 일괄 삭제"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM cache WHERE expires_at < ?",
            (time.time(),)
        )

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count

    def clear_all(self):
        """모든 캐시 삭제"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache")
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """캐시 통계 조회"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM cache")
        total_entries = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM cache WHERE expires_at > ?",
            (time.time(),)
        )
        valid_entries = cursor.fetchone()[0]

        conn.close()

        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": total_entries - valid_entries,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "ttl_hours": self.ttl_seconds / 3600
        }

    def cached(self, func):
        """
        데코레이터: 함수 결과를 자동 캐싱

        사용법:
            @cache_manager.cached
            def expensive_function(arg1, arg2):
                ...
        """
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = self._generate_key(func.__name__, args, kwargs)

            # 캐시 확인
            cached_value = self.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 함수 실행
            result = func(*args, **kwargs)

            # 캐시 저장
            metadata = {
                "func": func.__name__,
                "cached_at": datetime.now().isoformat()
            }
            self.set(cache_key, result, metadata)

            return result

        return wrapper


# 전역 캐시 인스턴스
_cache_instance: Optional[CacheManager] = None


def get_cache_manager(
    cache_dir: str = "backend/cache",
    ttl_hours: int = 24,
    enabled: bool = True
) -> Optional[CacheManager]:
    """
    전역 캐시 매니저 인스턴스 가져오기

    Args:
        cache_dir: 캐시 디렉토리
        ttl_hours: TTL (시간)
        enabled: 캐시 활성화 여부

    Returns:
        CacheManager 또는 None (비활성화시)
    """
    global _cache_instance

    if not enabled:
        return None

    if _cache_instance is None:
        _cache_instance = CacheManager(cache_dir, ttl_hours)

    return _cache_instance


# 환경 변수 기반 초기화
def init_cache_from_env():
    """환경 변수에서 캐시 설정 읽어서 초기화"""
    enabled = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'
    ttl_hours = int(os.getenv('CACHE_EXPIRY_HOURS', '24'))

    return get_cache_manager(
        cache_dir="backend/cache",
        ttl_hours=ttl_hours,
        enabled=enabled
    )


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("캐시 매니저 테스트")
    print("=" * 60)

    # 캐시 생성
    cache = CacheManager(cache_dir="backend/cache_test", ttl_hours=1)

    # 데이터 저장
    print("\n[1] 데이터 저장")
    cache.set("test_key", {"result": [1, 2, 3]}, metadata={"source": "test"})
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
