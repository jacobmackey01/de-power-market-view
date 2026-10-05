# August heatwave: German evening power, 13 August 2026

**Call: bullish evening price pressure; no position without a matching entry price.**

Reconstructed practice, written 5 October 2026. Hypothetical decision cutoff:
12 August, 11:30 Europe/Berlin. Target: EPEX SPOT DE-LU day-ahead auction
quarter-hours from **2026-08-13T18:00:00+02:00 to 22:00:00+02:00**, excluding
the endpoint: 16 periods. This is an evening strip, not the standard peakload block.

## Decision and rationale

The [Commission's 11 August report](https://energy.ec.europa.eu/news/europes-electricity-system-remains-stable-despite-extreme-weather-2026-08-11_en)
described heatwave and drought pressure on European generation, with solar
relieving the midday balance. That suggests examining evening delivery, when
solar declines. The report also found no immediate adequacy problem:
cross-border supply and demand response could absorb the stress. It does not
establish a German generation outage or a German demand shock.

The [existing v1 forecast](https://github.com/jacobmackey01/de-power-live-forecast/blob/d97676ab5ba2c11241301b6b4ffda6612bcb9f90/predictions/2026-08-13.json),
sealed on 12 August at 07:22:11 UTC, projected **198.26 EUR/MWh** across these
four hours. The same hours on 6 August averaged **146.87 EUR/MWh** in the
settled SMARD snapshot. Back-of-envelope: 198.26 − 146.87 = **51.39 EUR/MWh**,
about **35%** above that technical reference. This is a price forecast, not an
estimate of heat's causal contribution.

A matching pre-cutoff market expectation is **unavailable in this reconstruction**.
A daily baseload future would include daytime solar hours and would not match
this strip. The week-earlier price is not a quote or an entry price. Therefore
the practice decision is **no position**. A conditional long would require a
matching executable price below the forecast by a margin that survives costs
and forecast uncertainty, plus an identified resale or physical-cover mechanism.
No volume, fill or profit is assumed here.

## What would change the view

Review the **forecast evening residual load**, defined as load minus wind and
solar, together with neighbouring generation availability and import capacity.
An extra 5 GW of wind, all else equal, reduces residual load by 5 GW; that is a
sensitivity, not a weather forecast. Such a revision would trigger reassessment
rather than automatic entry. Stay out if the matching quote, delivery cover,
issue-time evidence or publication deadline is missing.

## Outcome, examined separately

The selected strip actually averaged **284.87 EUR/MWh**, 138.00 above D-7.
The archived forecast understated it by **86.61 EUR/MWh**, versus D-7's
138.00 absolute error. This supports the direction relative to D-7 for this
chosen example, but cannot tell us whether a long beat the market.

Observed residual load averaged **36.70 GW**, versus **23.62 GW** a week earlier.
Load rose only 0.51 GW; wind fell 13.21 GW and solar rose 0.64 GW:
0.51 − (−13.21) − 0.64 = **13.08 GW** more residual load.
The realised German balance was dominated by weaker wind, which cautions
against attributing the price increase simply to heat. These are outturn
observations, never hypothetical decision inputs.

## How I would test the rule across events

Define event eligibility, hours, direction and abstention before examining
outcomes; reconstruct only forecasts and news available at each issue time;
include every eligible event and missed day; keep threshold selection separate
from a later holdout. With auction prices alone I can test forecasting accuracy.
Testing a tradable rule additionally needs matched historical entry and exit
marks, liquidity and costs. EEX settlements can support an expectation comparison
for matching products, but still do not prove executable fills. Missing EEX data
does not prevent a price-forecast backtest; it limits that particular comparison.

Sources: Commission report above; sealed forecast above; [settled SMARD snapshot](../../../data/processed/market_hourly.csv)
and [provenance](../../../data/provenance.json), written 27 August, used for outturn
and the retrospectively retrieved D-7 benchmark. The snapshot does not prove
which data revisions were available at the hypothetical cutoff.

Publication: retrospective practice; event and hours selected after outcomes were available; no prospective memo receipt or trading-performance claim.
