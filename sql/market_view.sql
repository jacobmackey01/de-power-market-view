-- Derived market-analysis table.
--
-- The source CSV contains only retrieved SMARD values and calendar fields
-- needed to inspect the snapshot. Market quantities used by the analysis are
-- derived here so the transformation is visible and executable in SQL.

CREATE OR REPLACE TABLE market_hourly AS
WITH typed AS (
    SELECT
        try_cast(timestamp_utc AS TIMESTAMPTZ) AS timestamp_utc,
        try_cast(local_date AS DATE) AS local_date,
        try_cast(local_hour AS INTEGER) AS local_hour,
        try_cast(month_num AS INTEGER) AS month_num,
        try_cast(day_of_week AS INTEGER) AS day_of_week,
        try_cast(is_weekend AS INTEGER) AS is_weekend,
        try_cast(price_eur_mwh AS DOUBLE) AS price_eur_mwh,
        try_cast(load_mw AS DOUBLE) AS load_mw,
        try_cast(wind_onshore_mw AS DOUBLE) AS wind_onshore_mw,
        try_cast(wind_offshore_mw AS DOUBLE) AS wind_offshore_mw,
        try_cast(solar_mw AS DOUBLE) AS solar_mw
    FROM raw_market
),
derived AS (
    SELECT
        *,
        wind_onshore_mw + wind_offshore_mw AS wind_total_mw
    FROM typed
)
SELECT
    timestamp_utc,
    local_date,
    local_hour,
    month_num,
    day_of_week,
    is_weekend,
    price_eur_mwh,
    load_mw,
    wind_onshore_mw,
    wind_offshore_mw,
    solar_mw,
    wind_total_mw,
    load_mw - wind_total_mw - solar_mw AS residual_load_mw,
    CASE
        WHEN price_eur_mwh IS NULL THEN NULL
        WHEN price_eur_mwh < 0 THEN 1
        ELSE 0
    END AS negative_price,
    CASE
        WHEN load_mw > 0 THEN wind_total_mw / load_mw
        ELSE NULL
    END AS wind_share_of_load,
    CASE
        WHEN load_mw > 0 THEN solar_mw / load_mw
        ELSE NULL
    END AS solar_share_of_load,
    CASE
        WHEN price_eur_mwh IS NOT NULL
         AND load_mw IS NOT NULL
         AND wind_onshore_mw IS NOT NULL
         AND wind_offshore_mw IS NOT NULL
         AND solar_mw IS NOT NULL
        THEN 1
        ELSE 0
    END AS analysis_complete
FROM derived
WHERE timestamp_utc IS NOT NULL
ORDER BY timestamp_utc;
