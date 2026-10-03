"""Check a saved DE-LU quarter-hour clearing-price response for a memo."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
UTC = timezone.utc


def utc_bounds(day: str) -> tuple[datetime, datetime]:
    local_day = date.fromisoformat(day)
    start = datetime.combine(local_day, time(), BERLIN)
    end = datetime.combine(local_day + timedelta(days=1), time(), BERLIN)
    return start.astimezone(UTC), end.astimezone(UTC)


def parse_boundary(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("strip boundaries need an explicit UTC offset")
    return result.astimezone(UTC)


def inspect_prices(
    payload: dict, day: str, start: str | None = None, end: str | None = None
) -> dict:
    if payload.get("unit") != "EUR / MWh":
        raise ValueError("expected EUR / MWh prices")
    license_info = payload.get("license_info", "")
    if not isinstance(license_info, str) or not all(
        text in license_info for text in ("CC BY 4.0", "SMARD")
    ):
        raise ValueError("the response lacks the verified DE-LU reuse attribution")
    stamps = payload.get("unix_seconds")
    prices = payload.get("price")
    if not isinstance(stamps, list) or not isinstance(prices, list):
        raise ValueError("expected timestamp and price arrays")
    day_start, day_end = utc_bounds(day)
    expected_stamps = list(range(int(day_start.timestamp()), int(day_end.timestamp()), 900))
    if any(type(stamp) is not int for stamp in stamps) or stamps != expected_stamps:
        raise ValueError("response must contain the complete ordered local day at 15-minute resolution")
    if len(prices) != len(stamps) or any(
        type(price) not in (int, float) or not math.isfinite(price) for price in prices
    ):
        raise ValueError("each interval needs one finite numeric price; no imputation is allowed")
    if bool(start) != bool(end):
        raise ValueError("supply both strip boundaries or neither")
    strip_start = parse_boundary(start) if start else day_start
    strip_end = parse_boundary(end) if end else day_end
    if not day_start <= strip_start < strip_end <= day_end:
        raise ValueError("strip must lie within the specified delivery day")
    if any(int(boundary.timestamp()) % 900 or boundary.microsecond for boundary in (strip_start, strip_end)):
        raise ValueError("strip boundaries must align with 15-minute intervals")
    selected = [
        (stamp, float(price))
        for stamp, price in zip(stamps, prices)
        if strip_start.timestamp() <= stamp < strip_end.timestamp()
    ]
    by_hour: dict[int, list[float]] = defaultdict(list)
    for stamp, price in zip(stamps, prices):
        by_hour[stamp // 3600 * 3600].append(float(price))
    hourly = [
        {
            "start_utc": datetime.fromtimestamp(stamp, UTC).isoformat(),
            "start_local": datetime.fromtimestamp(stamp, UTC).astimezone(BERLIN).isoformat(),
            "price_eur_mwh": sum(values) / 4,
        }
        for stamp, values in sorted(by_hour.items())
    ]
    return {
        "bidding_zone": "DE-LU",
        "delivery_date_local": day,
        "timezone": "Europe/Berlin",
        "unit": "EUR/MWh",
        "interval_minutes": 15,
        "day_quarter_hours": len(stamps),
        "day_elapsed_hours": (day_end - day_start).total_seconds() / 3600,
        "license_info": license_info,
        "strip": {
            "start_utc": strip_start.isoformat(),
            "end_utc_exclusive": strip_end.isoformat(),
            "quarter_hours": len(selected),
            "elapsed_hours": len(selected) / 4,
            "mean_price_eur_mwh": sum(price for _, price in selected) / len(selected),
            "negative_quarter_hours": sum(price < 0 for _, price in selected),
        },
        "hourly_means": hourly,
        "negative_hourly_mean_hours": sum(row["price_eur_mwh"] < 0 for row in hourly),
        "interpretation": "Clearing-price outcome and hourly averages; not an executable pre-auction quote or P&L.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Europe/Berlin delivery date")
    parser.add_argument("--input", type=Path, required=True, help="saved Energy-Charts /price response")
    parser.add_argument("--start", help="inclusive strip start, with explicit UTC offset")
    parser.add_argument("--end", help="exclusive strip end, with explicit UTC offset")
    parser.add_argument("--output", type=Path, help="new inspection record; existing paths are refused")
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("price response must be a JSON object")
        result = inspect_prices(payload, args.date, args.start, args.end)
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
        result["source_url"] = (
            "https://api.energy-charts.info/price?bzn=DE-LU"
            f"&start={args.date}&end={args.date}"
        )
        result["source_attribution"] = "Energy-Charts.info / Fraunhofer ISE; Bundesnetzagentur | SMARD.de, CC BY 4.0"
        result["checked_at_utc"] = datetime.now(UTC).isoformat()
        rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        else:
            print(rendered, end="")
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        parser.exit(2, f"price check failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
