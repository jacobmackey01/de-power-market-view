"""Historical risk tables and a deliberately modest holdout diagnostic."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .data import expected_hours_for_local_date

MIN_SUPPORT_PER_CLASS = 50
# Residual load is defined as load - wind - solar, so including load_mw
# alongside the other three would make the design matrix exactly rank
# deficient and the coefficients unidentified. Load is therefore represented
# through residual load and the two generation terms only.
MODEL_FEATURES = [
    "residual_load_mw",
    "wind_total_mw",
    "solar_mw",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
]


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Return a Wilson interval for a binomial proportion."""

    if total <= 0:
        return (math.nan, math.nan)
    proportion = successes / total
    denominator = 1.0 + z**2 / total
    centre = (proportion + z**2 / (2.0 * total)) / denominator
    spread = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z**2 / (4.0 * total**2)
        )
        / denominator
    )
    return max(0.0, centre - spread), min(1.0, centre + spread)


def add_cyclic_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add smooth calendar terms used by the diagnostic model."""

    out = frame.copy()
    out["hour_sin"] = np.sin(2.0 * np.pi * out["local_hour"] / 24.0)
    out["hour_cos"] = np.cos(2.0 * np.pi * out["local_hour"] / 24.0)
    out["month_sin"] = np.sin(2.0 * np.pi * (out["month_num"] - 1) / 12.0)
    out["month_cos"] = np.cos(2.0 * np.pi * (out["month_num"] - 1) / 12.0)
    return out


def _rate_row(label: Any, subset: pd.DataFrame) -> dict[str, Any]:
    n_hours = int(len(subset))
    negative_hours = int(subset["negative_price"].sum())
    rate = negative_hours / n_hours if n_hours else math.nan
    low, high = wilson_interval(negative_hours, n_hours)
    return {
        "group": str(label),
        "n_hours": n_hours,
        "negative_hours": negative_hours,
        "negative_rate": rate,
        "ci_low": low,
        "ci_high": high,
    }


def rate_table(
    frame: pd.DataFrame,
    group_column: str,
    *,
    order: list[Any] | None = None,
) -> pd.DataFrame:
    """Calculate event rates and Wilson intervals for a grouping column."""

    groups = (
        list(frame[group_column].dropna().drop_duplicates())
        if order is None
        else order
    )
    return pd.DataFrame(
        [_rate_row(group, frame.loc[frame[group_column] == group]) for group in groups]
    )


def add_residual_load_quartile(frame: pd.DataFrame) -> pd.DataFrame:
    """Assign equal-count retrospective residual-load strata."""

    out = frame.copy()
    ranked = out["residual_load_mw"].rank(method="first", pct=True)
    out["residual_load_quartile"] = pd.cut(
        ranked,
        bins=[-np.inf, 0.25, 0.50, 0.75, np.inf],
        labels=[
            "Q1 · lowest residual load",
            "Q2",
            "Q3",
            "Q4 · highest residual load",
        ],
        include_lowest=True,
    )
    return out


def residual_quartile_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Primary descriptive table for residual-load risk."""

    labelled = add_residual_load_quartile(frame)
    result = rate_table(
        labelled,
        "residual_load_quartile",
        order=[
            "Q1 · lowest residual load",
            "Q2",
            "Q3",
            "Q4 · highest residual load",
        ],
    )
    bounds = (
        labelled.groupby("residual_load_quartile", observed=False)["residual_load_mw"]
        .agg(["min", "max", "median"])
        .reset_index()
        .rename(
            columns={
                "residual_load_quartile": "group",
                "min": "residual_load_min_mw",
                "max": "residual_load_max_mw",
                "median": "residual_load_median_mw",
            }
        )
    )
    return result.merge(bounds, on="group", how="left")


