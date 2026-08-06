# -*- coding: utf-8 -*-
"""PostgreSQL connection pool (optional, graceful fallback to file-based)."""
import os
import logging

logger = logging.getLogger(__name__)

_pool = None
_AVAILABLE = False


def _get_pool():
    global _pool, _AVAILABLE
    if _pool is not None:
        return _pool
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        return None
    try:
        import psycopg2.pool
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1, maxconn=4, dsn=dsn,
            options="-c search_path=public",
        )
        _AVAILABLE = True
        logger.info("PostgreSQL pool connected")
        return _pool
    except Exception as e:
        logger.warning("PostgreSQL unavailable (%s), using file fallback", e)
        return None


def get_conn():
    pool = _get_pool()
    if pool is None:
        return None
    return pool.getconn()


def put_conn(conn):
    pool = _get_pool()
    if pool is not None and conn is not None:
        pool.putconn(conn)


def is_available() -> bool:
    _get_pool()
    return _AVAILABLE
