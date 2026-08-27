"""DuckDB loading and SQL transformation helpers."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pandas as pd

from . import NEGATIVE_PRICE_THRESHOLD_EUR_MWH

REQUIRED_SNAPSHOT_COLUMNS = {
    "timestamp_utc",
    "local_date",
    "local_hour",
    "month_num",
    "day_of_week",
    "is_weekend",
    "price_eur_mwh",
    "load_mw",
    "wind_onshore_mw",
    "wind_offshore_mw",
    "solar_mw",
}


def load_snapshot(path: Path) -> pd.DataFrame:
    """Read and type the processed CSV before handing it to DuckDB."""

    snapshot = pd.read_csv(path)
    missing = sorted(REQUIRED_SNAPSHOT_COLUMNS - set(snapshot.columns))
    if missing:
        raise ValueError(f"processed snapshot is missing columns: {missing}")
    snapshot["timestamp_utc"] = pd.to_datetime(
        snapshot["timestamp_utc"], utc=True, errors="coerce"
    )
    snapshot["local_date"] = pd.to_datetime(
        snapshot["local_date"], errors="coerce"
    ).dt.date
    numeric_columns = sorted(REQUIRED_SNAPSHOT_COLUMNS - {"timestamp_utc", "local_date"})
    for column in numeric_columns:
        snapshot[column] = pd.to_numeric(snapshot[column], errors="coerce")
    if snapshot["timestamp_utc"].isna().any():
        raise ValueError("processed snapshot contains an invalid timestamp")
    return snapshot


def market_view_sql() -> str:
    """Return the checked-in SQL transformation.

    The file ships as package data, so this resolves correctly whether the
    project is installed editable or into site-packages. Resolving it
    relative to __file__ only worked for an editable checkout.
    """

    return (
        resources.files(__package__)
        .joinpath("sql/market_view.sql")
        .read_text(encoding="utf-8")
    )


def build_warehouse(
    snapshot_path: Path,
    database_path: Path,
    sql_path: Path | None = None,
):
    """Load the snapshot and execute the checked-in SQL transformation."""

    import duckdb

    snapshot = load_snapshot(snapshot_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    connection.register("snapshot_df", snapshot)
    connection.execute("CREATE OR REPLACE TABLE raw_market AS SELECT * FROM snapshot_df")
    connection.unregister("snapshot_df")

    # The negative-price rule has one definition, in Python. It is passed to
    # SQL through this table so the two layers cannot drift apart.
    connection.execute(
        "CREATE OR REPLACE TABLE analysis_config AS "
        "SELECT CAST(? AS DOUBLE) AS negative_price_threshold_eur_mwh",
        [NEGATIVE_PRICE_THRESHOLD_EUR_MWH],
    )

    sql = (
        sql_path.read_text(encoding="utf-8")
        if sql_path is not None
        else market_view_sql()
    )
    connection.execute(sql)
    return connection


def read_market_table(connection) -> pd.DataFrame:
    """Return the SQL-derived hourly table in chronological order."""

    return connection.sql(
        "SELECT * FROM market_hourly ORDER BY timestamp_utc"
    ).df()
