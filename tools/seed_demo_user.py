#!/usr/bin/env python3
"""Ensure the fixed MarketGate demo login exists in local users.json.

Email: demo@marketgate.test
Password: MarketGateDemo2026!

Does not print secrets beyond confirming the email was seeded.
Runtime data path is services/p1-export-fit-api/data/users.json (not committed).
"""

from __future__ import annotations

import json
import os
import sys
import uuid

try:
    import bcrypt
except ImportError:  # pragma: no cover
    print("bcrypt required: pip install bcrypt", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
USERS_PATH = os.path.join(ROOT, "services", "p1-export-fit-api", "data", "users.json")
EMAIL = "demo@marketgate.test"
PASSWORD = "MarketGateDemo2026!"


def main() -> int:
    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
    users: list = []
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, encoding="utf-8") as f:
            users = json.load(f) or []

    if any(str(u.get("email", "")).lower() == EMAIL for u in users):
        print(f"ok: demo user already present ({EMAIL})")
        return 0

    hashed = bcrypt.hashpw(PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    users.append(
        {
            "user_id": str(uuid.uuid4()),
            "email": EMAIL,
            "hashed_pw": hashed,
            "plan": "Basic",
        }
    )
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    print(f"ok: seeded demo user ({EMAIL})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
