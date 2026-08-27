"""Entry-point defaults.

Both console scripts previously derived the project root from
Path(__file__).parents[2]. That is the repository only for an editable
checkout; from a wheel it points at the parent of site-packages, so the
default resolved to something like .venv/Lib and the failure surfaced as a
raw pandas FileNotFoundError naming a path inside the virtualenv.
"""

import sys
from pathlib import Path

import pytest

from de_power_market_view import fetch, view
from de_power_market_view.view import SnapshotNotFoundError, run_view


def test_neither_entry_point_derives_the_project_root_from_the_package():
    fetch_args = fetch.build_parser().parse_args(
        ["--start", "2024-01-01", "--end", "2024-01-02"]
    )
    view_args = view.build_parser().parse_args([])
    assert fetch_args.project_root is None
    assert view_args.project_root is None


def test_run_view_names_the_missing_snapshot_and_the_way_out(tmp_path):
    with pytest.raises(SnapshotNotFoundError) as excinfo:
        run_view(tmp_path)
    message = str(excinfo.value)
    assert "market_hourly.csv" in message
    assert "de-power-fetch" in message
    assert "--project-root" in message


def test_view_main_defaults_to_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["de-power-view"])
    with pytest.raises(SystemExit) as excinfo:
        view.main()
    message = str(excinfo.value)
    assert str(Path.cwd().resolve()) in message
    assert "site-packages" not in message


def test_fetch_main_defaults_to_the_working_directory(tmp_path, monkeypatch):
    """fetch writes rather than reads, so verify the root it would write into."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["de-power-fetch", "--start", "2024-01-01", "--end", "2024-01-02"]
    )
    seen: dict[str, Path] = {}

    def capture(start, end, project_root):
        seen["root"] = project_root
        raise SystemExit(0)

    monkeypatch.setattr(fetch, "fetch_snapshot", capture)
    with pytest.raises(SystemExit):
        fetch.main()
    assert seen["root"] == Path.cwd().resolve()
