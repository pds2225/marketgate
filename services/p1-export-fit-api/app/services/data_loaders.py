from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from app.config import Files
from app.utils import read_csv_safely, detect_separator, strip_all_spaces, logger


@dataclass
class DataStore:
    kotra: pd.DataFrame
    mofa: pd.DataFrame
    trade: pd.DataFrame
    wb_gdp: pd.DataFrame
    wb_growth: pd.DataFrame
    distance: pd.DataFrame


_DATASTORE: Optional[DataStore] = None
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(file_path: str) -> str:
    path = Path(file_path)
    if path.is_absolute():
        return str(path)
    return str(_PROJECT_ROOT / path)


def _load_trade(path: str) -> pd.DataFrame:
    """
    trade_data.csv 전용 로더
    1) 구분자 자동탐지 (쉼표/탭/세미콜론)
    2) 인코딩 자동탐지 fallback
    3) 필수 컬럼 검증 후 진단 로그 출력
    """
    sep = detect_separator(path)
    logger.info(f"[TRADE] 감지된 구분자: '{sep}'")
    df = read_csv_safely(path, sep=sep)

    logger.info(f"[TRADE] 컬럼 목록: {df.columns.tolist()}")
    logger.info(f"[TRADE] shape: {df.shape}")

    required = ["refYear", "reporterISO", "partnerISO", "cmdCode", "primaryValue"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"[TRADE] 필수 컬럼 누락: {missing}\n실제 컬럼: {df.columns.tolist()}")

    return df


def load_datastore() -> DataStore:
    global _DATASTORE
    if _DATASTORE is not None:
        return _DATASTORE

    kotra = read_csv_safely(_resolve_path(Files.KOTRA_RECO))
    mofa = read_csv_safely(_resolve_path(Files.MOFA_ISO3))
    trade = _load_trade(_resolve_path(Files.TRADE))
    wb_gdp = read_csv_safely(_resolve_path(Files.WB_GDP))
    wb_growth = read_csv_safely(_resolve_path(Files.WB_GDP_GROWTH))
    distance = read_csv_safely(_resolve_path(Files.DISTANCE))

    # KOTRA 컬럼 검증
    for col in ["HSCD", "NAT_NAME"]:
        if col not in kotra.columns:
            raise ValueError(f"{Files.KOTRA_RECO} missing column: {col}")

    # 외교부 컬럼 검증
    for col in ["한글명", "국제표준화기구_3자리"]:
        if col not in mofa.columns:
            raise ValueError(f"{Files.MOFA_ISO3} missing column: {col}")

    # World Bank 컬럼 검증
    for df, name in [(wb_gdp, "WB_GDP"), (wb_growth, "WB_GDP_GROWTH")]:
        for col in ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"]:
            if col not in df.columns:
                raise ValueError(f"{name} missing column: {col}")

    # Trade 컬럼명 정리 (primaryValue → trade_value_usd)
    trade = trade.rename(columns={"primaryValue": "trade_value_usd"})
    trade["trade_value_usd"] = (
        trade["trade_value_usd"].astype(str).str.replace(",", "", regex=False)
    )
    trade["trade_value_usd"] = pd.to_numeric(trade["trade_value_usd"], errors="coerce").fillna(0.0)

    # Distance 컬럼 검증
    for col in ["origin_country", "target_country", "distance_km"]:
        if col not in distance.columns:
            raise ValueError(f"{Files.DISTANCE} missing column: {col}")

    _DATASTORE = DataStore(
        kotra=kotra,
        mofa=mofa,
        trade=trade,
        wb_gdp=wb_gdp,
        wb_growth=wb_growth,
        distance=distance,
    )
    return _DATASTORE


def _build_mofa_lookup(mofa: pd.DataFrame) -> Dict[str, List[str]]:
    mofa_local = mofa.copy()
    mofa_local["_k"] = mofa_local["한글명"].astype(str).map(strip_all_spaces)
    mofa_local["_iso3"] = mofa_local["국제표준화기구_3자리"].astype(str).str.strip().str.upper()

    lookup: Dict[str, List[str]] = {}
    for row in mofa_local[["_k", "_iso3"]].dropna().itertuples(index=False):
        key = str(row[0])
        iso3 = str(row[1])
        if len(iso3) != 3:
            continue
        lookup.setdefault(key, []).append(iso3)

    return {k: sorted(set(v)) for k, v in lookup.items()}


