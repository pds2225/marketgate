# -*- coding: utf-8 -*-
"""Company verification store.

Primary path is PostgreSQL (``core.company_registry_checks``). When
``DATABASE_URL`` is unset, or the connection cannot be used (Render rootDir
does not ship ``db/migrations``, so ``core.company_registry_checks`` is often
missing), it falls back to an atomic JSON file, the same pattern as
``inquiry_store`` / ``credit_store``. If that file cannot be written, the
single worker keeps the record in memory so POST then owner GET still
succeeds. The CV-02 provider is a deterministic mock, so a persisted computed
status is not a masked provider failure.

User isolation is preserved on every path: ``get_verification`` only returns a
record whose ``user_id`` matches the caller.
"""
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone

from app.db_conn import get_conn, put_conn

_VERIFICATIONS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "company_verifications.json"
)
_lock = threading.Lock()
# Last resort when Postgres and the ephemeral disk are both unusable.
_memory: dict[str, dict] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _public_record(
    check_id: str,
    company_name: str,
    country_iso3: str,
    registry_check_status: str,
    result_json: dict,
    provider: str,
    requested_at: str,
    completed_at: str | None = None,
) -> dict:
    return {
        "verification_id": check_id,
        "company_name": company_name,
        "country_iso3": country_iso3,
        "registry_check_status": registry_check_status,
        "result_json": result_json,
        "provider": provider,
        "requested_at": requested_at,
        "completed_at": completed_at or requested_at,
    }


def _load() -> dict:
    try:
        with open(_VERIFICATIONS_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    directory = os.path.dirname(_VERIFICATIONS_PATH)
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        prefix=".company-verifications-", suffix=".tmp", dir=directory, text=True
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, _VERIFICATIONS_PATH)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def _stored_record(
    check_id: str,
    user_id: str,
    company_name: str,
    country_iso3: str,
    registration_number: str | None,
    provider: str,
    registry_check_status: str,
    result_json: dict,
    now_iso: str,
) -> dict:
    return {
        "user_id": user_id,
        "registration_number": registration_number,
        **_public_record(
            check_id, company_name, country_iso3,
            registry_check_status, result_json, provider, now_iso,
        ),
    }


def _as_public(rec: dict) -> dict:
    return _public_record(
        rec["verification_id"],
        rec["company_name"],
        rec["country_iso3"],
        rec["registry_check_status"],
        rec["result_json"],
        rec["provider"],
        rec["requested_at"],
        rec.get("completed_at"),
    )


def _owned(rec: dict | None, user_id: str) -> dict | None:
    if rec is None or rec.get("user_id") != user_id:
        return None
    return _as_public(rec)


def _write_file(rec: dict) -> None:
    with _lock:
        data = _load()
        data[rec["verification_id"]] = rec
        _save(data)


def _read_file(check_id: str, user_id: str) -> dict | None:
    with _lock:
        rec = _load().get(check_id)
    return _owned(rec, user_id)


def _write_memory(rec: dict) -> None:
    with _lock:
        _memory[rec["verification_id"]] = rec


def _read_memory(check_id: str, user_id: str) -> dict | None:
    with _lock:
        rec = _memory.get(check_id)
    return _owned(rec, user_id)


def _read_fallback(check_id: str, user_id: str) -> dict | None:
    try:
        found = _read_file(check_id, user_id)
    except OSError:
        found = None
    if found is not None:
        return found
    return _read_memory(check_id, user_id)


def _rollback(conn) -> None:
    try:
        conn.rollback()
    except Exception:
        return


def create_verification(
    *,
    user_id: str,
    company_name: str,
    country_iso3: str,
    registration_number: str | None,
    provider: str,
    registry_check_status: str,
    result_json: dict,
) -> dict:
    """Insert a verification record into core.company_registry_checks (or file)."""
    check_id = str(uuid.uuid4())
    now = _now()
    now_iso = now.isoformat()
    rec = _stored_record(
        check_id, user_id, company_name, country_iso3, registration_number,
        provider, registry_check_status, result_json, now_iso,
    )
    try:
        conn = get_conn()
    except Exception:
        conn = None
    if conn is None:
        try:
            _write_file(rec)
        except OSError:
            _write_memory(rec)
        return _as_public(rec)
    try:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO core.company_registry_checks
                        (check_id, user_id, company_name, country_iso3,
                         registration_number, provider, registry_check_status,
                         result_json, requested_at, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        check_id,
                        user_id,
                        company_name,
                        country_iso3,
                        registration_number,
                        provider,
                        registry_check_status,
                        json.dumps(result_json),
                        now,
                        now,
                    ),
                )
            conn.commit()
        except Exception:
            _rollback(conn)
            try:
                _write_file(rec)
            except OSError:
                _write_memory(rec)
            return _as_public(rec)
        return _as_public(rec)
    finally:
        put_conn(conn)


def _row_to_public(row) -> dict:
    return {
        "verification_id": row[0],
        "company_name": row[1],
        "country_iso3": row[2],
        "registry_check_status": row[3],
        "result_json": row[4],
        "provider": row[5],
        "requested_at": row[6].isoformat() if row[6] else None,
        "completed_at": row[7].isoformat() if row[7] else None,
    }


def get_verification(check_id: str, user_id: str) -> dict | None:
    """Fetch a verification record owned by user_id."""
    try:
        conn = get_conn()
    except Exception:
        conn = None
    if conn is None:
        return _read_fallback(check_id, user_id)
    try:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT check_id, company_name, country_iso3,
                           registry_check_status, result_json, provider,
                           requested_at, completed_at
                    FROM core.company_registry_checks
                    WHERE check_id = %s AND user_id = %s
                    """,
                    (check_id, user_id),
                )
                row = cur.fetchone()
        except Exception:
            _rollback(conn)
            return _read_fallback(check_id, user_id)
        if not row:
            return _read_fallback(check_id, user_id)
        return _row_to_public(row)
    finally:
        put_conn(conn)
