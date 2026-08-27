"""Public analysis API with stable local-date handling."""

from __future__ import annotations

import pandas as pd

from .analysis_base import (
    MIN_SUPPORT_PER_CLASS,
    MODEL_FEATURES,
    add_cyclic_features,
    add_residual_load_quartile,
    chronological_diagnostic,
    historical_analogues,
    latest_day_summary,
    rate_table,
    residual_quartile_table,
    wilson_interval,
)
from .analysis_base import analyse_market as _analyse_market


def analyse_market(frame: pd.DataFrame) -> dict:
    """Run the analysis after normalising DuckDB date values to ISO dates."""

    prepared = frame.copy()
    prepared["local_date"] = pd.to_datetime(
        prepared["local_date"], errors="coerce"
    ).dt.date.astype(str)
    return _analyse_market(prepared)


__all__ = [
    "MIN_SUPPORT_PER_CLASS",
    "MODEL_FEATURES",
    "add_cyclic_features",
    "add_residual_load_quartile",
    "analyse_market",
    "chronological_diagnostic",
    "historical_analogues",
    "latest_day_summary",
    "rate_table",
    "residual_quartile_table",
    "wilson_interval",
]
