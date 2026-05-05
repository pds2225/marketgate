from __future__ import annotations

import argparse
import csv
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = BASE_DIR / "input"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_SAMPLE_DIR = BASE_DIR / "sample_input"

ENCODING_FALLBACKS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
DELIMITER_CANDIDATES = (",", ";", "\t", "|")

COMMON_OUTPUT_COLUMNS = [
    "record_type",
    "source_dataset",
    "source_file",
    "source_row_no",
    "title",
    "normalized_name",
    "country_raw",
    "country_norm",
    "country_iso3",
    "hs_code_raw",
    "hs_code_norm",
    "keywords_raw",
    "keywords_norm",
    "has_contact",
    "contact_name",
    "contact_email",
    "contact_phone",
    "contact_website",
    "valid_until",
]

TITLE_ALIASES = (
    "제목",
    "공고명",
    "문의제목",
    "인콰이어리",
    "관심상품내용",
    "영어상품명",
    "한글상품명",
    "품목명",
    "상세제목",
    "subject",
    "title",
    "offer_name",
    "오퍼명",
    "구매오퍼",
    "요청제목",
)
COMPANY_ALIASES = (
    "회사명",
    "업체명",
    "기업명",
    "상호",
    "바이어명",
    "영어기업명",
    "제공기관명",
    "buyer_name",
    "company_name",
    "company",
)
COUNTRY_ALIASES = (
    "국가",
    "국가명",
    "국가(명)",
    "인솔바이어국가명",
    "country",
    "country_name",
    "buyer_country",
    "소재국",
    "국가(영문)",
    "주소",
)
HS_ALIASES = (
    "HS코드",
    "HS 코드",
    "HS",
    "hs_code",
    "업종코드",
    "품목코드",
    "product_code",
    "상품코드",
)
KEYWORD_ALIASES = (
    "키워드",
    "관심키워드",
    "관심품목",
    "관심상품내용",
    "주요품목",
    "품목명",
    "상품명",
    "제품명",
    "제품군",
    "업종한글명",
    "한글HS코드명",
    "카테고리",
    "품목",
    "keyword",
    "keywords",
)
CONTACT_NAME_ALIASES = (
    "담당자",
    "담당자명",
    "연락담당자",
    "contact_name",
    "manager_name",
)
CONTACT_EMAIL_ALIASES = (
    "이메일",
    "메일",
    "e-mail",
    "email",
    "contact_email",
)
CONTACT_PHONE_ALIASES = (
    "전화번호",
    "연락처",
    "휴대폰",
    "phone",
    "tel",
    "contact_phone",
)
CONTACT_WEBSITE_ALIASES = (
    "웹사이트",
    "홈페이지",
    "사이트",
    "website",
    "url",
    "contact_website",
)
VALID_UNTIL_ALIASES = (
    "유효기간",
    "마감일",
    "만료일",
    "종료일",
    "유효종료일자",
    "상담일",
    "신청종료일",
    "valid_until",
    "expiry_date",
    "end_date",
)

BASE_FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "title": TITLE_ALIASES,
    "company_name": COMPANY_ALIASES,
    "country": COUNTRY_ALIASES,
    "hs_code": HS_ALIASES,
    "keywords": KEYWORD_ALIASES,
    "contact_name": CONTACT_NAME_ALIASES,
    "contact_email": CONTACT_EMAIL_ALIASES,
    "contact_phone": CONTACT_PHONE_ALIASES,
    "contact_website": CONTACT_WEBSITE_ALIASES,
    "valid_until": VALID_UNTIL_ALIASES,
}

MANUAL_COUNTRY_ALIASES = {
    "USA": "미국",
    "US": "미국",
    "UNITEDSTATES": "미국",
    "UNITEDSTATESOFAMERICA": "미국",
    "KOREA": "대한민국",
    "SOUTHKOREA": "대한민국",
    "REPUBLICOFKOREA": "대한민국",
    "KOREAREPUBLICOF": "대한민국",
    "ROK": "대한민국",
    "UK": "영국",
    "U.K.": "영국",
    "UNITEDKINGDOM": "영국",
    "GREATBRITAIN": "영국",
    "BRITAIN": "영국",
    "UAE": "아랍에미리트",
    "UNITEDARABEMIRATES": "아랍에미리트",
    "VIETNAM": "베트남",
    "VIETNAMSOCIALISTREPUBLICOF": "베트남",
    "CHINA": "중국",
    "PRC": "중국",
    "JAPAN": "일본",
    "SINGAPORE": "싱가포르",
    "THAILAND": "태국",
    "INDIA": "인도",
    "MALAYSIA": "말레이시아",
    "HONGKONG": "홍콩",
    "TAIWAN": "대만",
}

