# -*- coding: utf-8 -*-
"""
Auto-run DB migrations on deploy.
Called from buildCommand: python -m app.run_migrations
Skips silently if DATABASE_URL is not set (file fallback mode).
"""
import os
import sys

def _migrations_dir() -> str:
    """Prefer the monorepo SQL. Render rootDir is the service folder, so the
    repo ``db/migrations`` path is absent there and the bundled copy is used.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.normpath(os.path.join(here, "..", "..", "..", "db", "migrations"))
    bundled_dir = os.path.normpath(os.path.join(here, "migrations"))
    if os.path.isfile(os.path.join(repo_dir, "0006_company_registry_checks.sql")):
        return repo_dir
    return bundled_dir


_MIGRATION_FILES = (
    "0004_auth_users.sql",
    "0005_payment_credits.sql",
    "0006_company_registry_checks.sql",
)


def _run_file(conn, path: str) -> None:
    sql = open(path, "r", encoding="utf-8").read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"[migrate] applied {os.path.basename(path)}")


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

    conn = psycopg2.connect(dsn)
    try:
        migrations_dir = _migrations_dir()
        for name in _MIGRATION_FILES:
            path = os.path.join(migrations_dir, name)
            if not os.path.isfile(path):
                print(f"[migrate] migration file not found: {path}, skipping")
                continue
            try:
                _run_file(conn, path)
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e):
                    print(f"[migrate] {name}: tables already exist ({e})")
                else:
                    print(f"[migrate] WARNING {name}: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
