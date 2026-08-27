# DE-LU power-market view

## When does Germany go negative?

This repository is a compact, reproducible case study of negative-price risk
in the DE-LU day-ahead power market.

It answers a deliberately narrow question:

> When does Germany go negative, and which observed fundamental conditions are
> associated with materially higher risk?

The workflow combines settled day-ahead prices with load, wind and solar
generation, derives residual load in SQL, and produces an analyst-style view:

**market question → fundamentals → SQL/DuckDB → historical risk → chart →
interpretation → invalidation conditions**

This is the missing kind of evidence in a portfolio otherwise centred on
forecasting, machine learning, pipelines and applied AI: not just whether a
model scores well, but whether the analyst can explain what the market was
doing.

## Scope

Version 0.1 is intentionally small:

- one market: Germany/Luxembourg (DE-LU);
- one event: price below 0 EUR/MWh;
- one data source: the Bundesnetzagentur's [SMARD chart-data
  API](https://www.smard.de/en/marktdaten);
- one historical descriptive view, supported by a chronological holdout
  diagnostic;
- two exploratory strata added after the first retrieval and reported as
  such, never in place of the preregistered readout.

The project uses observed fundamentals. It is not a live signal, a
pre-auction forecast, a causal model or a trading strategy. In particular,
beating a prevalence baseline on a historical holdout would not establish
tradeable edge.

Read <code>PREREGISTRATION.md</code> for the frozen question, metrics, support
gate and information boundary.

## Run it

The commands below assume a fresh Python 3.11+ environment.

~~~powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

de-power-fetch --start 2024-01-01 --end 2026-08-25
de-power-view
pytest
~~~

<code>de-power-fetch</code> retrieves the selected historical window, normalises
the five SMARD series into <code>data/processed/market_hourly.csv</code>, and
writes source provenance to <code>data/provenance.json</code>. Raw responses are
cached under <code>data/raw/</code> and ignored by Git.

<code>de-power-view</code> builds <code>data/market_view.duckdb</code>, runs the
checked-in SQL transformation in
<code>src/de_power_market_view/sql/market_view.sql</code>, writes the report to
<code>outputs/market_view.md</code>, saves the summary to
<code>outputs/results.json</code>, and creates
<code>outputs/negative_price_risk.png</code> together with
<code>outputs/negative_price_exploratory.png</code>.

The retrieval end date should be chosen far enough in the past that the last
local day is settled and complete. The report itself selects the latest
complete local day rather than assuming every API row is usable.

## What the report contains

The generated view keeps the analyst and modelling layers separate:

- coverage and completeness checks;
- overall negative-price incidence;
- rates by residual-load quartile with Wilson intervals (preregistered);
- rates by local delivery hour;
- the latest complete day’s observed setup;
- prior historical analogue days;
- an exploratory decile and renewable-surplus sensitivity, clearly separated
  from the preregistered readout and carried in its own figure;
- a chronological logistic-regression diagnostic with support checks;
- explicit conditions that would make the interpretation stale.

The latest-day section is a retrospective description. It does not imply that
the same inputs were available before the auction.

## Repository layout

~~~text
PREREGISTRATION.md
src/de_power_market_view/
  smard.py       SMARD client, response hashes and source-series parsing
  data.py        local-day normalisation and quality checks
  warehouse.py   DuckDB loading and query helpers
  analysis.py    risk tables, analogues and chronological diagnostic
  plotting.py    the preregistered figure and the exploratory figure
  report.py      analyst-style Markdown output
  fetch.py       de-power-fetch entry point
  view.py        de-power-view entry point
  sql/
    market_view.sql   the single source of truth for derived fields
tests/
~~~

## Data provenance

The source is public SMARD data. The five filter IDs are kept in
<code>src/de_power_market_view/smard.py</code> and are recorded with every
retrieval. The processed file is a convenience snapshot, not a permanent
guarantee that SMARD will never revise history. Re-running the fetch records
new hashes and timestamps so changes can be reviewed rather than hidden.

## Why this is useful

The project is designed to grow in a controlled direction:

**one market view → automate it → add further views → market monitor**

The next additions, if justified by the evidence, would be forward-available
weather, neighbouring prices or flows, and a genuinely prospective version.
They are deliberately outside version 0.1.

Author: Jacob Mackey · [jacobmackey.com](https://jacobmackey.com) · MIT licensed.
