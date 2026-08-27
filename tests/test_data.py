import pandas as pd
import pytest

from de_power_market_view.data import (
    SOURCE_COLUMNS,
    expected_hours_for_local_date,
    local_date_window,
    normalise_market_frame,
    quality_report,
)


def _source_frame(index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "price_da": [-1.0] * len(index),
            "load_actual": [50_000.0] * len(index),
            "wind_onshore_actual": [10_000.0] * len(index),
            "wind_offshore_actual": [5_000.0] * len(index),
            "solar_actual": [2_000.0] * len(index),
        },
        index=index,
    )


def test_dst_day_lengths_are_not_hard_coded():
    assert expected_hours_for_local_date("2026-03-29") == 23
    assert expected_hours_for_local_date("2026-10-25") == 25
    assert expected_hours_for_local_date("2026-08-25") == 24


def test_local_date_window_respects_berlin_dst():
    start, end = local_date_window("2026-10-25", "2026-10-25")
    assert start.isoformat() == "2026-10-24T22:00:00+00:00"
    assert end.isoformat() == "2026-10-25T21:59:59.999999999+00:00"


def test_normalisation_and_quality_preserve_negative_price_and_fields():
    index = pd.date_range("2026-08-25 00:00", periods=24, freq="h", tz="UTC")
    snapshot = normalise_market_frame(_source_frame(index))
    assert set(SOURCE_COLUMNS) == {
        "price_da",
        "load_actual",
        "wind_onshore_actual",
        "wind_offshore_actual",
        "solar_actual",
    }
    assert snapshot["local_date"].iloc[0] == "2026-08-25"
    report = quality_report(snapshot)
    assert report["n_rows"] == 24
    assert report["n_complete_analysis_rows"] == 24
    assert report["negative_price_hours"] == 24
    assert report["duplicate_timestamps"] == 0


def test_negative_generation_is_rejected():
    index = pd.date_range("2026-08-25", periods=1, freq="h", tz="UTC")
    frame = _source_frame(index)
    frame.loc[index[0], "solar_actual"] = -1
    with pytest.raises(ValueError, match="solar_mw"):
        normalise_market_frame(frame)
