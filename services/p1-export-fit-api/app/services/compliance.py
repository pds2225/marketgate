"""제재국 컴플라이언스 — 단일 진실 출처 (SIMULATION_SPEC §2, §5).

이 모듈 외의 어디에도 제재 국가 목록을 두지 않는다.
- BLOCKED: 거래 불가. 진입점에서 HTTP 400 (SPEC §2.2), 추천 결과에서 제외.
- RESTRICTED: 경고 + 감점 대상. 점수 반영(-10)은 scoring 쪽에서 이 모듈을 import해 적용(B1).
"""
from fastapi import HTTPException

# SPEC §5.1 — ISO2 기준 목록
BLOCKED_COUNTRIES = {
    "KP": "북한",
    "IR": "이란",
    "SY": "시리아",
    "CU": "쿠바",
}

# restricted: ISO2 -> 제한 시작일 (SPEC §5.1)
RESTRICTED_COUNTRIES = {
    "RU": "2022-03-01",
    "BY": "2022-03-01",
    "MM": "2021-02-01",
    "VE": "2019-01-01",
}

RESTRICTED_NAMES = {
    "RU": "러시아",
    "BY": "벨라루스",
    "MM": "미얀마",
    "VE": "베네수엘라",
}

# 추천 엔진은 ISO3(partner_country_iso3)를 사용하므로 ISO3 → ISO2 매핑 병기
_ISO3_TO_ISO2 = {
    "PRK": "KP", "IRN": "IR", "SYR": "SY", "CUB": "CU",
    "RUS": "RU", "BLR": "BY", "MMR": "MM", "VEN": "VE",
}

LEGAL_NOTICE = (
    "UN 안보리 결의 및 대한민국 전략물자 수출입고시에 따라 거래가 제한되는 국가입니다."
)
REFERENCE_URL = "https://www.yestrade.go.kr"


def normalize_country_code(code: str) -> str:
    """ISO2/ISO3 입력을 ISO2로 정규화. 대소문자 무시(SPEC §5.3)."""
    c = (code or "").strip().upper()
    return _ISO3_TO_ISO2.get(c, c)


def is_blocked(code: str) -> bool:
    return normalize_country_code(code) in BLOCKED_COUNTRIES


def is_restricted(code: str) -> bool:
    return normalize_country_code(code) in RESTRICTED_COUNTRIES


def restricted_since(code: str) -> str | None:
    return RESTRICTED_COUNTRIES.get(normalize_country_code(code))


def assert_country_allowed(code: str) -> None:
    """blocked 국가면 SPEC §2.2 응답 필드로 HTTP 400을 발생시킨다."""
    norm = normalize_country_code(code)
    if norm in BLOCKED_COUNTRIES:
        name = BLOCKED_COUNTRIES[norm]
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "error_code": "BLOCKED_COUNTRY",
                "error_message": f"{name}({norm})은(는) 거래 불가 국가입니다.",
                "target_country": norm,
                "country_name": name,
                "compliance_status": "blocked",
                "legal_notice": LEGAL_NOTICE,
                "reference_url": REFERENCE_URL,
            },
        )


def restricted_info(code: str) -> dict | None:
    """restricted 국가면 SPEC §2.3 플래그 블록을, 아니면 None을 반환한다."""
    norm = normalize_country_code(code)
    if norm not in RESTRICTED_COUNTRIES:
        return None
    return {
        "status": "restricted",
        "country_code": norm,
        "country_name": RESTRICTED_NAMES.get(norm),
        "requires_export_license": True,
        "restricted_since": RESTRICTED_COUNTRIES[norm],
    }


def filter_blocked_results(results: list) -> list:
    """국가 추천 결과에서 blocked 국가를 제거하고 rank를 다시 매긴다."""
    filtered = [
        r for r in results if not is_blocked(r.get("partner_country_iso3", ""))
    ]
    if len(filtered) != len(results):
        for i, r in enumerate(filtered, start=1):
            r["rank"] = i
    return filtered
