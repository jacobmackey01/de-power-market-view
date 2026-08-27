"""Public report API with readable percentage and count tables."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from . import report_base


def _table(
    frame: pd.DataFrame,
    columns: list[str],
    headers: list[str] | None = None,
) -> str:
    """Render report tables with human-readable units."""

    if frame.empty:
        return "_No rows available._"
    headers = headers or columns
    percent_columns = {"negative_rate", "ci_low", "ci_high"}
    count_columns = {"n_hours", "negative_hours"}
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame[columns].iterrows():
        values: list[str] = []
        for column in columns:
            value: Any = row[column]
            if column in percent_columns:
                number = float(value)
                values.append(f"{number:.1%}" if math.isfinite(number) else "n/a")
            elif column in count_columns:
                values.append(f"{int(value):,}")
            elif isinstance(value, (float, int)) and math.isfinite(float(value)):
                values.append(f"{float(value):.3f}")
            else:
                values.append("n/a" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


# report_base.render_report resolves _table in its own module namespace. Point
# that one helper at this public formatter while keeping all narrative logic in
# the tested implementation.
report_base._table = _table
render_report = report_base.render_report

__all__ = ["render_report"]
