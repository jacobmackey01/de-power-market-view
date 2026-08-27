"""Command-line generation of the report, chart and JSON summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .analysis import analyse_market
from .plotting import plot_exploratory_view, plot_market_view
from .report import render_report
from .warehouse import build_warehouse, read_market_table


def _jsonable(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return [_jsonable(row) for row in value.to_dict(orient="records")]
    if isinstance(value, pd.Series):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return value.isoformat()
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def run_view(
    project_root: Path,
    snapshot_path: Path | None = None,
    database_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Build the warehouse and all user-facing outputs."""

    snapshot_path = snapshot_path or project_root / "data" / "processed" / "market_hourly.csv"
    database_path = database_path or project_root / "data" / "market_view.duckdb"
    output_dir = output_dir or project_root / "outputs"
    provenance_path = project_root / "data" / "provenance.json"
    provenance = (
        json.loads(provenance_path.read_text(encoding="utf-8"))
        if provenance_path.exists()
        else {}
    )

    connection = build_warehouse(snapshot_path, database_path)
    try:
        market_table = read_market_table(connection)
    finally:
        connection.close()

    result = analyse_market(market_table)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / "negative_price_risk.png"
    exploratory_chart_path = output_dir / "negative_price_exploratory.png"
    report_path = output_dir / "market_view.md"
    summary_path = output_dir / "results.json"
    plot_market_view(result, chart_path)
    plot_exploratory_view(result, exploratory_chart_path)
    render_report(
        result,
        report_path,
        provenance=provenance,
        quality=provenance.get("quality"),
    )
    summary = {
        key: value for key, value in result.items() if key != "complete_frame"
    }
    summary_path.write_text(
        json.dumps(_jsonable(summary), indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return {
        "database_path": database_path,
        "chart_path": chart_path,
        "exploratory_chart_path": exploratory_chart_path,
        "report_path": report_path,
        "summary_path": summary_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the DE-LU market view.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--snapshot", type=Path, default=None)
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = run_view(
        args.project_root.resolve(),
        snapshot_path=args.snapshot,
        database_path=args.database,
        output_dir=args.output_dir,
    )
    for label, path in paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
