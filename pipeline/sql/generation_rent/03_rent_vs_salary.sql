-- =====================================================================================
-- Generation Rent · 03 · Bonus question
-- "What share of an average net salary does a 1-bed flat in the capital cost?"
-- New concepts: JOIN to a dimension table, window functions RANK() and PARTITION BY
--
-- CAVEATS (put them in every chart note):
--  * city rents come from Eurostat's correction coefficients for EU-officials' duty
--    stations, so they're NOT the average local rent (probably above it)
--  * capital-city rent vs NATIONAL average net salary (single person, no children)
--  * net earnings break in 2024 → the rent share drops artificially in 2024; compare
--    rent LEVELS across years, and rent SHARES only within the same year
--  * the Netherlands has no capital in this data (only Den Haag), so "EU capitals" = 26
-- =====================================================================================

-- 1. 2025 ranking of EU capitals by rent as % of net monthly salary
SELECT RANK() OVER (ORDER BY r.rent_share_of_net_salary_pct DESC) AS rank,
       r.city,
       d.country,
       r.rent_1bed_eur_month,
       ROUND(r.net_salary_eur_month, 0) AS net_salary_eur_month,
       r.rent_share_of_net_salary_pct
FROM city_rent AS r
JOIN dim_country AS d
  ON d.geo = r.country_geo
WHERE r.year = 2025
  AND d.is_eu27                                   -- EU capitals only (drops London, Oslo, Belgrade…)
  AND r.is_capital                                -- capitals only (drops Munich, Bonn, Varese, Den Haag…)
  AND r.rent_share_of_net_salary_pct IS NOT NULL
ORDER BY rank, r.city;

-- 2. How much have capital rents risen since 2015? (levels: the earnings break doesn't matter here)
--    All capitals in the data, EU and non-EU.
SELECT city,
       MAX(CASE WHEN year = 2015 THEN rent_1bed_eur_month END) AS rent_2015,
       MAX(CASE WHEN year = 2025 THEN rent_1bed_eur_month END) AS rent_2025,
       ROUND((MAX(CASE WHEN year = 2025 THEN rent_1bed_eur_month END)
            / MAX(CASE WHEN year = 2015 THEN rent_1bed_eur_month END) - 1) * 100, 1) AS pct_change
FROM city_rent
WHERE is_capital
GROUP BY city
HAVING rent_2015 IS NOT NULL AND rent_2025 IS NOT NULL
ORDER BY pct_change DESC, city;

-- 3. Lisbon year by year, with its rank among capitals each year (PARTITION BY year)
--    Ranks are comparable year to year (every country is ranked on the same basis each year),
--    but the share itself drops in 2024 because of the earnings-method break.
WITH ranked AS (
    SELECT r.year, r.city, r.rent_1bed_eur_month, r.rent_share_of_net_salary_pct,
           RANK() OVER (PARTITION BY r.year ORDER BY r.rent_share_of_net_salary_pct DESC) AS rank_that_year,
           COUNT(*) OVER (PARTITION BY r.year)                                             AS capitals_that_year
    FROM city_rent AS r
    JOIN dim_country AS d ON d.geo = r.country_geo
    WHERE d.is_eu27 AND r.is_capital AND r.rent_share_of_net_salary_pct IS NOT NULL
)
SELECT *
FROM ranked
WHERE city = 'Lisboa'
ORDER BY year;

-- -------------------------------------------------------------------------------------
-- Further questions
--   a) Query 1: how many capitals have rent above 50% of the net salary? (COUNT + WHERE)
--   b) Query 2: add the growth of net earnings 2015 → 2023 next to rent growth.
--   c) Query 3: replace Lisboa with Madrid and Dublin. Use WHERE city IN (…).
-- -------------------------------------------------------------------------------------
