from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional
import weakref
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
    load_errors: list[str] = None


_DATASTORE: Optional[DataStore] = None
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DATASTORE_LOCK = RLock()
_LOOKUP_LOCK = RLock()
_FRAME_LOOKUPS: dict[int, tuple[weakref.ReferenceType, dict]] = {}


def _frame_lookup(frame: pd.DataFrame, name: str, build):
    """Index immutable loader frames once, without attaching mutable attrs.

    Weak references release indexes with replaced/test frames and guard against
    Python object-id reuse. Normalization never changes the source DataFrame.
    """
    identity = id(frame)
    with _LOOKUP_LOCK:
        entry = _FRAME_LOOKUPS.get(identity)
        if entry is None or entry[0]() is not frame:
            def release(reference):
                with _LOOKUP_LOCK:
                    current = _FRAME_LOOKUPS.get(identity)
                    if current is not None and current[0] is reference:
                        del _FRAME_LOOKUPS[identity]
            entry = (weakref.ref(frame, release), {})
            _FRAME_LOOKUPS[identity] = entry
        if name not in entry[1]:
            entry[1][name] = build()
        return entry[1][name]


def _trade_index(trade: pd.DataFrame) -> dict:
    def build():
        keys = pd.DataFrame({
            "year": trade["refYear"].astype(int),
            "reporter": trade["reporterISO"].astype(str).str.upper().str.strip(),
            "partner": trade["partnerISO"].astype(str).str.upper().str.strip(),
            "hs": trade["cmdCode"].astype(str).str.strip(),
        })
        groups = keys.groupby(["year", "reporter", "partner", "hs"], sort=False).indices
        # Use the original pandas Series.sum per group (not groupby.sum's
        # different accumulation) to preserve the exact floating-point result.
        return {key: float(trade["trade_value_usd"].iloc[positions].fillna(0).sum())
                for key, positions in groups.items() if len(key[3]) in (2, 4)}
    return _frame_lookup(trade, "trade", build)


def _numeric_mean_index(frame: pd.DataFrame, *, distance: bool = False) -> dict:
    def build():
        if distance:
            keys = pd.DataFrame({
                "origin": frame["origin_country"].astype(str).str.upper(),
                "target": frame["target_country"].astype(str).str.upper(),
            })
        else:
            keys = pd.DataFrame({
                "iso": frame["REF_AREA"].astype(str).str.upper(),
                "year": frame["TIME_PERIOD"].astype(int),
            })
        return keys.groupby(list(keys.columns), sort=False).indices
    return _frame_lookup(frame, "distance" if distance else "wb", build)


def _indexed_mean(frame: pd.DataFrame, key: tuple, *, distance: bool = False) -> Optional[float]:
    positions = _numeric_mean_index(frame, distance=distance).get(key)
    if positions is None:
        return None
    with _LOOKUP_LOCK:
        values = _frame_lookup(frame, "distance_means" if distance else "wb_means", dict)
        if key not in values:
            # Compute only requested groups, once. Precomputing all 50k
            # distances would unnecessarily delay startup. Preserve the old
            # per-group conversion/dropna/mean and its exact float/NaN result.
            column = "distance_km" if distance else "OBS_VALUE"
            values[key] = float(pd.to_numeric(frame[column].iloc[positions], errors="coerce").dropna().mean())
        return values[key]


def _resolve_path(file_path: str) -> str:
    path = Path(file_path)
    if path.is_absolute():
        return str(path)
    return str(_PROJECT_ROOT / path)


def _empty_trade_df() -> pd.DataFrame:
    """필수 컬럼만 가진 빈 trade DataFrame"""
    return pd.DataFrame(columns=["refYear", "reporterISO", "partnerISO", "cmdCode", "trade_value_usd"])


