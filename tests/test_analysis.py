import numpy as np
import pandas as pd
import pytest

from de_power_market_view.analysis import (
    MIN_SUPPORT_PER_CLASS,
    MODEL_FEATURES,
    add_cyclic_features,
    analyse_market,
    chronological_diagnostic,
    wilson_interval,
)
from de_power_market_view.analysis_base import _average_precision


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


def test_average_precision_of_a_constant_predictor_equals_prevalence():
    """A constant score ranks nothing, so its AP must be the prevalence.

    The earlier implementation ranked tied scores by array order, which made
    the prevalence baseline depend on the chronological position of negative
    hours inside the test window.
    """

    y = np.zeros(1000, dtype=int)
    y[np.linspace(0, 999, 87).astype(int)] = 1  # positives clustered early
    constant = np.full(len(y), y.mean())
    assert _average_precision(y, constant) == pytest.approx(y.mean(), rel=1e-12)


def test_average_precision_is_invariant_to_the_order_of_tied_scores():
    y = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0, 0])
    constant = np.full(len(y), 0.3)
    reversed_order = np.arange(len(y))[::-1]
    assert _average_precision(y, constant) == pytest.approx(
        _average_precision(y[reversed_order], constant), rel=1e-12
    )


def test_average_precision_matches_a_hand_computed_ranking():
    # Scores strictly ordered: ranks are 1,0,1,0 -> AP = (1/1 + 2/3)/2.
    y = np.array([1, 0, 1, 0])
    scores = np.array([0.9, 0.8, 0.7, 0.6])
    assert _average_precision(y, scores) == pytest.approx((1.0 + 2.0 / 3.0) / 2.0)


def _non_degenerate_frame(days: int = 400) -> pd.DataFrame:
    """A year-plus fixture with noisy load, for rank checks.

    _hourly_frame builds load as an exact sinusoid in the hour of day, which
    makes it a linear combination of hour_sin and hour_cos. That is fine for
    the descriptive tests but useless for detecting collinearity, so this
    fixture adds independent variation and spans every month.
    """

    frame = _hourly_frame(days=days)
    rng = np.random.default_rng(0)
    frame["load_mw"] = frame["load_mw"] + rng.normal(0, 3_000, len(frame))
    frame["residual_load_mw"] = (
        frame["load_mw"] - frame["wind_total_mw"] - frame["solar_mw"]
    )
    return frame


def test_model_features_exclude_the_collinear_load_term():
    """residual_load_mw == load_mw - wind_total_mw - solar_mw.

    Including all four would make the design matrix exactly rank deficient and
    leave the reported coefficients unidentified, so at most three of them may
    appear together.
    """

    collinear_set = {"residual_load_mw", "load_mw", "wind_total_mw", "solar_mw"}
    assert not collinear_set.issubset(set(MODEL_FEATURES))


def test_model_features_are_full_rank_on_realistic_variation():
    frame = add_cyclic_features(_non_degenerate_frame())
    design = frame[MODEL_FEATURES].to_numpy(dtype=float)
    centred = design - design.mean(axis=0)
    assert np.linalg.matrix_rank(centred) == len(MODEL_FEATURES)


def test_a_collinear_feature_set_would_fail_the_rank_check():
    """Confirm the rank check above can actually fail, rather than always passing."""

    frame = add_cyclic_features(_non_degenerate_frame())
    collinear = [*MODEL_FEATURES, "load_mw"]
    design = frame[collinear].to_numpy(dtype=float)
    centred = design - design.mean(axis=0)
    assert np.linalg.matrix_rank(centred) < len(collinear)


def test_support_gate_rejects_a_partition_without_enough_events():
    """The gate must actually refuse to report metrics, not just pass through."""

    frame = _hourly_frame(days=12)
    frame["negative_price"] = 0
    frame.loc[frame.index[:3], "negative_price"] = 1
    frame["price_eur_mwh"] = np.where(frame["negative_price"] == 1, -5.0, 40.0)
    result = chronological_diagnostic(frame)
    assert result["status"] == "insufficient_support"
    assert result["support_gate"]["ok"] is False
    assert "logistic_metrics" not in result
