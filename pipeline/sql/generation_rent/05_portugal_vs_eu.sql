-- =====================================================================================
-- Generation Rent · 05 · Portugal vs the EU average over time
-- New concepts: LAG() for year-on-year change, self-join, monthly → latest value
-- =====================================================================================

-- 1. Portugal and EU side by side, every year (self-join of the same table)
SELECT pt.year,
       pt.house_price_index_2015       AS pt_house_prices,
       eu.house_price_index_2015       AS eu_house_prices,
       pt.pct_18_34_with_parents       AS pt_with_parents,
       eu.pct_18_34_with_parents       AS eu_with_parents,
       pt.overburden_25_29             AS pt_overburden_25_29,
       eu.overburden_25_29             AS eu_overburden_25_29
FROM country_year AS pt
JOIN country_year AS eu
  ON eu.year = pt.year AND eu.geo = 'EU27_2020'
WHERE pt.geo = 'PT' AND pt.year >= 2010
ORDER BY pt.year;

-- 2. Year-on-year change in house prices with LAG (the value from the previous row)
SELECT geo,
       year,
       house_price_index_2015,
       ROUND((house_price_index_2015
              / LAG(house_price_index_2015) OVER (PARTITION BY geo ORDER BY year) - 1) * 100, 1)
           AS house_prices_yoy_pct
FROM country_year
WHERE geo IN ('PT', 'EU27_2020') AND year >= 2015
ORDER BY geo, year;

-- 3. Latest monthly inflation (annual rate, %) for rents, food, energy and everything, PT vs EU
--    hicp_monthly: one row per geo × category × month, with index_2015 and annual_rate_pct as columns.
--    Trap: the newest month is often a FLASH estimate with only the total, so "MAX(month)" alone
--    would drop rents/food/energy. We take the latest month where all 4 categories have a rate.
WITH complete_months AS (
    SELECT geo, month
    FROM hicp_monthly
    WHERE annual_rate_pct IS NOT NULL AND geo IN ('PT', 'EU27_2020')
      AND coicop18 IN ('TOTAL', 'CP011', 'CP041', 'CP045')
    GROUP BY geo, month
    HAVING COUNT(DISTINCT coicop18) = 4
),
latest_month AS (
    SELECT geo, MAX(month) AS month
    FROM complete_months
    GROUP BY geo
)
SELECT h.geo, h.month, h.coicop18, h.coicop18_label, h.annual_rate_pct
FROM hicp_monthly AS h
JOIN latest_month AS l USING (geo, month)
WHERE h.coicop18 IN ('TOTAL', 'CP011', 'CP041', 'CP045')
ORDER BY h.coicop18, h.geo;

-- 4. Rents vs overall prices since 2015 (HICP index, annual averages): who's above the line?
SELECT country,
       ROUND(hicp_rent_index, 1)                   AS rents_2025,
       ROUND(hicp_all_index, 1)                    AS all_prices_2025,
       ROUND(hicp_rent_index - hicp_all_index, 1)  AS rents_minus_all
FROM country_year
WHERE year = 2025 AND hicp_rent_index IS NOT NULL
ORDER BY rents_minus_all DESC, country;

-- -------------------------------------------------------------------------------------
-- Further questions
--   a) Query 2: add net earnings YoY with LAG. Which year looks suspicious, and why? (flag column!)
--   b) Query 3: remove the complete_months CTE and use MAX(month) directly. What disappears, and why?
--   c) Query 1: swap Portugal for Spain ('ES'). Write one headline sentence comparing the two.
-- -------------------------------------------------------------------------------------
