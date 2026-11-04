# Generation Rent – cleaned outputs

Produced by `pipeline/python/generation_rent_01_clean.ipynb` from the raw files in `datasets/eurostat-*`.
**Don't edit these by hand.** Re-run the notebook instead (it works from its own folder). Source for everything: Eurostat (CC BY 4.0), modified by cleaning and reshaping.

CSV, UTF-8 with BOM (opens correctly in Excel), comma-separated, **dot as the decimal separator**. Missing values are empty cells.
Flag columns: `b` break in series, `p` provisional, `e` estimated, `u` low reliability, `d` definition differs (combinations like `bu` are possible).
Independent QA of these files: `qa/QA_REPORT.md`.

| File | Grain | Use for |
|---|---|---|
| `country_year.csv` | 1 row per country × year (EU27 + `EU27_2020`, 2005–2025) | Main Power BI fact table |
| `city_rent.csv` | 1 row per city × year (1-bedroom flat, EUR, 2013–2025) | Rent vs net salary page |
| `hicp_monthly.csv` | 1 row per geo × category × month (EU27 + EU average, 1996-01 → 2026-10) | Inflation trend lines |
| `dim_country.csv` | 1 row per geo code (52) | Country dimension |
| `dim_year.csv` | 1 row per year, 1996–2026 | Year dimension shared by all facts |
| `long_*.csv` | Every cleaned row of each raw table, all dimensions | SQL practice and drill-downs |

## `country_year.csv` columns
| Column | Meaning |
|---|---|
| `geo`, `country`, `iso2`, `year` | Keys (`iso2` is empty for the EU average) |
| `house_price_index_2015` | House price index, all dwellings, 2015 = 100 |
| `real_house_price_index_2015` | House prices relative to general inflation (HPI ÷ HICP all-items × 100) |
| `net_earnings_eur`, `net_earnings_pps` | Annual net earnings, single person, no children, average wage (EUR / purchasing power standard). **EU-wide break in 2024** |
| `price_to_income_vs_lt_avg` | House price-to-income ratio vs the country's long-term average (100 = normal) |
| `overburden_total`, `overburden_18_24`, `overburden_25_29` | % of people spending > 40% of disposable income on housing |
| `age_leaving_home` | Average age of leaving the parental home |
| `pct_18_34_with_parents` | % of 18–34-year-olds living with parents |
| `hicp_rent_index`, `hicp_all_index` | Annual average HICP index (2015 = 100) for actual rentals / all items (full years only) |
| `*_flag` | Eurostat flag for the column before it |

## `city_rent.csv` columns
`city_geo`, `city`, `country_geo`, `is_capital` (true for `_CAP` codes), `year`, `rent_1bed_eur_month`, `net_salary_eur_month` (national net earnings ÷ 12), `rent_share_of_net_salary_pct` (rounded to 1 decimal), `net_earnings_eur_flag`.

**Caveats:** rents come from Eurostat's correction coefficients for **EU officials' duty stations**, not the average local rent. The share compares a **city** rent with a **national** average salary, and can exceed 100% (13 city-years, e.g. Riga 2013, Lisbon 2023). Because of the 2024 earnings break, compare shares **within one year only**. Not every city is a capital (`_DEL` = other duty stations: Munich, Bonn, Karlsruhe, Varese, Geneva, Culham, Den Haag). **The Netherlands has no capital in the data**, so there are 26 EU capitals. 90 city-years have no national earnings value (non-EU countries, UK from 2020, Cyprus 2013/2015/2016) and therefore no share.

## `hicp_monthly.csv` columns
`geo`, `coicop18`, `coicop18_label`, `month` (`YYYY-MM` text), `date` (first day of the month, a real date), `year`, `index_2015` (index, 2015 = 100), `index_2015_flag`, `annual_rate_pct` (change vs the same month a year earlier, %), `annual_rate_pct_flag`.
The newest month is often a flash estimate that covers only a few countries and categories (2026-10: 21 values). Use the latest **complete** month (see `sql/generation_rent/05_portugal_vs_eu.sql`).

## `dim_country.csv` / `dim_year.csv` columns
- `dim_country`: `geo`, `country`, `is_eu27`, `is_aggregate` (EU / euro area / EEA groupings), `iso2` (ISO code for maps: Greece `EL` → `GR`, UK → `GB`; empty for aggregates), `in_country_year` (true for the 28 geos in the main table: use it to filter slicers).
- `dim_year`: `year`, `earnings_series` (`up to 2023` / `2024+ (new method)`, to split earnings-based lines at the break), `in_country_year` (2005–2025).

## Coverage gaps (disclose in the dashboard)
- **Greece: no house price index in any year**, so no real house price index either.
- House prices in 2005–2009 are missing for several countries (marked "not for publication" by Eurostat); in 2005 only 13 of 27 countries have a value.
- **Cyprus: no net earnings 2008–2013 and 2015–2016.**
- France: no housing-cost overburden values for 2021.
- `long_net_earn`: Türkiye's EUR values for 2000–2003 are in the billions (old lira, before the 2005 redenomination). Not used in any analysis table.

## Using these files in Power BI
1. **Locale**: the files use dot decimals. If numbers come in ~100× too big, set *File → Options and settings → Options → Regional settings → Locale for import = English*, or use *Change type → Using locale → English*. Check: Finland 2018 `house_price_index_2015` must read **103.34**.
2. **Relationships**: `dim_country[geo]` 1→* `country_year[geo]`, `city_rent[country_geo]`, `hicp_monthly[geo]`; `dim_year[year]` 1→* `country_year[year]`, `city_rent[year]`, `hicp_monthly[year]`. Don't relate the facts to each other.
3. **Summarize by = None** on every value column: they are indices, rates, averages and ages, so adding them up is meaningless. Build DAX measures instead (e.g. `DIVIDE(SUM(city_rent[rent_1bed_eur_month]), SUM(city_rent[net_salary_eur_month])) * 100` at city-year level).
4. Hide `country` and `iso2` in `country_year` and use the ones from `dim_country`.