def _daily_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate only complete local power days."""

    rows: list[dict[str, Any]] = []
    for local_date, day in frame.groupby("local_date", sort=True):
        expected = expected_hours_for_local_date(str(local_date))
        if len(day) != expected:
            continue
        rows.append(
            {
                "local_date": str(local_date),
                "hours": int(len(day)),
                "negative_hours": int(day["negative_price"].sum()),
                "negative_price_rate": float(day["negative_price"].mean()),
                "mean_price_eur_mwh": float(day["price_eur_mwh"].mean()),
                "min_price_eur_mwh": float(day["price_eur_mwh"].min()),
                "mean_load_mw": float(day["load_mw"].mean()),
                "mean_wind_mw": float(day["wind_total_mw"].mean()),
                "mean_solar_mw": float(day["solar_mw"].mean()),
                "mean_residual_load_mw": float(day["residual_load_mw"].mean()),
                "mean_wind_share_of_load": float(day["wind_share_of_load"].mean()),
                "mean_solar_share_of_load": float(day["solar_share_of_load"].mean()),
            }
        )
    return pd.DataFrame(rows)


def latest_day_summary(frame: pd.DataFrame, daily: pd.DataFrame) -> dict[str, Any]:
    """Describe the latest complete day against strictly earlier days."""

    if daily.empty:
        raise ValueError("no complete local day is available")
    latest = daily.sort_values("local_date").iloc[-1]
    prior = daily.loc[daily["local_date"] < latest["local_date"]]
    percentile = (
        float((prior["mean_residual_load_mw"] <= latest["mean_residual_load_mw"]).mean())
        if len(prior)
        else math.nan
    )
    latest_rows = frame.loc[frame["local_date"] == latest["local_date"]]
    return {
        "local_date": str(latest["local_date"]),
        "hours": int(latest["hours"]),
        "negative_hours": int(latest["negative_hours"]),
        "negative_price_rate": float(latest["negative_price_rate"]),
        "mean_price_eur_mwh": float(latest["mean_price_eur_mwh"]),
        "min_price_eur_mwh": float(latest["min_price_eur_mwh"]),
        "mean_load_mw": float(latest["mean_load_mw"]),
        "mean_wind_mw": float(latest["mean_wind_mw"]),
        "mean_solar_mw": float(latest["mean_solar_mw"]),
        "mean_residual_load_mw": float(latest["mean_residual_load_mw"]),
        "mean_wind_share_of_load": float(latest["mean_wind_share_of_load"]),
        "mean_solar_share_of_load": float(latest["mean_solar_share_of_load"]),
        "residual_load_percentile_vs_prior_days": percentile,
        "min_observed_fundamental_rows": int(len(latest_rows)),
    }


def historical_analogues(
    daily: pd.DataFrame,
    latest: dict[str, Any],
    n_analogues: int = 5,
) -> pd.DataFrame:
    """Find prior complete days with similar observed fundamental averages."""

    if daily.empty:
        return pd.DataFrame()
    candidates = daily.loc[daily["local_date"] < latest["local_date"]].copy()
    if candidates.empty:
        return pd.DataFrame()

    feature_columns = [
        "mean_load_mw",
        "mean_wind_share_of_load",
        "mean_solar_share_of_load",
        "mean_residual_load_mw",
    ]
    scales = candidates[feature_columns].std(ddof=0).replace(0, 1.0).fillna(1.0)
    target = np.array([latest[column] for column in feature_columns], dtype=float)
    values = candidates[feature_columns].to_numpy(dtype=float)
    distances = np.sqrt(
        (((values - target) / scales.to_numpy()) ** 2).sum(axis=1)
    )
    candidates["distance"] = distances
    return candidates.sort_values(["distance", "local_date"]).head(n_analogues)[
        [
            "local_date",
            "distance",
            "negative_hours",
            "negative_price_rate",
            "mean_price_eur_mwh",
            "min_price_eur_mwh",
            "mean_residual_load_mw",
            "mean_wind_share_of_load",
            "mean_solar_share_of_load",
        ]
    ].reset_index(drop=True)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    """Numerically stable logistic function."""

    clipped = np.clip(values, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _fit_logistic(
    x_train: np.ndarray,
    y_train: np.ndarray,
    *,
    l2: float = 1.0,
    max_iter: int = 100,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit a small standardised logistic model with Newton updates.

    This is intentionally transparent and keeps the diagnostic independent of
    the SciPy stack. The model is not used to select a threshold or make a
    production forecast.
    """

    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale == 0] = 1.0
    standardised = (x_train - mean) / scale
    design = np.column_stack([np.ones(len(standardised)), standardised])
    beta = np.zeros(design.shape[1], dtype=float)
    penalty = np.eye(design.shape[1], dtype=float) * l2
    penalty[0, 0] = 0.0

    for _ in range(max_iter):
        probability = _sigmoid(design @ beta)
        gradient = design.T @ (probability - y_train) + penalty @ beta
        weights = probability * (1.0 - probability)
        hessian = design.T @ (design * weights[:, None]) + penalty
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        beta_next = beta - step
        if np.linalg.norm(step, ord=np.inf) < 1e-7:
            beta = beta_next
            break
        beta = beta_next
    return mean, scale, beta


