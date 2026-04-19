import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import logging

logger = logging.getLogger("p1")
logging.basicConfig(level=logging.INFO)


def new_request_id() -> str:
    return str(uuid.uuid4())


def now_seoul_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def read_csv_safely(path: str, sep: str = ",") -> pd.DataFrame:
    """
    인코딩 자동탐지 + fallback (utf-8-sig → utf-8 → cp949 → euc-kr → latin1)
    trade_data.csv처럼 인코딩이 깨진 파일에도 대응
    """
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr", "latin1"]
    last_err = None
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, sep=sep, on_bad_lines="skip")
            logger.info(f"[CSV] Loaded '{path}' with encoding={enc}, rows={len(df)}")
            return df
        except Exception as e:
            last_err = e
            continue
    raise ValueError(f"[CSV] 모든 인코딩 시도 실패: {path} / 마지막 오류: {last_err}")


def detect_separator(path: str) -> str:
    """파일 첫 줄로 구분자 자동 탐지 (쉼표/탭/세미콜론)"""
    try:
        with open(path, "rb") as f:
            first_line = f.readline().decode("utf-8-sig", errors="replace")
    except Exception:
        return ","
    tab_count = first_line.count("\t")
    semi_count = first_line.count(";")
    comma_count = first_line.count(",")
    if tab_count >= comma_count and tab_count >= semi_count:
        return "\t"
    if semi_count > comma_count:
        return ";"
    return ","


def strip_all_spaces(s: str) -> str:
    return "".join(str(s).split())
