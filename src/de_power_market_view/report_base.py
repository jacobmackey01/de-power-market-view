"""Render an answer-first analyst-style Markdown readout."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd


def _pct(value: Any, digits: int = 1) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return "n/a" if not math.isfinite(value) else f"{value:.{digits}%}"


def _num(value: Any, digits: int = 0) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(value):
        return "n/a"
    return f"{value:,.{digits}f}"


def _table(frame: pd.DataFrame, columns: list[str], headers: list[str] | None = None) -> str:
    """Small dependency-free Markdown table renderer."""

    if frame.empty:
        return "_No rows available._"
    headers = headers or columns
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame[columns].iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.3f}" if math.isfinite(value) else "n/a")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _regime_label(percentile: float) -> str:
    if not math.isfinite(percentile):
        return "not rankable against earlier complete days"
    if percentile <= 0.25:
        return "lower-residual-load, renewable-heavy"
    if percentile >= 0.75:
        return "higher-residual-load"
    return "middle-of-sample"


def render_report(
    result: dict[str, Any],
    output_path: Path,
    *,
    provenance: dict[str, Any] | None = None,
    quality: dict[str, Any] | None = None,
) -> None:
    """Write the generated market view."""

    coverage = result["coverage"]
    latest = result["latest_day"]
    quartiles = result["residual_quartiles"].copy()
    hours = result["hourly_rates"].copy()
    months = result["monthly_rates"].copy()
    analogues = result["analogues"].copy()
    diagnostic = result["diagnostic"]
    percentile = float(latest["residual_load_percentile_vs_prior_days"])

    q1 = quartiles.iloc[0]
    q4 = quartiles.iloc[-1]
    latest_regime = _regime_label(percentile)

    if len(analogues):
        analogue_rate = float(analogues["negative_price_rate"].mean())
        analogue_sentence = (
            f"The {len(analogues)} nearest prior complete days had a mean "
            f"negative-price rate of {_pct(analogue_rate)}; their individual "
            f"rates ranged from {_pct(analogues['negative_price_rate'].min())} to "
            f"{_pct(analogues['negative_price_rate'].max())}."
        )
    else:
        analogue_sentence = "No prior complete days were available for an analogue comparison."

    if diagnostic.get("status") == "ok":
        baseline = diagnostic["baseline_metrics"]
        logistic = diagnostic["logistic_metrics"]
        diagnostic_sentence = (
            f"On the untouched final {diagnostic['test_start_date']} to "
            f"{diagnostic['test_end_date']} period, the untuned logistic diagnostic "
            f"returned average precision {_pct(logistic['average_precision'], 1)} "
            f"versus {_pct(baseline['average_precision'], 1)} for the prevalence "
            f"baseline. Its Brier score was {logistic['brier_score']:.4f} versus "
            f"{baseline['brier_score']:.4f}; lower is better. This is an "
            f"explanatory holdout using observed fundamentals, not evidence of a "
            f"pre-auction or tradeable signal."
        )
        coefficients = pd.DataFrame(diagnostic["coefficients"]).head(5)
        coefficient_section = (
            "\nTop standardised model associations (not causal effects):\n\n"
            + _table(
                coefficients,
                ["feature", "standardised_coefficient", "odds_ratio_per_standard_deviation"],
                ["Feature", "Coefficient", "Odds ratio per SD"],
            )
        )
    else:
        diagnostic_sentence = (
            f"The chronological diagnostic was not interpreted because its status "
            f"was {diagnostic.get('status', 'unknown')}. The support gate requires "
            f"{diagnostic.get('support_gate', {}).get('minimum_per_class', 'the specified')} "
            f"observations in each class of both partitions."
        )
        coefficient_section = ""

    provenance_sentence = ""
    if provenance:
        provenance_sentence = (
            f"The snapshot records {provenance.get('n_fetches', 'n/a')} response "
            f"fetches, of which {provenance.get('n_cached_fetches', 'n/a')} were "
            f"served from the local raw-response cache. See "
            f"data/provenance.json for URL hashes and retrieval timestamps."
        )

    quality_section = ""
    if quality:
        missing = quality.get("missing_counts", {})
        quality_section = (
            "\n\n## Data quality\n\n"
            f"The processed snapshot contains {quality.get('n_rows', 'n/a'):,} "
            f"rows and {quality.get('n_complete_analysis_rows', 'n/a'):,} complete "
            f"analysis rows. Missing counts in the five source series were: "
            f"price {_num(missing.get('price_eur_mwh'))}, load "
            f"{_num(missing.get('load_mw'))}, onshore wind "
            f"{_num(missing.get('wind_onshore_mw'))}, offshore wind "
            f"{_num(missing.get('wind_offshore_mw'))}, solar "
            f"{_num(missing.get('solar_mw'))}. Missing values were not converted "
            f"to zero."
        )

    text = f"""# DE-LU negative-price risk view