def _average_precision(y_true: np.ndarray, probability: np.ndarray) -> float:
    """Average precision, with tied scores collapsed into one threshold.

    Ties are not an edge case here: the prevalence baseline assigns one
    identical probability to every test hour. Ranking ties by array order
    would score that baseline on the accident of chronological ordering
    rather than on its actual (constant) ranking. Collapsing tied scores
    makes the baseline's average precision equal the test-set prevalence,
    which is the only defensible value for a constant predictor, and matches
    scikit-learn's average_precision_score.
    """

    positives = int(y_true.sum())
    if positives == 0:
        return math.nan
    order = np.argsort(-probability, kind="mergesort")
    sorted_y = y_true[order]
    sorted_probability = probability[order]

    # One threshold per distinct score: the last index of each tied run.
    thresholds = np.append(
        np.flatnonzero(np.diff(sorted_probability)), len(sorted_y) - 1
    )
    true_positives = np.cumsum(sorted_y)[thresholds]
    precision = true_positives / (thresholds + 1)
    recall = true_positives / positives
    return float((np.diff(np.concatenate(([0.0], recall))) * precision).sum())


def _roc_auc(y_true: np.ndarray, probability: np.ndarray) -> float:
    positives = int(y_true.sum())
    negatives = int(len(y_true) - positives)
    if positives == 0 or negatives == 0:
        return math.nan
    order = np.argsort(probability, kind="mergesort")
    sorted_probability = probability[order]
    ranks = np.empty(len(probability), dtype=float)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and sorted_probability[end] == sorted_probability[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    rank_sum = ranks[y_true == 1].sum()
    return float((rank_sum - positives * (positives + 1) / 2) / (positives * negatives))


def _classification_metrics(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    clipped = np.clip(probability, 1e-12, 1.0 - 1e-12)
    logloss = -np.mean(
        y_true * np.log(clipped) + (1 - y_true) * np.log1p(-clipped)
    )
    return {
        "average_precision": _average_precision(y_true, probability),
        "roc_auc": _roc_auc(y_true, probability),
        "brier_score": float(np.mean((probability - y_true) ** 2)),
        "log_loss": float(logloss),
    }


def chronological_diagnostic(frame: pd.DataFrame) -> dict[str, Any]:
    """Fit one untuned time-ordered logistic diagnostic, or report no support."""

    out = add_cyclic_features(frame).sort_values("timestamp_utc").copy()
    dates = sorted(out["local_date"].astype(str).unique())
    if len(dates) < 10:
        return {"status": "insufficient_time_span", "n_complete_days": len(dates)}

    split_index = max(1, int(len(dates) * 0.80))
    if split_index >= len(dates):
        return {"status": "insufficient_time_span", "n_complete_days": len(dates)}
    split_date = dates[split_index]
    train = out.loc[out["local_date"].astype(str) < split_date]
    test = out.loc[out["local_date"].astype(str) >= split_date]

    train_positive = int(train["negative_price"].sum())
    test_positive = int(test["negative_price"].sum())
    train_negative = int(len(train) - train_positive)
    test_negative = int(len(test) - test_positive)
    support_ok = min(train_positive, test_positive, train_negative, test_negative) >= (
        MIN_SUPPORT_PER_CLASS
    )
    base = {
        "status": "ok" if support_ok else "insufficient_support",
        "support_gate": {
            "minimum_per_class": MIN_SUPPORT_PER_CLASS,
            "ok": bool(support_ok),
        },
        "train_start_date": str(train["local_date"].min()),
        "train_end_date": str(train["local_date"].max()),
        "test_start_date": str(test["local_date"].min()),
        "test_end_date": str(test["local_date"].max()),
        "train_hours": int(len(train)),
        "test_hours": int(len(test)),
        "train_positive_hours": train_positive,
        "test_positive_hours": test_positive,
        "train_negative_hours": train_negative,
        "test_negative_hours": test_negative,
    }
    if not support_ok:
        return base

    x_train = train[MODEL_FEATURES].to_numpy(dtype=float)
    x_test = test[MODEL_FEATURES].to_numpy(dtype=float)
    y_train = train["negative_price"].to_numpy(dtype=int)
    y_test = test["negative_price"].to_numpy(dtype=int)
    prevalence = float(y_train.mean())
    baseline_probability = np.full(len(y_test), prevalence, dtype=float)

    mean, scale, beta = _fit_logistic(x_train, y_train)
    standardised_test = (x_test - mean) / scale
    model_probability = _sigmoid(
        np.column_stack([np.ones(len(standardised_test)), standardised_test]) @ beta
    )
    coefficient_rows = [
        {
            "feature": feature,
            "standardised_coefficient": float(coefficient),
            "odds_ratio_per_standard_deviation": float(
                np.exp(np.clip(coefficient, -50.0, 50.0))
            ),
        }
        for feature, coefficient in zip(MODEL_FEATURES, beta[1:])
    ]
    coefficient_rows.sort(
        key=lambda row: abs(row["standardised_coefficient"]), reverse=True
    )

    base["baseline_metrics"] = _classification_metrics(y_test, baseline_probability)
    base["logistic_metrics"] = _classification_metrics(y_test, model_probability)
    base["coefficients"] = coefficient_rows
    return base


def analyse_market(frame: pd.DataFrame) -> dict[str, Any]:
    """Build the complete result object used by the report and chart."""

    required = {
        "timestamp_utc",
        "local_date",
        "local_hour",
        "month_num",
        "is_weekend",
        "price_eur_mwh",
        "load_mw",
        "wind_total_mw",
        "solar_mw",
        "residual_load_mw",
        "wind_share_of_load",
        "solar_share_of_load",
        "negative_price",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"market table is missing columns: {missing}")

    # DuckDB returns local_date as datetime.date; downstream grouping, day
    # completeness and the chronological split all compare ISO strings.
    frame = frame.copy()
    frame["local_date"] = pd.to_datetime(
        frame["local_date"], errors="coerce"
    ).dt.date.astype(str)

    complete = frame.dropna(subset=list(required - {"timestamp_utc", "local_date"})).copy()
    complete["timestamp_utc"] = pd.to_datetime(complete["timestamp_utc"], utc=True)
    complete = complete.sort_values("timestamp_utc").reset_index(drop=True)
    complete["negative_price"] = complete["negative_price"].astype(int)
    if complete.empty:
        raise ValueError("no complete analysis rows are available")

    complete = add_residual_load_quartile(complete)
    daily = _daily_table(complete)
    latest = latest_day_summary(complete, daily)
    analogues = historical_analogues(daily, latest)
    return {
        "coverage": {
            "first_timestamp_utc": complete["timestamp_utc"].min().isoformat(),
            "last_timestamp_utc": complete["timestamp_utc"].max().isoformat(),
            "complete_rows": int(len(complete)),
            "negative_price_hours": int(complete["negative_price"].sum()),
            "negative_price_rate": float(complete["negative_price"].mean()),
            "complete_local_days": int(len(daily)),
        },
        "residual_quartiles": residual_quartile_table(complete),
        "hourly_rates": rate_table(
            complete,
            "local_hour",
            order=list(range(24)),
        ),
        "monthly_rates": rate_table(
            complete,
            "month_num",
            order=list(range(1, 13)),
        ),
        "daily": daily,
        "latest_day": latest,
        "analogues": analogues,
        "diagnostic": chronological_diagnostic(complete),
        "complete_frame": complete,
    }
