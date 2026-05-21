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
import app.auth_deps as _auth_deps_module  # noqa: E402

_MOCK_USER = {
    "user_id": "test-user",
    "email": "test@example.com",
    "plan": "Advanced",
    "login_fail_count": 0,
    "locked_until": None,
}

app.dependency_overrides[get_current_user] = lambda: _MOCK_USER
app.dependency_overrides[get_token_payload] = lambda: {"sub": "test-user", "type": "access", "jti": "test-jti"}

# require_plan now calls get_subscription() directly (not via Depends), so we
# patch the module-level reference in auth_deps to return Advanced for the test user.
_auth_deps_module.get_subscription = lambda user_id: {"plan": "Advanced", "started_at": None, "expires_at": None}