Generated from settled SMARD observations. This is a historical analyst case
study, not a live trading signal.

## The short answer

In the retrieved sample, {coverage['negative_price_hours']:,} of
{coverage['complete_rows']:,} complete delivery hours were negative
({_pct(coverage['negative_price_rate'])}). The clearest descriptive separation
is residual load: the lowest-residual-load quartile had a negative-price rate of
{_pct(q1['negative_rate'])} (95% Wilson interval {_pct(q1['ci_low'])}–{_pct(q1['ci_high'])},
n={int(q1['n_hours']):,}), compared with {_pct(q4['negative_rate'])} in the
highest-residual-load quartile (95% interval {_pct(q4['ci_low'])}–{_pct(q4['ci_high'])},
n={int(q4['n_hours']):,}).

That pattern is an association in settled data. It does not establish that
residual load causes negative prices, nor that the same variables were
available early enough to trade on.

## Latest observed setup

The latest complete local day in the snapshot was **{latest['local_date']}**.
Its observed averages were {_num(latest['mean_load_mw'])} MW load,
{_num(latest['mean_wind_mw'])} MW wind and {_num(latest['mean_solar_mw'])} MW
solar, leaving {_num(latest['mean_residual_load_mw'])} MW mean residual load.
It recorded {latest['negative_hours']} negative-price hours out of
{latest['hours']} and a minimum settled price of
{_num(latest['min_price_eur_mwh'], 2)} EUR/MWh.

Relative to strictly earlier complete days, its mean residual load was at the
{_pct(percentile, 0)} percentile. That places the day in a
**{latest_regime}** observed setup. The nearest-day comparison is deliberately
historical: {analogue_sentence}

## Primary evidence

### Residual-load strata

The quartile boundaries are calculated from this retrieved sample and are
retrospective descriptive strata, not proposed trading thresholds.

{_table(
    quartiles,
    ["group", "n_hours", "negative_hours", "negative_rate", "ci_low", "ci_high"],
    ["Stratum", "Hours", "Negative", "Rate", "CI low", "CI high"],
)}

### Intraday and seasonal context

{_table(
    hours,
    ["group", "n_hours", "negative_hours", "negative_rate", "ci_low", "ci_high"],
    ["Local hour", "Hours", "Negative", "Rate", "CI low", "CI high"],
)}

The month-level rates are included as context rather than as a claim that
seasonality is stable across future years:

{_table(
    months,
    ["group", "n_hours", "negative_hours", "negative_rate", "ci_low", "ci_high"],
    ["Month", "Hours", "Negative", "Rate", "CI low", "CI high"],
)}

![Historical negative-price risk figure](negative_price_risk.png)

## Chronological diagnostic

{diagnostic_sentence}
{coefficient_section}

## What would invalidate this view?

This view should be treated as stale or incomplete if any of the following
change materially:

- SMARD revises the historical series, changes a filter's meaning or alters
  timestamp conventions;
- new forward weather, outage, interconnector or market-coupling information
  changes the fundamental setup;
- the market-design or regulatory regime changes the relationship between
  renewable surplus and prices;
- the analyst interprets settled actuals as though they were available before
  the day-ahead auction.

The next version should add forward-available inputs and a separate prospective
evaluation before making any pre-auction claim.

## Data boundary

The complete-row window is {coverage['first_timestamp_utc']} to
{coverage['last_timestamp_utc']}, covering {coverage['complete_local_days']} complete
local days. {provenance_sentence}
{quality_section}

No P&L, execution rule or deterministic “sell” instruction is produced.
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
