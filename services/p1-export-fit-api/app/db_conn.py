# -*- coding: utf-8 -*-
"""PostgreSQL connection pool (optional, graceful fallback to file-based)."""
import os
import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_pool = None
_AVAILABLE = False
_tx = threading.local()


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
    # Prefer an open shared transaction so payment ledger + credit/plan
    # side effects commit atomically (L027 Render wipe / confirm retry).
    shared = getattr(_tx, "conn", None)
    if shared is not None:
        return shared
    pool = _get_pool()
    if pool is None:
        return None
    return pool.getconn()


def put_conn(conn):
    if conn is not None and conn is getattr(_tx, "conn", None):
        # Shared tx connection is released by transaction() below.
        return
    pool = _get_pool()
    if pool is not None and conn is not None:
        # End any open/aborted transaction before reuse. Callers that
        # SELECT … FOR UPDATE (credits, subscriptions) or fail mid-statement
        # otherwise return a locked/aborted connection to ThreadedConnectionPool
        # (maxconn=4), blocking later checkouts until process restart.
        # Successful paths already commit(); rollback after commit is a no-op.
        try:
            conn.rollback()
        except Exception:
            logger.warning("put_conn rollback failed", exc_info=True)
        pool.putconn(conn)


def is_available() -> bool:
    _get_pool()
    return _AVAILABLE


def in_transaction() -> bool:
    return getattr(_tx, "conn", None) is not None


@contextmanager
def transaction():
    """Hold one pool connection for nested store writes in this thread."""
    if getattr(_tx, "conn", None) is not None:
        # Already inside an outer transaction — reuse it.
        yield _tx.conn
        return
    conn = None
    pool = _get_pool()
    if pool is None:
        yield None
        return
    conn = pool.getconn()
    _tx.conn = conn
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _tx.conn = None
        pool.putconn(conn)
