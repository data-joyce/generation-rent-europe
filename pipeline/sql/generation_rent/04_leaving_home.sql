-- =====================================================================================
-- Generation Rent · 04 · Headline question 2
-- "Why do young Europeans leave home at 30 in some countries and at 21 in others?"
-- New concepts: CASE buckets, corr() aggregate, comparing to the EU average with a subquery
--
-- Correlation ≠ causation: culture, unemployment and student support matter too.
-- Use this as "the data is consistent with…", never "housing costs cause…".
-- =====================================================================================

-- 1. Latest year side by side: age leaving home, % living with parents, housing stress of 18-24s
SELECT country,
       age_leaving_home,
       pct_18_34_with_parents,
       overburden_18_24,
       price_to_income_vs_lt_avg,
       CASE
           WHEN age_leaving_home >= 30 THEN '30+ (late)'
           WHEN age_leaving_home >= 25 THEN '25-29'
           ELSE 'under 25 (early)'
       END AS leaving_home_group
FROM country_year
WHERE year = 2025
  AND geo <> 'EU27_2020'
  AND age_leaving_home IS NOT NULL
ORDER BY age_leaving_home DESC, country;

-- 2. Averages per group (does a later age go with more housing stress or worse affordability?)
WITH latest AS (
    SELECT *,
           CASE WHEN age_leaving_home >= 30 THEN '1. 30+'
                WHEN age_leaving_home >= 25 THEN '2. 25-29'
                ELSE '3. under 25' END AS grp
    FROM country_year
    WHERE year = 2025 AND geo <> 'EU27_2020' AND age_leaving_home IS NOT NULL
)
SELECT grp,
       COUNT(*)                                 AS countries,
       STRING_AGG(geo, ', ' ORDER BY geo)       AS which,
       ROUND(AVG(pct_18_34_with_parents), 1)    AS avg_pct_with_parents,
       ROUND(AVG(overburden_18_24), 1)          AS avg_overburden_18_24,
       ROUND(AVG(net_earnings_pps), 0)          AS avg_net_earnings_pps
FROM latest
GROUP BY grp
ORDER BY grp;

-- 3. Correlations across countries (-1 … +1). Which factor moves most with the age of leaving home?
--    corr() silently skips rows where either value is NULL, so count the pairs it really used
--    (regr_count) instead of COUNT(*). In 2025 all three are 27; in other years they can differ.
SELECT ROUND(corr(age_leaving_home, net_earnings_pps), 2)          AS vs_net_earnings_pps,
       ROUND(corr(age_leaving_home, overburden_18_24), 2)          AS vs_overburden_18_24,
       ROUND(corr(age_leaving_home, price_to_income_vs_lt_avg), 2) AS vs_price_to_income,
       regr_count(age_leaving_home, net_earnings_pps)              AS n_pps,
       regr_count(age_leaving_home, overburden_18_24)              AS n_overburden,
       regr_count(age_leaving_home, price_to_income_vs_lt_avg)     AS n_price_to_income
FROM country_year
WHERE year = 2025 AND geo <> 'EU27_2020';

-- 4. Countries above / below the EU average age (scalar subquery)
SELECT country,
       age_leaving_home,
       ROUND(age_leaving_home - (SELECT age_leaving_home FROM country_year
                                 WHERE geo = 'EU27_2020' AND year = 2025), 1) AS years_vs_eu_avg
FROM country_year
WHERE year = 2025 AND geo <> 'EU27_2020' AND age_leaving_home IS NOT NULL
ORDER BY years_vs_eu_avg DESC, country;

-- -------------------------------------------------------------------------------------
-- Further questions
--   a) Query 3: run it for 2015 instead of 2025. Are the relationships stable?
--   b) Query 1: add sex differences. You'll need the long table long_with_parents
--      (filter age = 'Y18-34', compare sex = 'F' vs 'M').
--   c) Why could net earnings in PPS correlate with leaving home earlier? Write 2 sentences.
-- -------------------------------------------------------------------------------------
