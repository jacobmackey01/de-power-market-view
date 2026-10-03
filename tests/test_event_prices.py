"""Contract-grain and clock-change checks for the event-memo price reader."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_event_prices.py"
SPEC = importlib.util.spec_from_file_location("event_prices", MODULE_PATH)
prices_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prices_module)


def day_payload(day: str) -> dict:
    start, end = prices_module.utc_bounds(day)
    stamps = list(range(int(start.timestamp()), int(end.timestamp()), 900))
    return {
        "license_info": "CC BY 4.0 from Bundesnetzagentur | SMARD.de",
        "unit": "EUR / MWh",
        "unix_seconds": stamps,
        "price": [1.0] * len(stamps),
    }


class PriceContractTests(unittest.TestCase):
    def test_clock_change_day_counts(self):
        for day, intervals, hours in (
            ("2026-10-01", 96, 24), ("2026-03-29", 92, 23), ("2026-10-25", 100, 25)
        ):
            with self.subTest(day=day):
                result = prices_module.inspect_prices(day_payload(day), day)
                self.assertEqual(result["day_quarter_hours"], intervals)
                self.assertEqual(result["day_elapsed_hours"], hours)
                self.assertEqual(result["strip"]["mean_price_eur_mwh"], 1)
                self.assertEqual(len(result["hourly_means"]), hours)

    def test_repeated_local_hour_needs_offsets(self):
        result = prices_module.inspect_prices(
            day_payload("2026-10-25"), "2026-10-25",
            "2026-10-25T02:00:00+02:00", "2026-10-25T03:00:00+01:00"
        )
        self.assertEqual(result["strip"]["quarter_hours"], 8)
        repeated = [row["start_local"] for row in result["hourly_means"] if "T02:00" in row["start_local"]]
        self.assertEqual(len(set(repeated)), 2)

    def test_negative_quarter_does_not_mean_negative_hour(self):
        payload = day_payload("2026-10-01")
        payload["price"][:4] = [-10, 10, 10, 10]
        result = prices_module.inspect_prices(payload, "2026-10-01")
        self.assertEqual(result["strip"]["negative_quarter_hours"], 1)
        self.assertEqual(result["negative_hourly_mean_hours"], 0)
        self.assertEqual(result["hourly_means"][0]["price_eur_mwh"], 5)

    def test_missing_duplicate_and_hourly_data_fail(self):
        original = day_payload("2026-10-01")
        variants = [deepcopy(original) for _ in range(3)]
        variants[0]["unix_seconds"].pop()
        variants[1]["unix_seconds"][1] = variants[1]["unix_seconds"][0]
        variants[2]["unix_seconds"] = variants[2]["unix_seconds"][::4]
        for payload in variants:
            with self.assertRaises(ValueError):
                prices_module.inspect_prices(payload, "2026-10-01")

    def test_unavailable_and_nonfinite_prices_fail(self):
        for invalid in (None, float("nan"), float("inf"), "12", True):
            payload = day_payload("2026-10-01")
            payload["price"][0] = invalid
            with self.assertRaises(ValueError):
                prices_module.inspect_prices(payload, "2026-10-01")

    def test_strip_is_half_open(self):
        payload = day_payload("2026-10-01")
        payload["price"][:4] = [1, 2, 3, 4]
        result = prices_module.inspect_prices(
            payload, "2026-10-01", "2026-10-01T00:00:00+02:00", "2026-10-01T01:00:00+02:00"
        )
        self.assertEqual(result["strip"]["quarter_hours"], 4)
        self.assertEqual(result["strip"]["mean_price_eur_mwh"], 2.5)

    def test_invalid_boundaries_fail(self):
        payload = day_payload("2026-10-01")
        for start, end in (
            ("2026-10-01T00:00:00", "2026-10-01T01:00:00"),
            ("2026-10-01T00:01:00+02:00", "2026-10-01T01:00:00+02:00"),
            ("2026-10-01T01:00:00+02:00", "2026-10-01T00:00:00+02:00"),
            ("2026-10-01T00:00:00+02:00", None),
        ):
            with self.assertRaises(ValueError):
                prices_module.inspect_prices(payload, "2026-10-01", start, end)


if __name__ == "__main__":
    unittest.main()
