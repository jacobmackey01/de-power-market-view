import pandas as pd

from de_power_market_view import warehouse
from de_power_market_view.data import complete_analysis_rows, write_snapshot
from de_power_market_view.warehouse import (
    build_warehouse,
    market_view_sql,
    read_market_table,
)


def test_sql_derives_market_quantities(tmp_path):
    index = pd.date_range("2026-08-25", periods=3, freq="h", tz="UTC")
    source = pd.DataFrame(
        {
            "timestamp_utc": index,
            "local_date": ["2026-08-25"] * 3,
            "local_hour": [2, 3, 4],
            "month_num": [8, 8, 8],
            "day_of_week": [1, 1, 1],
            "is_weekend": [0, 0, 0],
            "price_eur_mwh": [-1.0, 20.0, None],
            "load_mw": [50_000.0, 50_000.0, 50_000.0],
            "wind_onshore_mw": [10_000.0, 10_000.0, 10_000.0],
            "wind_offshore_mw": [5_000.0, 5_000.0, 5_000.0],
            "solar_mw": [2_000.0, 2_000.0, 2_000.0],
        }
    )
    snapshot_path = tmp_path / "market_hourly.csv"
    write_snapshot(source, snapshot_path)
    connection = build_warehouse(snapshot_path, tmp_path / "view.duckdb")
    try:
        result = read_market_table(connection)
    finally:
        connection.close()
    assert result["wind_total_mw"].iloc[0] == 15_000.0
    assert result["residual_load_mw"].iloc[0] == 33_000.0
    assert result["negative_price"].iloc[0] == 1
    assert result["analysis_complete"].iloc[2] == 0


def test_packaged_sql_is_readable_as_package_data():
    """Resolving the SQL relative to __file__ only worked for an editable checkout."""

    sql = market_view_sql()
    assert "CREATE OR REPLACE TABLE market_hourly" in sql
    assert "CROSS JOIN analysis_config" in sql
    # The rule must not be hard coded back into the SQL.
    assert "price_eur_mwh < 0" not in sql


def test_negative_price_threshold_comes_from_the_python_constant(tmp_path, monkeypatch):
    """One definition of the rule: changing the constant must change the SQL output."""

    index = pd.date_range("2026-08-25", periods=4, freq="h", tz="UTC")
    source = pd.DataFrame(
        {
            "timestamp_utc": index,
            "local_date": ["2026-08-25"] * 4,
            "local_hour": [0, 1, 2, 3],
            "month_num": [8] * 4,
            "day_of_week": [1] * 4,
            "is_weekend": [0] * 4,
            "price_eur_mwh": [-5.0, 0.5, 2.0, 20.0],
            "load_mw": [50_000.0] * 4,
            "wind_onshore_mw": [10_000.0] * 4,
            "wind_offshore_mw": [5_000.0] * 4,
            "solar_mw": [2_000.0] * 4,
        }
    )
    snapshot_path = tmp_path / "market_hourly.csv"
    write_snapshot(source, snapshot_path)

    def flags(threshold: float) -> list[int]:
        monkeypatch.setattr(
            warehouse, "NEGATIVE_PRICE_THRESHOLD_EUR_MWH", threshold
        )
        connection = build_warehouse(snapshot_path, tmp_path / f"w{threshold}.duckdb")
        try:
            return list(read_market_table(connection)["negative_price"])
        finally:
            connection.close()

    assert flags(0.0) == [1, 0, 0, 0]
    assert flags(1.0) == [1, 1, 0, 0]


def test_derived_fields_are_not_recomputed_in_pandas():
    """complete_analysis_rows must filter only; SQL owns the derived quantities."""

    index = pd.date_range("2026-08-25", periods=2, freq="h", tz="UTC")
    snapshot = pd.DataFrame(
        {
            "timestamp_utc": index,
            "price_eur_mwh": [-1.0, 20.0],
            "load_mw": [50_000.0, 50_000.0],
            "wind_onshore_mw": [10_000.0, 10_000.0],
            "wind_offshore_mw": [5_000.0, 5_000.0],
            "solar_mw": [2_000.0, 2_000.0],
        }
    )
    rows = complete_analysis_rows(snapshot)
    assert len(rows) == 2
    for derived in (
        "negative_price",
        "wind_total_mw",
        "residual_load_mw",
        "wind_share_of_load",
        "solar_share_of_load",
    ):
        assert derived not in rows.columns
