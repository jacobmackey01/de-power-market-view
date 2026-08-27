# Preregistration — DE-LU negative-price risk view

Status: frozen for version 0.1 before the first historical retrieval.

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