NON_NAME_CHAR_RE = re.compile(r"[^0-9A-Za-z가-힣]+")
WHITESPACE_RE = re.compile(r"\s+")
KEYWORD_SPLIT_RE = re.compile(r"[,\|;/\n\r\t·•]+")
NOISE_MARKER_RE = re.compile(
    r"(?:kim@example\.com|example\.com|test@|sample@|dummy@|noreply@|no-reply@|"
    r"\btest\b|\btests?\b|\bsample\b|\bdummy\b|\bdemo\b|테스트|샘플|예시|임시|플레이스홀더)",
    re.IGNORECASE,
)

CONTACT_PHONE_BLACKLIST = {"번호"}
COSMETICS_HS_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "330499",
        (
            "cosmetic",
            "cosmetics",
            "makeup",
            "skin care",
            "skincare",
            "serum",
            "cream",
            "lotion",
            "ampoule",
            "mask",
            "maskpack",
            "sunscreen",
            "sun care",
            "toner",
            "essence",
            "beauty",
            "페이셜",
            "세럼",
            "크림",
            "로션",
            "앰플",
            "마스크",
            "선크림",
            "토너",
            "에센스",
            "스킨케어",
            "화장품",
            "메이크업",
            "미용",
        ),
    ),
)


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("cosmetics_preprocess")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


LOGGER = setup_logger()


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\u3000", " ")
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _is_empty(value: Any) -> bool:
    text = _normalize_text(value)
    return text == "" or text.lower() in {"nan", "none", "null"}


def _normalize_column_key(value: Any) -> str:
    text = _normalize_text(value).casefold()
    text = re.sub(r"[\s\-\_\/\\\.\,\:\;\(\)\[\]\{\}·•'`\"]+", "", text)
    return text


def _normalize_lookup_key(value: Any) -> str:
    text = _normalize_text(value).upper()
    text = re.sub(r"[\s\-\_\/\\\.\,\:\;\(\)\[\]\{\}·•'`\"]+", "", text)
    return text


def _first_non_empty(values: Iterable[Any]) -> str:
    for value in values:
        if not _is_empty(value):
            return _normalize_text(value)
    return ""


