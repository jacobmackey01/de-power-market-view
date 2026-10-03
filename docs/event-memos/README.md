# Prospective weather-event memos

Status, 3 October 2026: publication workflow and templates prepared. No live
event memo has been sealed.

The first case will state a weather-driven DE-LU price call before the auction,
then compare the outcome with the information available when the call was made.
It is a companion to the existing research, with its own event record.

## Product and comparison

Use EPEX SPOT DE-LU day-ahead quarter-hour auction contracts for a delivery
period fixed in advance. Prefer a full local day when the weather mechanism
supports it: an EEX German Power Base Day future then provides a matching
market benchmark. A narrower strip is permissible, but a whole-day or weekend
future is only context for that strip, not its market price.

EEX's free hub displayed both day and weekend settlements during the
[market-reference check](source-readiness.md). Capture the latest **pre-cutoff
daily settlement**, with its exact contract, delivery period, trading date,
published update time and observation time. Record any staleness or estimation
caveat. Do not use the final settlement that already incorporates the auction
outcome. End-of-day data normally appear at 21:00–22:00 Berlin time, so the
same trading day's evening update is unavailable to a morning memo.

When a matching reference is obtained before sealing, freeze the forecast-minus-
market difference and score realised price minus that market reference. Keep
D-7 same-local-hour persistence as a separate forecast benchmark. If no matching
market reference is obtained, write **market reference unavailable** in the
call and use D-7 only for the technical comparison.

For this first case, use whole-hour boundaries and the live model's hourly
forecasts. Compute realised strip means from the four quarter-hour clearing
prices per hour, with elapsed-duration weights. Use explicit UTC offsets for
clock-change days. Freeze the forecast, reference values, strip, direction,
deadband and success rule together; report forecast and reference absolute
errors as well as the directional result. Do not substitute a different
reference after seeing the outcome.

## Morning sequence

Draft the reasoning and prepare the evidence pack in advance. The live system
has a 07:30 Berlin seal target but often queues until later; recent seals ranged
from 10:03 to 10:52. The [schedule check](source-readiness.md) records the exact
observations. If the required forecast is not publicly available by **11:00
Europe/Berlin on D-1**, skip that delivery day and record the reason.

1. Choose the first future October delivery day with a defensible weather
   forecast or warning and adequate inputs. Use a genuine weather mechanism,
   not an extreme-weather label added for presentation.
2. Complete [the decision memo](memo-template.md) and a copy of
   [the publication manifest](publication-template.json). Cite the already
   sealed forecast at its exact upstream commit. Save weather, reference and
   forecast evidence, including issue/observation times and SHA-256 hashes.
3. Add the completed memo, manifest and evidence under
   `docs/event-memos/sealed/`, then commit and push. Publication must be
   recorded by GitHub **before 11:30 Europe/Berlin on D-1**. The auction closes
   at noon. Use the workflow receipt described below; a local Git timestamp
   alone is insufficient.
4. Keep the sealed files unchanged. Store subsequent revisions, cancellations
   and no-trade decisions separately, with their own timestamps.
5. After the clearing prices are published and complete, fill
   [the outcome record](outcome-template.md), retaining the original call,
   failed calls and no-trade updates. Keep later weather observations out of
   the original rationale.

## Publication workflow

[Publish event memo](../../.github/workflows/publish-event-memo.yml) runs
when a new event or dummy manifest is pushed. It records the full memo text,
manifest/evidence hashes, exact commit and **GitHub's API-provided run creation
time** in the Actions log, run summary and a downloadable receipt. It also posts
the complete receipt JSON to the permanent [Memo receipts issue](https://github.com/jacobmackey01/de-power-market-view/issues/2).
The checkout is fixed to that commit. Repository contents remain read-only;
`issues: write` is used to post the receipt comment.

For real events, it checks the 11:30 deadline in Berlin time, rejects a forecast
sealed after the memo was written, and verifies the saved prediction against
its immutable upstream URL. Pushes that edit or delete sealed files fail.
A queued job may execute later: the receipt distinguishes GitHub's run creation
time from the later recording time. The issue comment retains that original
timestamp, committed memo and hashes after the 90-day Actions retention ends.
Its own posting timestamp is additional evidence and may be later because of
queueing. Keep receipt comments unchanged; add corrections separately.

The [dummy memo](dry-runs/publication-dry-run.md) is clearly separate from event
results. A local rehearsal is:

```bash
python scripts/publish_event_memo.py --local-dry-run \
  --manifest docs/event-memos/dry-runs/publication-dry-run.json \
  --output /tmp/memo-publication-dry-run.json
python -m unittest discover -s tests -p 'test_memo_publication.py'
```

The dummy is always labelled as a dry run. Real memos and their evidence must
be committed to `main`. The default-branch workflow also provides a manual
Run workflow control for checking a committed manifest.

## Fallback and end date

At **11:30 Europe/Berlin on 24 October 2026**, if no valid event memo has been
published, start the reconstructed case that afternoon. State its historical
cutoff and hindsight limitation. A later genuine event may be added separately,
but must not delay the fallback or application preparation. Aim for one
prospective case; add at most one further case for a different mechanism.

This companion uses delivery dates through **31 October 2026**. The live
forecast workflows currently have no automatic stop at that date; that does
not extend the preregistered evaluation window. Do not change the live model,
predictions, ledger or preregistration for this work.

## Price checks and public presentation

The [price-access check](price-data-check.md) includes saved quarter-hour curves
and clock-change verification. Run `scripts/check_event_prices.py` on the
selected complete curve using the exact strip timestamps frozen in the memo.

Keep the public README focused on its existing historical result and figure.
Add a case-study link after a completed memo exists, with its publication
receipt and outcome status. The GitHub profile and pinned repositories should
then lead with the energy work as one coherent story.

## Scope

These illustrative cases assess price views, not realised trading profit.
A settlement can be stale or estimated and is not an executable bid/ask.
Profit would require separate entry, fill, exit, volume and cost evidence.

## Sources

- [EPEX SPOT products and hourly index](https://www.epexspot.com/en/new-15-minute-products-market-coupling).
- [EEX public market-data hub](https://www.eex.com/en/market-data/market-data-hub) and [publication-time FAQ](https://www.eex.com/en/faq).
- [Existing live forecasting record](https://github.com/jacobmackey01/de-power-live-forecast).
