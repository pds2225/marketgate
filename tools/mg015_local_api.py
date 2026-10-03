"""Run the real API locally with isolated file stores and no production DB.

Used for MG-015 login/search smoke tests. All state is inside tools/.mg015.
Pass --baseline to execute the four changed scoring/API modules directly from
09ae2f7 git objects, using the same CSV paths without altering tracked files.
"""
import os
import ipaddress
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "services/p1-export-fit-api"
STATE = ROOT / "tools/.mg015/local-api"
STATE.mkdir(parents=True, exist_ok=True)
os.environ.update(APP_ENV="e2e", DATABASE_URL="", PYTHONDONTWRITEBYTECODE="1")
os.environ["TOSS_SECRET_KEY"] = ""
os.environ["JWT_SECRET"] = secrets.token_hex(32)
os.environ["E2E_ADMIN_TOKEN"] = secrets.token_hex(32)
sys.dont_write_bytecode = True
sys.path.insert(0, str(API))
os.chdir(API)


def _local_connections_only(event, args):
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple):
            host = str(address[0])
            if host == "localhost":
                return
            try:
                if ipaddress.ip_address(host).is_loopback:
                    return
            except ValueError:
                pass
        raise RuntimeError("MG-015 local E2E blocks outbound connections")


sys.addaudithook(_local_connections_only)

# Also stop async HTTP clients before Windows ConnectEx can bypass the normal
# socket.connect path. No production/paid HTTP call is permitted by this tool.
import httpx
_sync_send = httpx.Client.send
_async_send = httpx.AsyncClient.send


def _check_http_request(request):
    if request.url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("MG-015 local E2E blocks outbound HTTP")


def _guarded_send(client, request, *args, **kwargs):
    _check_http_request(request)
    return _sync_send(client, request, *args, **kwargs)


async def _guarded_async_send(client, request, *args, **kwargs):
    _check_http_request(request)
    return await _async_send(client, request, *args, **kwargs)


httpx.Client.send = _guarded_send
httpx.AsyncClient.send = _guarded_async_send

if "--baseline" in sys.argv:
    from mg015_predict_benchmark import BaselineLoader
    sys.meta_path.insert(0, BaselineLoader())

import main
from app import auth_store, credit_store, inquiry_store, subscription_store

for module, name, filename in (
    (auth_store, "USERS_PATH", "users.json"),
    (auth_store, "BLACKLIST_PATH", "token_blacklist.json"),
    (credit_store, "CREDITS_PATH", "credits.json"),
    (inquiry_store, "INQUIRIES_PATH", "inquiries.json"),
    (subscription_store, "SUBSCRIPTIONS_PATH", "subscriptions.json"),
):
    setattr(module, name, str(STATE / filename))

# The frontend journey cleans up its local accounts using this temporary token.
(STATE / "admin-token").write_text(os.environ["E2E_ADMIN_TOKEN"], encoding="utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(main.app, host="127.0.0.1", port=8000, log_level="warning")
