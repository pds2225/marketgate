from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

from main import app  # noqa: E402
from app.auth_deps import get_current_user, get_token_payload  # noqa: E402
import app.subscription_store as _ss  # noqa: E402

_MOCK_USER = {
    "user_id": "test-user",
    "email": "test@example.com",
    "plan": "Advanced",
    "login_fail_count": 0,
    "locked_until": None,
}

# Provide a matching subscription record so require_plan() resolves correctly.
_MOCK_SUBSCRIPTION = {"plan": "Advanced", "started_at": None, "expires_at": None}
_orig_get_subscription = _ss.get_subscription


def _mock_get_subscription(user_id: str) -> dict:
    if user_id == _MOCK_USER["user_id"]:
        return _MOCK_SUBSCRIPTION
    return _orig_get_subscription(user_id)


_ss.get_subscription = _mock_get_subscription

app.dependency_overrides[get_current_user] = lambda: _MOCK_USER
app.dependency_overrides[get_token_payload] = lambda: {"sub": "test-user", "type": "access", "jti": "test-jti"}
