-- =====================================================================================
-- Generation Rent · 01 · Explore the data (SELECT, WHERE, ORDER BY, GROUP BY)
-- Goal: understand what's in the tables before asking big questions.
-- =====================================================================================

-- 1. What columns does the main table have, and what types did DuckDB pick?
DESCRIBE country_year;

-- 2. Look at a few rows: Portugal, latest years
SELECT geo, country, year, house_price_index_2015, net_earnings_eur, pct_18_34_with_parents
FROM country_year
WHERE geo = 'PT'
ORDER BY year DESC
LIMIT 5;

-- 3. How many countries and years are there? (COUNT DISTINCT)
SELECT COUNT(DISTINCT geo) AS geos,
       MIN(year)           AS first_year,
       MAX(year)           AS last_year,
       COUNT(*)            AS rows
FROM country_year;

-- 4. Coverage: how many countries have each measure, per year? COUNT(column) skips NULLs
SELECT year,
       COUNT(house_price_index_2015) AS has_house_prices,
       COUNT(net_earnings_eur)       AS has_earnings,
       COUNT(age_leaving_home)       AS has_age_leaving_home,
       COUNT(overburden_18_24)       AS has_overburden_18_24
FROM country_year
WHERE year IN (2005, 2010, 2015, 2020, 2024, 2025)
GROUP BY year
ORDER BY year;

-- 5. Latest year: where do young people leave home latest? (filter out the EU average row)
SELECT country, age_leaving_home
FROM country_year
WHERE year = 2025
  AND geo <> 'EU27_2020'
  AND age_leaving_home IS NOT NULL
ORDER BY age_leaving_home DESC, country          -- second key = fixed order when two countries tie
LIMIT 10;

-- 6. Which cities are in the city rent table, and from when? (not all are capitals: see is_capital)
SELECT city, country_geo, is_capital, MIN(year) AS first_year, MAX(year) AS last_year, COUNT(*) AS years
FROM city_rent
GROUP BY city, country_geo, is_capital
ORDER BY city;

-- -------------------------------------------------------------------------------------
-- Further questions
--   a) Change query 5 to show the 10 countries where young people leave home EARLIEST.
--   b) In query 4, add a column counting countries with pct_18_34_with_parents.
--   c) List the EU average (geo = 'EU27_2020') for every year since 2015.
-- -------------------------------------------------------------------------------------
