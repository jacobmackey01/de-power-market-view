"""DuckDB loading and SQL transformation helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

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

    if sql_path is None:
        sql_path = Path(__file__).resolve().parents[2] / "sql" / "market_view.sql"
    connection.execute(sql_path.read_text(encoding="utf-8"))
    return connection


def read_market_table(connection) -> pd.DataFrame:
    """Return the SQL-derived hourly table in chronological order."""

    return connection.sql(
        "SELECT * FROM market_hourly ORDER BY timestamp_utc"
    ).df()
