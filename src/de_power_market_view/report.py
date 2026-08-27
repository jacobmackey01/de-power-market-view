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

    exploratory = result.get("exploratory", {})
    deciles = exploratory.get("residual_deciles", pd.DataFrame()).copy()
    sign_split = exploratory.get("residual_sign_split", pd.DataFrame()).copy()

    if len(sign_split) == 2:
        surplus = sign_split.iloc[0]
        rest = sign_split.iloc[1]
        sign_sentence = (
            f"In this sample, hours in which wind and solar together exceeded "
            f"German load cleared below zero {_pct(surplus['negative_rate'])} of "
            f"the time (95% Wilson interval {_pct(surplus['ci_low'])}"
            f"–{_pct(surplus['ci_high'])}, n={int(surplus['n_hours']):,}), "
            f"against {_pct(rest['negative_rate'])} for all other hours "
            f"(n={int(rest['n_hours']):,})."
        )
    else:
        sign_sentence = "The renewable-surplus split was not available."

    provenance_sentence = ""
    if provenance:
        unknown_time = provenance.get("n_cached_without_retrieval_time") or 0
        provenance_sentence = (
            f"The snapshot records {_num(provenance.get('n_response_reads'))} "
            f"response reads: {_num(provenance.get('n_from_smard'))} retrieved "
            f"from SMARD during the run that wrote it and "
            f"{_num(provenance.get('n_from_cache'))} read from the local "
            f"raw-response cache."
        )
        if unknown_time:
            provenance_sentence += (
                f" Of the cached responses, {_num(unknown_time)} predate "
                f"retrieval-time recording, so the moment SMARD actually served "
                f"them is unknown and is reported as null rather than as the "
                f"cache-read time."
            )
        provenance_sentence += (
            " See data/provenance.json for URL hashes and both timestamps."
        )

    quality_section = ""
    if quality:
        missing = quality.get("missing_counts", {})
        quality_section = (
            "\n\n## Data quality\n\n"
            f"The processed snapshot contains {_num(quality.get('n_rows'))} "
            f"rows and {_num(quality.get('n_complete_analysis_rows'))} complete "
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

## Exploratory sensitivity, added after the first retrieval

Neither view below was preregistered. Both were added once the preregistered
quartiles turned out to place almost the entire event mass inside Q1, leaving
Q2 to Q4 nearly empty and hiding how steeply risk varies inside that bottom
quartile. Amendment 1 in <code>PREREGISTRATION.md</code> records that decision
and its date.

They are reported alongside the primary readout, not in place of it. Because
they were chosen with knowledge of the data, their sharper separation is a
description of this sample rather than evidence of the same standing as the
preregistered table above.

### Residual-load deciles

{_table(
    deciles,
    ["group", "n_hours", "negative_hours", "negative_rate", "ci_low", "ci_high"],
    ["Stratum", "Hours", "Negative", "Rate", "CI low", "CI high"],
)}

### Renewable surplus: residual load below zero

Unlike the quantile strata, this boundary is fixed by the physics of the
system rather than by the retrieved sample, so it does not move when the
window changes.

{_table(
    sign_split,
    ["group", "n_hours", "negative_hours", "negative_rate", "ci_low", "ci_high"],
    ["Condition", "Hours", "Negative", "Rate", "CI low", "CI high"],
)}

{sign_sentence}

![Exploratory negative-price risk figure](negative_price_exploratory.png)

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
