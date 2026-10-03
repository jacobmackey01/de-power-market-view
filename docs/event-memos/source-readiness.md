# Source readiness checked on 3 October 2026

## Live-forecast timing

The [prediction workflow](https://github.com/jacobmackey01/de-power-live-forecast/blob/main/.github/workflows/predict.yml)
runs on a `02:12 UTC` schedule and waits for a **07:30 Europe/Berlin** seal
window. A delayed run seals when it starts, subject to the noon guard.
The schedule does not guarantee publication at 07:30.

Recent committed predictions show the practical timing:

| Delivery | Seal on D-1, Europe/Berlin | Minutes before auction close |
|---|---|---:|
| 1 October | 30 September, 10:29 | 90.6 |
| 2 October | 1 October, 10:52 | 67.8 |
| 3 October | 2 October, 10:27 | 92.1 |
| 4 October | 3 October, 10:03 | 116.3 |

These are the `sealed_at_utc` values in the corresponding public
`predictions/YYYY-MM-DD.json` files, converted to Berlin time. Draft the case
beforehand and insert the exact forecast once it appears. If it is not public
by 11:00 Berlin on D-1, skip that day. Publish before 11:30.

The prediction and scoring schedules currently contain no 31 October stop.
The predictor's default date remains tomorrow's local delivery date. The
preregistered evaluation nevertheless ends on 31 October; later automation
does not extend that study. This companion also stops at October deliveries.

## EEX settlements are visible without a paid subscription

After the user approved the displayed data-use terms, the public
[EEX market-data hub](https://www.eex.com/en/market-data/market-data-hub)
showed these manually selected examples for trading day **2 October 2026**:

| Contract | Delivery | Displayed settlement, EUR/MWh | Displayed update |
|---|---|---:|---|
| German Power Base Day 4 Future, DB04 | 4 October 2026 | 166.03 | 2 October, 21:20 CET |
| German Power Base Weekend 1 Future, DWB1 | Weekend 2026-40 | 167.52 | 2 October, 21:20 CET |

Both were read on 3 October, after that day's auction cutoff. They verify
access only; they are not a pre-auction capture for an event memo. The site's
timestamp is retained verbatim because it labels the October update "CET".
For a live case, record the observed UTC time separately and preserve the
displayed trading date and update label.

EEX's [FAQ](https://www.eex.com/en/faq) says that public traded-contract prices
have 45 days of history and normally update at 21:00–22:00 CE(S)T; intraday
prices are delayed by 15 minutes. A morning memo can use a previously
published settlement, not that evening's later update.

The [German contract description](https://www.eex.com/en/markets/power/german-power-markets)
defines the futures' underlying as average German day-ahead power prices and
lists day and weekend maturities. A daily base settlement matches a full-day
base target. A weekend contract is not a Sunday-only reference; neither is a
whole-day price a market price for an evening strip.

Capture a matching reference manually before the memo, identifying the exact
contract and delivery period rather than relying on a rolling short code.
Retain staleness and estimation caveats; a futures settlement can include risk
premia and does not establish an executable quote. If it is missing or does
not match the strip, say so explicitly and keep D-7 as the technical benchmark.

The hub permits infrequent redistribution of insubstantial manually selected
data, with restrictions on systematic republication. This study does not add
an automated EEX scraper or republish a futures history.
