import pandas as pd

from de_power_market_view.data import write_snapshot
from de_power_market_view.warehouse import build_warehouse, read_market_table


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
