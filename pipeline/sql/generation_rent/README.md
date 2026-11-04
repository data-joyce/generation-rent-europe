# Generation Rent – SQL starter queries (DuckDB)

Query the cleaned CSVs from `clean/generation-rent/` with SQL. No server needed: DuckDB is a file-based database (like SQLite, but built for analytics).

## How to run
From the project root (`DataStudy`):

```powershell
python pipeline/python/run_sql.py pipeline/sql/generation_rent/00_setup.sql          # once (and after re-running the notebook)
python pipeline/python/run_sql.py pipeline/sql/generation_rent/02_prices_vs_earnings.sql
python pipeline/python/run_sql.py "pipeline/sql/generation_rent/*.sql"               # everything, in order
```

Paths relative to `pipeline/` (e.g. `"sql/generation_rent/*.sql"`) also work. If a pattern matches no `.sql` file, the runner stops with an error.
`00_setup.sql` creates `pipeline/sql/generation_rent.duckdb`. It can always be rebuilt from the CSVs, so don't edit it by hand.
To write queries interactively, open that file in **DBeaver** (free, has a DuckDB driver) or VS Code with a DuckDB extension.
DuckDB allows only one writer at a time: close DBeaver before re-running `00_setup.sql`.

## Files
| File | Question | SQL concepts |
|---|---|---|
| `00_setup.sql` | Load the CSVs into tables | `CREATE TABLE AS`, `read_csv` |
| `01_explore.sql` | What's in the data? | `SELECT`, `WHERE`, `ORDER BY`, `GROUP BY`, `COUNT(DISTINCT)`, NULL-aware `COUNT(col)` |
| `02_prices_vs_earnings.sql` | **Have house prices outrun salaries since 2015?** | CTEs, pivot with `MAX(CASE WHEN …)`, `RANK()` |
| `03_rent_vs_salary.sql` | What share of a net salary does a capital-city flat cost? | `JOIN`, `RANK() OVER (PARTITION BY …)` |
| `04_leaving_home.sql` | **Why do young people leave home at 30 in some countries and 21 in others?** | `CASE` buckets, `corr()`, `STRING_AGG`, scalar subquery |
| `05_portugal_vs_eu.sql` | Portugal vs the EU over time | self-join, `LAG()`, `HAVING`, latest-complete-month pattern |
| `06_data_quality.sql` | Can we trust it? | uniqueness check, missing values, flags, **the double-counting trap** |

Each file ends with **"Further questions"** exercises.

## Tables
`country_year`, `city_rent`, `dim_country`, `dim_year`, `hicp_monthly`, `long_overburden`, `long_net_earn`, `long_with_parents`. Columns are described in `clean/generation-rent/README.md`.
Note: `hicp_monthly` has one row per geo × category × month, with `index_2015` and `annual_rate_pct` as separate columns (no `unit` column).

## First findings (2025 data, as of 2026-11-04)
- **Portugal leads the EU on affordability loss**: price-to-income ratio at 137 vs its long-term average (EU: 100). House prices +106% vs net earnings +33% (2015 → 2023), then another +28% for prices in 2023 → 2025.
- After removing general inflation, Portuguese house prices are 2.1× their 2015 level, the highest in the EU (just above Hungary).
- **Lisbon has the highest rent-to-salary ratio of all 26 EU capitals in the data** (1-bed flat ≈ 78% of a national average net salary in 2025). It's been #1 every year since 2020. *Caveats: EU-staff duty-station rents. Capital rent vs national wage. The drop from 105.9% (2023) to 74.6% (2024) is the earnings-series break, not cheaper rent, so compare shares only within one year. No Dutch capital in the data.*
- Young people leave home latest in Croatia, Greece, Slovakia, Spain and Italy (30+). Portugal: 28.8 (EU: 26.3).
- Counter-intuitive: countries where young people leave home **early** (Nordics, NL, DE) have **higher** housing-cost overburden among 18–24s (corr ≈ −0.38). People who move out early pay the costs themselves. Living with parents hides housing stress, which makes a good discussion point.

## Databricks / other SQL engines
Only `00_setup.sql` is DuckDB-specific (`read_csv`). On Databricks, upload the CSVs to a Volume and use `read_files(…)`. The rest is standard SQL (CTEs, window functions, `corr`). Two small differences: `STRING_AGG(x, ', ' ORDER BY x)` → `array_join(array_sort(collect_list(x)), ', ')`, and `GROUP BY ALL` works in both.
