import numpy as np
import pandas as pd

from de_power_market_view.analysis import (
    MIN_SUPPORT_PER_CLASS,
    analyse_market,
    chronological_diagnostic,
    wilson_interval,
)


def _hourly_frame(days: int = 24) -> pd.DataFrame:
    index = pd.date_range(
        "2024-01-01 00:00", periods=days * 24, freq="h", tz="UTC"
    )
    local = index.tz_convert("Europe/Berlin")
    hour = local.hour.to_numpy()
    day_number = np.arange(len(index)) // 24
    wind = 8_000 + 2_000 * np.sin(np.arange(len(index)) / 18)
    solar = np.maximum(0, 7_000 * np.sin((hour - 6) * np.pi / 12))
    load = 42_000 + 2_000 * np.cos((hour - 8) * np.pi / 12)
    residual = load - wind - solar
    negative = (residual < np.quantile(residual, 0.25)).astype(int)
    price = np.where(negative, -5.0, 40.0)
    return pd.DataFrame(
        {
            "timestamp_utc": index,
            "local_date": local.strftime("%Y-%m-%d"),
            "local_hour": local.hour,
            "month_num": local.month,
            "is_weekend": (local.dayofweek >= 5).astype(int),
            "price_eur_mwh": price,
            "load_mw": load,
            "wind_total_mw": wind,
            "solar_mw": solar,
            "residual_load_mw": residual,
            "wind_share_of_load": wind / load,
            "solar_share_of_load": solar / load,
            "negative_price": negative,
        }
    )


def test_wilson_interval_is_bounded():
    low, high = wilson_interval(2, 10)
    assert 0 <= low < 0.2 < high <= 1


def test_analysis_has_primary_tables_and_latest_day():
    result = analyse_market(_hourly_frame())
    assert result["coverage"]["complete_rows"] == 24 * 24
    assert len(result["residual_quartiles"]) == 4
    assert len(result["hourly_rates"]) == 24
    assert len(result["monthly_rates"]) == 12
    assert result["latest_day"]["hours"] == 24
    assert len(result["analogues"]) == 5


def test_chronological_diagnostic_applies_support_gate():
    result = chronological_diagnostic(_hourly_frame(days=10))
    assert result["status"] in {"ok", "insufficient_support"}
    assert result["support_gate"]["minimum_per_class"] == MIN_SUPPORT_PER_CLASS
