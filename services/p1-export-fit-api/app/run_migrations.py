# -*- coding: utf-8 -*-
"""
Auto-run auth migrations on deploy.
Called from buildCommand: python -m app.run_migrations
Skips silently if DATABASE_URL is not set (file fallback mode).
"""
import os
import sys

MIGRATION_SQL = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "db", "migrations", "0004_auth_users.sql"
)


def run():
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        print("[migrate] DATABASE_URL not set, skipping (file fallback)")
        return

    try:
        import psycopg2
    except ImportError:
        print("[migrate] psycopg2 not installed, skipping")
        return

    if not os.path.isfile(MIGRATION_SQL):
        print(f"[migrate] migration file not found: {MIGRATION_SQL}, skipping")
        return

    sql = open(MIGRATION_SQL, "r", encoding="utf-8").read()
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("[migrate] auth tables created/verified")
    except Exception as e:
        conn.rollback()
        # Table already exists is fine
        if "already exists" in str(e):
            print(f"[migrate] tables already exist: {e}")
        else:
            print(f"[migrate] WARNING: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
