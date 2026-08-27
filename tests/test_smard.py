import json

from de_power_market_view.smard import FILTERS, SmardClient


def test_filter_set_is_explicit_and_unique():
    assert set(FILTERS) == {
        "price_da",
        "load_actual",
        "wind_onshore_actual",
        "wind_offshore_actual",
        "solar_actual",
    }
    assert len(set(FILTERS.values())) == len(FILTERS)
    assert SmardClient().provenance() == []


def test_provenance_separates_a_smard_retrieval_from_a_cache_read(tmp_path):
    """A cache read must not be recorded as if SMARD had just served it."""

    client = SmardClient(cache_dir=tmp_path, delay_seconds=0.0)
    url = "https://example.invalid/block.json"
    body = b'{"series": [[1, 2.0]]}'

    # Seed the cache the way a real retrieval would, sidecar included.
    body_path, meta_path = client._cache_paths(url)
    body_path.write_bytes(body)
    meta_path.write_text(
        json.dumps({"url": url, "retrieved_from_smard_at_utc": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    client._get_json(url)
    record = client.provenance()[0]
    assert record["source"] == "cache"
    assert record["retrieved_from_smard_at_utc"] == "2026-01-01T00:00:00+00:00"
    assert record["read_at_utc"] != record["retrieved_from_smard_at_utc"]


def test_a_cache_entry_without_a_sidecar_reports_an_unknown_retrieval_time(tmp_path):
    """Legacy cache entries must report null, not the cache-read time."""

    client = SmardClient(cache_dir=tmp_path, delay_seconds=0.0)
    url = "https://example.invalid/legacy.json"
    body_path, _ = client._cache_paths(url)
    body_path.write_bytes(b'{"series": []}')

    client._get_json(url)
    record = client.provenance()[0]
    assert record["source"] == "cache"
    assert record["retrieved_from_smard_at_utc"] is None
    assert record["read_at_utc"]
