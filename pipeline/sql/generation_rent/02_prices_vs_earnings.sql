-- =====================================================================================
-- Generation Rent · 02 · Headline question 1
-- "Since 2015, have house prices outrun salaries in your country?"
-- New concepts: CTEs (WITH), pivoting with MAX(CASE WHEN …), RANK() window function
--
-- IMPORTANT: net earnings have an EU-wide break in 2024 (flag 'b'). So we compare
-- 2015 → 2023 for BOTH prices and earnings (same period, no break), and show the
-- extra price growth 2023 → 2025 separately.
-- =====================================================================================

-- 1. Growth of house prices vs net earnings, 2015 → 2023, by country
WITH pivoted AS (
    -- Turn rows (one per year) into columns (one per year we need)
    SELECT geo,
           country,
           MAX(CASE WHEN year = 2015 THEN house_price_index_2015 END) AS hpi_2015,
           MAX(CASE WHEN year = 2023 THEN house_price_index_2015 END) AS hpi_2023,
           MAX(CASE WHEN year = 2025 THEN house_price_index_2015 END) AS hpi_2025,
           MAX(CASE WHEN year = 2015 THEN net_earnings_eur END)       AS earn_2015,
           MAX(CASE WHEN year = 2023 THEN net_earnings_eur END)       AS earn_2023
    FROM country_year
    GROUP BY geo, country
),
growth AS (
    SELECT geo,
           country,
           ROUND((hpi_2023  / hpi_2015  - 1) * 100, 1) AS house_prices_pct_2015_23,
           ROUND((earn_2023 / earn_2015 - 1) * 100, 1) AS net_earnings_pct_2015_23,
           ROUND((hpi_2025  / hpi_2023  - 1) * 100, 1) AS house_prices_pct_2023_25
    FROM pivoted
    WHERE hpi_2015 IS NOT NULL AND earn_2015 IS NOT NULL      -- need both starting points
      AND geo <> 'EU27_2020'                                  -- rank countries only (EU average is not a country)
)
SELECT RANK() OVER (ORDER BY house_prices_pct_2015_23 - net_earnings_pct_2015_23 DESC) AS rank,
       country,
       house_prices_pct_2015_23,
       net_earnings_pct_2015_23,
       ROUND(house_prices_pct_2015_23 - net_earnings_pct_2015_23, 1) AS gap_pct_points,
       house_prices_pct_2023_25                                       AS then_prices_2023_25
FROM growth
ORDER BY rank, country;

-- 2. Same idea with the official affordability ratio (no break problem):
--    price-to-income vs the country's long-term average (100 = normal, >100 = less affordable)
--    The EU average row is kept as a reference point (it is not ranked).
SELECT country,
       MAX(CASE WHEN year = 2015 THEN price_to_income_vs_lt_avg END) AS ratio_2015,
       MAX(CASE WHEN year = 2025 THEN price_to_income_vs_lt_avg END) AS ratio_2025
FROM country_year
GROUP BY country
HAVING ratio_2025 IS NOT NULL
ORDER BY ratio_2025 DESC, country;

-- 3. "Real" house prices: after removing general inflation, how much more expensive are homes than in 2015?
--    (EU average kept as a reference row. Greece has no house price index, so it's missing here.)
SELECT country, ROUND(real_house_price_index_2015, 1) AS real_hpi_2025
FROM country_year
WHERE year = 2025 AND real_house_price_index_2015 IS NOT NULL
ORDER BY real_hpi_2025 DESC, country;

-- -------------------------------------------------------------------------------------
-- Further questions
--   a) Query 1: show only countries where prices grew at least twice as fast as earnings.
--      (Hint: add a WHERE on the growth CTE, or wrap the final SELECT in another CTE.)
--   b) Query 1 uses EUR. Repeat with net_earnings_pps. Does the ranking change? Why (or why not)?
--   c) Query 3: add the 2015 → 2025 change in pct_18_34_with_parents next to real house prices.
-- -------------------------------------------------------------------------------------
