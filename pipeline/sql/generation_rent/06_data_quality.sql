-- =====================================================================================
-- Generation Rent · 06 · Data quality & the double-counting trap
-- These are the queries that impress in interviews: they show you check before you chart.
-- =====================================================================================

-- 1. Uniqueness: is there exactly one row per country-year? (should return NO rows)
SELECT geo, year, COUNT(*) AS n
FROM country_year
GROUP BY geo, year
HAVING COUNT(*) > 1;

-- 2. Missing values in the latest year, per measure
SELECT COUNT(*)                                   AS countries,
       COUNT(*) - COUNT(house_price_index_2015)   AS missing_house_prices,
       COUNT(*) - COUNT(net_earnings_eur)         AS missing_earnings,
       COUNT(*) - COUNT(overburden_18_24)         AS missing_overburden_18_24,
       COUNT(*) - COUNT(age_leaving_home)         AS missing_age_leaving_home
FROM country_year
WHERE year = 2025;

-- 3. Breaks in series: which years have flag 'b' in net earnings? (spot the EU-wide 2024 break)
SELECT year, COUNT(*) AS geos_flagged_b          -- 27 countries + the EU average
FROM country_year
WHERE net_earnings_eur_flag = 'b'
GROUP BY year
ORDER BY year;

-- 4. Where do low-reliability values ('u') appear? Only in SMALL subgroups.
--    Survey samples shrink when you slice them (young AND below the poverty line), so Eurostat warns you.
SELECT rskpovth, age, COUNT(*) AS low_reliability_values
FROM long_overburden
WHERE flag LIKE '%u%' AND sex = 'T'
GROUP BY rskpovth, age
ORDER BY low_reliability_values DESC
LIMIT 5;

-- 5. The 2025 low-reliability values for young people below the poverty line: mark these in charts
SELECT geo, time AS year, age, value, flag, flag_label
FROM long_overburden
WHERE flag LIKE '%u%' AND sex = 'T' AND rskpovth = 'B_60' AND age IN ('Y18-24', 'Y25-29')
  AND time = '2025'
ORDER BY age, geo;

-- 6. THE DOUBLE-COUNTING TRAP. Long tables repeat each country-year once per combination of
--    dimensions. "Average overburden in Portugal in 2025" without filters is meaningless:
SELECT 'no filters (WRONG)' AS approach, COUNT(*) AS rows_used, ROUND(AVG(value), 1) AS avg_value
FROM long_overburden
WHERE geo = 'PT' AND time = '2025'
UNION ALL
SELECT 'all dimensions fixed (RIGHT)', COUNT(*), ROUND(AVG(value), 1)
FROM long_overburden
WHERE geo = 'PT' AND time = '2025' AND sex = 'T' AND rskpovth = 'TOTAL' AND age = 'TOTAL';

-- 7. Which combinations exist? Always check the dimensions of a long table first
SELECT age, age_label, COUNT(*) AS rows
FROM long_overburden
GROUP BY age, age_label
ORDER BY age;

-- 8. Same trap in net earnings: 3 currencies × 6 earnings parts × 13 household types per country-year
SELECT COUNT(*) AS rows_for_PT_2025,
       COUNT(DISTINCT currency) AS currencies,
       COUNT(DISTINCT estruct)  AS earnings_parts,
       COUNT(DISTINCT ecase)    AS household_types
FROM long_net_earn
WHERE geo = 'PT' AND time = '2025';

-- -------------------------------------------------------------------------------------
-- Further questions
--   a) Query 3: do the same for house_price_index_2015_flag. Any breaks?
--   b) Query 6: what does the "right" query give for age = 'Y18-24'? And for B_60 (below poverty line)?
--   c) Write a query that would catch a percentage above 100 anywhere in long_with_parents.
-- -------------------------------------------------------------------------------------
