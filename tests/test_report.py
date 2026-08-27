"""Cover the two things that are actually the deliverable.

Nothing previously imported report or plotting, so a syntax error or a
formatting regression in either could ship with a green suite.
"""

import json

import pytest

from de_power_market_view.analysis import analyse_market
from de_power_market_view.plotting import plot_exploratory_view, plot_market_view
from de_power_market_view.report import render_report
from test_analysis import _hourly_frame


@pytest.fixture(scope="module")
def result():
    return analyse_market(_hourly_frame(days=40))


def test_report_renders_rates_as_percentages_without_import_order_tricks(
    result, tmp_path
):
    """render_report once depended on report.py being imported before report_base."""

    path = tmp_path / "market_view.md"
    render_report(result, path)
    text = path.read_text(encoding="utf-8")
    assert "%" in text
    # The unpatched renderer emitted bare decimals such as "| 0.247 |".
    assert "| 0.2" not in text
    assert "Q1" in text


def test_report_contains_the_preregistered_and_exploratory_sections(result, tmp_path):
    path = tmp_path / "market_view.md"
    render_report(result, path)
    text = path.read_text(encoding="utf-8")
    assert "## Primary evidence" in text
    assert "Exploratory sensitivity, added after the first retrieval" in text
    assert "Neither view below was preregistered." in text
    # The exploratory material must come after the preregistered readout.
    assert text.index("## Primary evidence") < text.index("Exploratory sensitivity")


def test_report_survives_a_quality_dict_with_missing_keys(result, tmp_path):
    """f"{'n/a':,}" raises ValueError, so the old defensive default crashed."""

    path = tmp_path / "market_view.md"
    render_report(result, path, provenance={}, quality={"missing_counts": {}})
    assert "n/a" in path.read_text(encoding="utf-8")


def test_report_states_the_provenance_split(result, tmp_path):
    path = tmp_path / "market_view.md"
    render_report(
        result,
        path,
        provenance={
            "n_response_reads": 705,
            "n_from_smard": 0,
            "n_from_cache": 705,
            "n_cached_without_retrieval_time": 705,
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "705" in text
    assert "retrieved" in text and "cache" in text
    assert "unknown" in text


def test_both_figures_render(result, tmp_path):
    primary = tmp_path / "negative_price_risk.png"
    exploratory = tmp_path / "negative_price_exploratory.png"
    plot_market_view(result, primary)
    plot_exploratory_view(result, exploratory)
    for path in (primary, exploratory):
        assert path.exists() and path.stat().st_size > 5_000


def test_the_result_object_is_json_serialisable(result):
    """view.py writes results.json with allow_nan=False."""

    from de_power_market_view.view import _jsonable

    summary = {k: v for k, v in result.items() if k != "complete_frame"}
    json.dumps(_jsonable(summary), allow_nan=False)
