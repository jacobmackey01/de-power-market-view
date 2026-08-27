"""Small, provenance-aware client for the SMARD chart-data API.

The filter IDs below are the IDs used by the existing DE-LU live-forecast
project after its source-series checks. This repository deliberately uses only
settled historical series: it does not consume SMARD's published D+1 forecasts.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

BASE_URL = "https://www.smard.de/app/chart_data"
REGION = "DE"
RESOLUTION = "hour"
USER_AGENT = "de-power-market-view/0.1 (+https://jacobmackey.com)"

# SMARD chart-data filter IDs. Values are MW except for the day-ahead price.
FILTERS: dict[str, int] = {
    "price_da": 4169,
    "load_actual": 410,
    "wind_onshore_actual": 4067,
    "wind_offshore_actual": 1225,
    "solar_actual": 4068,
}


class SmardError(RuntimeError):
    """Raised when SMARD cannot be reached or returns unusable data."""


@dataclass(frozen=True)
class FetchRecord:
    """Evidence about one API response used by the data snapshot."""

    url: str
    sha256: str
    n_bytes: int
    retrieved_at_utc: str
    from_cache: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "sha256": self.sha256,
            "n_bytes": self.n_bytes,
            "retrieved_at_utc": self.retrieved_at_utc,
            "from_cache": self.from_cache,
        }


@dataclass
class SmardClient:
    """Fetch hourly SMARD series while retaining response provenance."""

    cache_dir: Path | None = None
    timeout: float = 45.0
    max_retries: int = 4
    backoff_seconds: float = 1.5
    delay_seconds: float = 0.08
    fetches: list[FetchRecord] = field(default_factory=list)

    def _cache_path(self, url: str) -> Path | None:
        if self.cache_dir is None:
            return None
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"

    def _get_raw(self, url: str) -> tuple[bytes, bool]:
        cache_path = self._cache_path(url)
        if cache_path is not None and cache_path.exists():
            return cache_path.read_bytes(), True

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                if self.delay_seconds:
                    time.sleep(self.delay_seconds)
                request = urllib.request.Request(
                    url,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                if cache_path is not None:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(raw)
                return raw, False
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_seconds * (2**attempt))

        raise SmardError(f"failed to fetch {url} after {self.max_retries} attempts: {last_error}")

    def _get_json(self, url: str) -> dict:
        raw, from_cache = self._get_raw(url)
        self.fetches.append(
            FetchRecord(
                url=url,
                sha256=hashlib.sha256(raw).hexdigest(),
                n_bytes=len(raw),
                retrieved_at_utc=pd.Timestamp.now(tz="UTC").isoformat(),
                from_cache=from_cache,
            )
        )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SmardError(f"malformed JSON from {url}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SmardError(f"unexpected non-object JSON from {url}")
        return payload

    def index_timestamps(self, filter_id: int) -> list[int]:
        """Return the weekly block start timestamps for a filter."""

        url = f"{BASE_URL}/{filter_id}/{REGION}/index_{RESOLUTION}.json"
        payload = self._get_json(url)
        timestamps = payload.get("timestamps")
        if not timestamps:
            raise SmardError(f"filter {filter_id} returned no block timestamps")
        try:
            return sorted(int(value) for value in timestamps)
        except (TypeError, ValueError) as exc:
            raise SmardError(f"filter {filter_id} returned invalid block timestamps") from exc

    def _block(self, filter_id: int, block_timestamp: int) -> list[list]:
        url = (
            f"{BASE_URL}/{filter_id}/{REGION}/"
            f"{filter_id}_{REGION}_{RESOLUTION}_{block_timestamp}.json"
        )
        payload = self._get_json(url)
        series = payload.get("series")
        if not isinstance(series, list):
            raise SmardError(f"filter {filter_id} block {block_timestamp} has no series")
        return series

    def fetch_series(
        self,
        name: str,
        start_utc: pd.Timestamp,
        end_utc: pd.Timestamp,
    ) -> pd.Series:
        """Fetch one named series and trim it to an inclusive UTC window."""

        if name not in FILTERS:
            raise KeyError(f"unknown series {name!r}; choose from {sorted(FILTERS)}")
        start = pd.Timestamp(start_utc)
        end = pd.Timestamp(end_utc)
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start_utc and end_utc must be timezone-aware")
        start = start.tz_convert("UTC")
        end = end.tz_convert("UTC")
        if end < start:
            raise ValueError("end_utc must not precede start_utc")

        filter_id = FILTERS[name]
        margin_ms = int(pd.Timedelta(days=8).total_seconds() * 1000)
        start_ms = int(start.timestamp() * 1000) - margin_ms
        end_ms = int(end.timestamp() * 1000) + margin_ms
        blocks = [
            block
            for block in self.index_timestamps(filter_id)
            if start_ms <= block <= end_ms
        ]
        if not blocks:
            raise SmardError(f"no SMARD blocks cover {name} from {start} to {end}")

        points: list[list] = []
        for block_timestamp in blocks:
            points.extend(self._block(filter_id, block_timestamp))
        if not points:
            raise SmardError(f"SMARD returned no points for {name}")

        frame = pd.DataFrame(points, columns=["timestamp_ms", "value"])
        frame["timestamp_utc"] = pd.to_datetime(
            frame["timestamp_ms"], unit="ms", utc=True, errors="coerce"
        )
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame = (
            frame.dropna(subset=["timestamp_utc"])
            .drop_duplicates(subset=["timestamp_utc"], keep="last")
            .sort_values("timestamp_utc")
        )
        frame = frame.loc[
            (frame["timestamp_utc"] >= start) & (frame["timestamp_utc"] <= end)
        ]
        if frame.empty:
            raise SmardError(f"SMARD returned no points inside the requested window for {name}")
        return pd.Series(
            frame["value"].to_numpy(dtype=float),
            index=pd.DatetimeIndex(frame["timestamp_utc"]),
            name=name,
        )

    def fetch_frame(
        self,
        names: list[str],
        start_utc: pd.Timestamp,
        end_utc: pd.Timestamp,
    ) -> pd.DataFrame:
        """Fetch and align several named series on one UTC hourly index."""

        if not names:
            raise ValueError("at least one series is required")
        frame = pd.concat(
            [self.fetch_series(name, start_utc, end_utc) for name in names],
            axis=1,
        ).sort_index()
        frame.index.name = "timestamp_utc"
        return frame

    def provenance(self) -> list[dict[str, object]]:
        return [record.to_dict() for record in self.fetches]
