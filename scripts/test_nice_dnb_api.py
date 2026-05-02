from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT_DIR / "logs" / "nice_dnb_test_response.json"
SUMMARY_PATH = ROOT_DIR / "logs" / "nice_dnb_report_summary.json"
TIMEOUT_SECONDS = 30
DEFAULT_DUNS = "804735132"
REPORT_PARAMS = {
    "productId": "birstd",
    "inLanguage": "en-US",
    "reportFormat": "PDF",
    "orderReason": "6332",
    "tradeUp": "hq",
    "customerReference": "customer reference text",
}


ERROR_MESSAGES = {
    401: "401 인증 실패: App Key/Secret Key가 잘못되었거나 access_token이 만료/누락되었을 수 있습니다.",
    403: "403 권한 없음: NICE D&B API 사용 권한, IP 허용 목록, 상품 권한을 확인하세요.",
    404: "404 경로 없음: NICE_DNB_TOKEN_URL 또는 NICE_DNB_API_URL이 실제 엔드포인트와 일치하는지 확인하세요.",
    429: "429 호출 한도 초과: API 호출 제한을 초과했습니다. 잠시 후 다시 실행하세요.",
    500: "500 서버 오류: NICE D&B 서버 오류 가능성이 있습니다. 같은 요청으로 재시도하거나 제공사에 문의하세요.",
    503: "503 서비스 사용 불가: 토큰 URL 서버가 일시적으로 응답하지 않거나 점검 중일 수 있습니다. NICE_DNB_TOKEN_URL 값과 제공사 서버 상태를 확인하세요.",
}


class LoggedRuntimeError(RuntimeError):
    pass


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f".env에 {name} 값이 없습니다.")
    return value


def get_access_token(token_url: str, app_key: str, secret_key: str) -> str:
    response = requests.post(
        token_url,
        json={
            "appKey": app_key,
            "appSecret": secret_key,
            "grantType": "client_credentials",
            "scope": "oob",
        },
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json;charset=utf-8",
        },
        timeout=TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        save_response("token", response)
        print_error(response.status_code)
        raise LoggedRuntimeError(f"access_token 발급 실패: HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        save_response("token", response)
        raise LoggedRuntimeError("access_token 발급 응답이 JSON 형식이 아닙니다.") from exc

    access_token = str(payload.get("access_token") or payload.get("accessToken") or "").strip()
    if not access_token:
        save_response("token", response)
        raise LoggedRuntimeError("access_token 발급 응답에 access_token이 없습니다.")

    return access_token


def build_report_url(api_url: str, duns: str) -> str:
    if "{{duns}}" in api_url:
        return api_url.replace("{{duns}}", duns)
    return urljoin(api_url.rstrip("/") + "/", duns)


def call_report_api(api_url: str, access_token: str, duns: str) -> requests.Response:
    return requests.get(
        build_report_url(api_url, duns),
        params=REPORT_PARAMS,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json;charset=utf-8",
        },
        timeout=TIMEOUT_SECONDS,
    )


def response_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def save_response(stage: str, response: requests.Response) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response_body(response),
    }
    LOG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_summary(body: Any) -> None:
    if not isinstance(body, dict):
        return
    summary = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "organization": body.get("organization"),
        "contents": body.get("contents"),
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_local_error(stage: str, message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "status_code": None,
        "headers": {},
        "body": {"error": message},
    }
    LOG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_error(status_code: int) -> None:
    message = ERROR_MESSAGES.get(status_code)
    if message:
        print(message)
    elif 400 <= status_code < 500:
        print(f"{status_code} 요청 오류: 요청 파라미터, 인증 정보, API 계약을 확인하세요.")
    elif status_code >= 500:
        print(f"{status_code} 서버 오류: NICE D&B API 서버 상태를 확인하세요.")


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")

    try:
        app_key = required_env("NICE_DNB_APP_KEY")
        secret_key = required_env("NICE_DNB_SECRET_KEY")
        token_url = required_env("NICE_DNB_TOKEN_URL")
        api_url = required_env("NICE_DNB_API_URL")
        duns = os.getenv("NICE_DNB_DUNS", DEFAULT_DUNS).strip() or DEFAULT_DUNS

        access_token = get_access_token(token_url, app_key, secret_key)
        response = call_report_api(api_url, access_token, duns)
        save_response("api", response)
        save_summary(response_body(response))

        print(f"응답 저장 완료: {LOG_PATH}")
        print(f"요약 저장 완료: {SUMMARY_PATH}")
        print(f"status_code: {response.status_code}")
        if response.status_code >= 400:
            print_error(response.status_code)
            return 1

        return 0
    except requests.Timeout:
        message = f"요청 시간 초과: {TIMEOUT_SECONDS}초 안에 응답이 오지 않았습니다."
        save_local_error("request", message)
        print(message)
        return 1
    except requests.RequestException as exc:
        message = f"HTTP 요청 실패: {exc}"
        save_local_error("request", message)
        print(message)
        return 1
    except RuntimeError as exc:
        message = str(exc)
        if not isinstance(exc, LoggedRuntimeError):
            save_local_error("config", message)
        print(message)
        return 1


if __name__ == "__main__":
    sys.exit(main())
