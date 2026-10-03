# [Weather episode]: DE-LU day-ahead decision memo

DRAFT TEMPLATE. Delivery: [date and start/end timestamps with UTC offsets].
Product: EPEX SPOT DE-LU day-ahead auction, [N] quarter-hour periods.
Written at: [UTC]. Publication deadline: [D-1 11:30 Europe/Berlin and UTC].

## Call

[Bullish / bearish / neutral] for this delivery period. Forecast mean:
[Y EUR/MWh]. Matching market reference: [X EUR/MWh, EEX contract, trading
and publication dates, exact delivery period] or **market reference unavailable**.
Difference: [Y − X]. Frozen direction/deadband rule: [rule]. D-7 reference:
[Z EUR/MWh], retained as a separate technical benchmark.

Intended expression: [buy/long, sell/short, or stay out]. State the price limit
or quote, volume and closing/physical-cover mechanism. Explain what the market
appears to have priced in and what your forecast adds. If those execution
inputs are missing, record a conditional plan with **no position**.

## Reasoning

[Weather-to-load/generation mechanism, why this product is exposed, and the
main countervailing effect. Cite forecasts available before this memo.]

Back-of-envelope: [formula, input values and units, result]. For example,
Δresidual load = Δload − Δwind − Δsolar. Label assumptions and distinguish
the MW estimate from the separate price forecast.

## What would change the view

Primary indicator: [observable quantity, source and next review time].
Reassess if [numeric condition]. Stay out if [missing input, stale market
reference, contrary setup, insufficient expected margin or missed deadline].

## Evidence and scoring

| Input | Value / unit | Issue or publication UTC | Retrieved UTC | Immutable file / URL and SHA-256 |
|---|---|---|---|---|
| Weather forecast / warning | [value] | [time] | [time] | [evidence] |
| Sealed hourly forecast | [value, model version] | [seal time] | [time] | [commit and file] |
| Matching market reference or unavailable status | [value] | [time] | [time] | [evidence] |
| D-7 reference | [values] | [time] | [time] | [evidence] |

Frozen scoring: realised minus market reference [if matched], realised minus
D-7, declared directional result, and forecast/reference absolute errors.
Publication receipt is recorded separately without changing this memo.

Scope: this is a price-view case. Hourly forecasts do not predict quarter-hour
shape; nominal intervals may under-cover. Settlement references may contain
risk premia or estimation and do not establish an executable trade or profit.
