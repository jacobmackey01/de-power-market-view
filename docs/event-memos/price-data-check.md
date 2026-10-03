# Price access checked before choosing the product

Checked on **3 October 2026**. The primary case will use a specified strip of
DE-LU day-ahead auction delivery periods. Quarter-hour clearing prices are
accessible without an API key; executable pre-auction prices are not established
by those responses.

## What was actually retrieved

The [Energy-Charts `/price` endpoint](https://api.energy-charts.info/) returned
complete DE-LU curves for a normal day and a historical autumn clock change.
Its official API description and both responses specify **CC BY 4.0 from
Bundesnetzagentur | SMARD.de** for these DE-LU prices. Retain attribution to
Energy-Charts.info / Fraunhofer ISE and Bundesnetzagentur | SMARD.de when using
the saved data. This permission is specific to the stated source and zone;
it does not establish rights to republish EPEX order-book data.

| Delivery date, Europe/Berlin | Quarter-hours | Elapsed hours | Mean clearing price, EUR/MWh |
|---|---:|---:|---:|
| 1 October 2026 | 96 | 24 | 195.18 |
| 26 October 2025 | 100 | 25 | 6.52 |

These dates check access and arithmetic only. Neither is a selected or
prospectively predicted weather case. Saved [raw responses and inspections](evidence/)
provide the actual timestamps, prices and SHA-256 fingerprints. The inspection
time is recorded separately from retrieval; the original curl downloads did
not capture a server-side publication time or precise retrieval timestamp.

The checks require exactly one complete local day, strictly ordered UTC
timestamps 900 seconds apart, finite prices and the stated units. The extra
autumn hour retains both UTC offsets. Independent arithmetic using decimal
prices reproduced the means. Seven offline test cases cover clock changes,
missing/duplicate intervals, invalid prices, explicit strip boundaries and the
difference between a negative quarter-hour and a negative hourly mean.

## What can be scored honestly

| Evidence | Status | Supported use |
|---|---|---|
| DE-LU quarter-hour day-ahead clearing prices | Retrieved and checked | Price-view outcome and mean over a frozen delivery strip |
| Existing hourly market snapshot | Inspected, through 25 August 2026 | Historical context; not a current executable quote |
| Live forecast's hourly predictions | Schema inspected | Forecast hourly-average prices; no quarter-hour prediction claim |
| Intraday executable bid/ask, depth and fills | Not obtained | No entry/exit or fill claim |
| EEX German day/weekend settlements | Public examples inspected; see [source readiness](source-readiness.md) | Matching delivery-period market reference when captured before sealing |

The existing forecasting system and Energy-Charts both ultimately use SMARD
for realised prices. This is a resolution/access check, not independent
confirmation from a second original exchange source.

The auction clearing price is discovered after bidding. Comparing it with
last week's price measures the direction of a research view, not the return
on a trade entered at last week's price. Keep the market-expectation question
explicit: what information is missing from the prevailing expectation, and
how could it be monetised? Without that evidence, a bullish or bearish view
does not authorise a position.

## Reproduce the check

From the repository root, fetch one completed delivery day and save the URL,
retrieval UTC, response hash and attribution with it. Respect the endpoint's
published request limits and any `Retry-After` response.

```bash
curl --fail --silent --show-error \
  'https://api.energy-charts.info/price?bzn=DE-LU&start=2026-10-01&end=2026-10-01' \
  -o /tmp/de-lu-price-2026-10-01.json
python scripts/check_event_prices.py --date 2026-10-01 \
  --input /tmp/de-lu-price-2026-10-01.json
```

For a selected event, freeze whole-hour strip boundaries in advance and pass
their exact offset-bearing timestamps with `--start` and `--end`. A whole-hour
price is the mean of four clearing prices; the existing hourly negative-price
target is not the count of individual negative quarter-hours.

## Sources and verification boundary

- [Energy-Charts API documentation](https://api.energy-charts.info/), with the [saved `/price` description](evidence/energy-charts-price-endpoint.json).
- [EPEX SPOT product description](https://www.epexspot.com/en/new-15-minute-products-market-coupling): noon coupled auction, quarter-hour prices and arithmetic hourly index. The description was available through web search; a direct page open returned 403.
- [EPEX SPOT annual results published in January 2026](https://www.epexspot.com/sites/default/files/download_center_files/2026-01-19_EPEX%20SPOT_Annual%20Power%20Trading%20Results%202025_final_0.pdf): confirms the quarter-hour transition happened from 1 October 2025.

**Assessment:** ready for a prospectively published price-view case with these
caveats. Trading profitability remains unevaluated. Public timestamp evidence,
the actual weather episode, its predictive inputs and the completed decision
memo still have to be recorded before an eligible future auction.
