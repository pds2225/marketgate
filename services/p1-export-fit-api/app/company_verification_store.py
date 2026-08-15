# -*- coding: utf-8 -*-
"""Company verification store (DB-only, no file fallback)."""
import json
import uuid
from datetime import datetime, timezone

from app.db_conn import get_conn, put_conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
    """Insert a verification record into core.company_registry_checks."""
    check_id = str(uuid.uuid4())
    now = _now()
    conn = get_conn()
    if conn is None:
        raise RuntimeError("PostgreSQL unavailable")
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
    finally:
        put_conn(conn)
    return {
        "verification_id": check_id,
        "company_name": company_name,
        "country_iso3": country_iso3,
        "registry_check_status": registry_check_status,
        "result_json": result_json,
        "provider": provider,
        "requested_at": now.isoformat(),
        "completed_at": now.isoformat(),
    }


def get_verification(check_id: str, user_id: str) -> dict | None:
    """Fetch a verification record owned by user_id."""
    conn = get_conn()
    if conn is None:
        return None
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
            if not row:
                return None
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
    finally:
        put_conn(conn)
