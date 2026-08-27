"""Normalisation and quality checks for the market snapshot."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import MARKET_TZ, NEGATIVE_PRICE_THRESHOLD_EUR_MWH

SOURCE_COLUMNS = [
    "price_da",
    "load_actual",
    "wind_onshore_actual",
    "wind_offshore_actual",
    "solar_actual",
]
ANALYSIS_COLUMNS = [
    "price_eur_mwh",
    "load_mw",
    "wind_onshore_mw",
    "wind_offshore_mw",
    "solar_mw",
]


def local_date_window(
    start_date: str,
    end_date: str,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Convert inclusive Berlin calendar dates to an inclusive UTC window."""

    start_local = pd.Timestamp(start_date).tz_localize(MARKET_TZ).normalize()
    end_local_exclusive = (
        pd.Timestamp(end_date).tz_localize(MARKET_TZ).normalize()
        + pd.Timedelta(days=1)
    )
    if end_local_exclusive <= start_local:
        raise ValueError("end_date must not precede start_date")
    return start_local.tz_convert("UTC"), (
        end_local_exclusive.tz_convert("UTC") - pd.Timedelta(nanoseconds=1)
    )


def expected_hours_for_local_date(local_date: str | pd.Timestamp) -> int:
    """Return 23, 24 or 25 for a Europe/Berlin local calendar day."""

    day = pd.Timestamp(local_date).tz_localize(None).normalize()
    start = day.tz_localize(MARKET_TZ)
    end = (day + pd.Timedelta(days=1)).tz_localize(MARKET_TZ)
    return int((end.tz_convert("UTC") - start.tz_convert("UTC")).total_seconds() / 3600)


def normalise_market_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Create a portable row-oriented snapshot from aligned SMARD series."""

    missing = [column for column in SOURCE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"source frame is missing columns: {missing}")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("source frame must have a DatetimeIndex")
    if frame.index.tz is None:
        raise ValueError("source frame index must be timezone-aware")

    index = pd.DatetimeIndex(frame.index).tz_convert("UTC")
    if index.has_duplicates:
        raise ValueError("source frame contains duplicate timestamps")

    local = index.tz_convert(MARKET_TZ)
    out = pd.DataFrame(
        {
            "timestamp_utc": index,
            "local_date": local.strftime("%Y-%m-%d"),
            "local_hour": local.hour.astype(int),
            "month_num": local.month.astype(int),
            "day_of_week": local.dayofweek.astype(int),
            "is_weekend": (local.dayofweek >= 5).astype(int),
            "price_eur_mwh": pd.to_numeric(frame["price_da"], errors="coerce").to_numpy(),
            "load_mw": pd.to_numeric(frame["load_actual"], errors="coerce").to_numpy(),
            "wind_onshore_mw": pd.to_numeric(
                frame["wind_onshore_actual"], errors="coerce"
            ).to_numpy(),
            "wind_offshore_mw": pd.to_numeric(
                frame["wind_offshore_actual"], errors="coerce"
            ).to_numpy(),
            "solar_mw": pd.to_numeric(frame["solar_actual"], errors="coerce").to_numpy(),
        }
    )

    generation_columns = [
        "load_mw",
        "wind_onshore_mw",
        "wind_offshore_mw",
        "solar_mw",
    ]
    for column in generation_columns:
        observed = out[column].dropna()
        if not observed.empty and float(observed.min()) < -1e-6:
            raise ValueError(f"{column} contains a negative generation/load value")

    return out


def complete_analysis_rows(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Keep rows with the price and every observed fundamental available."""

    missing = [column for column in ANALYSIS_COLUMNS if column not in snapshot.columns]
    if missing:
        raise ValueError(f"snapshot is missing analysis columns: {missing}")
    out = snapshot.dropna(subset=ANALYSIS_COLUMNS).copy()
    out["negative_price"] = (
        out["price_eur_mwh"] < NEGATIVE_PRICE_THRESHOLD_EUR_MWH
    ).astype(int)
    out["wind_total_mw"] = out["wind_onshore_mw"] + out["wind_offshore_mw"]
    out["residual_load_mw"] = out["load_mw"] - out["wind_total_mw"] - out["solar_mw"]
    out["wind_share_of_load"] = np.where(
        out["load_mw"] > 0, out["wind_total_mw"] / out["load_mw"], np.nan
    )
    out["solar_share_of_load"] = np.where(
        out["load_mw"] > 0, out["solar_mw"] / out["load_mw"], np.nan
    )
    return out


def quality_report(snapshot: pd.DataFrame) -> dict[str, object]:
    """Summarise completeness and ranges before analysis."""

    required = ["timestamp_utc", *ANALYSIS_COLUMNS]
    missing_columns = [column for column in required if column not in snapshot.columns]
    if missing_columns:
        raise ValueError(f"snapshot is missing columns: {missing_columns}")

    complete = complete_analysis_rows(snapshot)
    timestamps = pd.to_datetime(snapshot["timestamp_utc"], utc=True, errors="coerce")
    price = pd.to_numeric(snapshot["price_eur_mwh"], errors="coerce")
    return {
        "n_rows": int(len(snapshot)),
        "n_unique_timestamps": int(timestamps.nunique()),
        "duplicate_timestamps": int(timestamps.duplicated().sum()),
        "first_timestamp_utc": timestamps.min().isoformat() if timestamps.notna().any() else None,
        "last_timestamp_utc": timestamps.max().isoformat() if timestamps.notna().any() else None,
        "missing_counts": {
            column: int(snapshot[column].isna().sum()) for column in ANALYSIS_COLUMNS
        },
        "n_complete_analysis_rows": int(len(complete)),
        "negative_price_hours": int((price < NEGATIVE_PRICE_THRESHOLD_EUR_MWH).sum()),
        "negative_price_rate_complete_rows": (
            float((complete["negative_price"] == 1).mean()) if len(complete) else None
        ),
        "ranges": {
            column: {
                "min": float(pd.to_numeric(snapshot[column], errors="coerce").min()),
                "max": float(pd.to_numeric(snapshot[column], errors="coerce").max()),
            }
            for column in ANALYSIS_COLUMNS
            if snapshot[column].notna().any()
        },
    }


def write_snapshot(snapshot: pd.DataFrame, path: Path) -> None:
    """Write the processed snapshot with stable, explicit column order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    out = snapshot.copy()
    out["timestamp_utc"] = pd.to_datetime(out["timestamp_utc"], utc=True).dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    columns = [
        "timestamp_utc",
        "local_date",
        "local_hour",
        "month_num",
        "day_of_week",
        "is_weekend",
        *ANALYSIS_COLUMNS,
    ]
    out[columns].to_csv(path, index=False, na_rep="")
