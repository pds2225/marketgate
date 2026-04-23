from __future__ import annotations

import os

DEFAULT_API_BASE_URL = "http://localhost:8000"


def get_api_base_url() -> str:
    return (
        os.getenv("VITE_VALUEUP_API_BASE_URL")
        or os.getenv("VITE_API_BASE_URL")
        or os.getenv("VALUEUP_API_BASE_URL")
        or DEFAULT_API_BASE_URL
    ).rstrip("/")
