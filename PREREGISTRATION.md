# Preregistration — DE-LU negative-price risk view

Status: frozen for version 0.1 before the first historical retrieval.
The body below is unedited. Later changes are appended as dated
amendments at the end of this file; read them before relying on any
specification stated here.

## Question

When does Germany go negative, and which observed fundamental conditions are
associated with materially higher negative-price incidence?

The unit of analysis is one settled DE-LU day-ahead delivery hour. A negative
price event is defined as a day-ahead price strictly below 0 EUR/MWh.

## Primary readout

The primary readout is descriptive:

1. negative-price incidence across quartiles of observed residual load;
2. negative-price incidence by local delivery hour;
3. the latest complete local day compared with prior days with similar observed
   load, wind and solar conditions.

Rates are accompanied by Wilson 95% intervals and observation counts. The
quartile boundaries are calculated from the retrieved sample and are described
as retrospective strata, not as trading thresholds.

## Secondary diagnostic

A single chronological logistic-regression holdout is included as a compact
sanity check. It uses observed hourly load, wind, solar, residual load and
calendar features. The first 80% of complete local days are training data and
the final 20% are test data. The model is compared with a training-period
prevalence baseline using average precision, Brier score, log loss and ROC AUC.

No hyperparameter search, repeated test-set selection or probability threshold
optimisation is performed. If the train or test partition has fewer than 50
positive and 50 negative hours, model metrics are reported as insufficient
support rather than interpreted.

## Information boundary

This is a historical market-analysis case study, not a prospective forecast.
The fundamental variables are settled observations and therefore cannot be
treated as fully available before the day-ahead auction. The project makes no
claim about pre-auction predictability, execution, causality or P&L.

The output is intended to answer: “What market conditions have historically
coincided with negative prices?” It is not intended to answer: “Should a trader
sell this hour?”

## Data and transformations

The retrieval uses hourly series from the Bundesnetzagentur's SMARD chart-data
API:

- DE-LU day-ahead price;
- German actual load;
- German onshore wind generation;
- German offshore wind generation;
- German solar generation.

Wind is the sum of onshore and offshore generation. Residual load is defined as
load minus wind minus solar. Missing source values remain missing; they are not
silently replaced with zero. An analysis row requires a price and all four
fundamental inputs.

The fetch records each response URL, SHA-256 hash, byte count and retrieval
timestamp in data/provenance.json. Source revisions can therefore be detected,
although a rerun may still produce different results if SMARD revises
historical values.

## Interpretation boundary

The generated analyst readout must distinguish:

- observed conditions from interpretation;
- historical association from causal explanation;
- a risk distribution from a deterministic prediction;
- a view from the conditions that would make it stale.

---

## Amendment 1 — exploratory strata added after the first retrieval

Date: 2026-08-27. Status: exploratory, not preregistered.

### What changed

Two additional descriptive views are reported alongside the primary readout:

1. negative-price incidence across **deciles** of observed residual load;
2. negative-price incidence split by the **sign** of residual load, that is,
   whether wind and solar together exceeded German load.

### Why

The preregistered quartiles behaved as an informative stratification only in
the first stratum. In the retrieved sample, 1,435 of 1,436 negative hours
fell in Q1, leaving Q2 to Q4 with one event between them. The primary table
is therefore close to a binary indicator for "bottom quartile", and it
averages away a steep gradient inside that quartile: the lowest decile ran
54.1% while the second ran 7.4%.

Deciles and the sign split describe that gradient. They were chosen **after**
seeing the quartile result, so they are exploratory by construction.

### Standing of these views

They are additions, not replacements. The preregistered quartile table
remains the primary readout, is reported first, and is unchanged by this
amendment. Nothing in the preregistered analysis was recalculated, dropped or
reordered.

Because these strata were selected with knowledge of the data, their sharper
separation is a description of this sample and carries less evidential weight
than the preregistered table. A genuine test of the sign split would require
a window that was not used to choose it.

The sign split is nonetheless reported because its boundary is fixed by the
physics of the system rather than estimated from the sample, so unlike the
quantile strata it does not move when the retrieval window changes.

### What was not done

The exploratory strata are not supplied to the model, no threshold was
optimised, and the 80/20 chronological split and 50-per-class support gate
are unchanged. Changes to the diagnostic specification itself are recorded
separately in Amendment 2.

---

## Amendment 2 — corrections to the preregistered diagnostic

Date: 2026-08-27. Status: corrections, disclosed because published numbers
changed.

### Feature set: a deviation from the preregistration

The preregistration specified that the diagnostic "uses observed hourly load,
wind, solar, residual load and calendar features". That specification is not
estimable. Residual load is defined in this project as load minus wind minus
solar, so those four terms are exactly linearly dependent: on the retrieved
sample the design matrix has rank 3 of 4, its smallest singular value is 0,
and its condition number is 1.7e15.

Under an L2 penalty the fit still converges, but the split of a shared effect
across the four terms is determined by the penalty rather than by the data,
so the published coefficient table was not identified and should not have
been read as a set of market associations.

`load_mw` has therefore been dropped, leaving residual load, wind and solar
to span the same information at full rank (condition number 6.4e4). This is a
deviation from the preregistered specification, made to render it estimable
rather than to improve a result: test average precision moves from 0.8143 to
0.8140 and ROC AUC from 0.9768 to 0.9768.

### Average precision: a bug fix, not a specification change

The preregistered metric set is unchanged. The implementation of average
precision was wrong: it ranked tied scores by array order, and because the
prevalence baseline assigns one identical probability to every hour, every
baseline score was tied. The baseline was therefore scored on the
chronological position of negative hours rather than on its constant ranking.

The reported baseline average precision changes from 7.6% to 8.7%, which is
the test-set prevalence and the only defensible value for a constant
predictor. The correction moves the comparison against the model, and is
disclosed for that reason.

### Standing

Neither change was made after inspecting an outcome the change would flatter.
Both were made because the original specification could not support the claim
being printed next to it.