def _load_trade(path: str) -> pd.DataFrame:
    """
    trade_data.csv 전용 로더
    1) 구분자 자동탐지 (쉼표/탭/세미콜론)
    2) 인코딩 자동탐지 fallback
    3) 필수 컬럼 검증 후 진단 로그 출력
    """
    try:
        sep = detect_separator(path)
        logger.info(f"[TRADE] 감지된 구분자: '{sep}'")
        df = read_csv_safely(path, sep=sep)

        logger.info(f"[TRADE] 컬럼 목록: {df.columns.tolist()}")
        logger.info(f"[TRADE] shape: {df.shape}")

        required = ["refYear", "reporterISO", "partnerISO", "cmdCode", "primaryValue"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            logger.warning(f"[TRADE] 필수 컬럼 누락: {missing}")
            return _empty_trade_df()

        return df
    except Exception as exc:
        logger.error(f"[TRADE] 로드 실패: {exc}")
        return _empty_trade_df()


def _safe_read_csv(path: str, required_cols: list[str], name: str) -> pd.DataFrame:
    """CSV 안전 로드: 실패 시 필수 컬럼을 가진 빈 DataFrame 반환"""
    try:
        resolved = _resolve_path(path)
        if not Path(resolved).exists():
            logger.warning(f"[{name}] 파일 없음: {resolved}")
            return pd.DataFrame(columns=required_cols)
        df = read_csv_safely(resolved)
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            logger.warning(f"[{name}] 컬럼 누락: {missing}")
        return df
    except Exception as exc:
        logger.error(f"[{name}] 로드 실패: {exc}")
        return pd.DataFrame(columns=required_cols)


def load_datastore() -> DataStore:
    with _DATASTORE_LOCK:
        return _load_datastore()


def _load_datastore() -> DataStore:
    global _DATASTORE
    if _DATASTORE is not None:
        return _DATASTORE

    load_errors: list[str] = []

    kotra = _safe_read_csv(Files.KOTRA_RECO, ["HSCD", "NAT_NAME", "EXP_BHRC_SCR"], "KOTRA_RECO")
    if kotra.empty:
        load_errors.append(f"KOTRA_RECO ({Files.KOTRA_RECO})")

    mofa = _safe_read_csv(Files.MOFA_ISO3, ["한글명", "국제표준화기구_3자리"], "MOFA_ISO3")
    if mofa.empty:
        load_errors.append(f"MOFA_ISO3 ({Files.MOFA_ISO3})")

    trade = _load_trade(_resolve_path(Files.TRADE))
    if trade.empty:
        load_errors.append(f"TRADE ({Files.TRADE})")

    wb_gdp = _safe_read_csv(Files.WB_GDP, ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"], "WB_GDP")
    if wb_gdp.empty:
        load_errors.append(f"WB_GDP ({Files.WB_GDP})")

    wb_growth = _safe_read_csv(Files.WB_GDP_GROWTH, ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"], "WB_GDP_GROWTH")
    if wb_growth.empty:
        load_errors.append(f"WB_GDP_GROWTH ({Files.WB_GDP_GROWTH})")

    distance = _safe_read_csv(Files.DISTANCE, ["origin_country", "target_country", "distance_km"], "DISTANCE")
    if distance.empty:
        load_errors.append(f"DISTANCE ({Files.DISTANCE})")

    # Trade 컬럼명 정리 (primaryValue → trade_value_usd)
    if "primaryValue" in trade.columns:
        trade = trade.rename(columns={"primaryValue": "trade_value_usd"})
    if "trade_value_usd" in trade.columns:
        trade["trade_value_usd"] = (
            trade["trade_value_usd"].astype(str).str.replace(",", "", regex=False)
        )
        trade["trade_value_usd"] = pd.to_numeric(trade["trade_value_usd"], errors="coerce").fillna(0.0)

    if load_errors:
        logger.warning(f"[DataStore] 누락 데이터: {load_errors}")

    datastore = DataStore(
        kotra=kotra,
        mofa=mofa,
        trade=trade,
        wb_gdp=wb_gdp,
        wb_growth=wb_growth,
        distance=distance,
        load_errors=load_errors,
    )
    _kotra_hs_positions(kotra)
    _frame_lookup(mofa, "mofa", lambda: _build_mofa_lookup(mofa))
    _trade_index(trade)
    _numeric_mean_index(wb_gdp)
    _numeric_mean_index(wb_growth)
    _numeric_mean_index(distance, distance=True)
    _DATASTORE = datastore
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


def _kotra_hs_positions(kotra: pd.DataFrame) -> dict:
    return _frame_lookup(kotra, "hs", lambda: kotra.groupby(
        kotra["HSCD"].astype(str).str.zfill(6), sort=False
    ).indices)


def kotra_candidate_scores(hs_code_6: str, mofa: pd.DataFrame, kotra: pd.DataFrame) -> Dict[str, float]:
    df = kotra.iloc[_kotra_hs_positions(kotra).get(hs_code_6, [])]
    if df.empty:
        return {}

    mofa_lookup = _frame_lookup(mofa, "mofa", lambda: _build_mofa_lookup(mofa))
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
    values = _trade_index(trade)
    key = (int(year), exporter_iso3, partner_iso3)
    return values.get((*key, hs_code_6[:4]), values.get((*key, hs_code_6[:2])))


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
    return get_trade_value_usd(trade, year, exporter_iso3, "W00", hs_code_6)


def get_wb_value(wb: pd.DataFrame, year: int, iso3: str) -> Optional[float]:
    return _indexed_mean(wb, (iso3, int(year)))


def get_distance_km(distance: pd.DataFrame, origin_iso3: str, target_iso3: str) -> Optional[float]:
    return _indexed_mean(distance, (origin_iso3, target_iso3), distance=True)
