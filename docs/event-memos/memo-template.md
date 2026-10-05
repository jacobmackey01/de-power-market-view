# [Weather episode]: DE-LU day-ahead decision memo

DRAFT TEMPLATE. Written at: [UTC].
Publication deadline: [D-1 11:30 Europe/Berlin and UTC].

## Product and market reference

Choose a product with a matching pre-cutoff EEX settlement first, then freeze
the delivery hours. For the first real case, prefer a full local day matched to
an [EEX German Power Base Day future](https://www.eex.com/en/markets/power/german-power-markets)
when the weather mechanism supports it.

EPEX SPOT DE-LU target: [delivery date, start/end with UTC offsets,
quarter-hour count and duration weights].
EEX reference: [contract, delivery period, load profile, X EUR/MWh,
trading date, displayed publication time and observed UTC time].

The delivery period must match exactly. An evening strip cannot use a Base Day
settlement as its market price. Use only a settlement published before the
cutoff; if missing, state **market reference unavailable**. Keep
[D-7 price Z EUR/MWh] as a separate technical benchmark.

## Forecast fundamental setup

Use forecasts for the matching hours, with duration-weighted means:

| Fundamental | Delivery forecast, GW | D-7 observed, GW | Change, GW |
|---|---:|---:|---:|
| Load | [L] | [L7] | [ΔL] |
| Wind, onshore + offshore | [W] | [W7] | [ΔW] |
| Solar | [S] | [S7] | [ΔS] |
| Residual load | [L − W − S] | [L7 − W7 − S7] | [ΔL − ΔW − ΔS] |

Back-of-envelope: [Δload − Δwind − Δsolar = Δresidual load, with values].
Explain the largest contribution, its price implication and the countervailing
effect. Use news as supporting context.

Save the forecast figures and source evidence before publication, even if the
sealed price file stores only hashes. Identify independent forecasts or analyst
estimates separately from the price model's inputs. Use only pre-cutoff
forecasts, never delivery-day actuals or post-cutoff forecasts.

## Call and uncertainty

[Bullish / bearish / neutral] relative to the matching settlement.
Sealed price forecast: [Y EUR/MWh, version, seal time and immutable commit].
Difference: [Y − X]. Frozen direction/deadband rule: [rule and threshold].

Forecast range: [quantiles, levels and aggregation method].
Averaged hourly quantiles are not quantiles of the period's mean price.
Explain how uncertainty affects the forecast-versus-reference comparison.

Intended expression: [buy/long, sell/short, or stay out]. State the executable
quote or price limit, volume and resale/physical-cover mechanism. If the
reference, execution inputs or sufficient margin are missing, record a
conditional plan with **no position**.

## What would change the view

Primary indicator: [forecast residual load, source and next review time].
Reassess if [numeric revision threshold]. Stay out if [stale reference,
contrary setup, insufficient margin, missing cover or missed deadline].

## Evidence and scoring

| Input | Value / unit | Issue or publication UTC | Retrieved UTC | Immutable file / URL and SHA-256 |
|---|---|---|---|---|
| Load, wind and solar forecasts | [figures above] | [time] | [time] | [evidence] |
| D-7 fundamentals and prices | [figures, revision status] | [time] | [time] | [evidence] |
| Sealed price forecast and quantiles | [values, version] | [seal time] | [time] | [commit and file] |
| Matching EEX settlement | [value, contract] | [time] | [time] | [evidence] |
| Weather forecast / warning | [context] | [time] | [time] | [evidence] |

Frozen scoring: realised minus matching settlement [if available], realised
minus D-7, declared directional result, and forecast/reference absolute errors.
Publication receipt is recorded separately without changing this memo.

Scope: this is a price-view case. Hourly forecasts do not predict quarter-hour
shape; nominal intervals may under-cover. Settlements may be stale, estimated
or include risk premia; they do not establish executable trades or profit.
Check [EEX publication timing](https://www.eex.com/en/faq).
