# -*- coding: utf-8 -*-
"""
NCP Object Storage persistent store for auth data.
Replaces ephemeral filesystem on Render free plan.
Falls back to local file if NCP credentials are not set.
"""
import json
import os
import threading
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BUCKET = os.environ.get("NCP_BUCKET", "marketgate-auth")
REGION = os.environ.get("NCP_REGION", "kr")
USERS_KEY = "auth/users.json"
BLACKLIST_KEY = "auth/token_blacklist.json"
LOCAL_USERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")
LOCAL_BLACKLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "token_blacklist.json")

_lock = threading.Lock()
_client = None
_available = False


def _get_s3():
    global _client, _available
    if _client is not None:
        return _client
    access_key = os.environ.get("NCP_ACCESS_KEY", "")
    secret_key = os.environ.get("NCP_SECRET_KEY", "")
    endpoint = os.environ.get("NCP_ENDPOINT", "https://kr.object.ncloudstorage.com")
    if not access_key or not secret_key:
        return None
    try:
        import boto3
        _client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=REGION,
        )
        _available = True
        logger.info("NCP Object Storage connected (bucket=%s)", BUCKET)
        return _client
    except Exception as e:
        logger.warning("NCP S3 unavailable (%s), using local file", e)
        return None


def _s3_load(key: str, fallback_path: str) -> dict | list:
    s3 = _get_s3()
    if s3 is None:
        return _local_load(fallback_path)
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=key)
        data = json.loads(resp["Body"].read().decode("utf-8"))
        # Also save locally as cache
        _local_save(fallback_path, data)
        return data
    except s3.exceptions.NoSuchKey:
        return {} if "users" in key else []
    except Exception as e:
        logger.warning("S3 load failed for %s: %s, falling back to local", key, e)
        return _local_load(fallback_path)


def _s3_save(key: str, data, fallback_path: str) -> None:
    _local_save(fallback_path, data)
    s3 = _get_s3()
    if s3 is None:
        return
    try:
        s3.put_object(
            Bucket=BUCKET, Key=key,
            Body=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as e:
        logger.warning("S3 save failed for %s: %s", key, e)


def _local_load(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if "users" in path else []


def _local_save(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_ncp_available() -> bool:
    _get_s3()
    return _available