def _collect_non_empty(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    collected: list[str] = []
    for value in values:
        text = _normalize_text(value)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        collected.append(text)
    return collected


def _split_keywords(values: Iterable[Any]) -> list[str]:
    tokens: list[str] = []
    for value in values:
        text = _normalize_text(value)
        if not text:
            continue
        for token in KEYWORD_SPLIT_RE.split(text):
            token = _normalize_text(token)
            if token:
                tokens.append(token)
    return tokens


def _normalize_keyword_token(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    text = WHITESPACE_RE.sub(" ", text)
    text = text.casefold()
    return text.strip()


def _join_keywords(values: Iterable[Any]) -> str:
    normalized: list[str] = []
    seen: set[str] = set()
    for token in _split_keywords(values):
        norm = _normalize_keyword_token(token)
        if not norm:
            continue
        key = norm.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(norm)
    return " | ".join(normalized)


def _normalize_company_name(value: Any) -> str:
    raw = _normalize_text(value)
    raw = raw.replace("㈜", " ")
    raw = raw.replace("(주)", " ")
    raw = raw.replace("주식회사", " ")
    raw = raw.replace("유한회사", " ")
    raw = raw.replace("합자회사", " ")
    raw = raw.replace("합명회사", " ")
    text = raw.upper()
    if not text:
        return ""

    suffix_patterns = [
        r"^(주식회사|유한회사|합자회사|합명회사|\(주\)|주)\s*",
        r"^\s*THE\s+",
        r"\s*(주식회사|유한회사|합자회사|합명회사|\(주\)|주)\s*$",
        r"\s*(CO\.?\s*,?\s*LTD\.?|CO\.?\s+LTD\.?|COMPANY\s+LIMITED|COMPANY|LIMITED|LTD\.?|INC\.?|CORP\.?|CORPORATION|LLC|L\.L\.C\.|GMBH|S\.A\.|SA|BV|AG|PLC|PTY\.?\s+LTD\.?|SAS|SRL|S\.R\.L\.|S\.A\.S\.?|PTE\.?\s+LTD\.?)\s*$",
    ]
    for pattern in suffix_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = text.replace("&", " ")
    text = re.sub(r"(^|\s)주($|\s)", " ", text)
    text = "".join(ch for ch in text if ch.isalnum() or "\uac00" <= ch <= "\ud7a3")
    text = WHITESPACE_RE.sub("", text)
    return text.strip()


def _normalize_hs_code(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    if not digits:
        return ""
    return digits[:6]


def _infer_hs_code_from_texts(*values: Any) -> str:
    combined = " ".join(_normalize_text(value).casefold() for value in values if _normalize_text(value))
    if not combined:
        return ""
    for hs_code, keywords in COSMETICS_HS_RULES:
        if any(keyword in combined for keyword in keywords):
            return hs_code
    return ""


def _normalize_valid_until(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""

    candidates = [
        text,
        text.replace(".", "-"),
        text.replace("/", "-"),
        text.replace("년", "-").replace("월", "-").replace("일", ""),
    ]
    for candidate in candidates:
        parsed = pd.to_datetime(candidate, errors="coerce", yearfirst=True, dayfirst=False)
        if pd.notna(parsed):
            return parsed.strftime("%Y-%m-%d")

    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"

    return text


def _normalize_dedup_title(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    return WHITESPACE_RE.sub(" ", text).casefold().strip()


def _row_text_blob(row: pd.Series) -> str:
    fields = [
        "title",
        "normalized_name",
        "country_raw",
        "country_norm",
        "hs_code_raw",
        "hs_code_norm",
        "keywords_raw",
        "keywords_norm",
        "contact_name",
        "contact_email",
        "contact_phone",
        "contact_website",
        "source_dataset",
        "source_file",
    ]
    parts: list[str] = []
    for field in fields:
        text = _normalize_text(row.get(field, ""))
        if text:
            parts.append(text)
    return " | ".join(parts)


def _noise_reason(row: pd.Series) -> str:
    country_iso3 = _normalize_text(row.get("country_iso3", "")).upper()
    country_norm = _normalize_text(row.get("country_norm", ""))
    title = _normalize_text(row.get("title", ""))
    normalized_name = _normalize_text(row.get("normalized_name", ""))
    contact_email = _normalize_text(row.get("contact_email", ""))
    blob = _row_text_blob(row)

    if country_iso3 == "KOR" or country_norm in {"대한민국", "한국"}:
        return "domestic_country"
    if NOISE_MARKER_RE.search(blob):
        return "sample_or_test_marker"
    if title == "" and normalized_name == "":
        return "missing_identity"
    if contact_email and NOISE_MARKER_RE.search(contact_email):
        return "sample_contact"
    return ""


def _filter_noise_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int, dict[str, int]]:
    if df.empty:
        return df.copy(), 0, {}

    working = df.copy()
    reasons: list[str] = []
    keep_mask: list[bool] = []

    for _, row in working.iterrows():
        reason = _noise_reason(row)
        reasons.append(reason)
        keep_mask.append(reason == "")

    working["_noise_reason"] = reasons
    mask_series = pd.Series(keep_mask, index=working.index)
    kept = working[mask_series].copy()
    removed = int((~mask_series).sum())
    reason_counts = (
        working.loc[~mask_series, "_noise_reason"]
        .value_counts()
        .to_dict()
    )
    kept = kept.drop(columns=["_noise_reason"])
    return kept, removed, {str(key): int(value) for key, value in reason_counts.items()}


def _normalize_country_key(value: Any) -> str:
    text = _normalize_text(value).upper()
    text = re.sub(r"[\s\-\_\/\\\.\,\:\;\(\)\[\]\{\}·•'`\"]+", "", text)
    return text


@dataclass(frozen=True)
class CountryLookup:
    exact_map: dict[str, tuple[str, str]]

    def resolve(self, value: Any) -> tuple[str, str]:
        raw = _normalize_text(value)
        if not raw:
            return "", ""

        key = _normalize_country_key(raw)
        if key in self.exact_map:
            return self.exact_map[key]

        for candidate in sorted(self.exact_map.keys(), key=len, reverse=True):
            if len(candidate) < 3:
                continue
            if candidate in key or key in candidate:
                return self.exact_map[candidate]

        return raw, ""


@dataclass(frozen=True)
class SourceSpec:
    key: str
    label: str
    target: str
    filename_patterns: tuple[str, ...]
    field_groups: Mapping[str, tuple[str, ...]]
    sample_rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class LoadResult:
    path: Path
    dataframe: pd.DataFrame
    encoding: str
    delimiter: str
    used_sample: bool


def _extend_groups(base: Mapping[str, tuple[str, ...]], **overrides: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    result = {key: tuple(value) for key, value in base.items()}
    for key, extra_values in overrides.items():
        current = list(result.get(key, ()))
        for value in extra_values:
            if value not in current:
                current.append(value)
        result[key] = tuple(current)
    return result


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec(
        key="ksure_buyer",
        label="한국무역보험공사_화장품 바이어 정보",
        target="buyer_candidate",
        filename_patterns=(
            "한국무역보험공사_화장품 바이어 정보_20200812.csv",
        ),
        field_groups=_extend_groups(
            BASE_FIELD_GROUPS,
            title=("상호명",),
            company_name=("상호명",),
            country=("주소",),
            hs_code=("업종코드",),
            keywords=("업종한글명", "업종코드"),
        ),
        sample_rows=(
            {
                "회사명": "아모레퍼시픽 ",
                "국가": " 미국 ",
                "HS코드": "330499",
                "키워드": "skincare;cosmetics | k-beauty",
                "담당자": "Kim",
                "이메일": "kim@example.com",
                "전화번호": "010-1111-2222",
                "웹사이트": "https://amorepacific.com",
                "유효기간": "2026-06-30",
            },
            {
                "회사명": "아모레퍼시픽",
                "국가": "USA",
                "HS코드": "33-04-99",
                "키워드": "화장품 / 스킨케어",
                "담당자": "",
                "이메일": "",
                "전화번호": "",
                "웹사이트": "",
                "유효기간": "2026/06/30",
            },
        ),
    ),
    SourceSpec(
        key="kotra_sns_buyer",
        label="대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보",
        target="buyer_candidate",
        filename_patterns=(
            "대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보_20251127.csv",
        ),
        field_groups=_extend_groups(
            BASE_FIELD_GROUPS,
            title=("관심상품내용",),
            company_name=("영어기업명",),
            country=("인솔바이어국가명",),
            hs_code=("HS코드",),
            keywords=("관심상품내용", "한글HS코드명"),
        ),
        sample_rows=(
            {
                "바이어명": "LG생활건강",
                "국가명": "대한민국",
                "관심키워드": "뷰티",
                "담당자명": "Lee",
                "연락처": "02-1234-5678",
                "이메일": "contact@lgcare.com",
                "홈페이지": "https://lgcare.com",
                "유효기간": "2026-05-01",
            },
            {
                "바이어명": "LG생활건강 ",
                "국가명": "Korea",
                "관심키워드": "cosmetics|beauty",
                "담당자명": "",
                "연락처": "",
                "이메일": "",
                "홈페이지": "",
                "유효기간": "2026-05-01",
            },
        ),
    ),
    SourceSpec(
        key="kotra_inquiry",
        label="대한무역투자진흥공사_인콰이어리 정보",
        target="opportunity_item",
        filename_patterns=(
            "대한무역투자진흥공사_인콰이어리 정보_20251127.csv",
        ),
        field_groups=_extend_groups(
            BASE_FIELD_GROUPS,
            title=("영어상품명", "한글상품명"),
            country=("국가명",),
            keywords=("영어상품명", "한글상품명"),
            valid_until=("유효종료일자",),
        ),
        sample_rows=(
            {
                "제목": "Skincare inquiry from US distributor",
                "회사명": "ABC Trading",
                "국가": "United States of America",
                "HS코드": "330499",
                "키워드": "skincare",
                "담당자": "John",
                "이메일": "john@abc.com",
                "전화번호": "212-555-0101",
                "유효기간": "2026-07-15",
            },
            {
                "제목": "Skincare inquiry from US distributor ",
                "회사명": "ABC Trading",
                "국가": "USA",
                "HS코드": "330499",
                "키워드": "skincare",
                "담당자": "John",
                "이메일": "john@abc.com",
                "전화번호": "212-555-0101",
                "유효기간": "2026/07/15",
            },
        ),
    ),
    SourceSpec(
        key="sbc_inquiry",
        label="중소벤처기업진흥공단_해외바이어 인콰이어리 신청",
        target="opportunity_item",
        filename_patterns=(
            "중소벤처기업진흥공단_해외바이어 인콰이어리 신청_20241230.csv",
        ),
        field_groups=_extend_groups(
            BASE_FIELD_GROUPS,
            title=("품목명",),
            country=("국가",),
            keywords=("품목명",),
            valid_until=("상담일",),
        ),
        sample_rows=(
            {
                "제목": "Vietnam distributor inquiry",
                "회사명": "Maple Import",
                "국가": "Viet Nam",
                "HS코드": "330499",
                "키워드": "cosmetics;skincare",
                "담당자": "Anna",
                "이메일": "anna@maple.vn",
                "전화번호": "84-28-0000-0000",
                "마감일": "2026-08-01",
            },
        ),
    ),
    SourceSpec(
        key="sbc_offer",
        label="중소벤처기업진흥공단_해외바이어 구매오퍼 정보",
        target="opportunity_item",
        filename_patterns=(
            "중소벤처기업진흥공단_해외바이어 구매오퍼 정보_20241231.csv",
        ),
        field_groups=_extend_groups(
            BASE_FIELD_GROUPS,
            title=("제목",),
            company_name=("제공기관명",),
            country=("국가명",),
            keywords=("제목", "카테고리"),
            valid_until=("신청종료일",),
        ),
        sample_rows=(
            {
                "오퍼명": "Purchase offer for Korean cosmetics",
                "회사명": "Sun Asia",
                "국가": "Singapore",
                "HS코드": "330499",
                "키워드": "beauty offer",
                "담당자명": "Chan",
                "연락처": "65-1111-2222",
                "이메일": "chan@sunasia.sg",
                "유효기간": "2026-09-30",
            },
            {
                "오퍼명": "Purchase offer for Korean cosmetics",
                "회사명": "Sun Asia",
                "국가": "SG",
                "HS코드": "330499",
                "키워드": "beauty offer",
                "담당자명": "Chan",
                "연락처": "65-1111-2222",
                "이메일": "chan@sunasia.sg",
                "유효기간": "2026-09-30",
            },
        ),
    ),
    SourceSpec(
        key="sbc_promising_product",
        label="중소벤처기업진흥공단_업종별 해외시장진출 유망상품 현황",
        target="opportunity_item",
        filename_patterns=(
            "중소벤처기업진흥공단_업종별 해외시장진출 유망상품 현황.csv",
            "중소벤처기업진흥공단_업종별 해외시장진출 유망상품 현황_*.csv",
        ),
        field_groups=_extend_groups(
            BASE_FIELD_GROUPS,
            title=("상품명",),
            company_name=("업천명","업천명","업천명","업천명","업천명","업천명"),
            keywords=("업종", "카테고리"),
        ),
        sample_rows=(
            {
                "업종": "뷰티, 미용, 화장품",
                "카테고리": "Beauty & Personal Care",
                "업천명": "(주)오피코스",
                "상품명": "Cerazor",
                "사업자등록번호": "221-81-45748",
            },
            {
                "업종": "뷰티, 미용, 화장품",
                "카테고리": "Beauty & Personal Care",
                "업천명": "(주)오딧세이",
                "상품명": "올인원 스킨케어 세트(남성용)",
                "사업자등록번호": "134-86-44417",
            },
        ),
    ),
    SourceSpec(
        key="kotra_export_recommend",
        label="대한무역투자진흥공사_수출유망추천정보",
        target="opportunity_item",
        filename_patterns=(
            "kotra_export_recommend_all.csv",
        ),
        field_groups=_extend_groups(
            BASE_FIELD_GROUPS,
            title=("NAT_NAME",),
            country_raw=("NAT_NAME",),
            hs_code_raw=("HSCD",),
            keywords=("EXPORTSCALE", "EXP_BHRC_SCR"),
        ),
        sample_rows=(
            {
                "EXPORTSCALE": "대형",
                "EXP_BHRC_SCR": 11.81,
                "HSCD": 330420,
                "NAT_NAME": "네덜란드",
                "UPDT_DT": "2025-06-26 16:08:53",
            },
        ),
    ),
)


def _build_country_lookup(df: pd.DataFrame) -> CountryLookup:
    required = [
        "국제표준화기구_2자리",
        "국제표준화기구_3자리",
        "영문명",
        "한글명",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"국가표준코드 파일에 필수 컬럼이 없습니다: {missing}")

    exact_map: dict[str, tuple[str, str]] = {}
    kor_to_iso3: dict[str, str] = {}

    columns = list(df.columns)
    kor_idx = columns.index("한글명")
    eng_idx = columns.index("영문명")
    iso2_idx = columns.index("국제표준화기구_2자리")
    iso3_idx = columns.index("국제표준화기구_3자리")

    for row in df.itertuples(index=False, name=None):
        kor = _normalize_text(row[kor_idx])
        eng = _normalize_text(row[eng_idx])
        iso2 = _normalize_text(row[iso2_idx]).upper()
        iso3 = _normalize_text(row[iso3_idx]).upper()

        if not kor:
            continue

        kor_to_iso3[kor] = iso3
        canonical = (kor, iso3)

        for alias in (kor, eng, iso2, iso3):
            alias_key = _normalize_country_key(alias)
            if alias_key:
                exact_map[alias_key] = canonical

    for alias, kor in MANUAL_COUNTRY_ALIASES.items():
        iso3 = kor_to_iso3.get(kor, "")
        alias_key = _normalize_country_key(alias)
        if alias_key:
            exact_map[alias_key] = (kor, iso3)

    return CountryLookup(exact_map=exact_map)


def _locate_country_code_file() -> Path:
    candidates = [
        BASE_DIR / "data" / "외교부_국가표준코드_20251222.csv",
        BASE_DIR / "data" / "외교부_국가표준코드_20251222_original.csv",
        BASE_DIR.parent / "p1-export-fit-api" / "csv" / "외교부_국가표준코드_20251222.csv",
        BASE_DIR.parent / "p1-export-fit-api" / "csv" / "외교부_국가표준코드_20251222_original.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "국가표준코드 파일을 찾지 못했습니다. "
        "services/p1-export-fit-api/csv/외교부_국가표준코드_20251222.csv 파일이 있는지 확인하세요."
    )


def _detect_delimiter(sample_text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=list(DELIMITER_CANDIDATES))
        return dialect.delimiter
    except csv.Error:
        lines = sample_text.splitlines()
        header = lines[0] if lines else sample_text
        counts = {delimiter: header.count(delimiter) for delimiter in DELIMITER_CANDIDATES}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def _read_csv_with_fallback(path: Path) -> LoadResult:
    last_error: Optional[Exception] = None
    with path.open("rb") as handle:
        sample_bytes = handle.read(8192)

    for encoding in ENCODING_FALLBACKS:
        try:
            sample_text = sample_bytes.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

        delimiters = [_detect_delimiter(sample_text)]
        for delimiter in DELIMITER_CANDIDATES:
            if delimiter not in delimiters:
                delimiters.append(delimiter)

        for delimiter in delimiters:
            try:
                df = pd.read_csv(
                    path,
                    encoding=encoding,
                    sep=delimiter,
                    dtype=str,
                    keep_default_na=False,
                    na_filter=False,
                    engine="python",
                )
                df.columns = [str(column).strip() for column in df.columns]
                return LoadResult(
                    path=path,
                    dataframe=df,
                    encoding=encoding,
                    delimiter=delimiter,
                    used_sample=False,
                )
            except Exception as exc:
                last_error = exc
                continue

    raise RuntimeError(f"CSV 파일을 읽지 못했습니다: {path}\n마지막 오류: {last_error}")


def _create_sample_csv(path: Path, rows: tuple[dict[str, str], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(list(rows))
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _ensure_sample_file(spec: SourceSpec, sample_dir: Path) -> Path:
    sample_path = sample_dir / f"{spec.label}.csv"
    if not sample_path.exists():
        _create_sample_csv(sample_path, spec.sample_rows)
    return sample_path


import fnmatch

def _matches_spec(file_name: str, spec: SourceSpec) -> bool:
    candidate_key = _normalize_lookup_key(file_name)
    if not candidate_key:
        return False

    for pattern in spec.filename_patterns:
        # 와일드카드 패턴 직접 매칭
        if fnmatch.fnmatch(file_name, pattern):
            return True
        pattern_key = _normalize_lookup_key(pattern)
        if not pattern_key:
            continue
        if pattern_key in candidate_key or candidate_key in pattern_key:
            return True
    return False


def _discover_source_file(spec: SourceSpec, input_dir: Path, allow_sample_fallback: bool, sample_dir: Path) -> tuple[Path, bool]:
    exact_candidates = [
        input_dir / f"{spec.label}.csv",
        input_dir / f"{spec.key}.csv",
        input_dir / f"{spec.label}.CSV",
        input_dir / f"{spec.key}.CSV",
    ]
    for candidate in exact_candidates:
        if candidate.exists():
            return candidate, False

    if input_dir.exists():
        csv_files = sorted(input_dir.glob("*.csv"), key=lambda path: (len(path.name), path.name))
        for file_path in csv_files:
            if _matches_spec(file_path.name, spec):
                return file_path, False

    if allow_sample_fallback:
        sample_path = _ensure_sample_file(spec, sample_dir)
        return sample_path, True

    raise FileNotFoundError(
        f"입력 CSV를 찾지 못했습니다: {spec.label}\n"
        f"검색 위치: {input_dir}\n"
        "파일명을 dataset label 또는 기관명 키워드로 맞춰 넣으세요."
    )


def _resolve_group_columns(columns: Iterable[str], aliases: tuple[str, ...]) -> list[str]:
    ordered_columns = list(columns)
    normalized_map = {_normalize_column_key(column): column for column in ordered_columns}
    resolved: list[str] = []

    for alias in aliases:
        alias_key = _normalize_column_key(alias)
        if not alias_key:
            continue
        if alias_key in normalized_map:
            column = normalized_map[alias_key]
            if column not in resolved:
                resolved.append(column)

    for alias in aliases:
        alias_key = _normalize_column_key(alias)
        if not alias_key:
            continue
        for normalized_column, actual_column in normalized_map.items():
            if actual_column in resolved:
                continue
            if alias_key in normalized_column or normalized_column in alias_key:
                if len(alias_key) >= 3 or len(normalized_column) >= 3:
                    resolved.append(actual_column)

    return resolved


def _pick_group_value(row: pd.Series, columns: list[str]) -> str:
    return _first_non_empty(row.get(column, "") for column in columns)


def _collect_group_values(row: pd.Series, columns: list[str]) -> list[str]:
    return _collect_non_empty(row.get(column, "") for column in columns)


def _compute_has_contact(
    record_type: str,
    title: str,
    normalized_name: str,
    country_norm: str,
    contact_name: str,
    contact_email: str,
    contact_phone: str,
    contact_website: str,
) -> bool:
    explicit_contact = any(
        not _is_empty(value)
        for value in (contact_name, contact_email, contact_phone, contact_website)
    )
    if explicit_contact:
        return True
    if record_type == "buyer_candidate":
        return not _is_empty(normalized_name) and not _is_empty(country_norm)
    if record_type == "opportunity_item":
        has_actionable_surface = not _is_empty(country_norm) and (
            not _is_empty(title) or not _is_empty(normalized_name)
        )
        return has_actionable_surface
    return False


def transform_source_dataframe(df: pd.DataFrame, spec: SourceSpec, source_file: Path, country_lookup: CountryLookup) -> pd.DataFrame:
    resolved_columns = {
        field_name: _resolve_group_columns(df.columns, aliases)
        for field_name, aliases in spec.field_groups.items()
    }
    if "contact_phone" in resolved_columns:
        resolved_columns["contact_phone"] = [
            column for column in resolved_columns["contact_phone"] if column not in CONTACT_PHONE_BLACKLIST
        ]

    LOGGER.info("[매핑] %s", spec.label)
    for field_name, columns in resolved_columns.items():
        LOGGER.info("  - %s -> %s", field_name, columns if columns else "[]")

    records: list[dict[str, Any]] = []
    for row_index, (_, row) in enumerate(df.iterrows(), start=1):
        title_raw = _pick_group_value(row, resolved_columns.get("title", []))
        company_raw = _pick_group_value(row, resolved_columns.get("company_name", []))
        country_raw = _pick_group_value(row, resolved_columns.get("country", []))
        hs_raw = _pick_group_value(row, resolved_columns.get("hs_code", []))
        valid_raw = _pick_group_value(row, resolved_columns.get("valid_until", []))
        contact_name = _pick_group_value(row, resolved_columns.get("contact_name", []))
        contact_email = _pick_group_value(row, resolved_columns.get("contact_email", []))
        contact_phone = _pick_group_value(row, resolved_columns.get("contact_phone", []))
        contact_website = _pick_group_value(row, resolved_columns.get("contact_website", []))

        keywords_sources = []
        keywords_sources.extend(_collect_group_values(row, resolved_columns.get("keywords", [])))
        if title_raw:
            keywords_sources.append(title_raw)
        if company_raw:
            keywords_sources.append(company_raw)
        if hs_raw:
            keywords_sources.append(hs_raw)

        country_norm, country_iso3 = country_lookup.resolve(country_raw)
        title_clean = _normalize_text(title_raw or company_raw)
        company_clean = _normalize_text(company_raw or title_raw)

        hs_code_norm = _normalize_hs_code(hs_raw)
        if not hs_code_norm:
            hs_code_norm = _infer_hs_code_from_texts(title_raw, company_raw, keywords_sources)

        record = {
            "record_type": spec.target,
            "source_dataset": spec.label,
            "source_file": source_file.name,
            "source_row_no": row_index,
            "title": title_clean or company_clean,
            "normalized_name": _normalize_company_name(company_clean or title_clean),
            "country_raw": country_raw,
            "country_norm": country_norm,
            "country_iso3": country_iso3,
            "hs_code_raw": hs_raw,
            "hs_code_norm": hs_code_norm,
            "keywords_raw": " | ".join(keywords_sources),
            "keywords_norm": _join_keywords(keywords_sources),
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "contact_website": contact_website,
            "valid_until": _normalize_valid_until(valid_raw),
        }
        record["has_contact"] = _compute_has_contact(
            record_type=spec.target,
            title=record["title"],
            normalized_name=record["normalized_name"],
            country_norm=country_norm,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            contact_website=contact_website,
        )
        records.append(record)

    transformed = pd.DataFrame.from_records(records)
    if transformed.empty:
        transformed = pd.DataFrame(columns=COMMON_OUTPUT_COLUMNS)

    for column in COMMON_OUTPUT_COLUMNS:
        if column not in transformed.columns:
            transformed[column] = ""

    transformed = transformed[COMMON_OUTPUT_COLUMNS]
    return transformed


def _deduplicate_target(df: pd.DataFrame, target: str) -> tuple[pd.DataFrame, int]:
    if df.empty:
        return df.copy(), 0

    working = df.copy()
    if target == "buyer_candidate":
        working["_dedup_name"] = working["normalized_name"].map(_normalize_company_name)
        working["_dedup_country"] = working["country_norm"].map(_normalize_text)
        subset = ["_dedup_name", "_dedup_country"]
    elif target == "opportunity_item":
        working["_dedup_title"] = working["title"].map(_normalize_dedup_title)
        working["_dedup_country"] = working["country_norm"].map(_normalize_text)
        working["_dedup_valid"] = working["valid_until"].map(_normalize_valid_until)
        subset = ["_dedup_title", "_dedup_country", "_dedup_valid"]
    else:
        raise ValueError(f"알 수 없는 target입니다: {target}")

    before = len(working)
    deduped = working.drop_duplicates(subset=subset, keep="first").copy()
    removed = before - len(deduped)

    helper_columns = [column for column in deduped.columns if column.startswith("_dedup_")]
    if helper_columns:
        deduped = deduped.drop(columns=helper_columns)

    deduped = deduped[COMMON_OUTPUT_COLUMNS]
    return deduped, removed


def _format_summary_line(
    title: str,
    raw_rows: int,
    transformed_rows: int,
    removed_noise: int,
    removed_rows: int,
    final_rows: int,
    output_path: Path,
) -> str:
    return (
        f"[{title}] 원본 {raw_rows}건 | 변환 {transformed_rows}건 | "
        f"샘플/국내 제거 {removed_noise}건 | 중복 제거 {removed_rows}건 | "
        f"최종 저장 {final_rows}건 | {output_path}"
    )


def process_pipeline(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    country_code_file: Optional[Path] = None,
    allow_sample_fallback: bool = True,
) -> dict[str, Any]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    sample_dir = DEFAULT_SAMPLE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    country_path = Path(country_code_file) if country_code_file else _locate_country_code_file()
    country_load = _read_csv_with_fallback(country_path)
    country_lookup = _build_country_lookup(country_load.dataframe)

    LOGGER.info("[국가표준코드] 경로: %s", country_path)
    LOGGER.info("[국가표준코드] 컬럼: %s", list(country_load.dataframe.columns))

    source_loads: list[dict[str, Any]] = []
    transformed_by_target: dict[str, list[pd.DataFrame]] = {
        "buyer_candidate": [],
        "opportunity_item": [],
    }

    for spec in SOURCE_SPECS:
        source_path, used_sample = _discover_source_file(
            spec=spec,
            input_dir=input_dir,
            allow_sample_fallback=allow_sample_fallback,
            sample_dir=sample_dir,
        )
        load_result = _read_csv_with_fallback(source_path)
        load_result = LoadResult(
            path=load_result.path,
            dataframe=load_result.dataframe,
            encoding=load_result.encoding,
            delimiter=load_result.delimiter,
            used_sample=used_sample,
        )

        LOGGER.info(
            "[원본 로드] %s | %s | encoding=%s | delimiter=%r | rows=%s",
            spec.label,
            load_result.path,
            load_result.encoding,
            load_result.delimiter,
            len(load_result.dataframe),
        )
        LOGGER.info("[원본 컬럼] %s", load_result.dataframe.columns.tolist())
        if used_sample:
            LOGGER.warning("[샘플 사용] 실제 CSV가 없어 샘플 입력을 사용했습니다: %s", load_result.path)

        transformed = transform_source_dataframe(
            df=load_result.dataframe,
            spec=spec,
            source_file=load_result.path,
            country_lookup=country_lookup,
        )
        transformed_by_target[spec.target].append(transformed)
        source_loads.append(
            {
                "spec_key": spec.key,
                "label": spec.label,
                "path": str(load_result.path),
                "rows": len(load_result.dataframe),
                "encoding": load_result.encoding,
                "delimiter": load_result.delimiter,
                "used_sample": used_sample,
                "columns": load_result.dataframe.columns.tolist(),
            }
        )

    summary_targets: dict[str, dict[str, Any]] = {}
    output_files = {
        "buyer_candidate": output_dir / "buyer_candidate.csv",
        "opportunity_item": output_dir / "opportunity_item.csv",
    }

    for target, frames in transformed_by_target.items():
        if frames:
            combined = pd.concat(frames, ignore_index=True)
        else:
            combined = pd.DataFrame(columns=COMMON_OUTPUT_COLUMNS)

        transformed_rows = len(combined)
        filtered, noise_removed, noise_reason_counts = _filter_noise_rows(combined)
        deduped, removed_rows = _deduplicate_target(filtered, target)
        final_rows = len(deduped)
        output_path = output_files[target]
        deduped.to_csv(output_path, index=False, encoding="utf-8-sig")

        summary_targets[target] = {
            "raw_rows": sum(item["rows"] for item in source_loads if SOURCE_KEY_TO_TARGET[item["spec_key"]] == target),
            "transformed_rows": transformed_rows,
            "noise_removed_rows": noise_removed,
            "noise_reason_counts": noise_reason_counts,
            "removed_rows": removed_rows,
            "final_rows": final_rows,
            "output_path": str(output_path),
        }

        LOGGER.info(
            _format_summary_line(
                title=target,
                raw_rows=summary_targets[target]["raw_rows"],
                transformed_rows=transformed_rows,
                removed_noise=noise_removed,
                removed_rows=removed_rows,
                final_rows=final_rows,
                output_path=output_path,
            )
        )

    return {
        "country_code_file": str(country_path),
        "sources": source_loads,
        "targets": summary_targets,
        "output_dir": str(output_dir),
    }


SOURCE_KEY_TO_TARGET = {spec.key: spec.target for spec in SOURCE_SPECS}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cosmetics MVP 데이터 전처리 파이프라인")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="원본 CSV가 들어있는 폴더",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="전처리 결과 CSV 저장 폴더",
    )
    parser.add_argument(
        "--country-code-file",
        type=Path,
        default=None,
        help="국가표준코드 CSV 경로. 비우면 자동 탐색",
    )
    parser.add_argument(
        "--sample-fallback",
        action="store_true",
        help="원본 CSV가 없을 때 sample_input을 사용함",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    process_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        country_code_file=args.country_code_file,
        allow_sample_fallback=args.sample_fallback,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