def kotra_candidate_scores(hs_code_6: str, mofa: pd.DataFrame, kotra: pd.DataFrame) -> Dict[str, float]:
    df = kotra[kotra["HSCD"].astype(str).str.zfill(6) == hs_code_6]
    if df.empty:
        return {}

    mofa_lookup = _build_mofa_lookup(mofa)
    iso3_scores: Dict[str, List[float]] = {}

    for row in df[["NAT_NAME", "EXP_BHRC_SCR"]].itertuples(index=False):
        nat = str(row.NAT_NAME)
        key = strip_all_spaces(nat)
        hits = mofa_lookup.get(key, [])

        if not hits:
            logger.warning(f"[ISO3] NAT_NAME '{nat}' cannot be mapped via MOFA")
            continue

        if len(hits) > 1:
            logger.warning(f"[ISO3] NAT_NAME '{nat}' mapped to multiple ISO3: {hits}")

        raw_score = pd.to_numeric(pd.Series([row.EXP_BHRC_SCR]), errors="coerce").iloc[0]
        score = float(raw_score) if pd.notna(raw_score) else 0.0

        for iso3 in hits:
            iso3_scores.setdefault(iso3, []).append(score)

    candidate_scores: Dict[str, float] = {}
    for iso3, scores in iso3_scores.items():
        valid_scores = [float(s) for s in scores if pd.notna(s)]
        if not valid_scores:
            candidate_scores[iso3] = 1.0
            continue
        candidate_scores[iso3] = max(float(sum(valid_scores) / len(valid_scores)), 0.1)

    return candidate_scores


def kotra_candidates_iso3(hs_code_6: str, mofa: pd.DataFrame, kotra: pd.DataFrame) -> List[str]:
    return sorted(kotra_candidate_scores(hs_code_6, mofa, kotra).keys())


def _trade_rows_for_reporter_partner(
    trade: pd.DataFrame,
    year: int,
    reporter_iso3: str,
    partner_iso3: str,
) -> pd.DataFrame:
    return trade[
        (trade["refYear"].astype(int) == int(year)) &
        (trade["reporterISO"].astype(str).str.upper().str.strip() == reporter_iso3) &
        (trade["partnerISO"].astype(str).str.upper().str.strip() == partner_iso3)
    ]


def _match_trade_value_by_hs(base: pd.DataFrame, hs_code_6: str) -> Optional[float]:
    if base.empty:
        return None

    hs4 = hs_code_6[:4]
    hs2 = hs_code_6[:2]
    cmd = base["cmdCode"].astype(str).str.strip()

    df4 = base[cmd.str.startswith(hs4)]
    df4 = df4[df4["cmdCode"].astype(str).str.strip().str.len() == 4]
    if not df4.empty:
        return float(df4["trade_value_usd"].fillna(0).sum())

    df2 = base[cmd.str.startswith(hs2)]
    df2 = df2[df2["cmdCode"].astype(str).str.strip().str.len() == 2]
    if not df2.empty:
        return float(df2["trade_value_usd"].fillna(0).sum())

    return None


def get_trade_value_usd(
    trade: pd.DataFrame,
    year: int,
    exporter_iso3: str,
    partner_iso3: str,
    hs_code_6: str,
) -> Optional[float]:
    """HS4 우선, 없으면 HS2 fallback. 중복행 합산."""
    base = _trade_rows_for_reporter_partner(trade, year, exporter_iso3, partner_iso3)
    return _match_trade_value_by_hs(base, hs_code_6)


def get_world_trade_value_usd(
    trade: pd.DataFrame,
    year: int,
    exporter_iso3: str,
    hs_code_6: str,
) -> Optional[float]:
    """
    partnerISO 가 W00(세계 합계)만 들어 있는 구조를 지원하기 위한 fallback.
    한국 2023 데이터처럼 국가별 파트너가 빠진 경우 이 값을 후보국별 proxy trade의 기준치로 사용한다.
    """
    base = _trade_rows_for_reporter_partner(trade, year, exporter_iso3, "W00")
    return _match_trade_value_by_hs(base, hs_code_6)


def get_wb_value(wb: pd.DataFrame, year: int, iso3: str) -> Optional[float]:
    df = wb[
        (wb["REF_AREA"].astype(str).str.upper() == iso3) &
        (wb["TIME_PERIOD"].astype(int) == int(year))
    ]
    if df.empty:
        return None
    return float(pd.to_numeric(df["OBS_VALUE"], errors="coerce").dropna().mean())


def get_distance_km(distance: pd.DataFrame, origin_iso3: str, target_iso3: str) -> Optional[float]:
    df = distance[
        (distance["origin_country"].astype(str).str.upper() == origin_iso3) &
        (distance["target_country"].astype(str).str.upper() == target_iso3)
    ]
    if df.empty:
        return None
    return float(pd.to_numeric(df["distance_km"], errors="coerce").dropna().mean())
