"""Command-line retrieval of a reproducible SMARD snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .data import local_date_window, normalise_market_frame, quality_report, write_snapshot
from .smard import FILTERS, SmardClient


def fetch_snapshot(start_date: str, end_date: str, project_root: Path) -> dict:
    """Fetch, validate and persist the processed market snapshot."""

    start_utc, end_utc = local_date_window(start_date, end_date)
    raw_dir = project_root / "data" / "raw"
    processed_path = project_root / "data" / "processed" / "market_hourly.csv"
    provenance_path = project_root / "data" / "provenance.json"

    client = SmardClient(cache_dir=raw_dir)
    source_frame = client.fetch_frame(list(FILTERS), start_utc, end_utc)
    snapshot = normalise_market_frame(source_frame)
    quality = quality_report(snapshot)
    if quality["duplicate_timestamps"]:
        raise ValueError("refusing to write a snapshot with duplicate timestamps")
    if quality["n_complete_analysis_rows"] == 0:
        raise ValueError("refusing to write a snapshot with no complete analysis rows")

    write_snapshot(snapshot, processed_path)
    records = client.provenance()
    provenance = {
        "project": "de-power-market-view",
        "retrieved_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "requested_local_dates": {"start": start_date, "end": end_date},
        "requested_utc_window": {
            "start": start_utc.isoformat(),
            "end": end_utc.isoformat(),
        },
        "filter_ids": FILTERS,
        "n_fetches": len(records),
        "n_cached_fetches": sum(bool(record["from_cache"]) for record in records),
        "quality": quality,
        "fetches": records,
    }
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return {
        "processed_path": processed_path,
        "provenance_path": provenance_path,
        "quality": quality,
        "n_fetches": len(records),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch settled DE-LU price and generation data from SMARD."
    )
    parser.add_argument("--start", required=True, help="Inclusive Berlin date, YYYY-MM-DD.")
    parser.add_argument("--end", required=True, help="Inclusive Berlin date, YYYY-MM-DD.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root (defaults to the checkout containing this package).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = fetch_snapshot(args.start, args.end, args.project_root.resolve())
    quality = result["quality"]
    print(
        f"Wrote {result['processed_path']} with "
        f"{quality['n_complete_analysis_rows']:,} complete rows; "
        f"{quality['negative_price_hours']:,} negative-price hours."
    )
    print(f"Provenance: {result['provenance_path']} ({result['n_fetches']} responses)")


if __name__ == "__main__":
    main()
