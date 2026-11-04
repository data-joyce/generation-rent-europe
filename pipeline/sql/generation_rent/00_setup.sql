-- =====================================================================================
-- Generation Rent · 00 · Setup
-- Loads the cleaned CSVs (made by python/generation_rent_01_clean.ipynb) into DuckDB tables.
-- Run once, and again whenever you re-run the notebook. From the project root (DataStudy):
--     python pipeline/python/run_sql.py pipeline/sql/generation_rent/00_setup.sql
-- The CSV paths below are relative to pipeline/ (the runner switches into that folder).
--
-- Databricks note: there you'd upload the CSVs to a Volume and use
--   CREATE TABLE country_year AS SELECT * FROM read_files('/Volumes/.../country_year.csv', format => 'csv', header => true);
-- Everything after this file is standard SQL that also runs on Databricks.
-- =====================================================================================

-- Analysis tables (small: 1 row per country-year / city-year / country / year)
CREATE OR REPLACE TABLE country_year AS
SELECT * FROM read_csv('clean/generation-rent/country_year.csv', header = true);

CREATE OR REPLACE TABLE city_rent AS
SELECT * FROM read_csv('clean/generation-rent/city_rent.csv', header = true);

CREATE OR REPLACE TABLE dim_country AS
SELECT * FROM read_csv('clean/generation-rent/dim_country.csv', header = true);

CREATE OR REPLACE TABLE dim_year AS
SELECT * FROM read_csv('clean/generation-rent/dim_year.csv', header = true);

-- Monthly inflation: one row per geo x category x month, with the index and the annual rate in separate columns
CREATE OR REPLACE TABLE hicp_monthly AS
SELECT * FROM read_csv('clean/generation-rent/hicp_monthly.csv', header = true,
                       types = {'month': 'VARCHAR', 'date': 'DATE'});   -- keep '2026-10' as text, date as a real DATE

-- Long tables (every dimension kept, for practice with filters)
CREATE OR REPLACE TABLE long_overburden AS
SELECT * FROM read_csv('clean/generation-rent/long_overburden.csv', header = true, types = {'time': 'VARCHAR'});

CREATE OR REPLACE TABLE long_net_earn AS
SELECT * FROM read_csv('clean/generation-rent/long_net_earn.csv', header = true, types = {'time': 'VARCHAR'});

CREATE OR REPLACE TABLE long_with_parents AS
SELECT * FROM read_csv('clean/generation-rent/long_with_parents.csv', header = true, types = {'time': 'VARCHAR'});

-- Check: what got loaded?
SELECT table_name, estimated_size AS approx_rows, column_count
FROM duckdb_tables()
ORDER BY table_name;
